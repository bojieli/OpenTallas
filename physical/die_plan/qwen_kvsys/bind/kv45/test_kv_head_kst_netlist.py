"""KV-KT-E0 11-18: the kt-station derivation of the KV as-built netlist / instance map / composition (kv_head_kst_netlist)."""
import gzip
import importlib.util
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _mod():
    s = importlib.util.spec_from_file_location("kv_head_kst_netlist", HERE / "kv_head_kst_netlist.py")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def test_netlist_is_the_kst_head_and_nothing_else():
    m = _mod()
    src = gzip.decompress(m.SRC.read_bytes()).decode()
    new = m.derive(src, 2)
    a, b = src.split("\n"), new.split("\n")
    assert len(b) == len(a) + 2 * 2048 + 2 * 384
    kst = [x for x in b if "ot_qkh_head_kst_native" in x]
    assert len(kst) == 4096 and all("#(.D(1))" in x for x in kst)
    # every line of the source survives, except the 2,048 stk lines (outputs renamed) and the 32 ECTL lines (HXK)
    gone = set(a) - set(b)
    assert len(gone) == 2048 + 32
    assert sum("ot_qkh_head_stk_native" in x for x in gone) == 2048 and sum(".HXK(13)" in x for x in gone) == 32
    assert new.count(".HXK(15)") == 32 and ".HXK(13)" not in new
    # one head, one lane, wire for wire: stk -> _s -> kst0 -> _m -> kst1 -> _k -> u_kt
    h = "head_WS_0_0"
    stk = next(x for x in b if f" {h}__g_t_5__u_stk " in x)
    assert f".kp_o(n_{h}__kp_s[191:160])" in stk and f".kpv_o(n_{h}__kpv_s[5])" in stk and f".gf_o(n_{h}__gf_s[5])" in stk
    k0 = next(x for x in b if f" {h}__g_t_5__u_kst0 " in x)
    k1 = next(x for x in b if f" {h}__g_t_5__u_kst1 " in x)
    assert f".kp_i(n_{h}__kp_s[191:160]), .kp_o(n_{h}__kp_m[191:160])" in k0 and f".kpv_i(n_{h}__kpv_s[5]), .kpv_o(n_{h}__kpv_m[5])" in k0
    assert f".kp_i(n_{h}__kp_m[191:160]), .kp_o(n_{h}__kp_k[191:160])" in k1 and f".gf_i(n_{h}__gf_m[5]), .gf_o(n_{h}__gf_k[5])" in k1
    clk = re.search(r"\.clk\(([^)]+)\)", stk).group(1)
    assert f".clk({clk})" in k0 and f".clk({clk})" in k1
    kt = next(x for x in b if f" {h}__u_kt " in x)
    assert kt in a                                                   # the K-tree line is untouched
    for w in ("kp", "kpv", "gf"):
        for sfx in ("_s", "_m"):
            assert sum(1 for x in b if re.fullmatch(rf"\s*wire \[\d+:0\] n_{h}__{w}{sfx};", x)) == 1


def test_depth_one_keeps_both_leaves():
    m = _mod()
    new = m.derive(gzip.decompress(m.SRC.read_bytes()).decode(), 1)
    assert new.count("ot_qkh_head_kst_native #(.D(1))") == 2048 and new.count("ot_qkh_head_kst_native #(.D(0))") == 2048
    assert new.count(".HXK(14)") == 32


def test_map_and_composition():
    m = _mod()
    mp0 = json.loads(m.MAP.read_text())
    mp = m.derive_map(mp0)
    assert len(mp["parts"]) == len(mp0["parts"]) + 4096
    part, name = mp0["parts"]["head_EN_0_0__g_t_5__u_stk"]
    assert mp["parts"]["head_EN_0_0__g_t_5__u_kst0"] == [part, name.replace("u_stk", "u_kst0")]
    assert mp["parts"]["head_EN_0_0__g_t_5__u_kst1"] == [part, name.replace("u_stk", "u_kst1")]
    assert all(mp["parts"][k] == v for k, v in mp0["parts"].items())
    c0 = json.loads(gzip.decompress(m.CMP.read_bytes()))
    c = m.derive_compose(c0)
    n = 0
    for x0, x in zip(c0["cores"], c["cores"]):
        if x0["module"] == "kv3_head_eighth_e0":
            add = sorted(set(x["members"]) - set(x0["members"]))
            head = next(k for k in x0["members"] if k.endswith("__u_kt"))[:-6]
            assert add == sorted(f"{head}__g_t_{t}__u_kst{k}" for t in (0, 1) for k in (0, 1))
            assert {k: v for k, v in x.items() if k != "members"} == {k: v for k, v in x0.items() if k != "members"}
            n += 1
        else:
            assert x == x0
    assert n == 128


def test_committed_depth_two_netlist_is_fresh():
    m = _mod()
    net = m.derive(gzip.decompress(m.SRC.read_bytes()).decode(), 2)
    assert gzip.decompress(m.outs(2)[0].read_bytes()).decode() == net
