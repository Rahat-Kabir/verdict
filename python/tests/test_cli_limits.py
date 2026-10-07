"""Reject invalid call limits before starting a benchmark."""

import pytest

from verdict_router.cli import main


@pytest.mark.parametrize(
    "argument,value",
    [("--limit", "0"), ("--limit", "-1"), ("--concurrency", "0")],
)
def test_invalid_limits_do_not_start_benchmark(monkeypatch, capsys, argument, value):
    def unexpected_run(**options):
        pytest.fail("Invalid limits must not start a benchmark")

    monkeypatch.setattr("verdict_router.cli.run_bench", unexpected_run)
    with pytest.raises(SystemExit) as exception:
        main(["bench", argument, value])
    assert exception.value.code == 2
    assert f"{argument} must be at least 1" in capsys.readouterr().err
