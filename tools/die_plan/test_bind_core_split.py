"""DIE-KV-67 11-04: opt-in asbuilt.core_splits (one hard leaf -> PCC + PCF, optional PC reset gate)."""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind_core_split as S
from bind_elab import Cell


def spec(**kw):
    s = dict({"from": "pc", "pcc": "pcc", "pcf": "pcf", "face": {"port": "x", "width": 2},
              "split": {"g": {"pcc": [0, 2], "pcf": [1], "pcc_port": "g_c", "pcf_port": "g_f"}},
              "shared": {"ck": None, "r": [0]}})
    s.update(kw)
    return s


def binder(*cells):
    F = SimpleNamespace(cells=list(cells), n=100)

    def new(n):
        F.n += n
        return F.n - n
    F.new = new
    R = SimpleNamespace(parts={}, part_of=lambda p: "P0" if p.startswith("u_") else None, local_of=lambda p: p)
    return SimpleNamespace(F=F, R=R)


def leaf(path="u_a", module="pc"):
    return Cell(path, module, {}, {"g": [1, 2, 3], "ck": [4], "r": [5, 6]},
                {"g": "input", "ck": "input", "r": "input"}, "leaf", ytype=module, yparams={}, src=None)


def test_split_ports_bits_and_face():
    b = binder(leaf(), Cell("u_o", "other", {}, {}, {}, "leaf", ytype="other", yparams={}, src=None))
    got = S.apply(b, [spec()])
    assert got == [dict(leaf="u_a", pcc="pcc", pcf="pcf", part="P0")]
    c, f, o = b.F.cells
    assert (c.path, c.module, f.path, f.module, o.module) == ("u_a", "pcc", "u_a_f", "pcf", "other")
    assert c.ports["g_c"] == [1, 3] and f.ports["g_f"] == [2] and "g" not in c.ports
    assert c.ports["x"] == f.ports["x"] == [100, 101]
    assert (c.dirs["x"], f.dirs["x"]) == ("output", "input")
    assert f.ports["ck"] == [4] and f.ports["r"] == [5] and c.ports["r"] == [5, 6]
    assert b.R.parts["u_a_f"] == ["P0", "u_a_f"]


def test_two_masters_for_two_sources():
    b = binder(leaf("u_a", "pc"), leaf("u_h", "pch"))
    S.apply(b, [spec(), spec(**{"from": "pch", "pcc": "pcc_h", "pcf": "pcf_h"})])
    assert [c.module for c in b.F.cells] == ["pcc", "pcf", "pcc_h", "pcf_h"]


@pytest.mark.parametrize("split", [{"pcc": [0], "pcf": [1]}, {"pcc": [0, 1], "pcf": [1, 2]}])
def test_split_must_cover_each_bit_once(split):
    bad = spec(split={"g": dict(split, pcc_port="g_c", pcf_port="g_f")})
    with pytest.raises(S.CoreSplitError):
        S.apply(binder(leaf()), [bad])


def test_missing_ports_and_partition_refused():
    with pytest.raises(S.CoreSplitError):
        S.apply(binder(leaf()), [spec(shared={"nope": None})])
    with pytest.raises(S.CoreSplitError):
        S.apply(binder(leaf("x_a")), [spec()])


def test_gate_ports_only_when_asked():
    assert S.gate_ports([spec()]) == {}
    assert S.gate_ports([spec(reset_gate=["r"])]) == {"pcc": {"r"}, "pcf": {"r"}}


def test_gate_tap_nearest_boot_tap():
    relays = [dict(q="rst_rl_0", xy=(0, 0)), dict(q="rst_n_t1", xy=(100, 0)), dict(q="rst_n_t0", xy=(10, 10))]
    assert S.gate_tap(relays, (0, 0), 2) == "rst_n_t0"
    assert S.gate_tap(relays, (90, 0), 2) == "rst_n_t1"
    with pytest.raises(S.CoreSplitError):
        S.gate_tap(relays[:1], (0, 0), 2)


def test_gate_tap_skips_registered_reset_out():
    # tap k >= consumer count is a reset out: emitted as rr_t<k>, no rst_n_t<k> net exists
    relays = [dict(q="rst_n_t0", xy=[0, 0]), dict(q="rst_n_t1", xy=[100, 0])]
    assert S.gate_tap(relays, (90, 0), 1) == "rst_n_t0"


def test_view_drop_and_parts():
    c = Cell("u_a", "pc", {}, {"g": [1, 2, 3], "ck": [4], "r": [5, 6], "h": [7], "e": [8, 9, 10, 11]},
             {"g": "input", "ck": "input", "r": "input", "h": "input", "e": "input"}, "leaf", ytype="pc", yparams={}, src=None)
    b = binder(c)
    S.apply(b, [spec(view_drop=["h"], view_parts={"e": {"e": [0], "e_2": [2, 3]}})])
    pcc = b.F.cells[0]
    assert pcc.ports["h"] == [7] and pcc.ports["e"] == [8] and pcc.ports["e_2"] == [10, 11]
    assert pcc.dirs["e_2"] == "input"
    assert S.view_hidden([spec(view_drop=["h"]), spec(pcc="o")]) == {"pcc": {"h"}}


@pytest.mark.parametrize("kw", [dict(view_drop=["nope"]), dict(view_parts={"nope": {"e": [0]}}),
                                dict(view_parts={"ck": {"e": [5]}})])
def test_view_fit_refuses_bad_spec(kw):
    with pytest.raises(S.CoreSplitError):
        S.apply(binder(leaf()), [spec(**kw)])


def test_emitted_and_derived_ifaces_agree_and_hide_view_drop():
    # KW-FIX-24: bind_verify stubs the split leaves (no source); both interface paths are the apply transform
    s = spec(view_drop=["ck"])
    b = binder(leaf())
    S.apply(b, [s])
    em = S.emitted_ifaces(b.F.cells, [s])
    assert em == {"pcc": {"params": [], "ports": {"g_c": ["input", 2], "r": ["input", 2], "x": ["output", 2]}},
                  "pcf": {"params": [], "ports": {"ck": ["input", 1], "g_f": ["input", 1], "r": ["input", 1],
                                                  "x": ["input", 2]}}}
    src = {"g": ("input", 3), "ck": ("input", 1), "r": ("input", 2)}
    assert S.derived_ifaces([s], {"pc": src}.get) == em
    with pytest.raises(S.CoreSplitError):
        S.derived_ifaces([s], {}.get)
