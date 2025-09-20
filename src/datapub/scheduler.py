import os
import time
import json
import logging
from datetime import datetime
from typing import Optional, Tuple

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from datapub.api.main import _run_extractor_sync, _run_processor_sync
import datapub.cli as datapub_cli
from prometheus_client import Counter, Histogram, Gauge, start_http_server


def env(name: str, default: Optional[str] = None) -> Optional[str]:
    return os.environ.get(name, default)


def _get_cron_pipeline() -> str:
    # Single CRON for the entire pipeline
    return env("CRON_PIPELINE") or env("CRON_ALL") or env("CRON") or "0 3 * * *"


def _get_dates_for_entity(entity: str) -> Tuple[Optional[str], Optional[str]]:
    key_start_std = f"{entity.upper()}_START"
    key_end_std = f"{entity.upper()}_END"
    key_start_alt = f"{entity.upper().replace('_', '')}_START"
    key_end_alt = f"{entity.upper().replace('_', '')}_END"
    # Allow global START/END as default
    start = env(key_start_std) or env(key_start_alt) or env("START")
    end = env(key_end_std) or env(key_end_alt) or env("END")
    return start, end


def _parse_cron(cron: str) -> CronTrigger:
    parts = cron.split()
    if len(parts) != 5:
        raise ValueError(f"Invalid CRON expression: {cron}")
    minute, hour, day, month, dow = parts
    return CronTrigger(minute=minute, hour=hour, day=day, month=month, day_of_week=dow)


def _job_pipeline():
    # ENTITIES can limit which entities to run; defaults to all extractors
    selected = env("ENTITIES")
    if selected:
        entities = [e.strip() for e in selected.split(",") if e.strip()]
    else:
        entities = list(datapub_cli.extractors.keys())

    jlog("info", "pipeline_start", entities=entities)
    for entity in entities:
        start, end = _get_dates_for_entity(entity)
        try:
            t0 = time.perf_counter()
            jlog("info", "extract_start", entity=entity, start=start, end=end)
            _run_extractor_sync(entity, "diario", start, end, True)
            dur = time.perf_counter() - t0
            MET_ENTITY_EXTRACT_SECONDS.labels(entity=entity).observe(dur)
            MET_LAST_EXTRACT_SUCCESS.labels(entity=entity).set_to_current_time()
            jlog("info", "extract_success", entity=entity, duration_seconds=round(dur, 3))
        except Exception as e:
            MET_ENTITY_EXTRACT_ERRORS.labels(entity=entity).inc()
            jlog("error", "extract_error", entity=entity, error=str(e))

        if entity in datapub_cli.processors:
            try:
                t1 = time.perf_counter()
                jlog("info", "process_start", entity=entity, start=start, end=end)
                _run_processor_sync(entity, "diario", start, end)
                durp = time.perf_counter() - t1
                MET_ENTITY_PROCESS_SECONDS.labels(entity=entity).observe(durp)
                MET_LAST_PROCESS_SUCCESS.labels(entity=entity).set_to_current_time()
                jlog("info", "process_success", entity=entity, duration_seconds=round(durp, 3))
            except Exception as e:
                MET_ENTITY_PROCESS_ERRORS.labels(entity=entity).inc()
                jlog("error", "process_error", entity=entity, error=str(e))

    MET_PIPELINE_RUNS.inc()
    MET_LAST_PIPELINE_RUN.set_to_current_time()
    jlog("info", "pipeline_end")


def build_scheduler() -> BlockingScheduler:
    sched = BlockingScheduler(timezone="UTC")
    cron = _get_cron_pipeline()
    trigger = _parse_cron(cron)
    sched.add_job(_job_pipeline, trigger, id="pipeline", replace_existing=True)
    return sched


def main():
    _setup_logging()
    jlog("info", "scheduler_start")
    # Start Prometheus exporter HTTP server
    port = int(env("METRICS_PORT", "9100"))
    start_http_server(port)
    jlog("info", "metrics_server_listen", port=port)
    sched = build_scheduler()
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        jlog("info", "scheduler_stop")


# ----------------- Logging (JSON) -----------------
_LOGGER = logging.getLogger("datapub.scheduler")


def _setup_logging():
    level = env("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=level, format="%(message)s")


def jlog(level: str, event: str, **fields):
    rec = {"ts": datetime.utcnow().isoformat() + "Z", "event": event, **fields}
    msg = json.dumps(rec, ensure_ascii=False)
    getattr(_LOGGER, level, _LOGGER.info)(msg)


# ----------------- Metrics -----------------
MET_PIPELINE_RUNS = Counter("datapub_pipeline_runs_total", "Total de execuções da pipeline")
MET_LAST_PIPELINE_RUN = Gauge("datapub_pipeline_last_run_timestamp", "Época do último run da pipeline")

MET_ENTITY_EXTRACT_SECONDS = Histogram(
    "datapub_entity_extract_seconds",
    "Duração da extração por entidade",
    labelnames=("entity",),
)
MET_ENTITY_PROCESS_SECONDS = Histogram(
    "datapub_entity_process_seconds",
    "Duração do processamento por entidade",
    labelnames=("entity",),
)
MET_ENTITY_EXTRACT_ERRORS = Counter(
    "datapub_entity_extract_errors_total",
    "Falhas na extração por entidade",
    labelnames=("entity",),
)
MET_ENTITY_PROCESS_ERRORS = Counter(
    "datapub_entity_process_errors_total",
    "Falhas no processamento por entidade",
    labelnames=("entity",),
)
MET_LAST_EXTRACT_SUCCESS = Gauge(
    "datapub_last_extract_success_timestamp",
    "Época do último sucesso de extração",
    labelnames=("entity",),
)
MET_LAST_PROCESS_SUCCESS = Gauge(
    "datapub_last_process_success_timestamp",
    "Época do último sucesso de processamento",
    labelnames=("entity",),
)


if __name__ == "__main__":
    main()
