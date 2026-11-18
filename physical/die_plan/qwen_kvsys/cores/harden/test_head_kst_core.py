"""KV-KT-E0 11-18: the in-core kt stations of kv3_head_eighth_e0 (head_kst_core.transform) on the committed core RTL."""
import importlib.util
import re
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
CORE = REPO / "results/kv_cores_r5/rtl/kv3_head_eighth_e0/kv3_head_eighth_e0.sv"


def _mod():
    s = importlib.util.spec_from_file_location("head_kst_core", HERE / "head_kst_core.py")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def _core():
    if not CORE.is_file():
        pytest.skip("core RTL not in this checkout (sparse)")
    return CORE.read_text()


def test_depth_zero_is_the_core_of_record():
    m = _mod()
    t = _core()
    assert m.transform(t, 0) == (t, dict(depth=0, lanes=[], flops=0))


def test_depth_two_stations_both_in_core_lanes_and_nothing_else():
    m = _mod()
    t0 = _core()
    t, rec = m.transform(t0, 2)
    assert rec["flops"] == 136 and [r["lane"] for r in rec["lanes"]] == [0, 1] and rec["ports_changed"] == 0
    assert len(re.findall(r"ot_qkh_head_kst_native #\(\.D\(1\)\) u_g_t_[01]_u_kst[01] ", t)) == 4
    # the module header (ports) and every other instance are byte-identical
    assert t.split(");", 1)[0] == t0.split(");", 1)[0]
    kt0 = re.search(r"    ot_qkh_ktree_lk.*?\n    \);\n", t0, re.S).group(0)
    assert kt0 in t                                                  # the K-tree still reads the same nets
    for lane in (0, 1):
        stk = re.search(rf"u_g_t_{lane}_u_stk \(\n(.*?)\n    \);", t, re.S).group(1)
        assert f".kp_o(kst_t{lane}_s_kp[31:0])" in stk and f".kpv_o(kst_t{lane}_s_kpv)" in stk and f".gf_o(kst_t{lane}_s_gf)" in stk
        k1 = re.search(rf"u_g_t_{lane}_u_kst1 \((.*)\);", t).group(1)
        old = re.search(rf"u_g_t_{lane}_u_stk \(\n(.*?)\n    \);", t0, re.S).group(1)
        for p in ("kp_o", "kpv_o", "gf_o"):
            assert re.search(rf"\.{p}\((.*)\)", old).group(1) in k1  # stage 1 drives exactly the nets the stk drove
    assert t.rstrip().endswith("`default_nettype wire") == t0.rstrip().endswith("`default_nettype wire")


def test_depth_one_keeps_both_named_leaves():
    m = _mod()
    t, rec = m.transform(_core(), 1)
    assert rec["flops"] == 68
    assert len(re.findall(r"#\(\.D\(1\)\) u_g_t_[01]_u_kst0 ", t)) == 2 and len(re.findall(r"#\(\.D\(0\)\) u_g_t_[01]_u_kst1 ", t)) == 2


def test_fails_closed():
    m = _mod()
    t = _core()
    with pytest.raises(ValueError):
        m.transform(t, 3)
    with pytest.raises(ValueError):
        m.transform(m.transform(t, 2)[0], 2)                         # already stationed
    with pytest.raises(ValueError):                                  # an eighth without the K-tree
        m.transform(re.sub(r"    ot_qkh_ktree_lk.*?\n    \);\n", "", t, flags=re.S), 2)
    # a second reader of a stk output net (e.g. a core output pin) would leave the core early
    net = re.search(r"u_g_t_0_u_stk \(\n.*?\.kpv_o\((n\d+)\[0\]\)", t, re.S).group(1)
    with pytest.raises(ValueError):
        m.transform(t.replace("\nendmodule", f"\n    wire early = {net}[0];\nendmodule"), 2)
