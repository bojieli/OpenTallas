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
