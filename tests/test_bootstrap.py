from money import bootstrap_status


def test_bootstrap_status() -> None:
    assert bootstrap_status() == "ok"
