from datetime import timedelta

import pendulum
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import dag

DBT_DIR = "/opt/airflow/dbt_power"

DBT_ENV = {
    "POSTGRES_HOST": "postgres",
    "POSTGRES_DB": "{{ var.value.get('postgres_db', 'power') }}",
    "POSTGRES_USER": "{{ var.value.get('postgres_user', 'power') }}",
    "POSTGRES_PASSWORD": "{{ var.value.get('postgres_password', 'power_local_pw') }}",
}


@dag(
    dag_id="dbt_transform",
    schedule="15 * * * *",
    start_date=pendulum.datetime(2026, 8, 30, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    default_args={
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["transform", "dbt"],
)
def dbt_transform():
    # Runs 15 minutes past the hour, after the ingestion DAG has finished.
    # A time offset is used rather than a cross-DAG dependency because the
    # transformations are safe to run on unchanged data.

    build = BashOperator(
        task_id="dbt_build",
        bash_command=(
            f"cd {DBT_DIR} && "
            "dbt build --profiles-dir . --target dev"
        ),
        env=DBT_ENV,
        append_env=True,
    )

    snapshot = BashOperator(
        task_id="dbt_snapshot",
        bash_command=(
            f"cd {DBT_DIR} && "
            "dbt snapshot --profiles-dir . --target dev"
        ),
        env=DBT_ENV,
        append_env=True,
    )

    build >> snapshot


dbt_transform()