#!/usr/bin/env python3
"""Fresh opt-in H0 prefix-adder vehicle; normal synth/LEC/place first."""
import gzip,json,shutil,subprocess,sys
from pathlib import Path
root,out=map(Path,sys.argv[1:3]);src=root/'results/codex_s81_cores_resume1029';slices=out/'slices';slices.mkdir(parents=True,exist_ok=True)
(slices/'dsdv_eng_rr_h0.json').write_bytes(gzip.decompress((src/'h0_prefix48_slice.json.gz').read_bytes()))
subprocess.run([sys.executable,str(root/'physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py'),'--module','dsdv_eng_rr_h0','--recipes',str(src/'h0_prefix_recipe.json'),'--out',str(out),'--suffix','prefix48_1029','--master-slice',str(slices),'--trial'],check=True)
kit=out/'dsdv_eng_rr_h0_prefix48_1029';freeze=json.load(open(kit/'freeze.json'));shutil.copy2(root/'physical/die_plan/s81'/freeze['pins_file'],kit/'plan_pins.json')
