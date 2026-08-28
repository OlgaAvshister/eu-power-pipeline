# EU Power Pipeline

![CI](https://github.com/OlgaAvshister/eu-power-pipeline/actions/workflows/ci.yml/badge.svg)

End-to-end data pipeline for European electricity generation: scheduled ingestion from a public API, warehouse modelling with dbt, data quality tests and a dashboard. Runs locally via docker-compose.

## Dashboard

![Dashboard](docs/screenshots/dashboard.png)

## Architecture

```mermaid
flowchart LR
    API[Energy-Charts API<br/>public_power] -->|hourly, 6h lookback| EX[Python extractor]
    EX --> RAW[(raw.public_power<br/>JSONB + load metadata)]
    RAW --> STG1[stg_public_power<br/>JSON unpivot]
    STG1 --> STG2[stg_public_power_deduped<br/>row_number dedup]
    SEED[production_types<br/>seed] --> STG3
    STG2 --> STG3[stg_public_power_enriched<br/>join dimension]
    STG3 --> FCT[(fct_power_generation<br/>incremental, merge)]
    FCT --> BI[Metabase dashboard]

    AF[Airflow scheduler] -.orchestrates.-> EX
    TESTS[dbt tests] -.validate.-> FCT
```

## Stack

- **Ingestion:** Python, requests
- **Orchestration:** Airflow 3.3 (LocalExecutor)
- **Warehouse:** PostgreSQL 16
- **Transformations:** dbt 1.12
- **BI:** Metabase
- **CI:** GitHub Actions (ruff, dbt build)
- **Infrastructure:** docker-compose