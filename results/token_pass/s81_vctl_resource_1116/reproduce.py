from pathlib import Path
import os,json,sys,re
r=Path('/srv/opentallas-scratch2/claude/tok-verify-2/recovery1116/ds_current_compile1116');code=r/'code_bf_components_2240';source=r/'source_bf_components_2240';b=Path('/srv/opentallas-scratch2/claude/s81-b3-clk/run/b/B6gF2s4tapfix1')
a=json.loads((source/'physical/die_plan/s81/bind/frame_asbuilt.json').read_text())
os.environ.update(PYTHONDONTWRITEBYTECODE='1',OT_S81_SELECTED_SOURCE_ROOT=str(source),OT_S81_SELECTED_ASBUILT_MANIFEST='physical/die_plan/s81/bind/frame_asbuilt.json',OT_S81_SELECTED_DEFINES=','.join(a['defines']),OT_S81_FRAME_SOURCE_ROOT=str(source),OT_S81_FRAME_ASBUILT_MANIFEST='physical/die_plan/s81/bind/frame_asbuilt.json',OT_S81_FRAME_PLAN='/srv/opentallas-scratch2/claude/s81-b3-clk/ev/B6gF2s4tapfix1.json',OT_XS_ASB_SCHEDULE_DIR=str(r/'profiles'),OT_GUNIT_BF_DEFINES='OT_GUNIT_BF_M1REG,OT_GUNIT_BF_C1REG,OT_GUNIT_BF_SVREG,OT_GUNIT_BF_FWPIPE')
sys.path[:0]=[str(code/'tools/s81_dv/layer_prog'),str(code/'tools/s81_dv'),str(code/'tools')]
os.environ['OT_S81_SELECTED_CHILD_FILES']='rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs.sv,rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstop.sv'
import dv_layer_compile as C
from layer_prog import bound_data as BD,bound_ctl_lanes as BCL,lower_gu as GU,lower_vpx as VPX
B=BD.load_bind(b/'out',str(b/'asbuilt_run.json'),code)
die=C.Die(code,netlist=B['netlist_path'],netlist_sha=B['netlist_sha256'],bound_rtl=b/'out/rtl');BD.rebind_links(die,B)
sched=C.layer_schedule(code,'L0','ar');prog=C.Prog(die)
ctx=dict(layer='L0',slice='u_s_0S',sched=sched,fixtures=r/'L0',svc_tag=0,svc_owner_epoch=None,svc_timing_profile='closing_allq',svc_allq=True,bound_ctl=BCL.load(B['bound']),bound_image_selectors=B['image_selectors'])
for op in sched['ops']:
 if any(re.search(rx,op['op']) for rx in GU.OPS):
  result=GU.lower(die,op,dict(ctx,t_issue=int(op['start']),ctl_used=set()))
  prog.absorb('gu',op,result)
# Exact command row from the preserved actual current819 L0 error.
prog.rows=[dict(eng=C.ENG['VN'],issue=10865,what='L0.ffn.router_allgather: u_s_7N cfg2')]
clashes=C.line_slot_conflicts(die,prog)
expected=(10865,'N',2,'ri_e',10943,'ffn.hc.coef_row0','L0.ffn.router_allgather: u_s_7N cfg2')
assert expected in clashes,clashes
reserved=C.gunit_ctl_line_reservations(die,prog)
assert (C.ENG['VN'],10865) in reserved
op=next(o for o in sched['ops'] if o['op']=='ffn.router_allgather')
raw=VPX.lower(die,op,dict(ctx,t_issue=int(op['start']),ctl_used=set()))
fixed=VPX.lower(die,op,dict(ctx,t_issue=int(op['start']),ctl_used=reserved))
baseline=C.Prog(die);baseline.events=list(prog.events);baseline.absorb('vpx',op,raw)
positive=C.Prog(die);positive.events=list(prog.events);positive.absorb('vpx',op,fixed)
raw_clashes=C.line_slot_conflicts(die,baseline)
fixed_clashes=C.line_slot_conflicts(die,positive)
assert not fixed_clashes,fixed_clashes
report=dict(status='REPRODUCED_AND_RESERVED_ACTUAL_CURRENT_SOURCE_COLLISION',captured_clashes=clashes,raw_collective_clashes=raw_clashes,fixed_collective_clashes=fixed_clashes,reserved=sorted(reserved),reservation_delays=fixed.get('reservation_delays'),raw_rows=raw['rows'],fixed_rows=fixed['rows'],gunit_ctl_events=[e for e in prog.events if e.get('inst')=='u_gunit' and e.get('kind')=='CTL' and e.get('dir')=='out'],router_collective=op,scope='minimum Gunit+actual captured Vrow and real collective allocator; no XS/frame arrays simulated')
(r/'bf_components_2240/vctl_collision_reservation_result.json').write_text(json.dumps(report,indent=1)+'\n')
print('ACTUAL_VCTL_COLLISION_RESERVED',expected,'raw_clashes',raw_clashes,'reservation_delays',fixed.get('reservation_delays'))
