#!/usr/bin/env python3
"""Merge successful independent allocations, preserving failures and pricing every lane."""
import argparse
import json
import sys
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('plan',type=Path);p.add_argument('--base',type=Path,required=True)
    p.add_argument('--chunks',type=Path,nargs='+',required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--ledger',type=Path,required=True)
    a=p.parse_args();root=Path(__file__).resolve().parents[3];sys.path.insert(0,str(root))
    from tools.die_plan import schema as S
    from tools.die_plan.gen import latency_table
    raw=json.loads(a.plan.read_text());base=json.loads(a.base.read_text());passed={};failed=[];slots=[]
    for path in a.chunks:
        chunk=json.loads(path.read_text())
        for r in chunk['results']:
            if r['verdict']=='FAIL':failed.append(dict(source=str(path),**r));continue
            tn=r['type']
            if tn in passed:raise ValueError('duplicate successful type '+tn)
            raw['partition_types'][tn]=chunk['types'][tn];passed[tn]=str(path);slots.extend(r['slots'])
    if {r['type'] for r in failed}-passed.keys():raise ValueError('unresolved failed types')
    old=latency_table(S.Plan(base,a.base));fresh=latency_table(S.Plan(raw,a.out));raw['latency']={'lanes':fresh}
    changes={lid:dict(old_cycles=old.get(lid,{}).get('cycles'),new_cycles=v['cycles'],delta=v['cycles']-old.get(lid,{}).get('cycles',0)) for lid,v in fresh.items() if old.get(lid,{}).get('cycles')!=v['cycles']}
    receipt=dict(status='ALLOCATED PLANNING PROTOTYPE; G0C, per-type actual placement and infra gates pending',successful_types=len(passed),preserved_failure_attempts=failed,source_chunks=passed,slots=slots,lane_cycle_changes=changes,max_slot_hop_um=max(max(v.get('hops_um',[0])) for v in slots))
    a.out.write_text(json.dumps(raw,separators=(',',':'))+'\n');a.ledger.write_text(json.dumps(receipt,indent=1)+'\n')
    print('MERGED',len(passed),'types;',len(changes),'lane cycle changes; maxhop',receipt['max_slot_hop_um'])


if __name__=='__main__':main()
