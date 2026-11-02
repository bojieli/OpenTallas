"""Reduction-OR state relations require native BASE and joint next-state proof."""
from collections import defaultdict
import itertools
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import lec
from test_lec_memory_layout import _seq, _sim_prove
from test_lec_cube_x import _design, _assert_constant

KEYS = ['ff:u_dut.x', 'ff:u_dut.y']
HINT = ['gate', 'ff:u_dut.z', ['cube', 'gold', KEYS, [0, 0], 1]]


def design(tmp_path, mutant=None):
    def OR(m, a, b):
        return m.AND(a ^ 1, b ^ 1) ^ 1
    def gold(m, l):
        return dict(x=m.AND(l['rst_n'], l['a']), y=m.AND(l['rst_n'], l['b']),
                    o=OR(m,l['x'],l['y']))
    def gate(m, l):
        d = m.AND(l['a'],l['b']) if mutant == 'and' else OR(m,l['a'],l['b'])
        z = OR(m,l['rst_n'] ^ 1,d) if mutant == 'base1' else m.AND(l['rst_n'],d)
        if mutant == 'unknown_base':
            z = d
        return dict(z=z,o=l['z'])
    g,gm=_seq(tmp_path,'g',['rst_n','a','b'],['x','y','o'],gold)
    t,tm=_seq(tmp_path,'t',['rst_n','a','b'],['z','o'],gate)
    return lec.Lec(g,gm,t,tm)


def run(tmp_path,monkeypatch,L,hints):
    monkeypatch.setattr(lec,'prove',_sim_prove)
    rec=lec.apply_hints(L,hints,tmp_path,100,[])
    m,_=L.build()
    return rec,_sim_prove(m)


def test_reduction_or_base_and_joint_step(tmp_path,monkeypatch):
    L=design(tmp_path)
    rec,st=run(tmp_path,monkeypatch,L,[HINT])
    assert rec['inverse_cube_base'][0]['covered']
    assert st['hyp:gate:ff:u_dut.z']=='proved' and st['ff:u_dut.o']=='proved'
    assert L.hyp['gate','ff:u_dut.z'][-1]==1
    assert not L.cons


@pytest.mark.parametrize('mutant',['base1','unknown_base'])
def test_wrong_or_unknown_reset_base_refused(tmp_path,monkeypatch,mutant):
    L=design(tmp_path,mutant)
    rec,_=run(tmp_path,monkeypatch,L,[HINT])
    assert rec['inverse_cube_refused'] and ('gate','ff:u_dut.z') not in L.hyp


def test_restored_inverse_profile_cannot_bypass_native_base(tmp_path):
    L=design(tmp_path,'base1')
    L.hyp['gate','ff:u_dut.z']=tuple(HINT[2])
    L.build()
    assert not L.hyp and L.inverse_cube_base_refused


@pytest.mark.parametrize('mutant,hint',[
    ('and',HINT),
    (None,['gate','ff:u_dut.z',['cube','gold',KEYS,[0,0],0]]),
    (None,['gate','ff:u_dut.z',['cube','gold',KEYS[:1],[0],1]])])
def test_wrong_next_state_polarity_or_omitted_group_drops(tmp_path,monkeypatch,mutant,hint):
    L=design(tmp_path,mutant)
    _,st=run(tmp_path,monkeypatch,L,[hint])
    assert ('gate','ff:u_dut.z') not in L.hyp
    assert st['ff:u_dut.o']=='differs'


def test_arbitrary_constraint_cannot_hide_wrong_group_function(tmp_path,monkeypatch):
    L=design(tmp_path,'and')
    _,st=run(tmp_path,monkeypatch,L,[HINT,['cons','gold',KEYS,[[0,0]]]])
    assert not L.cons and ('gate','ff:u_dut.z') not in L.hyp
    assert st['ff:u_dut.o']=='differs'


def test_inverse_simulation_refinement_uses_same_polarity(tmp_path):
    L=design(tmp_path)
    L.hyp['gate','ff:u_dut.z']=tuple(HINT[2])
    lec.sim_refine(L,[],defaultdict(int),words=2)
    assert ('gate','ff:u_dut.z') in L.hyp


def test_malformed_inversion_refused(tmp_path,monkeypatch):
    L=design(tmp_path)
    rec,_=run(tmp_path,monkeypatch,L,[['gate','ff:u_dut.z',['cube','gold',KEYS,[0,0],2]]])
    assert rec['skipped'] and ('gate','ff:u_dut.z') not in L.hyp


def test_inverse_ternary_predicate_keeps_known_false_atoms(monkeypatch):
    # Exercise only the X rail here; native BASE refusal has separate controls.
    monkeypatch.setattr(lec,'inverse_cube_base_check',lambda *a: dict(covered=True))
    for values in itertools.product((0,1,None),repeat=2):
        for target in itertools.product((0,1),repeat=2):
            false=any(v is not None and v!=t for v,t in zip(values,target))
            cube=0 if false else 1 if None not in values else None
            predicate=None if cube is None else cube ^ 1
            for gate in (0,1):
                g,gm=_design(values);t,tm=_design((),gate=gate)
                L=lec.Lec(g,gm,t,tm)
                L.hyp['gate','ff:u.hot']=('cube','gold',['ff:u.st[0]','ff:u.st[1]'],list(target),1)
                m,_=L.build(with_compare=False)
                _assert_constant(m,int(predicate is not None and predicate!=gate))
