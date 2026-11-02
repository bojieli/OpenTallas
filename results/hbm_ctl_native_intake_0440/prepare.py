#!/usr/bin/env python3
"""Source-only CTL model and exact ABI inventory; no physical release."""
import json,hashlib
from pathlib import Path
r=Path(__file__).resolve().parent;w=r.parents[1];c=json.loads((r/'provider.json').read_text());top=c['module'];W,H=c['planning_outline_um'];pins=[]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for d in ('input','output'):
 bits=[p['name']+(f'[{i}]'if p['is_vector']else'')for p in c['ports']if p['direction']==d and p['name']not in ('clk','rst_n','u_core_u_rst__rst_n')for i in range(p['width'])]
 for i,n in enumerate(bits):
  along=round((4.344+(i//2)*.192)/.048)*.048
  if i%2==0:x,y,layer=(.096 if d=='input'else W-.096),along,'M4'
  else:x,y,layer=along,(.096 if d=='input'else H-.096),'M5'
  assert .048<x<W-.048 and .048<y<H-.048,(n,x,y)
  pins.append(dict(name=n,layer=layer,x=round(x,6),y=round(y,6)))
cx=round((W/2-.012)/.048)*.048+.012;cy=round((H/2-.012)/.048)*.048+.012
pins.extend([dict(name='clk[0]',layer='M5',x=cx,y=cy,w=.048,h=.48),dict(name='rst_n[0]',layer='M5',x=cx,y=cy-8.64,w=.048,h=.48),dict(name='u_core_u_rst__rst_n[0]',layer='M5',x=cx,y=cy+8.64,w=.048,h=.48)])
assert len(pins)==11810 and len({p['name']for p in pins})==11810
write=lambda n,v:(r/n).write_text(json.dumps(v,indent=2)+'\n')
write('CTL_pins.json',pins);write('core_macros.json',{})
plan=dict(schema='opentallas.die_plan.v1',die=dict(name='HBM_CTL_SOURCE_COMPONENT',tech='asap7',period_ps=833,reach_um=405,rep_um=450,grid_um=8.64,layer_budget=dict(partition_signal_max='M7')),clock=dict(insertion_ps=250,insertion_tol_ps=80),partition_types={'native_provider_slot':dict(outline_um=[W,H],hard_cores=[dict(inst='u_native_ctl',module=top,origin_um=[0,0],outline_um=[W,H],pins_file='CTL_pins.json')])},partitions=[],ports=[],lanes=[])
write('GEN_plan.json',plan)
view=top+'@'+sha(r/'CTL_pins.json')[:12]
write('views.json',dict(schema='opentallas.hbm_arch.views.v1',plan='GEN_plan.json',plan_sha256=sha(r/'GEN_plan.json'),view_list=[dict(view=view,module=top,outline_um=[W,H],pins_file='CTL_pins.json',pins_sha256=sha(r/'CTL_pins.json'),pins=len(pins),recipe_keys=[top],family='SOURCE13_NATIVE_CTL_COMPONENT',canonical_type=None,instances=['q_b113.u_sfucore_Q_ctl'],placed=0)]))
name='closure_'+top+'.sv'
write('readset.json',dict(top=top,source13_frozen_native=True,files=[dict(file=str((r/name).relative_to(w)),sha256=sha(r/name))],clock_ports=['clk'],reset_ports=['rst_n','u_core_u_rst__rst_n'],native_capacity={},conditional_formal_reset_edges=4,release_eligible=False,pins_sha256=sha(r/'CTL_pins.json'),plan_sha256=sha(r/'GEN_plan.json'),planned_core_macros_sha256=sha(r/'core_macros.json')))
write('model.json',dict(status='SOURCE_ONLY_INTAKE_MODEL_NO_PHYSICAL_RELEASE',source=c['source_model'],ABI=dict(ports=len(c['ports']),bits=11810,inputs=5354,outputs=6456),planning_outline_um=[W,H],outline_authority='Historical declared allocation; mapped area/fill and legal placement unmeasured.',microarchitecture='Exact CTL logic/VM READ_RETURN88/WRITE_RETURN85. No RTL, replication or cycle changes.',added_cycles=0,pin_capacity=dict(nominal_pitch_um=.192,pins_per_um=1/.192,names_unique=True,all_inside=True,credit='GEN inventory only; no native parent-body pin/reach qualification.'),physical_holds=['Mapped area/fill/clock sinks unmeasured','Clock decomposition/native pin access/PG unavailable','Exact native reset/66START physical phase unqualified','Parent L730/programme provider placement unjoined','SOURCE13/default activation held'],requested_scope='GEN/SYNTH then official component source proof. No PLACE/CTS/GRT/STA.'))
print('PREPARED',view,11810,'ABI bits',36240,'declared FF, zero SRAM')
