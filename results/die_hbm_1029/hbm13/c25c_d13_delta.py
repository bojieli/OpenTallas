"""DIE-HBM-13 plan delta on Codex street plan 4d53747f (codex/hbm-plan-1029: exact-count ring f9c82446b + PHY tuple 886f74f7d).
usage: c25c_d13_delta.py STREET_DIR OUT_DIR   (OUT_DIR gets die_plan.json, core_conns.json, clock_taps_die.json, cores/<ring pins>; link the rest)
(1) G0C hard_cores: NE u_ctl_Q_p15 origin (4324.32,3080.16) off the 8.64 lattice -> (4328.64,3075.84); its tap, 28 internal-station
    endpoints and die tap move by the same (+4.32,-4.32) [die frame MY: (-4.32,-4.32)]. Gaps: Q0 8.64, Q3 3.456, xq_p0_bd 12.1 um.
(2) COORD 05:35 ruling (HBM-CORES-KITS-9 ASK YES): ring_ag qid is a declared ID strap -> ring_ag pins qid[*] -> strap_qid[*];
    qid core_conns body<->ring_ag removed (tied at parent, bind strap regex .qid); phantom cij inj_d*/inj_idx* and hcollgl pa_* ->
    ring_ag targets removed (ring_ag has no such pins); the matching 40 internal-station legs (679 plan regs) dropped."""
import json,os,sys
S,D=sys.argv[1].rstrip('/')+'/',sys.argv[2].rstrip('/')+'/'
os.makedirs(D+'cores',exist_ok=True)
p=json.load(open(S+'die_plan.json')); t=p['partition_types']['q_hub_ne']
dx,dy=4.32,-4.32; NEW=[4328.64,3075.84]
NOTE=' | DIE-HBM-13: snapped to 8.64 lattice by (+4.32,-4.32) (G0C hard_cores); p15 endpoints/tap translated'
for c in t['hard_cores']:
  if c['inst']=='u_ctl_Q_p15': assert c['origin_um']==[4324.32,3080.16]; c['origin_um']=NEW; c['note']+=NOTE
for c in t['contents']:
  if c.get('inst')=='u_ctl_Q_p15': c['origin_um']=NEW
for tp in t['clock']['taps']:
  if tp['name']=='u_ctl_Q_p15': tp['xy']=[round(tp['xy'][0]+dx,6),round(tp['xy'][1]+dy,6)]; tp['note']+=NOTE
for s in t['internal_stations']:
  a,_,b=s['conn'].partition('|')
  if a.startswith('u_ctl_Q_p15.'): s['from_um']=[round(s['from_um'][0]+dx,6),round(s['from_um'][1]+dy,6)]
  if b=='u_ctl_Q_p15' or b.startswith('u_ctl_Q_p15.'): s['to_um']=[round(s['to_um'][0]+dx,6),round(s['to_um'][1]+dy,6)]
for tn in ['q_hub_nw','q_hub_ne']:
  tt=p['partition_types'][tn]; keep=[]
  for s in tt['internal_stations']:
    a,_,b=s['conn'].partition('|'); port=a.split('.',1)[1] if '.' in a else ''
    if ('ring_ag' in s['conn'] and port.startswith('qid')) or (b=='u_hb_coll_Q_ring_ag' and port.startswith(('inj_d','inj_idx','pa_'))): continue
    keep.append(s)
  tt['internal_stations']=keep
json.dump(p,open(D+'die_plan.json','w'),indent=1)
ct=json.load(open(S+'clock_taps_die.json'))
L=ct if isinstance(ct,list) else next(v for v in ct.values() if isinstance(v,list))
for e in L:
  if e.get('part')=='NE_hub' and e.get('tap')=='u_ctl_Q_p15': e['xy_die_um']=[round(e['xy_die_um'][0]-dx,6),round(e['xy_die_um'][1]+dy,6)]
json.dump(ct,open(D+'clock_taps_die.json','w'),indent=1)
RF='cores/ot_hfd_coll_q2_hard_v8g__ring_ag__233.28x233.28__q_hub_u_hb_coll_Q_ring_ag__oneclk__c25c_centerclk.json'
d=json.load(open(S+RF))
for pin in d:
  if pin['name'].startswith('qid['): pin['name']='strap_'+pin['name']
if os.path.islink(D+RF): os.remove(D+RF)
json.dump(d,open(D+RF,'w'))
c=json.load(open(S+'core_conns.json'))
for tn in ['q_hub_nw','q_hub_ne']:
  for core,ports in c[tn].items():
    for port in list(ports):
      dst=ports[port]
      if port=='qid' and ('ring_ag' in core or any('ring_ag' in x for x in dst)): del ports[port]; continue
      if port.startswith(('inj_d','inj_idx','pa_')) and any('ring_ag' in x for x in dst): ports[port]=[x for x in dst if 'ring_ag' not in x]
json.dump(c,open(D+'core_conns.json','w'),indent=1)
