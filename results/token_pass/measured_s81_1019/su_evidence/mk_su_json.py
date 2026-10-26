#!/usr/bin/env python3
# TOKSIM-S81/SU: writes elements/SU.json from op_types.json + the measurements collected below (no repricing).
import json, datetime
B='/home/ubuntu/scratch/toksim-s81'
ot={e['op']:e for e in json.load(open(f'{B}/op_types.json'))}
REL='origin/claude/s81-bind-mu4-1019@19bf4121e'
FL='ot-epyc7:/srv/opentallas-scratch/claude/toksim-s81-su'
M=json.load(open(f'{B}/su/meas.json'))   # op -> overrides
def old(o):
    e=ot[o]; return round(e['cyc_crit']/e['n_crit'],1) if e['n_crit'] else (e['per_instance'][0] if e['per_instance'] else None)
ops=[]
for o,ov in M['ops'].items():
    e=ot.get(o,{})
    r={"op":o,"dag_cls":e.get('cls',ov.get('dag_cls')),"n_crit":e.get('n_crit',ov.get('n_crit')),
       "old_cycles_per_instance":old(o) if o in ot else ov.get('old'),
       "cycles":None,"grade":"measured-old-RTL","definition":None,"shape":None,"bit_exact":None,"golden":None,
       "rtl":None,"bench":None,"evidence":None,"job":None,"edges_owed":None,"note":None}
    r.update({k:v for k,v in ov.items() if k not in ('old',)})
    if r['grade']=='measured-old-RTL' and r['cycles'] is None: r['cycles']=r['old_cycles_per_instance']; r.setdefault('evidence', e.get('note','')[:300])
    if not r.get('evidence') and e: r['evidence']='old DAG note: '+e.get('note','')[:300]
    ops.append(r)
out={"cls":"SU","written":datetime.datetime.now().strftime('%Y-%m-%d %H:%M PT'),"agent_branch":"claude/toksim-s81-su-1019 (no commits: bench adaptations are env-only, job scripts in /home/ubuntu/scratch/toksim-s81/su)",
     "release_source":REL,"fleet_dir":FL,"summary":M['summary'],"ops":ops}
json.dump(out,open(f'{B}/elements/SU.json','w'),indent=1)
print(len(ops),'ops written')
