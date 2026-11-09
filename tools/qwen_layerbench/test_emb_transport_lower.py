"""QC-TRANSPORT-FIX-3 11-09: the bound-plan embedding / RoPE return move (DV_EMB_TRANSPORT=dro_added=N)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dv_lower as D  # noqa: E402
import dv_lower_mat as M  # noqa: E402
import dv_lower_vec as V  # noqa: E402


class FakeSched:
    def __init__(self):
        self.edges = []

    def cmd(self, edge, word, label):
        self.edges.append(edge)


def _rope(monkey_words=(1, 2, 3)):
    saved = V.rope_words
    V.rope_words = lambda pos: list(monkey_words)
    try:
        s = FakeSched()
        cal, nxt = V.rope_rx(s, 100, dict(ROPE=dict(base=32)), None)
    finally:
        V.rope_words = saved
    return s.edges, cal, nxt


def _embed():
    ch = M.Chain(D.slice_map())
    em = M.lower_embed(100, ch)
    return em, dict(ch.used)


def _with_env(value, fn):
    import os
    saved = os.environ.pop('DV_EMB_TRANSPORT', None)
    try:
        if value is not None:
            os.environ['DV_EMB_TRANSPORT'] = value
        return fn()
    finally:
        os.environ.pop('DV_EMB_TRANSPORT', None)
        if saved is not None:
            os.environ['DV_EMB_TRANSPORT'] = saved


def test_default_is_zero():
    assert _with_env(None, D.emb_dro_added) == 0


def test_bad_spec_raises():
    try:
        _with_env('added=11', D.emb_dro_added)
    except D.LowerError:
        return
    raise AssertionError('bad spec accepted')


def test_rope_moves_arm_and_words_together():
    e0, c0, n0 = _with_env(None, _rope)
    e1, c1, n1 = _with_env('dro_added=11', _rope)
    assert [x + 11 for x in e0] == e1
    assert [x['edge'] + 11 for x in c0] == [x['edge'] for x in c1]
    assert n0 + 11 == n1


def test_rope_arm_lead_unchanged():
    e1, c1, _ = _with_env('dro_added=11', _rope)
    assert c1[0]['edge'] - e1[0] == V.ROPE_ARM_LEAD


def test_embedding_landing_moves():
    a, ua = _with_env(None, _embed)
    b, ub = _with_env('dro_added=11', _embed)
    assert b['word0'] == a['word0'] + 11
    assert sorted(ub) == sorted(e + 11 for e in ua)
    assert a['expected_vm'] == b['expected_vm']
