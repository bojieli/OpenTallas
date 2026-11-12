"""LF-CS-DIRECT: cs rows within reach become direct links (no register); beyond reach fails closed."""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import leaf_cs_depth as LCD           # noqa: E402
import stage_leaf_cs_direct as SD     # noqa: E402


def _plan(d):
    cs = dict(conn="core:u_lf.u_vn.u_a.c_s|core:u_lf.u_vn.u_b", launch="core:u_lf.u_vn.u_a.c_s",
              capture="u_lf.u_vn.u_b", regs_um=[[5.0, 5.0]], from_um=[0.0, 0.0], to_um=[d, 0.0])
    y = dict(conn="core:u_lf.u_vn.u_b.y|core:u_lf.u_vq.y", launch="core:u_lf.u_vn.u_b.y", capture="u_lf.u_vq.y",
             regs_um=[[1.0, 1.0]], from_um=[0.0, 0.0], to_um=[600.0, 0.0])
    return dict(partition_types={"ot_s81sl_leaf__t5": dict(hard_cores=[1], internal_stations=[cs, y])})


def test_cs_within_reach_becomes_direct_and_other_classes_keep_their_registers():
    p = _plan(388.9)
    rows = SD.stage(p, 405.0)
    st = p["partition_types"]["ot_s81sl_leaf__t5"]["internal_stations"]
    assert st[0]["regs_um"] == [] and len(st[1]["regs_um"]) == 1
    assert rows[0]["manhattan_um"] == 388.9 and rows[0]["regs_before"] == 1 and rows[0]["limit_um"] == 405.0
    want, _ = LCD.plan_depths(p["partition_types"]["ot_s81sl_leaf__t5"])
    assert want["cs"] == 0 and want["y"] == 1          # the strict gate then needs no cs register


def test_cs_beyond_reach_fails_closed():
    with pytest.raises(SystemExit, match="beyond 405"):
        SD.stage(_plan(420.0), 405.0)
