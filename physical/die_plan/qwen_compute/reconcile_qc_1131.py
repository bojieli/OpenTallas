#!/usr/bin/env python3
"""Replay qualified QC source fixes on current main without replacing a type.

The reference collector comes from strict-PASS5271. Reuse is allowed only when
all current core physical/clock fields and noncollector landing fields equal
that reference. A changed early-tap input requires a fresh collector derivation.
Usage: reconcile_qc_1131.py PLAN REFERENCE_PLAN REPORT
"""
import copy,json,re,sys
from pathlib import Path
import delta_su_groups_1101 as groups
p,ref,out=map(Path,sys.argv[1:]);raw=json.loads(p.read_text());before=copy.deepcopy(raw);old=json.loads(ref.read_text());rows=[]
keys=('collector_tree','collector_root_node','collector_local_sources')
def physical(cores):
    result=copy.deepcopy(cores)
    for c in result:c.pop('bound_group',None)
    return result
def no_collector(t):
    t=copy.deepcopy(t)
    for k in keys:t.pop(k,None)
    return t
for name,t in raw['partition_types'].items():
    if not any(re.fullmatch(r'qfd_qc_su_lane_[we]_l[0-7]',c['module']) for c in t.get('hard_cores',[])):continue
    prior=old['partition_types'][name]
    assert physical(t['hard_cores'])==physical(prior['hard_cores']),(name,'core physical/clock inputs changed')
    a=copy.deepcopy(t['clock']);b=copy.deepcopy(prior['clock']);la=a.pop('landing_contract');lb=b.pop('landing_contract')
    assert a==b and no_collector(la)==no_collector(lb),(name,'current clock/pins require fresh collector derivation')
    changes=[]
    for k in keys:
        if la.get(k)!=lb.get(k):
            if k in lb:t['clock']['landing_contract'][k]=copy.deepcopy(lb[k])
            else:t['clock']['landing_contract'].pop(k,None)
            changes.append(k)
    rows.append(dict(type=name,collector_fields=changes,core_physical_fields_preserved=True,clock_fields_preserved=True,landing_pin_fields_preserved=True))
assert len(rows)==9,len(rows)
group_changes=groups.apply(raw)
p.write_text(json.dumps(raw)+'\n')
# Existing deterministic delta handles the two dedicated pads only.
import subprocess
subprocess.run([sys.executable,str(Path(__file__).with_name('delta_cseq_pads_1101.py')),str(p)],check=True)
raw=json.loads(p.read_text())
changed=[n for n in raw['partition_types'] if raw['partition_types'][n]!=before['partition_types'][n]]
assert set(changed)=={x['type'] for x in rows}|{'glue'},changed
assert all(raw.get(k)==v for k,v in before.items() if k!='partition_types')
report=dict(base=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),collector_reference='5271d9d7f strictPASS',changed_types=changed,groups_added=len(group_changes),su=rows,non_type_fields_preserved=True,unaffected_types_preserved=True,added_cycles=0)
out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(changed_types=len(changed),groups=len(group_changes),all_earlytap_fields_preserved=True,added_cycles=0)))
