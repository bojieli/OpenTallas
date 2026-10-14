#!/usr/bin/env python3
"""Build the publication parent from actual production net aliases and LEF pins."""
import json,re
from pathlib import Path
import smpub_parent_wire_audit as A
R=A.ROOT;O=A.OUT
n=json.loads(Path('/tmp/smpub-parent-wire-audit/net.json').read_text())['modules']['ot_hgi_sm_pub_parent'];p=json.loads((O/'parent_placements.json').read_text());v,pending=A.views(n)
# Qualified route submission requires every pending child view to be replaced.
net={}
for inst,c in n['cells'].items():
 size,pins=v[c['type']]
 for port,bits in c['connections'].items():
  for i,b in enumerate(bits):
   if not isinstance(b,int):continue
   pin=port if len(bits)==1 else f'{port}[{i}]'
   if pin not in pins:raise ValueError((inst,pin))
   pt=A.point(p[inst],size,pins[pin]);net.setdefault(b,[]).append((inst,pin,*pt))
children=[]
for inst,d in p.items():
 paths=list((R/'physical/ref_tile').glob('*/views/'+d['master']));
 if not paths:raise ValueError('Need actual view '+d['master'])
 children.append(dict(view=str(paths[0].relative_to(R)),count=1,inst=inst,at=[d['x'],d['y']],orient=d['orient']))
clks=[];pins=[];sm=[];resets=[];native=[];W,H=1814.4,1296
# Native clock landing pads on parent M7, with real short routing to each assigned child.
# Avoid both nominal/global and core-relative fixed PDN stripe phases; actual route still must verify PG/access.
def clock_coord(value, phases):
    base=round((value-0.016)/0.064)*0.064+0.016
    options=[base+0.064*i for i in range(-16,17)]
    options.sort(key=lambda q:abs(q-value))
    for q in options:
        if all(abs((q-phase+2.7)%5.4-2.7)>=0.32 for phase in phases):return round(q,3)
    raise ValueError('no legal clock landing near '+str(value))
for port,c in n['ports'].items():
 for i,b in enumerate(c['bits']):
  name=port if len(c['bits'])==1 else f'{port}[{i}]';ends=net.get(b,[])
  if not ends:raise ValueError('Unbound parent '+name)
  # Distributed physical die clock entries on M7 route to each exact assigned child's clock pin.
  if port.startswith('clk'):
   if len(ends)!=1:raise ValueError((name,ends))
   end=ends[0];cx,cy=end[2:4];x=clock_coord(cx,[1.0,3.16]);y=clock_coord(cy,[0.513,0.897,2.673,3.057]);layer='M7';clks.append(dict(port=name,hard_child_pin=end[0]+'.'+end[1],location_um=[x,y],child_pin_um=[cx,cy],layer=layer,placement_entry_reach_um=round(abs(x-cx)+abs(y-cy),3),actual_entry_wire_measurement_required=True))
  elif port.startswith('sm_'):
   end=ends[0];k=int(re.search(r'\[(\d+)\]',end[0])[1]);x,y=end[2],H if k<4 else 0;layer='M5';sm.append(dict(port=name,hard_child_pin=end[0]+'.'+end[1],parent_pin_um=[x,y],child_pin_um=list(end[2:4]),native_face='N' if k<4 else 'S',manhattan_um=round(abs(y-end[3]),3)))
  elif port=='rst_slice':
   end=ends[0];x,y=end[2]+0.048,H if i<4 else 0;layer='M5';resets.append(dict(port=name,hard_child_pin=end[0]+'.'+end[1],parent_pin_um=[x,y],child_pin_um=list(end[2:4]),native_face='N' if i<4 else 'S',recovery_removal_required_under_actual_clock=f'clk_slice[{i}]',manhattan_um=round(abs(x-end[2])+abs(y-end[3]),3)))
  else:
   end=ends[0];x,y=(W if port in ('vmq','vmr') and i//(338 if port=='vmq' else 274)>=2 else 0),end[3];layer='M4';native.append(dict(port=name,hard_child_pin=end[0]+'.'+end[1],parent_pin_um=[x,y],child_pin_um=list(end[2:4]),manhattan_um=round(abs(x-end[2]),3)))
  pins.append(f'place_pin -pin_name {{{name}}} -layer {layer} -location {{{x:.3f} {y:.3f}}}'+(' -pin_size {0.064 0.128}' if port.startswith('clk') else ''))
(R/'physical/hgi_sm_pub_parent_stations/parent_pins.tcl').write_text('# Actual die pins: each data/reset bit binds its exact hard child; M7 own-root clock pads require real entry routing and measurement.\n'+'\n'.join(pins)+'\n')
(O/'sm_die_pins.json').write_text(json.dumps(dict(schema='opentallas.smpub.actual-native-pin-bindings.v2',outline_um=[W,H],source='actual production parent synthesized net aliases + real child LEF pins',pending_actual_views=pending,sm_bit_count=len(sm),sm_pins=sm,raw_slice_reset_entries=resets,public_native_pins=native,own_clock_entries=clks),indent=2)+'\n')
(O/'clock_entries.json').write_text(json.dumps(dict(schema='opentallas.smpub.actual-clock-entry-bindings.v2',top='ot_hgi_sm_pub_parent',entry_count=len(clks),entries=[dict(e,master=p[e['hard_child_pin'].rsplit('.',1)[0]]['master'],view=next(c['view'] for c in children if c['inst']==e['hard_child_pin'].rsplit('.',1)[0])) for e in clks],reset_behavior=dict(baseline_release_cycles=3,middle_release_cycles=[3,4,5,6],credit_release_cycles=[4,5,6,7],max_added_cold_release_cycles=4,added_hot_transaction_cycles=0)),indent=2)+'\n')
base=json.loads((R/'tools/ref_tile/specs_smpub/smpub_cmd_quiet.json').read_text())
s=dict(name='smpub_parent',top='ot_hgi_sm_pub_parent',kind='cluster',hard_define='SYNTHESIS',sources=base['sources'],clock='entries',clock_port='clk_rst',clock_ports=[c['port'] for c in clks],reset_ports=['rst_n','rst_slice'],outline=dict(w=W,h=H),pins={'ANY':list(n['ports'])},children=children,child_lattice_um=8.64,recipe=2,inhold=False,outhold=False,io_flop_at_pins=False,io_tcl='physical/hgi_sm_pub_parent_stations/parent_pins.tcl',route=dict(pd=.5,threads=16,peak_ram_gb=64),job=dict(base['job'],tag='r1',purpose='Actual wires-only publication parent: 69 own clock entries, immutable CLOSED leaves, every production native pin and regional reset explicitly bound, directed signal reach <=500um and channels >=20um',views_to='physical/ref_tile/smpub_parent/views',record_to='results/rtl/ref_tile/smpub_parent'))
s['job']['extra_paths']+=['physical/hgi_sm_pub_parent_stations','results/rtl/hgi_sm_pub_parent_stations_20261013'];(R/'tools/ref_tile/specs_smpub/smpub_parent.json').write_text(json.dumps(s,indent=2)+'\n');print('pins',len(pins),'SM',len(sm),'reset',len(resets),'clock',len(clks),'pending',pending)
