#!/usr/bin/env python3
"""Run the ordinary kit generator with an explicit private recipe JSON.
Remaining arguments are passed unchanged to gen_core_kit_hbm.main; use a new
output kit and the atomic candidate plan/view. This does not bypass its guards.
"""
import argparse,json,sys,importlib.util
from pathlib import Path
ap=argparse.ArgumentParser(add_help=False);ap.add_argument('--wt',type=Path,required=True);ap.add_argument('--recipe-json',type=Path,required=True)
a,rest=ap.parse_known_args();p=a.wt/'physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py'
spec=importlib.util.spec_from_file_location('gen_core_kit_hbm_candidate',p);m=importlib.util.module_from_spec(spec);sys.path.insert(0,str(p.parent));spec.loader.exec_module(m)
sys.argv=[str(p),*rest]
m.main(recipe_overrides=json.loads(a.recipe_json.read_text()))
