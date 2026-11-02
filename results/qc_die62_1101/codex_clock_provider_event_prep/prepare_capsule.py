#!/usr/bin/env python3
"""Materialize source inputs/config only; never invoke ot-run, clock kit or EDA."""
import argparse, hashlib, json, pathlib, shutil, subprocess
import yaml
p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--tools-root',required=True);p.add_argument('--out',required=True);a=p.parse_args()
here=pathlib.Path(__file__).resolve().parent;plan=pathlib.Path(a.plan).resolve();tools=pathlib.Path(a.tools_root).resolve();out=pathlib.Path(a.out).resolve()
assert hashlib.sha256(plan.read_bytes()).hexdigest()=='913be9b7f5ee612824f323d3d476999a36e2f224f1c3139f163d1b6558cdaab7','wrong frozen plan'
for rel,sha in [('tools/clk/ot_clk.py','84e4d3c680f7a1410e2a6df9605e76c812805d932c71a2e1a3cd88b7962305dd'),('tools/die_plan/die_trial.py','4706a921414952540f9a0d31ce2c58c4fa172f971bdb1239bc7bddce10906cfe')]:
 assert hashlib.sha256((tools/rel).read_bytes()).hexdigest()==sha,rel+' context mismatch'
assert not out.exists(),'fresh own output required';out.mkdir(parents=True)
shutil.copyfile(plan,out/'FROZEN_PLAN.json')
known=json.loads((here/'part_region_FROZEN.json').read_text())
mapping=json.loads((here/'recovered_part_region_actual1364730.json').read_text())['part_region']
assert len(mapping)==377 and len(set(mapping.values()))==313
assert all(mapping.get(k)==v for k,v in known.items())
assert set(mapping)-set(known)=={'io_serdes','io_serdes_1','io_serdes_2','ucie_kv'}
(out/'part_region_FROZEN_wrapped.json').write_text(json.dumps({'part_region':mapping},indent=2)+'\n')
shutil.copyfile(here/'feed_rt2_FROZEN.json',out/'feed_rt2_FROZEN.json')
# Plan-relative pin/bin references must travel with a relocated plan. Repository
# LEF/Lib references remain in the explicit frozen tools/readset checkout.
plan_dir=tools/'physical/die_plan/qwen_compute/plan_of_record';refs=set()
def walk(obj):
 if isinstance(obj,dict):
  for key,val in obj.items():
   if key in {'pins_file','sink_bins_file','clock_entries_file','source_file','lib','lef'} and isinstance(val,str):refs.add((key,val))
   walk(val)
 elif isinstance(obj,list):
  for val in obj:walk(val)
walk(json.loads(plan.read_text()));assets=[];missing=[]
for key,val in sorted(refs):
 src=pathlib.Path(val)
 if src.is_absolute():
  if not src.is_file():missing.append(val)
  continue
 if (plan_dir/src).is_file():
  source=plan_dir/src;dest=(out/src).resolve();assert dest.is_relative_to(out),val
  dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest);mode='copied_plan_relative'
 elif (tools/src).is_file():source=tools/src;mode='repo_root_reference_present'
 else:missing.append(val);continue
 assets.append({'key':key,'path':val,'mode':mode,'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
(out/'RELATIVE_ASSET_CLOSURE.json').write_text(json.dumps({'files':assets,'missing':missing},indent=2)+'\n')
assert not missing,'missing frozen readset: '+str(missing)
cal_rel='results/qc_die52_1031/inv2_1x_stage_cal_gen52b_grt1x.json'
cal=subprocess.check_output(['git','show','HEAD:'+cal_rel],cwd=tools)
assert hashlib.sha256(cal).hexdigest()=='f3e6848295a16882127a6b4d073882d4c0aa4cc8d887a224beec87f735fc5e47'
(out/'stage_cal_source_FROZEN.json').write_bytes(cal)

c=yaml.safe_load((here/'config_FROZEN_DISABLED.yaml').read_text())
for k,n in [('plan','FROZEN_PLAN.json'),('region_map','part_region_FROZEN_wrapped.json'),('feed','feed_rt2_FROZEN.json')]:c['inputs'][k]=str(out/n)
(out/'config.yaml').write_text(yaml.safe_dump(c,sort_keys=False))
(out/'PHY_CLOCK_BINDING_HOLD.json').write_text(json.dumps({'status':'HOLD_NO_PHY_PHASE_OR_RELEASE_CREDIT','semantic377region_input_recovery_only':True,'serdes833regional_vs_nativeFDI1000MHz':'Knowncalendar/sourcehold; no clockalias or borrowedPHYarrivals evenifcorejoinmatches'},indent=2)+'\n')
(out/'PREP_ONLY.json').write_text(json.dumps({'status':'MATERIALIZED_NOT_GENERATED','tools_root':str(tools),'clock_kit_requires_separate_source_review':True,'native_import_requires_actual_clock_LOOK_and_provider_join':True},indent=2)+'\n')
print(out/'config.yaml')
