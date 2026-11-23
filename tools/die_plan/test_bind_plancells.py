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
