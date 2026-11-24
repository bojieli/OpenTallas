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
