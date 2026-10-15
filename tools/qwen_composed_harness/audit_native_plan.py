#!/usr/bin/env python3
"""Audit every emitted embedding/decoder/head word, independently of arithmetic.

No simulation rerun. Reads the exact immutable programs consumed by a live plan.
A target manifest may replace component evidence only with real elaboration and
port bindings; absence fails closed. --out is separate from arithmetic receipts.
"""
import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from native_operation_coverage import audit, operations, sha
from native_coverage_inventory import inventory


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--plan',type=Path,required=True)
    p.add_argument('--embedding-program',type=Path,required=True)
    p.add_argument('--head-program',type=Path,required=True)
    p.add_argument('--target-manifest',type=Path)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    components=inventory(a.root)
    target=json.loads(a.target_manifest.read_text()) if a.target_manifest else {}
    if target:
        components=target['components']
    programs=[('embedding',None,a.embedding_program)]
    layers=[]
    for line in a.plan.read_text().splitlines():
        if not line or line.startswith('#'):continue
        number,epoch,position,image,program,oracle=line.split()
        layers.append(int(number))
        for rank in range(8):programs.append(('layer'+number,rank,Path(program)/('die'+str(rank))/'program.hex'))
    if layers != list(range(36)):
        raise ValueError('native whole-token audit requires the complete original 36-layer plan')
    for rank in range(8):programs.append(('head',rank,a.head_program/('die'+str(rank))/'program.hex'))
    reports=[]
    for stage,rank,path in programs:
        ops=operations(path)
        bindings={}
        for op in ops:
            engine={'unit0':'lv6_compute','unit1':'lv6_compute','unit2':'lv6_compute','unit3':'native_attention_kernel'}.get(op['opcode'],'unknown')
            bindings[op['id']]={**op,'instance':None,'output_provider':'target_rtl','components':[engine,'vm_sram','program_rom'],'operands':[],'results':[]}
        source_manifest=target.get('programs',{}).get(sha(path),{})
        manifest={'program_sha256':sha(path),'required_components':target.get('required_components',list(components)),'components':components,'operations':bindings,**source_manifest}
        if 'elaboration' in target:manifest['elaboration']=target['elaboration']
        report=audit(a.root,path,manifest)
        reports.append({'stage':stage,'rank':rank,**report})
    passed=all(r['native_operation_coverage_pass'] for r in reports)
    report={'schema':'opentallas.qwen_complete_program_native_audit.v1','policy':'Only PHY/off-chip models and expected-only observers allowed. All on-chip engines/controllers/ROM/SRAM/link logic require actual target RTL/macros.','plan_sha256':sha(a.plan),'decoder_layers':layers,'program_count':len(reports),'emitted_operation_count':sum(len(r['operations']) for r in reports),'all_native_operation_coverage_pass':passed,'native_qualified':False,'historical_arithmetic_verdicts_preserved':True,'components':components,'programs':reports}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    if a.out.suffix=='.gz':
        with gzip.open(a.out,'wt') as f:json.dump(report,f,sort_keys=True)
    else:a.out.write_text(json.dumps(report,indent=2)+'\n')
    print(('PASS' if passed else 'FAIL')+' native coverage across '+str(len(reports))+' programs / '+str(report['emitted_operation_count'])+' emitted operations; historical arithmetic receipts unchanged')
    raise SystemExit(0 if passed else 1)

if __name__=='__main__':main()
