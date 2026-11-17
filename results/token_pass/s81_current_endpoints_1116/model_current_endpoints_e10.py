from pathlib import Path
import json,os,sys
r=Path('/srv/opentallas-scratch2/claude/tok-verify-2/recovery1116/ds_current_compile1116');src=r/'selected_source';code=r/'code';b=Path('/srv/opentallas-scratch2/claude/s81-b3-clk/run/b/B6gF2s4tapfix1');a=json.loads((src/'physical/die_plan/s81/bind/frame_asbuilt.json').read_text())
os.environ.update(PYTHONDONTWRITEBYTECODE='1',OT_S81_SELECTED_SOURCE_ROOT=str(src),OT_S81_SELECTED_ASBUILT_MANIFEST='physical/die_plan/s81/bind/frame_asbuilt.json',OT_S81_SELECTED_DEFINES=','.join(a['defines']),OT_S81_SELECTED_CHILD_FILES='rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs.sv,rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstop.sv')
sys.path[:0]=[str(code/'tools/s81_dv'),str(code/'tools')]
import dv_layer_compile as C
from layer_prog import bound_data as BD
B=BD.load_bind(b/'out',str(b/'asbuilt_run.json'),code)
d=C.Die(code,netlist=B['netlist_path'],netlist_sha=B['netlist_sha256'],bound_rtl=b/'out/rtl')
pf={n:v for n,v in d.links.items() if v.get('direct_source_wire')};assert len(pf)==24,len(pf)
rec=BD.rebind_links(d,B);p={n:rec['rows'][n] for n in pf};h=rec['rows']['hbc_reverse_l0']
(r/'actual_current_endpoint_model.json').write_text(json.dumps(dict(schema='opentallas.s81.actual-endpoint-model.v1',source_bind=str(b),counts=rec['counts'],pf=p,hbc=h,selected_input_aliases=rec['selected_input_aliases'],scope='minimum static endpoint/age composition only; old disconnected w_x_* remain retired, no programme or clock-window qualification'),indent=1)+'\n')
assert h['status']=='PASS' and h['identity']=='selected_direct_wrapper_input',h
assert all(v['status']=='PASS' for v in p.values()),p
print('CURRENT_ENDPOINT_MODEL_PASS PF',len(p),'HBC',h['bound_age'],'COUNTS',rec['counts'])
