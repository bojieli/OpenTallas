from pathlib import Path
import importlib.util,sys,json,hashlib
import numpy as np
D=Path('/srv/opentallas-scratch/claude/hbm-native-record23-clock-1019');O=Path.cwd()
sys.path[:0]=[str(D/'tools'),str(D/'tools/hbm_static'),str(D/'tools/hgi_adapters'),str(D)]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
LI=load('fixed',O/'layer_images_fixed.py');old=load('baseline',D/'tools/hbm_layer_vehicle/layer_images.py')
F=D/'results/rtl/hbm_ds_layer_tput_1018/fixtures/L00';rec=LI.ds_dispatches_image(F/'images/ds_v41_1M_L00_per_die.json');fixture=LI.load_fixture(F)[23]
import su_bench as SB
from hbm_layer_vehicle.native_profile import NativeTiming
from native_su_calendar import compile_calendar
raw=SB.pack_rec(rec[23][1])
def gen(m,safe=False):
 place=m.Placement(0);place.nxt=[33]*8
 kwargs={'safe_calendar':True}if safe else {}
 return m.su_record(raw,data=dict(fixture['vm_in']),place=place,pad_zero=True,timing=NativeTiming(18,15),**kwargs)
a,b=gen(old),gen(LI);assert a['lines']==b['lines'];assert a['expect']==b['expect'];assert a['preload']==b['preload']
r=gen(LI,True);LI.fixture_check(r,fixture);assert r['fixture']['mismatched_words']==0
assert r['last_commit']==a['last_commit']+1
assert [dict(x,edge=0)for x in a['expect']]==[dict(x,edge=0)for x in r['expect']]
assert r['lines']==[int(x,16)for x in (O/'production/quarter.mem').read_text().split()]
# Two static users with different controls cannot overlap one live datapath.
# Even all-zero vs disjoint nonzero controls collide under the new contract.
t=LI.QLine();u=LI.QLine();t.f['control'][0]=0;u.f['control'][0]=1
assert not LI.calendar_collision(t,u,0)
assert LI.calendar_collision(t,u,0,exclusive_controls=True)
t=LI.QLine();u=LI.QLine();t.f['control'][0]=1;u.f['control'][0]=2
assert not LI.calendar_collision(t,u,0)
assert LI.calendar_collision(t,u,0,exclusive_controls=True)
for edge in range(73):
 assert LI.calendar_collision(r['ql'],r['ql'],edge,exclusive_controls=True)
assert not LI.calendar_collision(r['ql'],r['ql'],73,exclusive_controls=True)
hashes={}
for name in ['drain0','drain1','production','absent_reader_identity','missing_control_lifetime','old_drain_gap','old_fill_deadline']:
 dest=O/name
 if not (dest/'quarter.mem').exists():continue
 words=[int(x,16)for x in(dest/'quarter.mem').read_text().split()];cw=[(x&~(((1<<180)-1)<<500))&~(((1<<234)-1)<<206)for x in words]
 c,_=compile_calendar(cw,first_serial=2675,bridge_serial=2675,bridge_stream=3567,host_launch=3500,rows=160,request_lane_edges_by_bank=[4,5,0,0,0,0,0,0],write_lane_edges_by_bank=[3,3,0,0,0,0,0,0])
 (dest/'calendar.mem').write_text(''.join(f'{x:064x}\n'for x in c))
 for file in ['quarter.mem','calendar.mem','cols/config.mem','replay.log']:
  p=dest/file
  if p.exists():hashes[str(p.relative_to(O))]=hashlib.sha256(p.read_bytes()).hexdigest()
for p in [D/'obj_arithmetic_clock/Vtb__ALL.a',D/'obj_arithmetic_clock/Vtb',D/'native_record23_tb.sv',D/'pll_functional_model.sv',D/'current_sources.tar',D/'su_SW0_gen2c_l12_source_profile.json',O/'layer_images_fixed.py']:
 hashes[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
(O/'contract_proof.json').write_text(json.dumps(dict(default_byte_identical=True,numeric128_fixture_unchanged=True,original32_RTL_PASS=True,multi_user_static_reservation_model_only=True,two_user_offset_serial_edges=73,old_commands=52,diagnostic_commands=53,production_commands=73,extra_drain_nominal_ps=10000/9,extra_drain_frozen_PLL_ps=1112,extra_busy_serial_edges=21,extra_busy_frozen_PLL_ps=23352,full_SU_MU_token_qualified=False,hashes=hashes),indent=2))
print('CONTRACT PASS defaults/numerics/lifetimes/static2usercollision/73edgeisolation')
