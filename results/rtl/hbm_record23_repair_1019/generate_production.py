from pathlib import Path
import sys,json,importlib.util,subprocess
import numpy as np
D=Path('/srv/opentallas-scratch/claude/hbm-native-record23-clock-1019');O=Path.cwd()
sys.path[:0]=[str(D/'tools'),str(D/'tools/hbm_static'),str(D/'tools/hgi_adapters'),str(D)]
spec=importlib.util.spec_from_file_location('fixed',O/'layer_images_fixed.py');LI=importlib.util.module_from_spec(spec);spec.loader.exec_module(LI)
F=D/'results/rtl/hbm_ds_layer_tput_1018/fixtures/L00'
records=LI.ds_dispatches_image(F/'images/ds_v41_1M_L00_per_die.json');fixture=LI.load_fixture(F)[23]
import su_bench as SB
from hbm_layer_vehicle.native_profile import NativeTiming
from native_su_calendar import compile_calendar
raw=SB.pack_rec(records[23][1]);place=LI.Placement(0);place.nxt=[33]*8
r=LI.su_record(raw,data=dict(fixture['vm_in']),place=place,pad_zero=True,timing=NativeTiming(18,15),safe_calendar=True)
LI.fixture_check(r,fixture);assert r['status']=='emitted',r['reasons']
LI.column_image(r['lines'],O/'production')
words=r['lines'];cw=[(x&~(((1<<180)-1)<<500))&~(((1<<234)-1)<<206)for x in words]
c,m=compile_calendar(cw,first_serial=2675,bridge_serial=2675,bridge_stream=3567,host_launch=3500,rows=160,request_lane_edges_by_bank=[4,5,0,0,0,0,0,0],write_lane_edges_by_bank=[3,3,0,0,0,0,0,0])
(O/'calendar.mem').write_text(''.join(f'{x:064x}\n'for x in c))
(O/'production/model.json').write_text(json.dumps({k:r[k]for k in ['setup_edge','issue_edges','last_commit','control_reservation','fixture']},indent=2))
(O/'production/calendar_model.json').write_text(json.dumps(m,indent=2))
W=len((O/'production/cols/config.mem').read_text().split())
with (O/'production/replay.log').open('w')as f:
 s=subprocess.run([str(D/'obj_arithmetic_clock/Vtb'),f'+CFG={O}/production/cols/config.mem',f'+GOLD={O}/production/quarter.mem',f'+N={len(words)}',f'+W={W}'],stdout=f,stderr=subprocess.STDOUT)
(O/'production/exit.txt').write_text(str(s.returncode));print('PRODUCTION',s.returncode,len(words),flush=True)
raise SystemExit(s.returncode)
