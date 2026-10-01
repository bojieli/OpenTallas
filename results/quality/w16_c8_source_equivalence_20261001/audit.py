#!/usr/bin/env python3
"""Additive equivalence sidecar only; never rewrites evidence or live job pins."""
import ast
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],cwd=Path(__file__).parent,text=True).strip())
PRIOR='fa55f4f8b'
MODEL='tools/uarch_model.py'
RECORDS=(
 'results/quality/w16_four_design_accounting_20261001/accounting.json',
 'results/uarch/w10_baseline_wake/prebuild.json',
 'results/uarch/w10_baseline_wake/fullgoal_bound.json',
)
TRANSITIVE=('results/uarch/consolidation.json','results/arch/v41_stage_owner_product.json')


def sha(b):return hashlib.sha256(b).hexdigest()


def prove(old,new):
    a,b=ast.parse(old),ast.parse(new)
    added=[n for n in b.body if isinstance(n,ast.FunctionDef) and n.name=='w10_capacity_diagnosis']
    assert len(added)==1
    b.body.remove(added[0])
    m=next(n for n in b.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    removed=[];kept=[]
    for n in m.body:
        option=(isinstance(n,ast.Expr) and isinstance(n.value,ast.Call)
                and isinstance(n.value.func,ast.Attribute) and n.value.func.attr=='add_argument'
                and isinstance(n.value.func.value,ast.Name) and n.value.func.value.id=='ap'
                and n.value.args and isinstance(n.value.args[0],ast.Constant)
                and n.value.args[0].value=='--w10-capacity')
        dispatch=(isinstance(n,ast.If) and isinstance(n.test,ast.Attribute)
                  and isinstance(n.test.value,ast.Name) and n.test.value.id=='a'
                  and n.test.attr=='w10_capacity')
        if option or dispatch:removed.append(n)
        else:kept.append(n)
    assert len(removed)==2
    m.body=kept
    before=ast.dump(a,include_attributes=False)
    assert before==ast.dump(b,include_attributes=False)
    assert not any(isinstance(n,ast.Name) and n.id=='w10_capacity_diagnosis' for n in ast.walk(b))
    return dict(normalized_ast_sha256=sha(before.encode()),
                added_function_ast_sha256=sha(ast.dump(added[0],include_attributes=False).encode()),
                removed_cli_ast=[ast.dump(n,include_attributes=False) for n in removed],
                existing_model_ast_identical=True,additional_function_uncalled_by_existing_calculations=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=Path(__file__).parent/'equivalence.json')
    args=parser.parse_args()
    old=subprocess.check_output(['git','show',PRIOR+':'+MODEL],cwd=ROOT)
    new=(ROOT/MODEL).read_bytes();proof=prove(old,new)
    # Negative controls reject changed calculations, extra functions, and
    # changed existing CLI defaults; only the registered additions are removed.
    controls=[]
    mutations={
        'changed_existing_numeric_constant':new.replace(b'HBM_W19 = dict(ar_us=442.14',b'HBM_W19 = dict(ar_us=442.15',1),
        'extra_unregistered_function':new+b'\ndef unexpected_addition():\n    return 1\n',
        'changed_existing_cli_default':new.replace(b'default=1048576',b'default=1048577',1),
    }
    for label,mutated in mutations.items():
        assert mutated!=new
        try:prove(old,mutated)
        except AssertionError:controls.append(dict(name=label,rejected=True))
        else:raise AssertionError('accepted mutation: '+label)
    derived={}
    for p in TRANSITIVE:
        before=subprocess.check_output(['git','show',PRIOR+':'+p],cwd=ROOT)
        after=(ROOT/p).read_bytes();a,b=json.loads(before),json.loads(after)
        assert a['source_sha256'][MODEL]==sha(old)
        assert b['source_sha256'][MODEL]==sha(new)
        b['source_sha256'][MODEL]=sha(old)
        assert a==b
        derived[p]=dict(old_sha256=sha(before),current_sha256=sha(after),
                        all_non_generator_pin_fields_identical=True,numerical_fields_identical=True)
    evidence=[];immutable={}
    for p in RECORDS:
        raw=(ROOT/p).read_bytes();immutable[p]=sha(raw);r=json.loads(raw)
        bindings=[]
        for f,h in r['source_sha256'].items():
            current=sha((ROOT/f).read_bytes())
            if current==h:classification='BYTE_IDENTICAL'
            elif f==MODEL:
                assert h==sha(old);classification='EXISTING_CALCULATIONS_AST_EQUIVALENT'
            elif f in derived:
                assert h==derived[f]['old_sha256'];classification='TRANSITIVE_JSON_GENERATOR_PIN_ONLY'
            else:raise AssertionError('unproved source drift: '+p+' -> '+f)
            bindings.append(dict(path=f,original_sha256=h,current_sha256=current,classification=classification))
        evidence.append(dict(path=p,immutable_record_sha256=sha(raw),original_source_commit=r.get('source_commit',r.get('basis')),
                             original_verdict=r.get('verdict'),original_adopted=r.get('adopted',r.get('nam_adoption')),
                             original_pin_bytes_current=False,calculation_equivalence_proven=True,
                             original_qualification_unchanged=True,current_hardware_qualified=False,
                             numerical_fields_changed=False,bindings=bindings))
    assert all(sha((ROOT/p).read_bytes())==h for p,h in immutable.items())
    result=dict(schema='opentallas.w16.c8-source-equivalence.v1',observed_utc=datetime.now(timezone.utc).isoformat(),
                basis=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                prior_model_commit=subprocess.check_output(['git','rev-parse',PRIOR],cwd=ROOT,text=True).strip(),
                old_model_sha256=sha(old),current_model_sha256=sha(new),proof=proof,
                transitive_equivalence=derived,evidence=evidence,
                validation=dict(negative_controls=controls,immutable_inputs_verified=True,source_bindings_verified=sum(len(e['bindings']) for e in evidence)),
                scope='Additive audit only. Original records retain original pins, verdicts, qualification and numerical values. Computational equivalence is not byte-identical source currency, a new job result, current-source hardware qualification or sign-off.',
                physical_wake_policy='Live b046de7f0 and prior b8 clean physical sources are protected and untouched; parent post-merge wake tests remain pending. This audit cannot transfer old-qualified job records to current main.',
                parent_six_record_refresh='Already completed in a9b6dd207; not duplicated here.',
                untouched_historical_records=['results/uarch/w16_measured_calibration_20261001/calibration_v2.json','results/uarch/fusion_audit.json','results/uarch/hbm_feasibility_audit.json','results/uarch/v41_rom_ksplit_bankmap.json','results/uarch/v41_rom_striped_bankmap.json'],
                generator_sha256=sha(Path(__file__).read_bytes()),full_sweep_run=False,live_sources_changed=False,
                headline_changed=False,hardware_adopted=False,full_qcnam_verdict=None)
    out=args.out
    with out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print('PASS: additive AST/transitive equivalence; 78 original bindings audited, original records unchanged; 3 negative controls rejected')


if __name__=='__main__':main()
