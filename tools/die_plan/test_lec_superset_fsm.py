"""HEAD-R18 11-23 (hd_ctl routed LEC, 318 differs in g_seqf.u_seq): with OT_LEC_SUPERSET_VEC=1 a yosys one-hot FSM
recode (gold binary st[1:0], gate st[0..2] under the same base name) must not keep the common bit names; the whole
gate vector is re-keyed so fsm_proposals pairs it by cube hypotheses and the design proves.  A wrong encoding still
fails, and a real dead-bit superset (gold not dense from 0) keeps its common names."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402
from test_lec import _sim_prove  # noqa: E402
from test_lec_fsm_repropose import fsm_design, vec_design  # noqa: E402


def test_superset_flag_leaves_fsm_recode_to_cube_search(monkeypatch):
    monkeypatch.setenv('OT_LEC_SUPERSET_VEC', '1')
    g, gm = fsm_design(False)
    t, tm = fsm_design(True)
    L = lec.Lec(g, gm, t, tm)
    assert L.superset_fsm == ['ff:u_dut.st'] and not L.superset_extra
    assert 'ff:u_dut.st[0]' not in L.matched and 'ff:u_dut.st#t[2]' in L.tonly
    assert lec.fsm_proposals(L, []) == 3
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert set(_sim_prove(m).values()) == {'proved'}


def test_superset_fsm_wrong_encoding_still_fails(monkeypatch):
    monkeypatch.setenv('OT_LEC_SUPERSET_VEC', '1')
    g, gm = fsm_design(False)
    t, tm = fsm_design(True)
    L = lec.Lec(g, gm, t, tm)
    lec.fsm_proposals(L, [])
    key = next(k for k, h in L.hyp.items() if h[0] == 'cube')
    h = L.hyp[key]
    L.hyp[key] = (h[0], h[1], h[2], [v ^ 1 for v in h[3]])
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert 'differs' in _sim_prove(m).values()


def test_dead_bit_superset_unchanged(monkeypatch):
    monkeypatch.setenv('OT_LEC_SUPERSET_VEC', '1')
    g, gm = vec_design([1, 2])
    t, tm = vec_design([0, 1, 2])
    L = lec.Lec(g, gm, t, tm)
    assert not L.superset_fsm and {'ff:u_dut.rec[1]', 'ff:u_dut.rec[2]'} <= set(L.matched)
