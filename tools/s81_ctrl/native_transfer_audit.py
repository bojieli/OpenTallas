#!/usr/bin/env python3
"""Audit immutable stage programs; abstract op coverage is not native execution."""
import argparse, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def audit(programs):
    idx=programs/'index.json'
    sources=[];changed=[];hload=[];hstore=[];posts=0
    for stage in json.loads(idx.read_text())['stages']:
        p=programs/(stage['stage']+'.json')
        raw=p.read_bytes();d=json.loads(raw)
        ids=[o['id'] for o in d['ops']]
        ps=[i for i in ids if i.endswith('.hc_post')]
        posts+=len(ps)
        if ps:changed.append({'stage':d['stage'],'post_ids':ps})
        hload.extend(i for i in ids if 'h_load' in i.lower())
        hstore.extend(i for i in ids if 'h_store' in i.lower())
        sources.append({'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(raw).hexdigest()})
    return {'schema':'opentallas.s81.native-transfer-audit.v1',
      'program_index_sha256':hashlib.sha256(idx.read_bytes()).hexdigest(),
      'abstract_hc_post_ops':posts,'abstract_changed_h_groups':len(changed),
      'changed_h_groups':changed,'explicit_h_load_ops':hload,'explicit_h_store_ops':hstore,
      'native_executed_transfer_count':None,'native120_dispatcher_qualified':False,
      'reason':'Committed stage jobs use abstract operator indices and price durations. Actual engine descriptor lowering, native120 program, and measured execution binding are missing; abstract changed-h groups do not measure transfers.',
      'sources':sources}
def main():
    a=argparse.ArgumentParser();a.add_argument('--programs',type=Path,default=ROOT/'results/rtl/s81_ctrl_20261008/programs');a.add_argument('--out',type=Path)
    args=a.parse_args();out=json.dumps(audit(args.programs),indent=2)+'\n'
    if args.out:args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(out)
    else:print(out,end='')
if __name__=='__main__':main()
