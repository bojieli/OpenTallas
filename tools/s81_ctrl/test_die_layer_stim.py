"""die_layer_stim program checks (rom-layer-tput-s81 10-14): the S81 layer stimulus died with a bare
'AssertionError: cycle' when the staged source carried no stage programs (empty layer -> H_STORE waits on a
missing hc_post).  Now: a missing program dir / empty layer and a dangling predecessor are named errors, a true
cycle names its nodes, and every committed layer the layer vehicle runs (L0, L2, L14 Engram, L20) orders cleanly."""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_layer_stim as S  # noqa: E402

PROGS = HERE.parents[1] / 'results/rtl/s81_ctrl_20261008/programs'


def node(i, preds, order=0.0):
    return dict(id=i, preds=list(preds), order=order)


def test_missing_programs_named(tmp_path):
    with pytest.raises(SystemExit, match='no stage programs'):
        S.layer_ops(tmp_path, 'L0')


def test_layer_without_ops_named():
    with pytest.raises(SystemExit, match='L999 has no ops'):
        S.layer_ops(PROGS, 'L999')


def test_dangling_pred_named():
    nodes = {'a': node('a', []), 'st': node('st', ['L0.ffn.hc_post'], 1)}
    with pytest.raises(ValueError, match=r'st <- L0\.ffn\.hc_post'):
        S.topo_order(nodes)


def test_true_cycle_named():
    nodes = {'a': node('a', ['b']), 'b': node('b', ['a']), 'c': node('c', [])}
    with pytest.raises(ValueError, match='cycle among a, b'):
        S.topo_order(nodes)


def test_order_ties_by_source_order():
    nodes = {'x': node('x', [], 2), 'y': node('y', [], 1), 'z': node('z', ['x', 'y'], 0)}
    assert [n['id'] for n in S.topo_order(nodes)] == ['y', 'x', 'z']


@pytest.mark.parametrize('L', ['L0', 'L2', 'L14', 'L20'])
def test_committed_layers_have_ops(L):
    ops = S.layer_ops(PROGS, L)
    ids = {o['id'] for o in ops}
    assert f'{L}.attn.hc_pre' in ids and f'{L}.ffn.hc_post' in ids


def test_dur_override_cli(tmp_path):
    """--dur on a real-master op is refused, an unknown op is named (both before the golden chain is built)."""
    import subprocess
    tool = HERE / 'die_layer_stim.py'
    for arg, msg in (('attn.hc_pre=1', "real master"), ('attn.nosuch=5', 'not in layer')):
        r = subprocess.run([sys.executable, str(tool), str(tmp_path / 'o'), '--cases', '/nonexistent', '--dur', arg],
                           capture_output=True, text=True)
        assert r.returncode != 0 and msg in r.stderr, (arg, r.stderr[-400:])
