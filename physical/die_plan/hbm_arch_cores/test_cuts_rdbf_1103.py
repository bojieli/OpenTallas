"""DIE-HBM-61/CUTS 11-03: recipe keys of the q2_reduce / bfqg RF1 cuts (0 added cycles)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
R = json.loads((ROOT / "physical/die_plan/hbm_arch_cores/recipes_b2.json").read_text())


def test_q2_reduce_cut1():
    base, cut = R["ot_hfd_coll_q2_hard_v8g__reduce"], R["ot_hfd_coll_q2_hard_v8g__reduce__cut1"]
    assert cut["top"] == base["top"] and cut["wrapper_by_pins_sha256"] == base["wrapper_by_pins_sha256"]
    assert set(cut["defines"]) == {"OT_HBM_REDUCE_LREP", "OT_HBM_REDUCE_LOCAL_CTRL"}
    assert base == cut  # DIE-HBM-66 11-04: the base entry takes the cut, so rows building by base key read it
    assert "rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_reduce_static_lr.sv" in cut["files"]
    for f in cut["files"]:
        assert (ROOT / f).is_file(), f
    keys = list(R)
    assert keys.index("ot_hfd_coll_q2_hard_v8g__reduce__cut1") == keys.index("ot_hfd_coll_q2_hard_v8g__reduce") + 1


def test_bfqg_cut1():
    base, cut = R["ot_hgi_sm_xload_cl2_bfqg"], R["ot_hgi_sm_xload_cl2_bfqg__cut1"]
    assert cut["params"] == {"RPR": 16} and cut["read_at_commit"] is False
    assert base == cut  # DIE-HBM-66 11-04: the base entry takes the cut, so rows building by base key read it
    src = (ROOT / "rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_bfqg.sv").read_text()
    assert "parameter integer RPR=1" in src


def test_cycles_zero():
    rows = (ROOT / "physical/die_plan/hbm/reform_1103/cycles/cuts_rdbf.tsv").read_text().splitlines()[1:]
    assert len(rows) == 2 and all(r.split("\t")[2] == "0" for r in rows)
