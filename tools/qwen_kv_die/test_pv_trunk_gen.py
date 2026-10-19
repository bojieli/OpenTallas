"""KVPLAN 1815: structural invariants of the trunked PV pair generator (no placement: the netlist does not depend on it)."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pv_trunk_gen as P  # noqa: E402


def _gen(ns=3):
    a = argparse.Namespace(ch=172.8, ch_even=172.8, ct=345.6, sw=0.0, strip=86.4, halo_tile=21.6, hop=390.0, ns=ns, cmd_lead=3,
                           mut_station='K1c0g0', no_place=True)
    g = P.Gen(a)
    g.build()
    return g


def test_every_column_aligned_and_flags_balanced():
    g = _gen()
    D, R = g.timing()
    assert len(D) == 32
    assert len({D[s] + R[s] for s in range(32)}) == 1          # one column-check slot in the control tile
    for gg in range(8):                                         # both rows of a GS group run at one static time
        assert len({D[P.col_of(c, r)] for c in range(2) for r in (2 * gg, 2 * gg + 1)}) == 1


def test_chunk_delta_non_negative_and_monotone():
    g = _gen()
    D, _ = g.timing()
    delta = [D[P.col_of(0, 2 * gg)] - (g.v_entry_stages + 2) for gg in range(8)]
    assert min(delta) >= 0
    assert all(delta[i] > delta[i + 1] for i in range(7))      # deeper groups (far from the strip) arrive later


def test_every_tile_input_has_one_station():
    g = _gen()
    for s in range(32):
        for t in list(range(8)) + ['j']:
            assert (s, t) in g.s1_of
        for t in range(8):
            assert (s, t) in g.rst_of


def _gen_rs():
    a = argparse.Namespace(ch=172.8, ch_even=172.8, ct=345.6, sw=0.0, strip=86.4, halo_tile=21.6, hop=390.0, ns=3, cmd_lead=3,
                           mut_station='K1c0g0', no_place=True, rtrunk=True, ew=P.RS_EW, rs_inj_y=320.0, rs_r1_y=500.0,
                           rs_r2_y=92.0)
    g = P.Gen(a)
    g.build()
    return g


def test_result_trunk_beats_consecutive_in_order_no_collision():
    """KV-RTRUNK: every column injects once, after its y is held, and its beat reaches the header exactly at
    1 + J0 + s (beat s s edges behind beat 0): 32 distinct consecutive slots, beat order = column order"""
    g = _gen_rs()
    D, R = g.timing()
    rs = g.rs_timing(D, D[0] + R[0] - D[0])
    J = {0: rs['J0'], 1: rs['J1']}
    arrive = {}
    for s, (c, j) in rs['node_of_col'].items():
        assert rs['y_ready_vs_out_age'][s] <= rs['inject_cycle_vs_out_age'][s]
        arrive[s] = rs['inject_cycle_vs_out_age'][s] + 1 + (J[c] - j)
    assert sorted(arrive) == list(range(32))
    assert all(arrive[s] == 1 + rs['J0'] + s for s in range(32))
    assert rs['rs_d'] == 2 + rs['J0'] and rs['t_header'] + 1 <= R[0]
    # column c's beats ride trunk c only; the heads are columns 0 / 8
    assert {s for s, (c, _) in rs['node_of_col'].items() if c == 0} == {P.col_of(0, r) for r in range(16)}
    assert rs['node_of_col'][0] == (0, 0) and rs['node_of_col'][8] == (1, 0)


def test_result_trunk_header_f2_adds_one_edge():
    """HKV-PVRS2 10-19: --rs-hd f (qkd_pv_rs_hd_f rev f2, input pin registers) = header 2 edges: RS_D + 1, T / epoch
    sampling cycle unchanged; r (and the legacy leaf) stay at 1"""
    g = _gen_rs()
    D, R = g.timing()
    r = g.rs_timing(D, D[0] + R[0] - D[0])
    g.a.rs_hd = 'f'
    f = g.rs_timing(D, D[0] + R[0] - D[0])
    assert r['header_stages'] == 1 and f['header_stages'] == 2
    assert f['rs_d'] == r['rs_d'] + 1 == 3 + f['J0'] and f['t_header'] == r['t_header']
    assert g.rs_mods()['hd'] == 'qkd_pv_rs_hd_f'
    g.a.rs_native = False
    assert g.rs_timing(D, D[0] + R[0] - D[0])['rs_d'] == r['rs_d']
