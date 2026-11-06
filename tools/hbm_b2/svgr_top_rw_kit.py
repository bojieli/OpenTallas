#!/usr/bin/env python3
"""Opt-in approved-cache-macro TOP recipe; normal invocation retains the canonical recipe."""
import argparse,importlib.util,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser(add_help=False);p.add_argument('--cache-rw',action='store_true');p.add_argument('--repo',type=Path,default=ROOT);p.add_argument('--prepare-only',action='store_true');p.add_argument('--profile-out',type=Path);a,rest=p.parse_known_args();repo=a.repo.resolve()
 recipes=None
 if a.cache_rw:
  if '--core-macros' in rest and rest[rest.index('--core-macros')+1]!='off':raise ValueError('RW proposal requires explicit reviewed recipe placements; --core-macros off')
  if '--core-macros' not in rest:rest.extend(['--core-macros','off'])
  recipes=json.loads((repo/'physical/die_plan/hbm/over_cap_split/reform_1106/svgr_top_cache/whole_top_recipe_delta.json').read_text())
  recipes['ot_svgr_top']['source_commit']=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
  if '--recipe-key' not in rest:rest.extend(['--recipe-key','ot_svgr_top'])
 if a.profile_out:a.profile_out.write_text(json.dumps(recipes,indent=2)+'\n')
 if a.prepare_only:return
 path=repo/'physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py';sys.path.insert(0,str(path.parent));spec=importlib.util.spec_from_file_location('svgr_top_rw_backend',path);gen=importlib.util.module_from_spec(spec);spec.loader.exec_module(gen);sys.argv=[str(path),*rest];gen.main(recipe_overrides=recipes)
if __name__=='__main__':main()
