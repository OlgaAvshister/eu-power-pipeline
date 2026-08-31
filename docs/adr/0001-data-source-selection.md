# ADR-0001: Use Energy-Charts API as the data source

## Status
Accepted, 2026-08-27

## Context

Electricity generation is a continuous process; data about it is published
every 15 minutes. Such data is only valuable in its current state.

Regular updates also shape the engineering problems involved: data arrives
in batches, is published with a delay and is revised retroactively. This
calls for incremental loading, idempotency and scheduled orchestration.

Constraints: free tooling only, local deployment via docker-compose,
publicly and legally available data.

## Decision

- **Source:** Energy-Charts API (Fraunhofer ISE), `/public_power` endpoint.
- **API version:** v1 — the format based on `unix_seconds` and `production_types`
  arrays. Chosen for maturity: its behaviour is predictable and third-party
  clients built on it can be used as a reference. v2 exists and may be more
  convenient — it exposes `available_from` as an explicit data availability
  boundary and includes units in metadata — but it has not been evaluated.
  This decision may be revisited in a separate ADR.
- **Countries:** Germany and France. They provide contrasting power systems —
  France runs on nuclear, Germany on coal; France exports electricity, Germany
  imports it. As a result the sets of indicators differ between responses, which
  forces a data model resilient to a variable set of fields.
- **License:** CC BY 4.0. Requires attribution. The attribution notice is placed
  in the root README and in `docs/samples/README.md`.

## Observed source behaviour

All observations below were made manually against the live API in August 2026.

1. **Columnar response format.** The response contains a `unix_seconds` array
   and a `production_types` array of `{name, data[]}` objects. Timestamps and
   values are linked by array position only — there are no explicit pairs.

2. **Timestamps are UTC unix seconds.** A `start` parameter without an explicit
   timezone is interpreted as UTC, not as local time of the requested country.

3. **Resolution is 15 minutes** for both DE and FR, giving 96 points per full day.

4. **The requested interval is inclusive on both ends.** A one-hour request
   returned 5 points instead of 4 (00:00, 00:15, 00:30, 00:45, 01:00).

5. **The set of indicators depends on the country.** Germany returns 21 series,
   France 19. Germany has no `Nuclear` (phased out in 2023); France has no coal
   series but has `Battery` and `Battery Consumption`. The set also changes over time — Germany's 2015 data includes `Nuclear`, which disappeared after the 2023 phase-out.

6. **Indicators are heterogeneous within a single array.** Generation in MW,
   consumption (`Load`), signed cross-border flow, storage consumption
   (negative values) and percentages all share the same structure.

7. **Responses are silently truncated.** A request for a full day returned only
   34 points — data ends where publication ends. No error, no warning, no
   indication in the payload.

8. **`null` means "not yet published", not zero.** `Load` and derived series lag
   generation by one interval and are padded with `null` to keep array lengths
   aligned.

9. **The data contains a verifiable internal relation:**
   `Load − Wind onshore − Wind offshore − Solar = Residual load`.
   Confirmed for both DE and FR within rounding error.

10. **Energy balance does not close.** Total generation plus imports minus storage
    consumption falls short of reported `Load` by roughly 2.7 GW for Germany.
    Cause not investigated. Hypothesis: `public_power` covers utility-scale
    generation only, while industrial self-generation is included in load but not
    in generation. **Not verified.**

11. **`deprecated` flag is `false`** for the v1 `/public_power` endpoint.

12. **No authentication required**, but the API does rate-limit. Manual
    exploration never hit a limit; a backfill fanning out to 14 concurrent
    requests received HTTP 429. Concurrency is capped and 429 is handled
    with a Retry-After pause.

13. **Published values are revised retroactively.** A full-day response captured on 2026-08-19 was compared with the same request re-issued eight days later. The array grew from 34 to 96 points, and previously published values changed by roughly 0.01% (e.g. Load[0]: 40274.8 → 40270.4). Derived percentage series shifted more noticeably (Renewable share of generation[0]: 50.8 → 49.4). Both snapshots are stored in `docs/samples/` for reference.

14. **Publication delay differs by country.** On 2026-08-31 Germany's data
    was available up to roughly four hours before the request time, while
    France returned HTTP 404 for the same window — no data at all. A single
    lookback window has to accommodate the slowest country.

15. **The API returns HTTP 404 when no data exists for the requested window**,
    rather than an empty response. This is indistinguishable from a genuine
    error such as a wrong country code, so the pipeline treats it as
    "no data yet" but counts consecutive occurrences and fails after six.

    
## Consequences

### What we get for free

- No authentication, no registration, no quota management — CI can run
  without secrets.
- History available at least back to 2015 at the same 15-minute resolution,
  enabling a meaningful backfill. Earliest available date not determined.
- A verifiable internal relation in the data (see observation 9) that can be
  turned into a real data quality test, not a formal one.
- Open license, so the repository can be public with proper attribution.

### What we must build because of this source

- **Unpivot in the staging layer.** The columnar format cannot be loaded as is;
  timestamps and values are linked by position and must be turned into rows.
- **Long-format fact table.** The set of indicators varies by country, so the
  production type must be a value in a row, not a column name. Adding a country
  must not require a schema change.
- **Merge-based loading with a lookback window.** Data is published with a delay
  and revised afterwards, and requested intervals overlap on their boundaries.
  A plain INSERT would produce both duplicates and permanent gaps.
- **UTC storage with conversion at the presentation layer**, to avoid ambiguity
  around daylight saving time transitions.
- **A production type dimension** carrying category and unit, since generation,
  load, signed flows and percentages share the same array.
- **Row count reconciliation on load.** Truncated responses are silent, so the
  loader must compare requested and received point counts and log the difference.
- **An `accepted_values` test on production types**, so that a new or renamed
  indicator fails the pipeline instead of passing unnoticed.

### Open risks

- **Single point of failure.** The project depends on one free API with no SLA.
  If it changes or disappears, the pipeline stops. Mitigation: raw responses are
  persisted, so downstream layers can be rebuilt from history.
- **v1 may eventually be deprecated** in favour of v2. The `deprecated` flag is
  currently `false` and is captured on load so the change would be detected.
- **The energy balance discrepancy is not explained** (observation 10). Metrics
  built on total generation may be misleading until the cause is understood.
