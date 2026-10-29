#!/usr/bin/env python3
"""Prepare fresh HK4 clock geometry with the approved generic clock tool.

This only emits the kit. Inspect its rendered clock tree before launching GRT.
Input plan and pin assets come from the source-pinned HK4 event in this repo.
"""
import argparse,gzip,json,shutil,subprocess,sys
from pathlib import Path
W=Path(__file__).resolve().parents[2]
def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--out',required=True);a=a.parse_args();out=Path(a.out).resolve();src=W/'results/die_head_21_1028/hk4';inp=out/'input';inp.mkdir(parents=True,exist_ok=True)
 with gzip.open(src/'plan_spine_raw.json.gz','rb') as f:(inp/'plan.json').write_bytes(f.read())
 shutil.copytree(src/'core_pins',inp/'core_pins',dirs_exist_ok=True)
 cfg={'schema':'ot_clk_config/1','die':'head','event':{'name':'hk4_fresh_spine','source':'HK4 G0C351parts/327regions; new N3 feed entries, existing spine region membership'},'inputs':{'plan':str(inp/'plan.json'),'region_map':str(src/'spine_regions.json')},'stack':{'cell':'inv2','clock_rc':'ndr'},'top':{'form':'spine_fishbone','leaf_um':600,'rep_um':200,'site_slide':True},'region':{'form':'none'},'residual':{'cell_paths':True},'extra_argv':['--rep-actual-max','405']}
 # Plain JSON is valid YAML and records exact paths; PyYAML is a checked tool dependency.
 (out/'config.yaml').write_text(json.dumps(cfg,indent=1))
 cmd=[sys.executable,str(W/'tools/clk/ot_clk.py'),'kit',str(out/'config.yaml'),'--out',str(out/'clock_build'),'--die-trial',str(W/'tools/die_plan/die_trial.py')]
 print(' '.join(cmd),flush=True);return subprocess.call(cmd,cwd=W)
if __name__=='__main__':raise SystemExit(main())
