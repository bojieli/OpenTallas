"""HG-SPLIT 11-03: kv_ex_join_regen (ep EX_ADD / EX_PAD from the bound EX legs) on a fake binder context."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location("kv_ex_join_regen", HERE / "kv_ex_join_regen.py")
X = importlib.util.module_from_spec(_s)
_s.loader.exec_module(X)


def ctx(cross, eps=("astk_EN__u_strip_u_strip_g_ep_0__u_ep", "astk_EN__u_strip_u_strip_g_ep_1__u_ep"), skew=None):
    """cross: {(ep index, lane): (out depth, back depth)}; skew: (ep index, lane, bit, depth) override of an xe bit"""
    cells = []
    for i, ep in enumerate(eps):
        cells.append(SimpleNamespace(path=ep, kind="leaf", module="qkd_astk_ep_s_head_e" if i == 0 else "qkd_astk_ep_s_e"))
        for k in range(4):
            cells.append(SimpleNamespace(path=ep.replace("__u_ep", f"__g_ex_{k}__u_ex"), kind="leaf", module="qkd_astk_ex_s"))
    idx = {c.path: n for n, c in enumerate(cells)}

    def depth(path, port):
        if port == "xa":
            i = next(j for j, ep in enumerate(eps) if path.startswith(ep.replace("__u_ep", "")))
            k = int(path.split("g_ex_")[1][0])
            return {b: cross.get((i, k), (0, 0))[0] for b in range(66)}
        i = eps.index(path)
        d = {34 * k + b: cross.get((i, k), (0, 0))[1] for k in range(4) for b in range(34)}
        if skew and skew[0] == i:
            d[34 * skew[1] + skew[2]] = skew[3]
        return d
    return SimpleNamespace(F=SimpleNamespace(cells=cells), cell_index=lambda: idx, depth=depth)


def test_no_cut_sets_nothing():
    p, rec = X.ex_join(ctx({}))
    assert p == {} and rec["ex_pad"] == 0 and rec["eps"] == 2


def test_cut_lanes_2_3_pad_every_ep():
    p, rec = X.ex_join(ctx({(1, 2): (2, 2), (1, 3): (2, 2)}))
    ep0, ep1 = sorted(p)
    assert p[ep1] == dict(EX_ADD0=0, EX_ADD1=0, EX_ADD2=4, EX_ADD3=4, EX_PAD=4)
    assert p[ep0] == dict(EX_ADD0=0, EX_ADD1=0, EX_ADD2=0, EX_ADD3=0, EX_PAD=4)   # same DT on the whole chain
    assert rec["crossed"] == 1 and rec["ex_pad"] == 4


def test_mixed_leg_depth_fails_closed():
    with pytest.raises(ValueError, match="one depth per EX leg"):
        X.ex_join(ctx({(1, 2): (2, 2)}, skew=(1, 2, 7, 3)))


def test_valid_bit_off_leg_fails_closed():
    with pytest.raises(ValueError, match="valid bit"):
        X.ex_join(ctx({(1, 2): (2, 2)}, skew=(1, 2, 0, 0)))


def test_missing_ex_leaf_fails_closed():
    c = ctx({})
    c.F.cells = [x for x in c.F.cells if not x.path.endswith("g_ex_3__u_ex")]
    idx = {x.path: n for n, x in enumerate(c.F.cells)}
    c.cell_index = lambda: idx
    with pytest.raises(ValueError, match="EX lane 3"):
        X.ex_join(c)
