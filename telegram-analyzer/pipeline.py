import subprocess
from dagster import op, job, ScheduleDefinition, Definitions, In, Nothing


def run_command(command, op_context):
    """
    Shared helper: runs a shell command, streams output into Dagster's
    logs, and raises an error if the command fails (non-zero exit code).
    """
    op_context.log.info(f"Running: {command}")

    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
    )

    # Always log both streams, so failures are debuggable from the Dagster UI
    if result.stdout:
        op_context.log.info(result.stdout)
    if result.stderr:
        op_context.log.warning(result.stderr)

    if result.returncode != 0:
        raise Exception(f"Command failed with exit code {result.returncode}: {command}")

    return result.returncode


@op
def scrape_telegram_data(context):
    """Runs the Telegram scraper - pulls messages and images from all configured channels."""
    run_command("python scrape_messages.py", context)


@op(ins={"start": In(Nothing)})
def load_raw_to_postgres(context):
    """Loads the scraped JSON data lake into raw.telegram_messages in Postgres."""
    run_command("python load_to_postgres.py", context)


@op(ins={"start": In(Nothing)})
def run_dbt_transformations(context):
    """Runs all dbt models (staging + marts) to rebuild the star schema."""
    run_command("dbt run --project-dir medical_warehouse --profiles-dir C:/Users/HP/.dbt", context)


@op(ins={"start": In(Nothing)})
def run_yolo_enrichment(context):
    """Runs YOLO object detection on downloaded images, then loads results into Postgres."""
    run_command("python src/yolo_detect.py", context)
    run_command("python load_yolo_to_postgres.py", context)


@job
def telegram_pipeline_job():
    """
    The full workflow execution order handled via explicit sequential steps.
    """
    scraped = scrape_telegram_data()
    loaded = load_raw_to_postgres(start=scraped)
    transformed = run_dbt_transformations(start=loaded)
    run_yolo_enrichment(start=transformed)


# Run automatically every day at 6:00 AM
daily_schedule = ScheduleDefinition(
    job=telegram_pipeline_job,
    cron_schedule="0 6 * * *",  # Minute Hour Day Month Day-of-week
)

defs = Definitions(
    jobs=[telegram_pipeline_job],
    schedules=[daily_schedule],
)