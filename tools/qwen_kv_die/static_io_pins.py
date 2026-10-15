#!/usr/bin/env python3
"""Assign native writer/return-CDC leaf slots and exact source-derived pins.
Geometry is checked against actual frames; historical relay/source replacement
is explicitly required before this reservation may form a die case.
"""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'tools/qwen_kv_die'))
from die_port_bind_kv import header,evalw
from astk_home_fit import overlaps
ap=argparse.ArgumentParser();ap.add_argument('--writer-rtl',type=Path,required=True);ap.add_argument('--cdc-rtl',type=Path,required=True);ap.add_argument('--instances',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
masters={}
for name,path,w,h,clocks,resets,swap in [('qkd_kv_static_writer_native',a.writer_rtl,172.8,302.4,['ck'],['rst_n'],True),('qkd_static_kv_return_cdc',a.cdc_rtl,129.6,216,['pll_hbm','ck'],['hrst','rsi'],False)]:
 params,ports=header(path.read_text(),name);assert ports
 widths={p:evalw(v[1],params) for p,v in ports.items()};assert all(widths.values())
 groups={'W':[],'E':[],'S':[]}
 for p,(direction,_) in ports.items():
  if p in clocks+resets:continue
  face=('E' if direction=='input' else 'W') if swap else ('W' if p in ('controller_co','controller_epoch') else 'E')
  groups[face]+=[p] if widths[p]==1 else [f'{p}[{j}]' for j in range(widths[p])]
 pins={}
 for face,names in groups.items():
  for i,p in enumerate(names):
   y=.012+.048*round((10+(h-20)*(i+.5)/len(names)-.012)/.048)
   pins[p]=dict(face=face,layer='M4',xy=[0 if face=='W' else w,y])
 for i,p in enumerate(clocks+resets):
  # S-face clock/reset pins on the ASAP7 M5 track lattice (offset .060, pitch .192): the old .024+.048k lattice put
  # writer ck/rst_n 36 nm off-track (57.624 / 115.224) -> DRT-0255 'cannot find path of net ck' (r2 route, 10-15).
  x=.06+.192*round((w*(i+1)/(len(clocks+resets)+1)-.06)/.192)
  pins[p]=dict(face='S',layer='M5',xy=[x,0])
 assert len(pins)==sum(widths.values())
 for face in ('W','E'):
  pos=sorted(v['xy'][1] for v in pins.values() if v['face']==face);assert all(b-c>=.096-1e-6 for c,b in zip(pos,pos[1:]))
 lines=[]
 for p,v in pins.items():
  x,y=v['xy'];size='.024 .144' if v['face']=='S' else '.144 .024'
  lines.append(f'place_pin -pin_name {{{p}}} -layer {v["layer"]} -location {{{x:.3f} {y:.3f}}} -pin_size {{{size}}}')
 (a.out/(name+'.tcl')).write_text('\n'.join(lines)+'\n')
 masters[name]=dict(outline_um=[w,h],port_widths=widths,pins=pins,clock_entries=clocks,reset_entries=resets,source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),source_path=str(path),parameters={'DEPTH':8} if name.endswith('cdc') else {'MUT':0})
instances=json.loads(a.instances.read_text());by={i['name']:i for i in instances};rooms=[]
for st in ('WS','WN','ES','EN'):
 old=by['wctl_'+st];land=by['land_'+st];side=st[0]
 x=land['x']+land['w']+21.6 if side=='W' else land['x']-21.6-172.8
 rooms.append(dict(name='native_writer_'+st,master='qkd_kv_static_writer_native',x=x,y=old['y'],w=172.8,h=302.4,orient='R0'))
 for pc in range(32):
  c=by[f'cdc_{st}_{pc}'];x=old['x'] if side=='W' else old['x']+old['w']-129.6
  rooms.append(dict(name=f'native_return_{st}_{pc}',master='qkd_static_kv_return_cdc',x=x,y=c['y'],w=129.6,h=216,orient='R0'))
peers=[i for i in instances if not i['name'].startswith(('rly_','wctl_'))]
collisions=[[x['name'],y['name']] for x in rooms for y in peers if overlaps(x,y)]
collisions += [[x['name'],y['name']] for n,x in enumerate(rooms) for y in rooms[n+1:] if overlaps(x,y)]
assert not collisions,collisions

for d in rooms:d['orient']='MY' if d['name'].split('_')[-2 if d['name'].startswith('native_return') else -1].startswith('E') else 'R0'
rec=dict(schema='opentallas.kvsys.native_static_io_slots.v1',status='OFFICIAL_LEAF_SLOT_PINS; relay/actualtransport integration OPEN',native_qualified=False,core_period_ps=833.334,hbm_period_ps=1024,masters=masters,homes=rooms,nonrelay_frame_collisions=0,open=['Current historical write-chain relay placement must be replaced with actual static writer/PC route','Actual compiled writer destination distribution and expected-observer transport','Actual CDC per-clock phi-R and phase','Mapped fit, native bench+mutants and TT/FF/DRC0','Full source-pinned die cut and actual native binding'])
(a.out/'contract.json').write_text(json.dumps(rec,indent=2)+'\n')
print({n:{'outline':d['outline_um'],'pins':len(d['pins'])} for n,d in masters.items()})
