#!/usr/bin/env python3
"""Restore the paired SU collector sidecar entries after plan reconciliation.

Usage: reconcile_collector_sidecar_1131.py PLAN SIDECAR REFERENCE_SIDECAR REPORT
Only the9 exact current-plan SU collector entries may change; count schedules,
boot budget, child edges and every other sidecar field remain unchanged.
"""
import copy,json,re,sys
from pathlib import Path
pp,sp,rp,out=map(Path,sys.argv[1:]);p=json.loads(pp.read_text());s=json.loads(sp.read_text());ref=json.loads(rp.read_text());before=copy.deepcopy(s);rows=[]
fields={'tree':'collector_tree','collector_root_node':'collector_root_node','local_sources':'collector_local_sources'}
allowed=set(fields)|{'collector_root_xy'}
for name,t in p['partition_types'].items():
    if not any(re.fullmatch(r'qfd_qc_su_lane_[we]_l[0-7]',c['module']) for c in t.get('hard_cores',[])):continue
    a=s['collector']['types'][name];b=ref['collector']['types'][name];lc=t['clock']['landing_contract']
    assert {k:v for k,v in a.items() if k not in allowed}=={k:v for k,v in b.items() if k not in allowed},(name,'unrelated collector fields changed')
    for key,pkey in fields.items():assert b[key]==lc[pkey],(name,key,'reference differs from current resolved plan')
    changed=[]
    for key in allowed:
        if a.get(key)!=b.get(key):
            if key in b:a[key]=copy.deepcopy(b[key])
            else:a.pop(key,None)
            changed.append(key)
    rows.append(dict(type=name,fields=sorted(changed)))
assert len(rows)==9
assert {k:v for k,v in s.items() if k!='collector'}=={k:v for k,v in before.items() if k!='collector'}
assert {k:v for k,v in s['collector'].items() if k!='types'}=={k:v for k,v in before['collector'].items() if k!='types'}
for name,t in s['collector']['types'].items():
    if name not in {x['type'] for x in rows}:assert t==before['collector']['types'][name],name
sp.write_text(json.dumps(s,indent=1)+'\n');out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(dict(reference='5271d9d7f strictPASS',paired_plan=str(pp),changed=rows,count_schedule_preserved=True,boot_budget_preserved=True,added_cycles=0),indent=2)+'\n');print('Paired9 SU collector entries restored; schedule/boot/other types unchanged')
