FROM apache/airflow:3.3.1

# dbt runs inside the same container as Airflow. A separate container would
# isolate them better, but would require Docker-in-Docker for the operator —
# more moving parts than this project needs.
RUN pip install --no-cache-dir dbt-postgres==1.9.0