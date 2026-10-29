"""DIE-HBM-13 option-R pair move: hcollgl__q1 (gq_land) next to ring_ag__q1 in both hubs.
usage: gl_pairmove.py PLAN_DIR(c25c_d13) OUT_DIR TOOLS_DIE_PLAN RING_FIXED_COUNT_PY
Moves u_hcollgl_Q__q1 to NEW (8.64 lattice, body+halo legal, gl_slot.py best), translates its station endpoints/tap/die tap,
re-sites every station chain that touches the moved core or sits in its new body+halo with the SAME register count
(exact-count Manhattan solver from codex f9c82446b ring_fixed_count.route); reports any unavoidable +N."""
import json,sys,os,shutil,hashlib,importlib.util
src,out,tools,rfc=sys.argv[1:5]; sys.path.insert(0,tools)
spec=importlib.util.spec_from_file_location('rfc',rfc); sys.argv_saved=sys.argv
import types; m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
import hub_repack as HR
NEW=[4492.8,2246.4]
p=json.load(open(src+'/die_plan.json')); rep={}
for tn in ['q_hub_nw','q_hub_ne']:
  t=p['partition_types'][tn]; H={h['inst']:h for h in t['hard_cores']}; gl=H['u_hcollgl_Q__q1']
  ox,oy=gl['origin_um']; w,h=gl['outline_um']; dx,dy=NEW[0]-ox,NEW[1]-oy
  inold=lambda q:ox-1<=q[0]<=ox+w+1 and oy-1<=q[1]<=oy+h+1
  gl['origin_um']=list(NEW); gl['note']=gl.get('note','')+f' | DIE-HBM-13 option-R pair move next to ring_ag__q1 by ({dx:.2f},{dy:.2f})'
  for c in t['contents']:
    if c.get('inst')=='u_hcollgl_Q__q1': c['origin_um']=list(NEW)
  for tp in t['clock']['taps']:
    if tp['name']=='u_hcollgl_Q__q1': tp['xy']=[round(tp['xy'][0]+dx,6),round(tp['xy'][1]+dy,6)]; tap=True
  R=HR.Raster(*t['outline_um'],[(hh['origin_um'][0]+hh.get('track_offset_um',[0,0])[0],hh['origin_um'][1]+hh.get('track_offset_um',[0,0])[1],hh['origin_um'][0]+hh.get('track_offset_um',[0,0])[0]+hh['outline_um'][0],hh['origin_um'][1]+hh.get('track_offset_um',[0,0])[1]+hh['outline_um'][1]) for hh in t['hard_cores']])
  nb=(NEW[0]-4.32,NEW[1]-4.32,NEW[0]+w+4.32,NEW[1]+h+4.32)
  rows=[]
  for i,s in enumerate(t['internal_stations']):
    moved=False
    if 'hcollgl' in s['conn']:
      a,_,b=s['conn'].partition('|')
      if a.startswith('u_hcollgl_Q') and inold(s['from_um']): s['from_um']=[round(s['from_um'][0]+dx,6),round(s['from_um'][1]+dy,6)]; moved=True
      if b.startswith('u_hcollgl_Q') and inold(s['to_um']): s['to_um']=[round(s['to_um'][0]+dx,6),round(s['to_um'][1]+dy,6)]; moved=True
    regs=s.get('regs_um',[]); hit=any(nb[0]<r[0]<nb[2] and nb[1]<r[1]<nb[3] for r in regs)
    pts=[s['from_um']]+regs+[s['to_um']]
    bad=max(abs(x[0]-y[0])+abs(x[1]-y[1]) for x,y in zip(pts,pts[1:]))>405+1e-5
    if not (moved or hit) or (not hit and not bad): continue
    n=len(regs); r=m.route(R,s['from_um'],s['to_um'],n) if n else None; actual=n
    if n==0:
      d=abs(s['from_um'][0]-s['to_um'][0])+abs(s['from_um'][1]-s['to_um'][1]); rows.append(dict(index=i,conn=s['conn'],old=0,final=0,direct_um=round(d,1))); continue
    if r is None:
      for actual in range(n+1,n+4):
        r=m.route(R,s['from_um'],s['to_um'],actual)
        if r is not None: break
    if r is None: rows.append(dict(index=i,conn=s['conn'],old=n,final=None)); continue
    s['regs_um']=r; s['note']=s.get('note','')+' | DIE-HBM-13 gl pair move exact-count re-site'
    rows.append(dict(index=i,conn=s['conn'],bits=s.get('bits'),old=n,final=actual,added=actual-n,reason='endpoint' if moved else 'in new body'))
  rep[tn]=dict(delta=[dx,dy],rows=rows,added=sum(r.get('added') or 0 for r in rows),failed=[r for r in rows if r.get('final') is None])
  print(tn,'resited',len(rows),'added',rep[tn]['added'],'failed',len(rep[tn]['failed']),flush=True)
os.makedirs(out,exist_ok=True)
for f in os.listdir(src):
  if f not in ('die_plan.json','clock_taps_die.json') and not os.path.exists(out+'/'+f): os.symlink(os.path.realpath(src+'/'+f) if f!='cores' else os.path.abspath(src+'/cores'),out+'/'+f)
json.dump(p,open(out+'/die_plan.json','w'),indent=1)
ct=json.load(open(src+'/clock_taps_die.json')); L=ct if isinstance(ct,list) else next(v for v in ct.values() if isinstance(v,list))
P={q['name']:q for q in (p['partitions'] if isinstance(p['partitions'],list) else p['partitions'].values())}
for e in L:
  if e.get('tap')=='u_hcollgl_Q__q1':
    tn=e['type']; dx,dy=rep[tn]['delta']; o=P[e['part']].get('orient','R0')
    sx=-1 if o in ('MY','R180') else 1; sy=-1 if o in ('MX','R180') else 1
    e['xy_die_um']=[round(e['xy_die_um'][0]+sx*dx,6),round(e['xy_die_um'][1]+sy*dy,6)]; e['note']='DIE-HBM-13 gl pair move'
json.dump(ct,open(out+'/clock_taps_die.json','w'),indent=1)
rep['plan_sha256']=hashlib.sha256(open(out+'/die_plan.json','rb').read()).hexdigest()
json.dump(rep,open(out+'/gl_pairmove_report.json','w'),indent=1)
