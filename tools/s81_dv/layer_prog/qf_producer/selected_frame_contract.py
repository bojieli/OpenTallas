#!/usr/bin/env python3
"""Actual selected MU3 inventory and private wq_b placement obligations.

Refuse missing hardware instead of pretending every head owns eight frames.
This emits source/model records, not production images or launch calendars.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
from head_local_contract import storage_offset

EXPECTED='61b683b697d17b7d6d1619352d302648d835822677c02097ce48639a0aa399b8'


def strap(x):
    m=re.fullmatch(r"\d+'([hdb])([0-9a-fA-F]+)",x)
    if not m:raise ValueError(f'not a real constant strap: {x}')
    return int(m[2],dict(h=16,d=10,b=2)[m[1]])


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--inventory',required=True)
    ap.add_argument('--plan',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();inv=json.loads(Path(a.inventory).read_text());plan=json.loads(Path(a.plan).read_text())
    if inv['sha256']!=EXPECTED:raise ValueError('foreign selected die snapshot')
    byname={x['name']:x for x in inv['frames']}
    blocks={x['name']:x for x in plan['blocks']}
    assert {x['name'] for x in plan['blocks'] if x['kind']=='frame'}=={n[2:] for n in byname}
    assert len(byname)==122 and len(inv['slices'])==16
    links={x['i']:x for x in plan['links']}
    rows=[];old_missing=0
    for s in inv['slices']:
        h=strap(s['ports']['sid']);group=blocks[s['name'][2:]]['group']
        frames=sorted(n for n in byname if blocks[n[2:]]['group']==group)
        n=len(frames)
        if n not in (6,7,8):raise ValueError('new selected shape needs explicit sizing')
        count0,rem=divmod(512,n);start=0;records=[]
        for i,name in enumerate(frames):
            f=byname[name];count=count0+int(i<rem)
            dims=list(range(start,start+count));start+=count
            k=strap(f['ports']['lk']);kvec=[(k>>(3*j))&7 for j in range(4)]
            r=links['r_'+name[2:]]
            records.append(dict(name=name,master=f['master'],lk=k,lk_lanes=kvec,
                actual_clock=f['ports']['clk'],actual_return=f['ports']['ret'],
                actual_return_stations=r['s'],return_capture_phase_native=None,
                dimension_first=dims[0],dimension_last=dims[-1],rows=count,
                six_row_phases=math.ceil(count/6),
                dimension_storage_tag=[[d,0x4000+1024*h+storage_offset(d)] for d in dims]))
        assert start==512
        old_missing+=(8-n)*64
        rows.append(dict(head=h,slice=s['name'],frames=n,records=records,
            old_fixed8_omitted_rows=(8-n)*64,
            selected_wqb_phase_count=max(x['six_row_phases'] for x in records),
            original_eight_frame_phases=11,
            added_phase_epochs=max(x['six_row_phases'] for x in records)-11,
            source_rows_complete=True,production_image_installed=False,
            exact_phase_cycles=None,whole_token_delta=None))
    rows.sort(key=lambda x:x['head'])
    assert [x['head'] for x in rows]==list(range(16))
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    rec=dict(schema='opentallas.s81.selected_wqb_frames.v1',
        selected_die_sha256=EXPECTED,selected_source='ceaed19c4',
        source_files={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in [a.inventory,a.plan]},
        physical_frames=122,missing_vs_fixed8=6,
        old_fixed8_omitted_rows=old_missing,
        wqb_total_semantic_rows=8192,private_actual_frame_placement_complete=True,
        new_hardware=False,new_ff=0,new_macros=0,
        production_compiler_changed=False,
        q_return_shape=dict(K=1280,nseg=3,q_pairs=10,rows_per_frame_phase=6),
        head_contracts=rows,
        old_loader_blocker='dv_layer_compile.Die hardcodes bind9/p4l; xs_place hardcodes NFRAME8',
        whole_layer_phase_count=None,
        other_ops_blocker='other matvec placements also hardcode8; their repartition/phase costs are not priced here',
        qualification='ACTUAL_INVENTORY_AND_SOURCE_MODEL_ONLY; no return-port/calendar/RTL/token closure')
    (out/'selected_frame_contract.json').write_text(json.dumps(rec,indent=2)+'\n')
    print('SELECTED_FRAME_MODEL_PASS die',EXPECTED,'frames122 semantic_rows8192 old_fixed8_missing',old_missing)
    for h in rows:
        if h['frames']<8:print('HEAD',h['head'],'frames',h['frames'],'phases',h['selected_wqb_phase_count'],'extra',h['added_phase_epochs'])

if __name__=='__main__':main()
