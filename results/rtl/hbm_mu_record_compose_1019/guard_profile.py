from pathlib import Path
import sys,importlib.util,json
D=Path('/srv/opentallas-scratch/claude/hbm-native-record23-clock-1019');O=Path('/srv/opentallas-scratch/claude/hbm-record23-repair-1019')
sys.path[:0]=[str(D/'tools'),str(D/'tools/hbm_static'),str(D/'tools/hgi_adapters'),str(D)]
spec=importlib.util.spec_from_file_location('guarded',O/'layer_images_guarded.py');LI=importlib.util.module_from_spec(spec);spec.loader.exec_module(LI)
import su_bench as SB,su_arith_lower as L,su_program_inventory as I
from hbm_layer_vehicle.native_profile import NativeTiming
F=D/'results/rtl/hbm_ds_layer_tput_1018/fixtures/L00'
records=LI.ds_dispatches_image(F/'images/ds_v41_1M_L00_per_die.json');fixture=LI.load_fixture(F)[23]
raw=SB.pack_rec(records[23][1]);place=LI.Placement(0);place.nxt=[33]*8
r=LI.su_record(raw,data=dict(fixture['vm_in']),place=place,pad_zero=True,timing=NativeTiming(18,15),safe_calendar=True)
assert r['status']=='emitted';LI.fixture_check(r,fixture)
assert r['lines']==[int(x,16) for x in (O/'production/quarter.mem').read_text().split()]
print('RECORD23_BYTE_IDENTICAL fixture128 PASS')
n=0
for index,rec in enumerate(records):
 if rec[1] is None: continue
 rr=SB.pack_rec(rec[1])
 try: row,sched=L.lower(rr)
 except Exception: continue
 if row.get('supported') and len(sched)>1:
  try: LI.su_record(rr,timing=NativeTiming(18,15),safe_calendar=True)
  except ValueError as e:
   assert 'exactly one issue group' in str(e);print('MULTI_GROUP_REFUSED',index,len(sched),str(e));n+=1
  else: raise AssertionError('multi-group admitted')
assert n
# Inject only the missing descriptor into decode; lower must not execute.
orig_decode=I.decode
_,unit,sut,desc=orig_decode(raw)
def no_a(x): return (_,unit,sut,{k:v for k,v in desc.items() if k!='A'})
I.decode=no_a
try: LI.su_record(raw,timing=NativeTiming(18,15),safe_calendar=True)
except ValueError as e: assert 'live A operand' in str(e);print('ABSENT_A_REFUSED PASS')
else: raise AssertionError('missing A admitted')
finally: I.decode=orig_decode
print('SUPPORTED_PROFILE_GUARDS PASS',n)
