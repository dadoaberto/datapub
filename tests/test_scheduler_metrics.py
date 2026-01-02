def test_pipeline_metrics_increment(monkeypatch):
    # Ensure deterministic entities from conftest
    import datapub.scheduler as sch

    # Snapshot counters
    before_runs = sch.MET_PIPELINE_RUNS._value.get()

    # Mock executor functions to avoid heavy work
    calls = {"extract": [], "process": []}

    def fake_extract(entity, tipo, start, end, headless):
        calls["extract"].append(entity)

    def fake_process(entity, tipo, start, end):
        calls["process"].append(entity)

    monkeypatch.setattr(sch, "_run_extractor_sync", fake_extract)
    monkeypatch.setattr(sch, "_run_processor_sync", fake_process)

    # Run pipeline once
    sch._job_pipeline()

    # Validate increments
    after_runs = sch.MET_PIPELINE_RUNS._value.get()
    assert after_runs == before_runs + 1

    # From conftest: entities include al_pa, al_go for extract; only al_pa for process
    assert set(calls["extract"]) >= {"al_pa", "al_go"}
    assert "al_pa" in calls["process"]
    assert "al_go" not in calls["process"]

