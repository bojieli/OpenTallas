"""W11: bank specification of the distributed V4.1 vector memory (tools/w11_vm_dist_spec.py,
results/floorplan/v41_vm_dist_spec.json).  Fast: reads the committed record only (the source pins are
checked against the tree; the model's rule is re-evaluated)."""
import hashlib
import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "results/floorplan/v41_vm_dist_spec.json"
sys.path.insert(0, str(ROOT / "tools"))


@pytest.fixture(scope="module")
def rec():
    return json.loads(REC.read_text())


def test_record_is_source_pinned(rec):
    assert len(rec["source_commit"]) == 40
    assert "tools/w11_vm_dist_spec.py" in rec["source_sha256"]
    for name, digest in rec["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name


def test_capacity_is_the_die_vm_and_holds_the_l0_layout(rec):
    cap = rec["capacity"]
    for name, line in cap["vm_aw_lines"].items():        # the RTL's VM depth is still the one the spec sized
        assert line in (ROOT / name).read_text(), name
    assert cap["full_shape_vm_aw"] == 19 and cap["words"] == 1 << 19 and cap["mib"] == 2.0
    assert cap["per_group_words"] * rec["groups"]["count"] == cap["words"]
    assert all(e < cap["words"] for e in cap["full_shape_l0_highest_element"].values())


def test_interleave_is_consistent(rec):
    ng = rec["groups"]["count"]
    for e, v in rec["interleave"]["example"].items():
        e = int(e)
        w = e // ng
        assert (v["group"], v["word"], v["bank"], v["row"], v["column"]) == (e % ng, w, (w >> 3) & 1, w >> 4, w & 7)


def test_macro_count_and_area(rec):
    m = rec["macros"]
    idx = json.loads((ROOT / "physical/asap7_memory_macros/index.json").read_text())["macros"][m["chosen"]]
    assert idx["spec"]["ports"] == "1r1w"
    assert m["per_group"] == m["read_replicas"] * m["banks_per_replica"] == 12
    assert m["total"] == 128 * m["per_group"] == 1536
    assert math.isclose(m["total_mm2"], m["total"] * idx["area_um2"] / 1e6, rel_tol=1e-4)
    # one replica holds the group's slice exactly
    assert m["banks_per_replica"] * idx["spec"]["words"] * idx["spec"]["bits"] // 32 == rec["capacity"]["per_group_words"]


def test_tree_stages_follow_the_model_rule(rec):
    import uarch_model as U
    for name, t in rec["trees"].items():
        assert t["stages"] == U.wire_cycles(t["distance_um"], 1e12 / 920, 0.76), name
    # the model (option H, root 2026-09-30) takes this record's block: its stages are the spec's, with the
    # collective endpoint at the VM port (the scatter tree's stages)
    tr = rec["trees"]
    for name in ("x_gather", "ret_scatter", "su_results"):
        assert tr[name]["model_stages"] == tr[name]["stages"], name
    assert tr["coll_write"]["model_stages"] == tr["ret_scatter"]["stages"]


def test_discrepancies_are_flagged(rec):
    items = " ".join(d["item"] for d in rec["discrepancies"])
    assert "not lane-group-local" in items
    assert "tree distances" in items
    assert "VM SRAM area" in items
    vs = rec["read_rule"]["measured"]["vehicle"]
    assert sum(vs["remote_elements"].values()) > 0


def test_footprint_fits_the_hub_region(rec):
    fp, geo = rec["footprint"], rec["geometry"]
    assert geo["fits_hub_su_vector"]
    assert fp["block_w_um"] <= geo["hub_su_vector"]["w"] + 1e-6
    assert fp["block_h_um"] <= geo["hub_su_vector"]["h"]
    assert math.isclose(fp["block_mm2"], fp["block_w_um"] * fp["block_h_um"] / 1e6, rel_tol=1e-3)
