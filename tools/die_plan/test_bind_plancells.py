from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bind_plancells import PlanCells
import reset_tree


def test_split_type_plan_cell_uses_base_reset_cluster(monkeypatch):
    base, variant = "pc", "pc__v1"
    wavefront = SimpleNamespace(types={base: {}})
    binder = SimpleNamespace(
        plan={"partition_types": {base: {}}},
        types={base: {}, variant: {"split_of": base}},
        wavefront_plan=lambda: wavefront,
        errors=[],
    )
    cells = PlanCells.__new__(PlanCells)
    cells.B = binder
    cells.ptype0 = {"pc_instance": base}
    cells.T = {base: {"cells": {"logic": {"module": "test_cell", "conns": {"rst_n": ["rst_n"]}}}}}
    cells.iface = {"test_cell": SimpleNamespace(ports={"rst_n": ("input", None)})}
    cells.busdrv = {}
    cells.celldrv = {base: {}}
    cells.efs_cfg = None
    cells.stats = {"cells_emitted": 0}
    cells.width = lambda *args: 1
    cells._atoms = lambda *args: [("net", "rst_n")]

    def lookup(plan, type_name):
        assert plan is wavefront
        assert type_name == base
        return {"logic": 7}

    monkeypatch.setattr(reset_tree, "leaf_cluster_inst_taps", lookup)
    body = []
    cells.emit("pc_instance", variant, {}, {}, {}, {}, [], body, [])
    assert ".rst_n(rst_n_t7)" in body[-1]
    assert not binder.errors


def test_plan_cell_types_follow_r8_and_landing_clones():
    """KV-R8-LANELOSS 11-23: an R8 / param-class clone (param_base_type only) must inherit its base type plan cells.
    A2g: kv3_pc_v3__r82626e324 had none, so pc_EN_7 lost u_efault and its lane L495 o_efault_pc_Q_N_fault went empty."""
    from bind_plancells import plan_cell_types
    doc = {"pc_v3": {"cells": {"u_efault": {}}}, "pc": {"cells": {"u_id": {}}}, "gone": {"cells": {}}}
    pts = {
        "pc_v3__r8aaaaaaaa": {"param_base_type": "pc_v3"},                   # R8 clone, base no longer a plan type
        "pc__clbbbbbbbb": {"landing_base_type": "pc"},                       # landing cohort (old alias)
        "pc__clbbbbbbbb__r8cccccccc": {"param_base_type": "pc__clbbbbbbbb", "landing_base_type": "pc"},
        "pc__cldddddddd__r8eeeeeeee": {"param_base_type": "pc__cldddddddd"},  # chain through a missing cohort: no row
        "hg__r8ffffffff": {"param_base_type": "hg__clgggggggg"},
        "hg__clgggggggg": {"landing_base_type": "pc"},                       # chain through a plan-type cohort
        "other": {},
    }
    T = plan_cell_types(doc, pts)
    assert T["pc_v3__r8aaaaaaaa"] is doc["pc_v3"]
    assert T["pc__clbbbbbbbb"] is doc["pc"]
    assert T["pc__clbbbbbbbb__r8cccccccc"] is doc["pc"]
    assert T["hg__r8ffffffff"] is doc["pc"]
    assert "pc__cldddddddd__r8eeeeeeee" not in T and "other" not in T and "gone" not in T


def test_plan_cell_types_without_clones_is_the_file():
    from bind_plancells import plan_cell_types
    doc = {"a": {"cells": {}}, "b": {"cells": {}}}
    assert plan_cell_types(doc, {"a": {}}) is doc


def test_plan_cell_types_cycle_terminates():
    from bind_plancells import plan_cell_types
    pts = {"x": {"param_base_type": "y"}, "y": {"param_base_type": "x"}}
    doc = {"z": {}}
    assert plan_cell_types(doc, pts) is doc


def _guard_cells(T):
    """a PlanCells over a two-partition plan: pc_a (base pc_v3), pc_b (R8 clone of pc_v3, param_base_type only)"""
    doc = {"pc_v3": {"cells": {"u_efault": {"module": "ot_dp_efault",
                                            "conns": {"fault": [{"bus": "o_efault"}], "eq": [{"bus": "i_x"}]}}},
                     "bus_drivers": [{"bus": "o_id", "drivers": [{"net": "clk"}]}]}}
    buses = [{"name": "o_efault", "dir": "out", "width": 1}, {"name": "o_id", "dir": "out", "width": 1},
             {"name": "o_data", "dir": "out", "width": 8}, {"name": "i_x", "dir": "in", "width": 1}]
    pts = {"pc_v3": {"buses": buses}, "pc_v3__r8aaaaaaaa": {"buses": buses, "param_base_type": "pc_v3"}}
    binder = SimpleNamespace(plan={"partition_types": pts, "partitions": [{"name": "pc_a", "type": "pc_v3"},
                                                                          {"name": "pc_b", "type": "pc_v3__r8aaaaaaaa"}]},
                             parts={"pc_a": {"type": "pc_v3"}, "pc_b": {"type": "pc_v3__r8aaaaaaaa"}}, errors=[])
    cells = PlanCells.__new__(PlanCells)
    cells.B, cells.doc = binder, {"types": doc}
    cells.T = T(doc, pts)
    cells.ptype0 = {p["name"]: p["type"] for p in binder.plan["partitions"]}
    cells.bus_dir = {tn: {b["name"]: b["dir"] for b in t["buses"]} for tn, t in pts.items()}
    cells.iface = {"ot_dp_efault": SimpleNamespace(ports={"fault": ("output", None), "eq": ("input", None)})}
    cells.busdrv = {tn: {b: {0: None} for b in ("o_efault", "o_id")} for tn in cells.T}
    return cells


def test_r8_clone_plan_cell_buses_are_reserved():
    """fails on the pre-fix bind (KV-R8-LANELOSS): the clone partition pc_b had no plan cells, its buses unreserved"""
    from bind_plancells import plan_cell_types
    cells = _guard_cells(plan_cell_types)
    assert {("pc_b", "o_efault"), ("pc_b", "o_id"), ("pc_a", "o_efault")} <= cells.reserved_buses()


def test_plan_cell_lane_with_zero_bits_is_a_bind_error():
    """the guard: a lane whose source bus plan cells drive (via the clone lineage) and that got 0 bits is an ERROR,
    whatever lost the cells; a lane on an as-built bus or an IN-port reference is not flagged"""
    prefix = lambda doc, pts: {tn: r for tn, r in doc.items() if tn in pts}      # the pre-fix alias (no R8 clones)
    cells = _guard_cells(prefix)
    unused = [{"id": "L495", "src": "pc_b", "oname": "o_efault"}, {"id": "L496", "src": "pc_b", "oname": "o_id"},
              {"id": "L9", "src": "pc_b", "oname": "o_data"}, {"id": "L8", "src": "pc_a", "oname": "o_data"}]
    errs = cells.empty_lane_errors(unused)
    assert [e.split()[1] for e in errs] == ["L495:", "L496:"]
    assert all(e.startswith("PLAN_CELL_LANE_EMPTY") and "pc_v3" in e for e in errs)
    assert cells.empty_lane_errors([{"id": "L7", "src": "pc_a", "oname": "i_x"}]) == []
