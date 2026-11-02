#!/usr/bin/env python3
"""Materialize source inputs/config only; never invoke ot-run, clock kit or EDA."""
import argparse, hashlib, json, pathlib, shutil
import yaml
p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--tools-root',required=True);p.add_argument('--out',required=True);a=p.parse_args()
here=pathlib.Path(__file__).resolve().parent;plan=pathlib.Path(a.plan).resolve();tools=pathlib.Path(a.tools_root).resolve();out=pathlib.Path(a.out).resolve()
assert hashlib.sha256(plan.read_bytes()).hexdigest()=='913be9b7f5ee612824f323d3d476999a36e2f224f1c3139f163d1b6558cdaab7','wrong frozen plan'
for rel,sha in [('tools/clk/ot_clk.py','84e4d3c680f7a1410e2a6df9605e76c812805d932c71a2e1a3cd88b7962305dd'),('tools/die_plan/die_trial.py','4706a921414952540f9a0d31ce2c58c4fa172f971bdb1239bc7bddce10906cfe')]:
 assert hashlib.sha256((tools/rel).read_bytes()).hexdigest()==sha,rel+' context mismatch'
assert not out.exists(),'fresh own output required';out.mkdir(parents=True)
shutil.copyfile(plan,out/'FROZEN_PLAN.json')
for n in ['part_region_FROZEN.json','feed_rt2_FROZEN.json']:shutil.copyfile(here/n,out/n)
c=yaml.safe_load((here/'config_FROZEN_DISABLED.yaml').read_text())
for k,n in [('plan','FROZEN_PLAN.json'),('region_map','part_region_FROZEN.json'),('feed','feed_rt2_FROZEN.json')]:c['inputs'][k]=str(out/n)
(out/'config.yaml').write_text(yaml.safe_dump(c,sort_keys=False))
(out/'PREP_ONLY.json').write_text(json.dumps({'status':'MATERIALIZED_NOT_GENERATED','tools_root':str(tools),'clock_kit_requires_separate_source_review':True,'native_import_requires_actual_clock_LOOK_and_provider_join':True},indent=2)+'\n')
print(out/'config.yaml')
