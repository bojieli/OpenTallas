import json,sys
p=json.load(open('die_plan.json')); cc=json.load(open('core_conns.json'))
out={}
for tn in ['q_hub_nw','q_hub_ne']:
  t=p['partition_types'][tn]; TW,TH=t['outline_um']
  H={h['inst']:h for h in t['hard_cores']}
  gl=H['u_hcollgl_Q__q1']; w,h=gl['outline_um']
  box=lambda c:(c['origin_um'][0]+c.get('track_offset_um',[0,0])[0],c['origin_um'][1]+c.get('track_offset_um',[0,0])[1],c['origin_um'][0]+c.get('track_offset_um',[0,0])[0]+c['outline_um'][0],c['origin_um'][1]+c.get('track_offset_um',[0,0])[1]+c['outline_um'][1])
  others=[box(c) for k,c in H.items() if k!='u_hcollgl_Q__q1']
  # current stations points (FT/ring) must stay outside new body+halo
  pts=[r for s in t['internal_stations'] for r in s.get('regs_um',[]) if 'hcollgl' not in s['conn']]
  pts+= [tp['xy'] for tp in t['clock']['taps'] if tp['name']!='u_hcollgl_Q__q1']
  ag=[s['from_um'] for s in t['internal_stations'] if s['conn'].startswith('u_hb_coll_Q_ring_ag.ag_') and s['from_um'][0]>4000]
  # partner centres of hcollgl q1 (all core conns in/out)
  part=set()
  for core,ports in cc[tn].items():
    for port,dst in ports.items():
      if core=='u_hcollgl_Q__q1': part|={d.split(':')[1] for d in dst if d.startswith('core:')}
      elif 'core:u_hcollgl_Q__q1' in dst: part.add(core)
  part.discard('u_hb_coll_Q_ring_ag__q1')
  cen=lambda b:((b[0]+b[2])/2,(b[1]+b[3])/2)
  P={k:cen(box(H[k])) for k in part if k in H}
  oldc=cen(box(gl))
  best=[]
  g=8.64
  for ix in range(int(3500/g),int((TW-w)/g)):
    for iy in range(int(1500/g),int((TH-h)/g)):
      x,y=ix*g,iy*g; b=(x,y,x+w,y+h)
      if any(b[0]<o[2]+4.32 and o[0]<b[2]+4.32 and b[1]<o[3]+4.32 and o[1]<b[3]+4.32 for o in others): continue
      if any(b[0]-4.32<q[0]<b[2]+4.32 and b[1]-4.32<q[1]<b[3]+4.32 for q in pts): continue
      d=max(min(abs(a[0]-xx)+abs(a[1]-yy) for xx in (b[0],b[2]) for yy in (b[1],b[3])) for a in ag)  # crude: ag pin to nearest gl corner
      dc=max(abs(a[0]-(x+w/2))+abs(a[1]-(y+h/2)) for a in ag)
      if dc>405: continue
      worst=max([abs(c[0]-(x+w/2))+abs(c[1]-(y+h/2))-(abs(c[0]-oldc[0])+abs(c[1]-oldc[1])) for c in P.values()] or [0])
      best.append((dc,worst,x,y))
  best.sort(key=lambda r:(r[1],r[0]))
  out[tn]=dict(old=gl['origin_um'],partners={k:[round(v,1) for v in c] for k,c in P.items()},n_slots=len(best),top=best[:5])
  print(tn,'old',gl['origin_um'],'partners',list(P),'slots',len(best),best[:3])
json.dump(out,open('/srv/opentallas-scratch/claude/die-hbm-13/gl_slot_report.json','w'),indent=1)
