#!/usr/bin/env python3
"""Independently check every down phase of a fresh CAP-aware source field."""
import argparse,json,re,hashlib
from pathlib import Path
from collections import Counter
import numpy as np
from check_ret_score_order import inspect


def check(field,kseg,bf16,experts):
    records=[];seen=set();counts=Counter()
    for p in field['phases']:
        if p['op']!='ffn.down':continue
        name=p['mat'].removesuffix('.w2');expert=6 if name=='shared'else experts.index(int(name.removeprefix('exp')))
        for row in p['row_index']:
            if (expert,row)in seen:raise ValueError('duplicate down expert/global row across full source field')
            seen.add((expert,row))
        plan=dict(p['plan']);plan.update(ret=p['ret'],nseg=p['nseg'],rows=p['rows'])
        f=dict(frame=field['frame'],phase=p['phase'],source_rows=p['row_index'],plan=plan)
        r=inspect(f,kseg,bf16,expert);r['expert_slot']=expert;r['mat']=p['mat'];records.append(r);counts[p['mat']]+=len(r['rows'])
    if not records:raise ValueError('source field has no actual down phases')
    return dict(status='PASS_INDEPENDENT_CAP_AWARE_FULLFIELD_FORESTS',frame=field['frame'],down_phases=len(records),checked_rows=len(seen),
        checked_Ksegments=5*len(seen),checked_returned_subtrees=sum(len(p['ret'])for p in field['phases']if p['op']=='ffn.down'),row_counts=dict(counts),records=records,
        producer_evaluator_imported=False,old_norm_partials_read=False,actual_native_CAP_runtime=False,actual_CW_payload_seam=False,actual_commit_or_RD_leases=False,physical_phase_qualified=False,HOST_START_authority=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in('field','kseg','bf16','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--experts',type=int,nargs=6,default=[61,69,112,170,299,357]);a=p.parse_args()
    if a.out.exists():raise ValueError('fresh verdict required')
    f=json.loads(a.field.read_text());k=np.fromfile(a.kseg,'<u4').reshape(7,5120,5);b=np.fromfile(a.bf16,'<u4').reshape(7,5120)
    r=check(f,k,b,a.experts)
    from copy import deepcopy
    bad=deepcopy(f);phase=next(p for p in reversed(bad['phases'])if p['op']=='ffn.down');phase['ret'][-1][2]^=1
    try:check(bad,k,b,a.experts)
    except ValueError as error:r['late_phase_payload_control']=dict(rejected=True,phase=phase['phase'],reason=str(error))
    else:raise ValueError('late full-field payload corruption was not caught')
    r['source_field_sha256']=hashlib.sha256(a.field.read_bytes()).hexdigest();r['fresh_Kseg_sha256']=hashlib.sha256(a.kseg.read_bytes()).hexdigest();r['fresh_BF16_sha256']=hashlib.sha256(a.bf16.read_bytes()).hexdigest()
    a.out.write_text(json.dumps(r,indent=1)+'\n');print(r['status'],r['down_phases'],'phases',r['checked_rows'],'rows',r['checked_returned_subtrees'],'actualsubtrees')
