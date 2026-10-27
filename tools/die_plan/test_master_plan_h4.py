"""INFRA-FIRST-HEAD-4: opt-in declared clock slots -> island_ft_inputs declared ties (unused slot of a replica)."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import master_rulings as MR  # noqa: E402

M = dict(htree=[dict(b=[10.0, 10.0])], drivers={}, xs=[100.0], ys=[200.0], taps=[], meta={})
ISL = [dict(kind="partition_slot", part="p0", inst="p0/slot0", role="clock_slot", rect_um=[5.0, 5.0, 15.0, 15.0]),
       dict(kind="partition_slot", part="p1", inst="p1/slot0", role="clock_slot", rect_um=[50.0, 50.0, 60.0, 60.0]),
       dict(kind="core", part="p1", inst="p1/c", role="tree_leaf", rect_um=[95.0, 50.0, 105.0, 60.0])]


def test_default_unused_slot_is_open():
    r = MR.island_ft_inputs(M, ISL)
    assert r["verdict"] == "FAIL" and r["open"] == 1 and "declared_ties" not in r


def test_slot_ties_declares_only_unused_slots():
    r = MR.island_ft_inputs(M, ISL, slot_ties=True)
    assert r["verdict"] == "PASS"
    assert r["fed"] == {"tree_node_or_mesh_driver": 1, "declared_tie_dead_output": 1, "local_strap": 1}
    assert [t["inst"] for t in r["declared_ties"]] == ["p1/slot0"]


def test_in_core_island_never_tied():
    isl = [dict(ISL[2], rect_um=[300.0, 300.0, 310.0, 310.0])]
    r = MR.island_ft_inputs(M, isl, slot_ties=True)
    assert r["verdict"] == "FAIL" and r["open"] == 1
