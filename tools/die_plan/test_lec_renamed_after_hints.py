"""RENAMED-BEFORE-HINTS (LEC-R3 11-27, hd_mesh 22dcfc2f, class P-LEC-PROOF-GAP): renamed() decided to re-key a vector
on a simulation in which the by-name relays were independent random inputs, so a counter whose gate tap was re-pointed
to another relay of its class looked renamed (base#t, 478 differs).  The structural relay classes are now seeded
(proposal only) before renamed(), which simulates with them bound.
    python3 -m pytest -q tools/die_plan/test_lec_renamed_after_hints.py"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402

REL = [["both", "ff:u_dut.rrl_2.q", ["eq", "gold", "ff:u_dut.rrl_1.q", 0]]]


def _sim_prove(m, *a, **k):
    val, mask = m.simulate(16, seed=12345)
    return {n: ("proved" if lec.lit_val(val, mask, o) == 0 else "differs") for n, o in zip(m.onames, m.outs)}


def _design(tmp_path, swap_gate, v1_next=None):
    """input d = var 1; latches rrl_1.q, rrl_2.q (both q' = d: one relay class), v[0], v[1].  Gold reads rrl_1 / rrl_2,
    the gate taps are re-pointed (swapped) when swap_gate."""
    def side(name, swapped, mutant=False):
        p = tmp_path / (name + ".aig")
        nxt = [2, 2, 6, 4] if swapped else [2, 2, 4, 6]
        if mutant:
            nxt[3] = 2                          # v[1]' = d: a real functional change, not a relay re-pointing
        p.write_bytes(b"aig 5 1 4 0 0\n" + "".join(f"{v}\n" for v in nxt).encode())
        mp = {"input": {0: [("d", 0)]}, "latch": {0: [("u_dut.rrl_1.q$_DFF_P_.lecq", 0)],
                                                   1: [("u_dut.rrl_2.q$_DFF_P_.lecq", 0)],
                                                   2: [("u_dut.v[0]$_DFF_P_.lecq", 0)],
                                                   3: [("u_dut.v[1]$_DFF_P_.lecq", 0)]}, "output": {}}
        return lec.read_aig(p), mp
    g, gm = side("gold", False)
    t, tm = side("gate", swap_gate, mutant=bool(v1_next))
    return lec.Lec(g, gm, t, tm)


def test_without_relay_classes_the_repointed_counter_is_rekeyed(tmp_path):
    L = _design(tmp_path, swap_gate=True)
    log = []
    lec.renamed(L, log)
    assert any("renamed: ff:u_dut.v" in x for x in log) and L.renamed_bases == ["ff:u_dut.v"]


def test_relay_classes_seeded_before_renamed_keep_the_names(tmp_path, monkeypatch):
    monkeypatch.delenv("OT_LEC_RENAMED_AFTER_HINTS", raising=False)
    L = _design(tmp_path, swap_gate=True)
    L.relay_pre = REL
    log = []
    assert lec.seed_relay_hints(L, tmp_path, 100, log) == 1
    lec.renamed(L, log)
    assert not getattr(L, "renamed_bases", []) and not L.tonly and not L.gonly
    assert L.hyp[("both", "ff:u_dut.rrl_2.q")] == ("eq", "gold", "ff:u_dut.rrl_1.q", 0)
    monkeypatch.setattr(lec, "prove", _sim_prove)
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert set(_sim_prove(m).values()) == {"proved"}


def test_correspond_end_to_end_and_disable_switch(tmp_path, monkeypatch):
    monkeypatch.setattr(lec, "prove", _sim_prove)
    monkeypatch.delenv("OT_LEC_RENAMED_AFTER_HINTS", raising=False)
    L = _design(tmp_path, swap_gate=True)
    L.relay_pre = REL
    log = []
    lec.correspond(L, tmp_path, 100, log)
    assert not getattr(L, "renamed_bases", []) and any("relay classes seeded" in x for x in log)
    monkeypatch.setenv("OT_LEC_RENAMED_AFTER_HINTS", "0")
    L = _design(tmp_path, swap_gate=True)
    L.relay_pre = REL
    lec.correspond(L, tmp_path, 100, [])
    assert getattr(L, "renamed_bases", []) == ["ff:u_dut.v"]            # the old order


def test_a_real_change_still_fails_with_relay_classes_seeded(tmp_path, monkeypatch):
    monkeypatch.setattr(lec, "prove", _sim_prove)
    monkeypatch.delenv("OT_LEC_RENAMED_AFTER_HINTS", raising=False)
    L = _design(tmp_path, swap_gate=True, v1_next=True)
    L.relay_pre = REL
    lec.correspond(L, tmp_path, 100, [])
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert "differs" in set(_sim_prove(m).values())
