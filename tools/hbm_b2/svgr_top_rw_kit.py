#!/usr/bin/env python3
"""Opt-in approved-cache-macro TOP recipe; normal invocation retains the canonical recipe."""
import argparse,importlib.util,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser(add_help=False);p.add_argument('--cache-rw',action='store_true');p.add_argument('--cache-placement',type=Path);p.add_argument('--repo',type=Path,default=ROOT);p.add_argument('--prepare-only',action='store_true');p.add_argument('--profile-out',type=Path);p.add_argument('--recipe-delta',type=Path,default=None);a,rest=p.parse_known_args();repo=a.repo.resolve()
 recipes=None
 if a.cache_placement and not a.cache_rw:raise ValueError('--cache-placement requires --cache-rw')
 if a.cache_rw:
  if '--core-macros' in rest and rest[rest.index('--core-macros')+1]!='off':raise ValueError('RW proposal requires explicit reviewed recipe placements; --core-macros off')
  if '--core-macros' not in rest:rest.extend(['--core-macros','off'])
  recipes=json.loads((a.recipe_delta or repo/'physical/die_plan/hbm/over_cap_split/reform_1106/svgr_top_cache/whole_top_recipe_delta.json').read_text())
  if a.cache_placement:
   placement=json.loads(a.cache_placement.read_text());rows=placement if isinstance(placement,list) else placement.get('proposed_macro_placement',placement.get('actual_macro_placement',[]));old={m['inst']:m['macro'] for m in recipes['ot_svgr_top']['macro_placement']};new=[dict(inst=m['instance'].removeprefix('u_fcore.'),macro=m['master'],xy_um=m['origin_um'],orient=m['orient']) for m in rows]
   if len(new)!=len(old) or {m['inst']:m['macro'] for m in new}!=old:raise ValueError('placement override must retain all nine exact source instances and masters')
   recipes['ot_svgr_top']['macro_placement']=new
  recipes['ot_svgr_top']['source_commit']=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
  if '--recipe-key' not in rest:rest.extend(['--recipe-key','ot_svgr_top'])
 if a.profile_out:a.profile_out.write_text(json.dumps(recipes,indent=2)+'\n')
 if a.prepare_only:return
 path=repo/'physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py';sys.path.insert(0,str(path.parent));spec=importlib.util.spec_from_file_location('svgr_top_rw_backend',path);gen=importlib.util.module_from_spec(spec);spec.loader.exec_module(gen);sys.argv=[str(path),*rest];gen.main(recipe_overrides=recipes)
if __name__=='__main__':main()
