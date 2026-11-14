import contextlib,copy,gzip,hashlib,importlib.util,io,json,sys,tempfile,types
from pathlib import Path
W=Path('/srv/opentallas-scratch2/claude/wt/die-kv-100')
D=Path('/srv/opentallas-scratch2/claude/tok-verify-2/kv_cpc_bridge')
sys.path[:0]=[str(W),str(W/'tools'),str(W/'tools/qwen_kv_die')]
s=importlib.util.spec_from_file_location('tools.token_pass.kv_pv_cpc_calendar',D/'kv_pv_cpc_calendar.py');C=importlib.util.module_from_spec(s);s.loader.exec_module(C);sys.modules[s.name]=C
p=W/'physical/die_plan/qwen_kvsys/hubc_pair_1113/native1'
plan=C.read(p/'plan_c.json');ab=C.read(p/'asbuilt_vN.json')
component=C.selected_pin_component(plan,ab,W,D/'proof')
assert component['cycles']==2
checks=['actual selected D5 source/CPC+2 match']
for variant in ('wrong_cost','duplicate_rule'):
 b=copy.deepcopy(ab)
 with tempfile.TemporaryDirectory(dir=D)as tmp:
  if variant=='duplicate_rule':b['core_pin_cycles']+=copy.deepcopy(b['core_pin_cycles'])
  else:
   t=Path(tmp)/'wrong.tsv';orig=W/b['core_pin_cycles'][0]['tsv'];t.write_text(orig.read_text().replace('\tout\t2\t','\tout\t3\t'));b['core_pin_cycles'][0]['tsv']=str(t)
  try:C.selected_pin_component(plan,b,W,D/'proof')
  except ValueError:checks.append(variant+' caught')
  else:raise AssertionError(variant+' not caught')
trunk=dict(schema='opentallas.kv.pv_landed_calendar.v1',result_cycles_added=3,first_input_age_cycles_added=0,arithmetic_cycles_added=0)
assert C.checked_calendar(trunk)==(3,0)
v2=dict(trunk,schema='opentallas.kv.pv_landed_calendar.v2',result_cycles_added=5,result_trunk_cycles_added=3,result_pin_cycles_added=2,source_pin_components=[component])
assert C.checked_calendar(v2)==(3,2)
for change in ({'result_cycles_added':7},{'source_pin_components':[component,component],'result_pin_cycles_added':4,'result_cycles_added':7},{'arithmetic_cycles_added':1}):
 try:C.checked_calendar(dict(v2,**change))
 except ValueError:checks.append('bad total/double count/input-arithmetic mutation caught')
 else:raise AssertionError('calendar mutation not caught')
from tools.qwen_kv_die import kv_static_params as KP,kv_bootage as BA
base=W/'physical/die_plan/qwen_kvsys/boot_v36/asbuilt_rtl6'
inp=D/'inputs';inp.mkdir(exist_ok=True)
for name in ('relay_stages','static_model','boot_ages'):
 (inp/(name+'.json')).write_bytes(gzip.open(base/(name+'.json.gz'),'rb').read())
paths=json.loads((inp/'static_model.json').read_text())['static_schedule']['paths'];pins=copy.deepcopy(paths);pins['fin']+=2
before=KP.schedule(paths,face_land_fin=1);after=KP.schedule(pins,face_land_fin=1)
assert before['pv']==after['pv']and before['vport']==after['vport']and after['attn']['F_DLY']==before['attn']['F_DLY']+2
assert after['attn']['PV_LEAD']==before['attn']['PV_LEAD']
boot0=BA.image_ages(before,dict(ECTL_QK_ISSUE_AGE=23));boot1=BA.image_ages(after,dict(ECTL_QK_ISSUE_AGE=23))
assert boot1['ages']['attn']['F_DLY']==boot0['ages']['attn']['F_DLY']+2
checks.append('actual schedule and boot F_DLY+2; PV/input/vport ages unchanged')
def boot_module(text,name):
 m=types.ModuleType(name);m.__file__=str(W/'physical/die_plan/qwen_kvsys/boot_v36/kv_boot_v36.py');exec(compile(text,m.__file__,'exec'),m.__dict__);return m
old=boot_module((W/'physical/die_plan/qwen_kvsys/boot_v36/kv_boot_v36.py').read_text(),'boot_old')
new=boot_module((D/'kv_boot_v36_new.py').read_text(),'boot_new')
args=dict(rs=str(inp/'relay_stages.json'),model=str(inp/'static_model.json'),groups=str(W/'physical/die_plan/qwen_kvsys/ns_kv100_out7/bind_1/out/bus_groups.json'),core_splits=str(W/'physical/die_plan/qwen_kvsys/plan_of_record/kv67_1104/core_splits.json'),pv_result_calendar=None)
for label,mod in [('old',old),('new',new)]:
 with contextlib.redirect_stdout(io.StringIO()):mod.prep(types.SimpleNamespace(**args,out=str(D/('prep_'+label))))
names={x.name for x in (D/'prep_old').iterdir()}
assert names=={x.name for x in (D/'prep_new').iterdir()}
assert all((D/'prep_old'/n).read_bytes()==(D/'prep_new'/n).read_bytes()for n in names)
checks.append('default actual ns7 prep byte-identical: '+str(len(names))+' files')
cal=D/'source_only_test_calendar.json';cal.write_text(json.dumps(dict(v2,result_cycles_added=2,result_trunk_cycles_added=0)))
with contextlib.redirect_stdout(io.StringIO()):new.prep(types.SimpleNamespace(**dict(args,pv_result_calendar=str(cal)),out=str(D/'prep_pin')))
b=json.loads((D/'prep_new/die_ages_bound_padded.json').read_text());a=json.loads((D/'prep_pin/die_ages_bound_padded.json').read_text())
assert a['schedule']['attn']['F_DLY']==b['schedule']['attn']['F_DLY']+2
assert a['schedule']['pv']==b['schedule']['pv']
assert a['pv']['RESULT_TRUNK_EXTRA']==0 and a['pv']['RESULT_PIN_EXTRA']==2
assert a['boot_ages']['attn']['F_DLY']==a['schedule']['attn']['F_DLY']
checks.append('scoped prep source-only contract F_DLY+2; no trunk/P0/P1 substitution')
r=dict(verdict='PASS_COMPONENT_TOOL_ONLY',checks=checks,pin_component=component,default_files=len(names),F_DLY_before=b['schedule']['attn']['F_DLY'],F_DLY_after=a['schedule']['attn']['F_DLY'],prototype_note='Old ns7 bind is a compatibility fixture, not current final geometry; actual trunk extension remains FAIL unsupportednode9->12. The source-only test calendar is a unit input, not a native provider or aggregate calendar.',native_programme_qualified=False)
(D/'proof.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
