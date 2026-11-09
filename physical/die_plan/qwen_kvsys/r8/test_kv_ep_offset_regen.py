import importlib.util
from pathlib import Path
from types import SimpleNamespace as N

import pytest

s = importlib.util.spec_from_file_location("kv_ep_offset_regen", Path(__file__).with_name("kv_ep_offset_regen.py"))
M = importlib.util.module_from_spec(s)
s.loader.exec_module(M)
# the depths of the KV-TYPES-6 strict bind (bind_sinks.json): qi is cumulative from the ctl, zi is one hop
QI = [54, 47, 40, 33, 26, 19, 12, 4]


def ctx(qi=QI, zn=None, stacks=("EN", "ES", "WN", "WS"), attn=1):
    zn = zn or {}
    cells = [N(path=f"native_composite_hub_x_astk_{st}", kind="composite", module="m") for st in stacks]
    cells += [N(path=f"attn{i}", kind="leaf", module=M.ATTN) for i in range(attn)]
    for st in stacks:
        cells += [N(path=f"astk_{st}__u_strip_u_strip_g_ep_{e}__u_ep", kind="leaf", module=M.EP[e == 0]) for e in range(8)]

    def depth(path, port):
        if port == M.ZN_PORT:
            return {0: zn.get(path[-2:], 5), 1: zn.get(path[-2:], 5)}
        e = int(path.split("g_ep_")[1][0])
        return {0: qi[e] if port == "qi" else 5, 1: 0}
    return N(F=N(cells=cells), depth=depth)


def test_bound_kv():
    p, r = M.ep_offset(ctx(zn={"WS": 6}))
    assert r["eo"] == [0, 21, 42, 63, 84, 105, 126, 148]
    assert r["per_stack"]["EN"]["last"] - M.REF == 58 and r["chain"] == 59 and r["zb_add"] == 83
    assert p["attn0"] == {"ZB_ADD": 83}
    for e, want in enumerate(r["eo"]):
        v = p[f"astk_EN__u_strip_u_strip_g_ep_{e}__u_ep"]
        assert (v["EO_E"] * e + v["EO_RL"] * (e + e // 2)) == want


def test_no_ep_sets_nothing():
    assert M.ep_offset(N(F=N(cells=[]), depth=None))[0] == {}


def test_stacks_must_agree():
    c = ctx()
    d0 = c.depth
    c.depth = lambda path, port: {0: d0(path, port)[0] + (port == "qi" and "WN" in path and "ep_3" in path)}
    with pytest.raises(ValueError, match="differ between stacks"):
        M.ep_offset(c)


def test_unencodable_offset():
    with pytest.raises(ValueError, match="no EO_E"):
        M.pair(6, 127)


def test_two_attn_leaves():
    with pytest.raises(ValueError, match="2 instances"):
        M.ep_offset(ctx(attn=2))


def test_mixed_depth_port():
    c = ctx()
    d0 = c.depth
    c.depth = lambda path, port: {0: 7, 1: 8} if port == "qi" else d0(path, port)
    with pytest.raises(ValueError, match="one non-zero depth"):
        M.ep_offset(c)
