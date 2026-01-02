import os


def test_build_scheduler_single_pipeline_job(monkeypatch):
    monkeypatch.setenv("CRON_PIPELINE", "0 1 * * *")

    from datapub.scheduler import build_scheduler

    sched = build_scheduler()
    try:
        jobs = {j.id for j in sched.get_jobs()}
        assert jobs == {"pipeline"}
    finally:
        sched.shutdown(wait=False)
