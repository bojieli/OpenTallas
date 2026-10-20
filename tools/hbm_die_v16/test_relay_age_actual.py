#!/usr/bin/env python3
"""Causal age-guard receipts on exact emitted production path partitions."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys
import d4g_relay_age_audit as A

TARGETS = [('pgp_SE','command','su_SE0','vmw_cmd'),
           ('pgp_NE','command','sucore_NE','red_cmd'),
           ('pgp_SW','command','sucore_SW','red_cmd'),
           ('hb_vms_SW','vmstat','vm_status4','quadrant_status')]


def subset(layer, compiler, targets):
    buses = []
    for b in layer['relay_splice_v2']:
        if any((b['driver'],p,d,dp) in targets for (p,_),ls in zip(b['driver_bits'],b['loads']) for d,dp,_ in ls):
            buses.append(copy.deepcopy(b))
    names = {n for b in buses for node in b['nodes'] for n in node['names']}
    names |= {n for b in buses for sk in b['sinks'].values() for st in sk['chain'] for n in st}
    ids = {b['bus'] for b in buses}
    return dict(instances=[i for i in layer['instances'] if i['name'] in names], relay_splice_v2=buses), \
           dict(compiler=[x for x in compiler['compiler'] if x['bus'] in ids])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--layer',required=True);ap.add_argument('--compiler-report',required=True)
    ap.add_argument('--pre-relay-contract',required=True);ap.add_argument('--contract',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    layer,report,contract=A.load(a.layer),A.load(a.compiler_report),A.load(a.contract)
    pre=A.load(a.pre_relay_contract)
    fixture,fr=subset(layer,report,TARGETS)
    raw=A.audit(fixture,fr,pre)
    coverage=[]
    for si,sp,di,dp in TARGETS:
        path=next(x for x in raw['paths'] if x['producer']==[si,sp] and x['consumer']==[di,dp])
        assert path['complete_original_source_bit_map']
        assert path['mixed_plain_forwarded'] and path['unknown_age'] and path['status']=='FAIL',path
        bits={d for row in path['rows'] for s,sh,d,dh in row['source_to_sink_ranges_half_open'] for d in range(d,dh)}
        width=contract['instances'][di]['ports'][dp]['bits']
        expected={b for e in pre['edges'] if e['source'][:2]==[si,sp] and e['sink'][:2]==[di,dp] for b in range(e['sink'][2],e['sink'][3])}
        assert bits==expected,(di,dp,len(bits),len(expected),width)
        coverage.append(dict(producer=[si,sp],consumer=[di,dp],full_consumer_port_width=width,source_partition_bits=len(bits),rows=path['rows']))
    (out/'actual_mixed_layer.json').write_text(json.dumps(fixture))
    (out/'actual_mixed_compiler.json').write_text(json.dumps(fr))
    (out/'actual_mixed_coverage.json').write_text(json.dumps(coverage,indent=2))
    tool=Path(A.__file__)
    args=[sys.executable,str(tool),'--layer',str(out/'actual_mixed_layer.json'),
          '--compiler-report',str(out/'actual_mixed_compiler.json'),'--pre-relay-contract',a.pre_relay_contract,'--out',str(out/'strict.json')]
    strict=subprocess.run(args,capture_output=True,text=True)
    assert strict.returncode==1,strict
    diagnostic=subprocess.run(args+['--diagnostic-incomplete-ages'],capture_output=True,text=True)
    assert diagnostic.returncode==0,diagnostic
    diagnostic_report=json.loads((out/'strict.json').read_text())
    assert diagnostic_report['verdict']=='FAIL' and diagnostic_report['qualification_eligible'] is False
    assert diagnostic_report['calendar_qualified'] is False
    # Numeric compiler E is still not current measured clock/reset evidence.
    numeric=copy.deepcopy(fr);numeric['landing']={'rows':[{'E':1}]}
    assert A.audit(fixture,numeric,pre)['unknown_groups']==raw['unknown_groups']
    # Actual reducer partition: fixed 12/12 passes static age; remove its
    # emitted pad to recover original torn 12/11 tag (causal negative).
    plain,pr=subset(layer,report,[('sucore_NW','red_tag','cxrc_NW_q','red_tag')])
    fixed=A.audit(plain,pr,pre);assert fixed['verdict']=='PASS',fixed
    broken=copy.deepcopy(plain)
    fast=next(b for b in broken['relay_splice_v2'] if b['bus']=='rf1262')
    fast['sinks']['cxrc_NW_q']['chain'].pop()
    torn=A.audit(broken,pr,pre);assert torn['unequal_known_groups']>=1 and torn['verdict']=='FAIL'
    wrong=copy.deepcopy(plain)
    row=next(b for b in wrong['relay_splice_v2'] if b['bus']=='rf1262')
    row['driver_bits'][1][1]+=1000
    wrong_result=A.audit(wrong,pr,pre)
    assert any(not x['complete_original_source_bit_map'] for x in wrong_result['paths'])
    assert wrong_result['verdict']=='FAIL'
    omitted=copy.deepcopy(plain)
    row=next(b for b in omitted['relay_splice_v2'] if b['bus']=='rf1262')
    row['driver_bits'].pop();row['loads'].pop();row['bits']-=1
    omitted_result=A.audit(omitted,pr,pre)
    assert any(not x['complete_original_source_bit_map'] for x in omitted_result['paths'])
    assert omitted_result['verdict']=='FAIL'
    missing=copy.deepcopy(plain);missing['instances'].pop()
    assert A.audit(missing,pr,pre)['defects']
    assert A.audit(plain,{'compiler':[]},pre)['verdict']=='FAIL'
    assert A.audit({'instances':[],'relay_splice_v2':[]},{'compiler':[]},pre)['verdict']=='FAIL'
    verdict=dict(actual_paths=len(coverage),all_consumer_bits_covered=True,
                 strict_cli_exit=strict.returncode,diagnostic_exit=diagnostic.returncode,
                 diagnostic_qualified=False,plain_fixed=fixed['verdict'],
                 causal_removed_pad=torn['verdict'],checks=12,
                 source_scope='actual r7 emitted partitions; no simulation or physical qualification')
    (out/'verdict.json').write_text(json.dumps(verdict,indent=2)+'\n')
    print('ACTUAL_AGE_GUARDS_PASS',json.dumps(verdict))


if __name__=='__main__':
    main()
