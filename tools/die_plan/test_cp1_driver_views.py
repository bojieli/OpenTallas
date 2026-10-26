"""CP1 proof harness driver views (COORD 2026-10-25 23:26 ruling (3)): a cut-out proof die keeps an explicit registered
upstream driver view for every die-edge input the FULL plan drives from a partition; under io_hold sender_min that
input takes the driver's guaranteed output-min instead of the -tol fallback.  Real die-edge inputs keep the fallback;
legacy mode is unchanged."""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import pair  # noqa: E402
import schema  # noqa: E402

FULL = json.loads((HERE / "examples" / "s81_pair" / "s81_pair_plan.json").read_text())


def _cut():
    """FULL with pfb removed from the harness view of port r: r now enters pfa from the die edge (as pair.py does)."""
    raw = copy.deepcopy(FULL)
    for q in raw["ports"]:
        if q["id"] == "r":
            q["src"] = {"part": schema.DIE_PART, "bus": "io_r"}
    return raw


def test_views_only_for_partition_driven_inputs():
    dv = pair.upstream_driver_views(_cut(), FULL)
    assert set(dv) == {"r"}                        # din / z0 come from the real die edge in FULL too
    v = dv["r"]
    assert (v["part"], v["type"], v["bus"]) == ("pfb", "fb", "r_o")
    assert v["out_hold_guarantee_ps"] == 12.5 and v["basis"] == "plan contract"


def test_sender_min_uses_driver_view_and_schema_accepts():
    raw = _cut()
    raw["clock"]["io_hold"] = "sender_min"
    assert gen_phys.input_hold_min(schema.Plan(raw), "fa") == {}        # without views: r_i is a die-edge input
    base = schema.validate(raw)          # the fixture cut leaves pfb.r_o unbound; the views add no new error
    raw["clock"]["io_hold_driver_views"] = pair.upstream_driver_views(raw, FULL)
    assert schema.validate(raw) == base
    m = gen_phys.input_hold_min(schema.Plan(raw), "fa")
    assert set(m) == {"r_i"} and m["r_i"]["in_min_ps"] == 12.5
    assert m["r_i"]["basis"].startswith("driver view fb") and m["r_i"]["senders"] == ["fb"]


def test_legacy_mode_ignores_views(monkeypatch):
    monkeypatch.delenv("OT_IO_HOLD", raising=False)
    raw = _cut()
    raw["clock"]["io_hold_driver_views"] = pair.upstream_driver_views(raw, FULL)
    assert gen_phys.input_hold_min(schema.Plan(raw), "fa") == {}


def test_bad_view_rejected_by_schema():
    raw = _cut()
    raw["clock"]["io_hold_driver_views"] = {"r": {"part": "pfb", "type": "fb", "bus": "r_o"}}
    assert any("out_hold_guarantee_ps" in e for e in schema.validate(raw))
