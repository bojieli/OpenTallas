"""The leaf packet boundary must follow RTL, including a real-crossing mutant."""
import ast
import copy
import json
import re
from pathlib import Path
import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

def validate(entry):
    dn, up = 'bus:leafdn_i0', 'bus:leafup_o0'
    for ci, ports in entry.items():
        if ci in ('u_lf.u_vn.u_a', 'u_lf.u_vn.u_b'):
            for n in ('n_go', 'n_pre'):
                assert dn not in ports.get(n, [])
        if ci == 'u_lf.u_vn.u_b':
            for n in ('rb_v', 'rb_d'):
                assert dn in ports[n], f'real boundary lost: {ci}.{n}'
        if ci == 'u_lf.u_vq':
            for n in ('k', 'sid', 'm_v', 'm_q', 'm_b', 'm_i'):
                assert dn not in ports.get(n, [])
            for n in ('xf_v', 'xf_s', 'xf', 'fault'):
                assert up in ports[n], f'real boundary lost: {ci}.{n}'

def test_leaf_boundary_follows_actual_rtl_and_generator():
    text=(ROOT/'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice.sv').read_text()
    header=text.split('module ot_s81sl_leaf',1)[1].split(');',1)[0]
    header=re.sub(r'//[^\n]*', '', header)
    for n in ('n_go','n_pre','m_v','m_q','m_b','m_i'):
        assert not re.search(r'\b'+n+r'\b', header)
    assert '.n_go(n_go_n), .n_pre(n_pre_n)' in text
    assert '.d({m_q_p, m_b_p, m_i_p})' in text
    assert '.rb_v(rb_v), .rb_d(rb_d)' in text
    # Evaluate only the pure connectivity constants, never regenerate the plan.
    tree=ast.parse((HERE/'gen_plan_v4.py').read_text()); ns={}
    wanted={'_LF','_HC','_ST','_DN','_UP','CORE_CONNS'}
    nodes=[n for n in tree.body if (isinstance(n,ast.FunctionDef) and n.name=='_cc') or (isinstance(n,ast.Assign) and any(isinstance(v,ast.Name) and v.id in wanted for t in n.targets for v in ast.walk(t)))]
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'connectivity-constants','exec'),ns)
    validate(ns['CORE_CONNS']['leaf'])
    data=json.load(open(HERE/'core_conns.json'))
    leaves=[e for e in data.values()if 'u_lf.u_vn.u_b' in e]
    assert leaves
    for e in leaves:validate(e)
    mutant=copy.deepcopy(leaves[0]);mutant['u_lf.u_vn.u_b']['rb_d']=[]
    with pytest.raises(AssertionError,match='real boundary lost'):
        validate(mutant)
