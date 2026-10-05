#!/usr/bin/env python3
"""Audit unified-model source currency without rerunning RTL or changing history."""
import ast
import hashlib
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/qwen_hbm_connected_20261001/unified_source_currency_r2.json'
OLD='7ce6b60c4'
CURRENT='11f5908af38f016c8351e5dd55cae538d07c753b'
ADDED={'w10_capacity_diagnosis','w10_pinaccess_contract_review'}
FLAGS={'--w10-capacity','--w10-pinaccess-contract'}
ATTRS={'w10_capacity','w10_pinaccess_contract'}

def get(rev):
    return subprocess.check_output(['git','show',rev+':tools/uarch_model.py'],cwd=ROOT)

def digest(raw):return hashlib.sha256(raw).hexdigest()

def audit():
    old,current=get(OLD),get(CURRENT)
    a,b=ast.parse(old),ast.parse(current)
    removed=[]
    body=[]
    for n in b.body:
        if isinstance(n,ast.FunctionDef) and n.name in ADDED:
            removed.append(n.name);continue
        if isinstance(n,ast.FunctionDef) and n.name=='main':
            kept=[]
            for q in n.body:
                flag=(isinstance(q,ast.Expr) and isinstance(q.value,ast.Call)
                      and isinstance(q.value.func,ast.Attribute) and q.value.func.attr=='add_argument'
                      and q.value.args and isinstance(q.value.args[0],ast.Constant)
                      and q.value.args[0].value in FLAGS)
                branch=(isinstance(q,ast.If) and isinstance(q.test,ast.Attribute)
                        and isinstance(q.test.value,ast.Name) and q.test.value.id=='a'
                        and q.test.attr in ATTRS)
                if flag or branch:removed.append(ast.unparse(q));continue
                kept.append(q)
            n.body=kept
        body.append(n)
    b.body=body
    assert len(removed)==6
    assert ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False)
    # No ordinary model path invokes the two new explicitly selected audits.
    assert not any(isinstance(n,ast.Name) and n.id in ADDED for n in ast.walk(b))
    receipts={}
    for name in ['L2_injector_before_RTL_r2.json','HBM_ingress_before_RTL_r2.json']:
        p=OUT.parent/name;x=json.loads(p.read_text())
        assert x['source_sha256']['tools/uarch_model.py']==digest(current)
        assert x['current_generator_replay']['numeric_values_identical']
        assert not x['adoption'] and not x['physical_build_ready']
        receipts[str(p.relative_to(ROOT))]=digest(p.read_bytes())
    x=dict(schema='opentallas.unified-model-source-currency.v1',
        current_revision=CURRENT,current_generator_sha256=digest(current),
        historical_revision=OLD,historical_generator_sha256=digest(old),
        computational_AST_identical_after_exact_audit_exclusions=True,
        excluded_added_functions=sorted(ADDED),excluded_CLI_flags=sorted(FLAGS),
        excluded_nodes=removed,ordinary_paths_do_not_call_added_audits=True,
        covered_models=['qwen_rom','qwen_hbm','v41_rom','v41_hbm'],
        scope='All retained computational functions, constants, preset definitions and ordinary CLI branches are AST-identical; no new numerical or RTL qualification claimed',
        current_Qwen_L2_and_ingress_receipt_sha256=receipts,
        historical_records_unchanged=True,adoption=False,physical_build_ready=False,
        audit_tool_sha256=digest(Path(__file__).read_bytes()))
    with OUT.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
    print('PASS: all four model computational ASTs unchanged; r2 records match current U2da5 at11f590')

if __name__=='__main__':audit()
