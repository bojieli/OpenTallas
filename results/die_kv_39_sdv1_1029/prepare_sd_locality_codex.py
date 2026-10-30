#!/usr/bin/env python3
"""KV-022 plan preparation from actual placed clk-family sinks. No route/adoption."""
import argparse, collections, copy, json, pathlib, re, sys
p=argparse.ArgumentParser(); p.add_argument('plan'); p.add_argument('dump'); p.add_argument('out'); a=p.parse_args()
root=pathlib.Path(__file__).resolve().parents[2]; sys.path.insert(0,str(root/'tools/die_plan'))
import schema, taps
cells={}; ports={}; nets=collections.defaultdict(list)
for line in pathlib.Path(a.dump).read_text().splitlines():
 r=line.split('\t')
 if r[0]=='C': cells[r[1]]=(r[2],(float(r[4])+float(r[6]))/2,(float(r[5])+float(r[7]))/2,r[8])
 elif r[0]=='P': ports[r[1]]=r[2]
 elif r[0]=='N': nets[r[2]].extend(r[3:])
roots=['p'+i for i,n in ports.items() if re.fullmatch(r'clk(?:_t\d+)?',n)]
seen=set(roots); todo=list(roots); sinks=set()
while todo:
 d=todo.pop()
 for s in nets.get(d,[]):
  if s.endswith('c') and s.startswith('i'):
   cid=s[1:-1]
   if cells.get(cid,('',))[0]=='S': sinks.add(cid)
  elif s.startswith('i') and cells.get(s[1:],('',))[0] in ('B','K') and s not in seen:
   seen.add(s);todo.append(s)
# Native main-clock sinks only; PHY and forwarded write clocks excluded by graph roots.
bins=collections.Counter((round(cells[i][1]/10.8)*10.8,round(cells[i][2]/10.8)*10.8) for i in sinks)
inv={'bin_um':10.8,'n':len(sinks),'bins':[[round(x,4),round(y,4),n] for (x,y),n in sorted(bins.items())]}
raw=json.load(open(a.plan)); out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=True)
bf=out/'sd_main_sinks.json';bf.write_text(json.dumps(inv,indent=2)+'\n')
report={'inventory_scope':'SD measured; SD_v1 provisional same-shape template, re-export before build','source_main_sinks':len(sinks),'not_adopted':True,'types':{}}
for tn,t in raw['partition_types'].items():
 if tn not in ('kv3_sys_SD','kv3_sys_SD_v1'):continue
 ck=t['clock'];ck.update(tap_mode='density',tap_um=[1890.,520.],tap_radius_um=200.,tap_max_sinks=1500,tap_target_sinks=1100,control_sinks=True,sink_bins_file=str(bf))
 ck.pop('tap_edge_y_um',None)
 ck['landing_export_form']='fwd_buffer'
 for pin in ck['landing_contract']['pins']:
  if pin['name']=='cland_tstart_in':pin.update(xy_um=[1898.656,520.],native_entry_reference_um=[1890.,520.])
 # Keep prior collector coordinates as history only. Next bind must rederive it from the new reset tree.
 report['types'][tn]={'primary_entry_um':[1890.,520.],'start_pin_um':[1898.656,520.], 'fstart_geometric_max_um':max(abs(1890-p['xy_um'][0])+abs(520-p['xy_um'][1]) for p in ck['landing_contract']['pins'] if p['name'].startswith('cland_fstart_out_'))}
pp=out/'plan_sd_locality_prep.json';pp.write_text(json.dumps(raw,indent=2)+'\n')
# Density geometric planning deliberately avoids full reset/START recursion (control=False).
P=schema.Plan(raw,pp)
for tn in report['types']:
 try:
  geom=taps.density_taps(P,tn,control=False)
  report['types'][tn]['density_geometry']=geom
  # Freeze density geometry, but anchor tap0 beside the new START/count origin.
  # Without this, nearest-density picks y432 -> y869 remains 437um, still FAIL.
  ck=P.types[tn]['clock']; ck['tap_mode']='explicit'; ck['tap_um']=[1883.52,520.]
  ck['taps']=[dict(name=n,xy=([1883.52,520.] if i==0 else [x,y]),kind='glue') for i,(n,x,y,*_) in enumerate(geom)]
  # Geometry phase only; full explicit_taps control budget is the next bind's obligation.
  report['types'][tn]['explicit_sites']=taps.explicit_tap_sites(P,tn)
  report['types'][tn]['raw_origin_to_fstart_max_um']=max(abs(1883.52-p['xy_um'][0])+abs(520-p['xy_um'][1]) for p in ck['landing_contract']['pins'] if p['name'].startswith('cland_fstart_out_'))
 except Exception as e:report['types'][tn]['density_error']=str(e)
pp.write_text(json.dumps(raw,indent=2)+'\n')
report['required_next']=['rederive reset/collector tree from new tap sites','strict bind and native START provider reach','full placed geometry; no CTS until structural failures fixed','recompute CA clocks and START schedule; source and cycle deltas gate adoption']
(out/'feasibility.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
