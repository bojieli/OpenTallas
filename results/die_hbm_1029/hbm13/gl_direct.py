"""DIE-HBM-13: after the gl pair move, ring_ag__q1 ag_* -> hcollgl__q1 pa_* are <=405 direct; RTL is direct (0 reg) -> plan regs [] (match RTL)."""
import json,sys,hashlib
f=sys.argv[1]; p=json.load(open(f)); n=[]
for tn in ['q_hub_nw','q_hub_ne']:
  for s in p['partition_types'][tn]['internal_stations']:
    if s['conn'].startswith('u_hb_coll_Q_ring_ag.ag_') and s['from_um'][0]>4000:
      d=abs(s['from_um'][0]-s['to_um'][0])+abs(s['from_um'][1]-s['to_um'][1]); assert d<=405
      n.append((tn,s['conn'],len(s['regs_um']),round(d,1))); s['regs_um']=[]; s['note']=s.get('note','')+' | DIE-HBM-13: RTL-direct, %.1f um <=405 after gl pair move -> 0 plan regs'%d
json.dump(p,open(f,'w'),indent=1); print(n, hashlib.sha256(open(f,'rb').read()).hexdigest()[:12])
