"""The BLOCKS pilot must read the DRV block, and must not call a block hardened without it.

Section 13 item 14 of docs/CHIP_ARCHITECTURE_DESIGN.md opened against
``tools/run_abi3_physical.py``: it built its ``closed`` verdict from setup,
hold, DRC and antenna and never read the max-slew/max-cap/max-fanout block
ORFS writes beside them.  The same defect appeared independently in
``tools/run_abi3_tile64_blocks_pilot.py``, for two compounding reasons: it
read metrics only from ``reports/.../metadata.json``, which the block leg's
``build_macros`` goal never writes, and its key map had no DRV entries at all.

It was not theoretical.  The two LQ8 abstracts the pilot hardened carry 462
and 423 max-slew violations in their own ``6_report.json``, and the ``.lib``
the parent's timing flows through was characterised from those netlists.

These tests pin the refusals and the one shape that is accepted.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "blocks_pilot", ROOT / "tools/run_abi3_tile64_blocks_pilot.py"
)
pilot = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(pilot)

FINISH = {
    "finish__design__instance__count__stdcell": 238788,
    "finish__design__instance__area__stdcell": 27_800.0,
    "finish__timing__setup__ws": 8733.39,
    "finish__timing__hold__ws": 39.3,
    "detailedroute__route__drc_errors": 0,
}


def _logs(tmp_path: Path, **drv) -> tuple[Path, Path]:
    logs = tmp_path / "logs"
    logs.mkdir()
    body = dict(FINISH)
    body.update(drv)
    (logs / "6_report.json").write_text(json.dumps(body))
    reports = tmp_path / "reports"          # deliberately empty: build_macros writes none
    reports.mkdir()
    return reports, logs


def test_metrics_are_recovered_when_metadata_json_is_absent(tmp_path):
    """build_macros writes no metadata.json; the metrics still exist in logs/."""
    reports, logs = _logs(tmp_path, finish__timing__drv__max_slew=0,
                          finish__timing__drv__max_cap=0,
                          finish__timing__drv__max_fanout=0)
    got = pilot.metrics_of(reports, logs)
    assert got is not None, "the leg's metrics were silently dropped"
    assert got["final_cells"] == 238788
    assert "metadata.json absent" in got["metrics_source"]


def test_a_slew_violating_block_is_not_signal_integrity_clean(tmp_path):
    reports, logs = _logs(tmp_path, finish__timing__drv__max_slew=462,
                          finish__timing__drv__max_cap=0,
                          finish__timing__drv__max_fanout=0)
    got = pilot.metrics_of(reports, logs)
    assert got["signal_integrity_clean"] is False
    assert "462" in got["signal_integrity_reason"]


def test_an_unread_drv_block_is_not_clean_it_is_unknown(tmp_path):
    """Absence of a count is not a zero count."""
    reports, logs = _logs(tmp_path)          # no DRV keys at all
    got = pilot.metrics_of(reports, logs)
    assert got["signal_integrity_clean"] is None
    assert "absent" in got["signal_integrity_reason"]


def test_a_clean_block_is_clean(tmp_path):
    reports, logs = _logs(tmp_path, finish__timing__drv__max_slew=0,
                          finish__timing__drv__max_cap=0,
                          finish__timing__drv__max_fanout=0)
    got = pilot.metrics_of(reports, logs)
    assert got["signal_integrity_clean"] is True


def test_metadata_json_still_wins_when_the_goal_wrote_one(tmp_path):
    reports, logs = _logs(tmp_path, finish__timing__drv__max_slew=462)
    body = dict(FINISH)
    body["finish__design__instance__count__stdcell"] = 111
    body["finish__timing__drv__max_slew"] = 0
    body["finish__timing__drv__max_cap"] = 0
    body["finish__timing__drv__max_fanout"] = 0
    (reports / "metadata.json").write_text(json.dumps(body))
    got = pilot.metrics_of(reports, logs)
    assert got["final_cells"] == 111
    assert got["signal_integrity_clean"] is True
    assert got["metrics_source"].endswith("metadata.json")


@pytest.mark.parametrize("work", ["work_blocks", "work_blocks_m5"])
def test_the_two_hardened_LQ8_abstracts_are_recorded_as_not_clean(work):
    """The real work directories, if they are still on this machine.

    Not a synthetic case: these are the netlists whose .lib the parent's
    timing flowed through.  Skipped rather than failed when the scratch has
    been cleared, because the tests above already pin the behaviour.
    """
    base = Path(
        "/tmp/claude-1000/-home-ubuntu-OpenTallas/ab3ca2fa-9fc4-4b10-a488-2763d0029546"
        f"/scratchpad/tile/phys/{work}"
    )
    logs = base / "logs/asap7/opentallas_a3_tile64_asap7_ot_a3_lq8/base"
    if not (logs / "6_report.json").is_file():
        pytest.skip(f"{work} work directory is not present")
    got = pilot.metrics_of(base / "reports/asap7/opentallas_a3_tile64_asap7_ot_a3_lq8/base", logs)
    assert got is not None
    assert got["max_slew_violations"] > 0
    assert got["signal_integrity_clean"] is False
