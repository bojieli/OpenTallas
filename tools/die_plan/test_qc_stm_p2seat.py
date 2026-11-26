"""QC-INT-R2-HCSETUP 11-26: P2SEAT seat tool, RTL P2FAR constant and plan delta."""
import importlib.util, subprocess, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]


def _load(rel, name):
    s = importlib.util.spec_from_file_location(name, R / rel)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def test_partition_is_a_permutation_of_the_same_trees():
    m = _load("tools/die_plan/qc_stm_p2seat.py", "p2seat")
    old, new = m.parts({73, 74, 152, 153})
    assert sorted(old) == sorted(new) == list(range(235))
    assert [i for i in new if new[i] == 8] == [73, 74, 152, 153]
    assert max(new[i] for i in new if i not in (73, 74, 152, 153)) == 7
    sizes = [sum(1 for v in new.values() if v == k) for k in range(9)]
    assert sum(sizes) == 235 and max(sizes[:8]) <= 29


def test_rtl_far_set_matches_the_measured_seats():
    for t in ("sle_stm_v2__cl7b3062fa", "sle_stm_v2__cl55be2264"):
        r = subprocess.run([sys.executable, "-I", str(R / "tools/die_plan/qc_stm_p2seat.py"),
                            str(R / f"results/qc_stm_p2seat_1126/seats_{t}.tsv"), "--rtl",
                            str(R / "rtl/qwen_dv/qfd_dv_stream_tile.sv")], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr


def test_s8_ce_carries_the_same_partition():
    a = (R / "rtl/qwen_dv/qfd_dv_stream_tile.sv").read_text()
    b = (R / "rtl/qwen_dv/s5/s8/qfd_dv_s8_ce.sv").read_text()
    blk = a.split("QC-INT-R2-HCSETUP 11-26 (C-LEG405", 1)[1].split("endfunction", 3)[2]
    assert blk in b


def test_delta_appends_only_the_define():
    m = _load("physical/die_plan/qwen_compute/delta_stm_p2seat_1126.py", "dlt")
    raw = {"partition_types": {t: {"verilog_defines": ["OT_QC_STMDQ"]} for t in m.TYPES}}
    raw["partition_types"][m.HC_TYPE] = {}
    out = m.apply(raw)
    assert all(out["partition_types"][t]["verilog_defines"] == ["OT_QC_STMDQ", m.DEFINE] for t in m.TYPES)
    assert out["partition_types"][m.HC_TYPE]["verilog_defines"] == [m.HC_DEFINE]
