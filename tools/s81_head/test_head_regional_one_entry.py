"""DIE-HEAD-20: head_regional_one_entry.apply on the committed DIE-HEAD-20 one-entry HEAD plan (results/die_head_20_1028)."""
import copy
import gzip
import json
from pathlib import Path
import sys

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / "tools/die_plan"))
import head_regional_one_entry as OE  # noqa: E402
import schema as S  # noqa: E402

PLAN = ROOT / "results/die_head_20_1028/plan_hd_tile_525.json.gz"


@pytest.fixture(scope="module")
def plan():
    return json.loads(gzip.decompress(PLAN.read_bytes()))


def strip_notes(raw):
    raw = copy.deepcopy(raw)
    for t in raw["partition_types"].values():
        t.pop("note", None)
    return raw


def test_committed_plan_is_one_entry(plan):
    assert S.validate(plan) == []
    P = S.Plan(plan)
    for tn in plan["partition_types"]:
        assert len(S.tap_grid(P, tn)) == 1 and not S.core_taps(P, tn), tn
    c = plan["partition_types"]["hd_tile"]["clock"]
    assert (c["insertion_ps"], c["insertion_ff_ps"]) == (525.0, 425.25)
    assert c["landing_export_form"] == "fwd_buffer" and c["tap_passthrough"] is True
    assert [q["kind"] for q in c["taps"]] == ["core"] * 5 and c["core_taps"] == "internal"
    spine = json.loads((ROOT / "results/die_head_17_1028/kit/reg_spine_hd_tile.json").read_text())
    assert plan["partition_types"]["hd_tile"]["reg_spine"] == spine
    band = c["landing_contract"]["bands"]["i"]
    bank = [q for q in c["reserved_sites_um"] if q.get("kind") == "landing_ring_bank"]
    assert len(bank) == 1 and bank[0]["rect_um"] == band["rect_um"] and band["ring_place"] == "ff"


def test_apply_is_idempotent(plan):
    out, rep = OE.apply(plan, 525., 425.25)
    assert strip_notes(out) == strip_notes(plan)
    assert rep["hd_tile"]["internal_core_means"] == 5


def test_apply_sets_budget_and_moves_exports(plan):
    out, rep = OE.apply(plan, 600., 500.)
    assert out["clock"]["insertion_ps"] == 600. and out["clock"]["insertion_ff_ps"] == 500.
    for tn, t in out["partition_types"].items():
        assert t["clock"]["insertion_ps"] == 600. and t["clock"]["insertion_ff_ps"] == 500.
        for q in t["clock"].get("landing_contract", {}).get("pins", []):
            if q.get("kind") == "clock" and q.get("dir") == "out":
                assert q["source_clock_port"] == "clk", (tn, q["name"])
    assert plan["clock"]["insertion_ps"] == 525.  # input untouched


def test_apply_rejects(plan):
    with pytest.raises(ValueError, match="FF <= TT"):
        OE.apply(plan, 400., 500.)
    bad = copy.deepcopy(plan); bad["clock"].pop("landing_network")
    with pytest.raises(ValueError, match="landing network"):
        OE.apply(bad)
    bad = copy.deepcopy(plan)
    bad["partition_types"]["hd_tile"]["clock"]["taps"][0]["budget_owner"] = "DECLARED"
    with pytest.raises(ValueError, match="SIGNED"):
        OE.apply(bad)
    bad = copy.deepcopy(plan)
    pin = next(q for q in bad["partition_types"]["hd_tile"]["clock"]["landing_contract"]["pins"]
               if q.get("kind") == "clock" and q.get("dir") == "out")
    pin["source_clock_port"] = "fclk_in_i"
    with pytest.raises(ValueError, match="not a removed region tap"):
        OE.apply(bad)
