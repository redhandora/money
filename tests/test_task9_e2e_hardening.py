from money.orchestration.validate_task9 import run_task9_validation


def test_task9_matrix_happy_path_covers_all_locales_modes_and_platforms() -> None:
    payloads = run_task9_validation()
    matrix = payloads["task-9-e2e-matrix.json"]

    assert matrix["checks"]["route_count_matches_full_matrix"] is True
    assert matrix["checks"]["all_routes_publish_success"] is True
    assert matrix["checks"]["happy_path_passes_all_locales"] is True
    assert set(matrix["happy_path_by_locale"].keys()) == {"EN-US", "EN-SEA", "JA-JP"}
    assert all(matrix["happy_path_by_locale"].values())


def test_task9_critical_gates_and_edge_cases_are_all_green() -> None:
    payloads = run_task9_validation()

    edge_cases = payloads["task-9-edge-cases.json"]
    qc = payloads["task-9-qc-thresholds.json"]
    fidelity = payloads["task-9-fidelity-gate.json"]
    transformation = payloads["task-9-transformation-gate.json"]
    release = payloads["task-9-release-gate.json"]

    assert all(edge_cases["checks"].values())
    assert qc["checks"]["a_mode_reuse_guard_passes"] is True
    assert qc["checks"]["all_thresholds_pass"] is True
    assert fidelity["checks"]["fidelity_gate_pass"] is True
    assert transformation["checks"]["transformation_gate_pass"] is True
    assert release["status"] == "pass"
    assert all(release["checks"].values())
