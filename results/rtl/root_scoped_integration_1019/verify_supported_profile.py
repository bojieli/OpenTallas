from pathlib import Path
import sys,importlib.util,json,hashlib
R=Path.cwd()
sys.path[:0]=[str(R/'tools'),str(R/'tools/hbm_static'),str(R/'tools/hgi_adapters')]
from hbm_layer_vehicle import layer_images as new
from hbm_layer_vehicle.native_profile import NativeTiming
import su_bench as SB,su_arith_lower as L,su_program_inventory as I
s=importlib.util.spec_from_file_location('current_main_baseline',R/'layer_images_baseline.py');old=importlib.util.module_from_spec(s);s.loader.exec_module(old)
F=R/'results/rtl/hbm_ds_layer_tput_1018/fixtures/L00'
records=new.ds_dispatches_image(F/'images/ds_v41_1M_L00_per_die.json');fixtures=new.load_fixture(F)
where={}
for image_index,entry in enumerate(records):where.setdefault(entry[2]['tag'],[]).append(image_index)
fixture_by_image={where[fr['tag']][fr['occ']]:fr for fr in fixtures.values() if fr['tag'] in where and fr['occ']<len(where[fr['tag']])}
counts=dict(default_emitted=0,default_other=0,matched_errors=0,multigroup_refused=0,actual_fixture_inputs=0)
qualified_negative_mapping=[]
for idx,rec in enumerate(records):
 if rec[1] is None:continue
 raw=SB.pack_rec(rec[1]);fixture=fixture_by_image.get(idx)
 if fixture is not None:counts['actual_fixture_inputs']+=1
 data=dict(fixture['vm_in']) if fixture is not None else {}
 results=[]
 for module in (old,new):
  place=module.Placement(0);place.nxt=[33]*8
  try:result=module.su_record(raw,data=dict(data),place=place,pad_zero=True);results.append(('ok',result))
  except Exception as e:results.append(('error',(type(e).__name__,str(e))))
 assert results[0][0]==results[1][0],(idx,results)
 if results[0][0]=='error':assert results[0][1]==results[1][1],(idx,results);counts['matched_errors']+=1;continue
 a,b=results[0][1],results[1][1]
 assert a.keys()==b.keys(),(idx,a.keys(),b.keys())
 for k in a:
  if k=='ql':assert a[k].f==b[k].f,(idx,k)
  else:assert a[k]==b[k],(idx,k)
 counts['default_emitted' if a['status']=='emitted' else 'default_other']+=1
assert counts['default_emitted']>0,counts
raw=SB.pack_rec(records[23][1]);fixture=fixture_by_image[23];assert fixture['k']==23 and fixture['tag']=='attend.bf16_p';place=new.Placement(0);place.nxt=[33]*8
r=new.su_record(raw,data=dict(fixture['vm_in']),place=place,pad_zero=True,timing=NativeTiming(18,15),safe_calendar=True)
new.fixture_check(r,fixture);assert r['fixture']['mismatched_words']==0 and r['fixture']['checked_words']==128,r['fixture']
quarter=R/'results/rtl/hbm_record23_repair_1019/production/quarter.mem'
assert r['lines']==[int(v,16) for v in quarter.read_text().split()]
for idx in (6,11,33,50):
 raw_group=SB.pack_rec(records[idx][1]);row,sched=L.lower(raw_group);assert row['supported'] and len(sched)>1
 tag=records[idx][2]['tag'];occ=where[tag].index(idx)
 priced=[i for i,fr in fixtures.items() if fr['tag']==tag and fr['occ']==occ]
 _,unit,sut,desc=I.decode(raw_group)
 qualified_negative_mapping.append(dict(image_index=idx,tag=tag,occurrence=occ,priced_ids=priced,fixture_k_layer=fixture_by_image[idx]['k'],decoded_unit=unit,decoded_roles=sorted(desc),decoded_sut=sut,issue_groups=len(sched)))
 try:new.su_record(raw_group,timing=NativeTiming(18,15),safe_calendar=True)
 except ValueError as e:assert 'exactly one issue group' in str(e);counts['multigroup_refused']+=1
 else:raise AssertionError(('multigroup admitted',idx))
original=I.decode
_,unit,sut,desc=original(raw)
def no_a(value):return (_,unit,sut,{k:v for k,v in desc.items() if k!='A'})
I.decode=no_a
try:
 try:new.su_record(raw,timing=NativeTiming(18,15),safe_calendar=True)
 except ValueError as e:assert 'live A operand' in str(e)
 else:raise AssertionError('missing A admitted')
finally:I.decode=original
for offset in range(73):assert new.calendar_collision(r['ql'],r['ql'],offset,exclusive_controls=True)
assert not new.calendar_collision(r['ql'],r['ql'],73,exclusive_controls=True)
print('CURRENT_MAIN_DEFAULT_IDENTITY_PASS',json.dumps(counts,sort_keys=True))
print('BOUNDED_NATIVE_PROFILE_PASS golden128 commands73 liveA singleissue; no MU/fulltoken qualification')
print('QUALIFIED_NEGATIVE_MAPPING',json.dumps(qualified_negative_mapping,sort_keys=True))
print('SOURCE_SHA256',hashlib.sha256((R/'tools/hbm_layer_vehicle/layer_images.py').read_bytes()).hexdigest())
print('BASELINE_SHA256',hashlib.sha256((R/'layer_images_baseline.py').read_bytes()).hexdigest())
