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


# ---------------------------------------------------------------------------
# The repair the item asks for: set_max_transition from the corner's own
# liberty plus ORFS SLEW_MARGIN, reaching BOTH the SDC and the config.mk.
# ---------------------------------------------------------------------------


def test_without_the_flags_the_sdc_is_what_every_earlier_record_carried():
    """No flag given must change nothing: the earlier pilot records stay reproducible."""
    text = pilot.sdc_text(16.0)
    assert "set_max_fanout 32 [current_design]" in text
    assert "set_max_transition" not in text


def test_the_max_transition_limit_is_read_from_the_liberty_not_typed():
    """`library` must resolve to the smallest default_max_transition the corner declares."""
    view = pilot.PHYSICAL_VIEWS["asap7"]
    corner = view["corners"][view["default_corner"]]
    constraints = pilot.resolve_signal_integrity_constraints(view, corner, "library", "default", 40.0)
    declared = [
        e["default_max_transition"]
        for e in constraints["library_default_max_transition"]
        if e["default_max_transition"] is not None
    ]
    assert declared, "the corner's liberty files declare no default_max_transition"
    assert constraints["max_transition_library_units"] == min(declared)
    assert f"set_max_transition {min(declared):g} [current_design]" in pilot.sdc_text(16.0, constraints)


def test_the_slew_margin_reaches_the_block_config_not_only_the_parent(tmp_path):
    """SLEW_MARGIN is what repairs the extraction gap, and the BLOCK is the leg that routes."""
    view = pilot.PHYSICAL_VIEWS["asap7"]
    corner = view["corners"][view["default_corner"]]
    constraints = pilot.resolve_signal_integrity_constraints(view, corner, "library", "default", 40.0)
    configs = pilot.write_configs(tmp_path, 16.0, 35, 0.60, "5 5", constraints=constraints)
    assert "export SLEW_MARGIN = 40" in configs["block"]
    assert "export SLEW_MARGIN = 40" in configs["parent"]
    assert "set_max_transition" in (tmp_path / pilot.BLOCK_TOP / "constraint.sdc").read_text()


def test_no_margin_means_no_slew_margin_export(tmp_path):
    configs = pilot.write_configs(tmp_path, 16.0, 35, 0.60, "5 5", constraints=None)
    assert "SLEW_MARGIN" not in configs["block"]
    assert "SLEW_MARGIN" not in configs["parent"]
