#!/usr/bin/env python3
"""Stage the exact real-LSL wrapper gate into an owned scratch run directory."""
import json, pathlib, shutil, sys
here=pathlib.Path(__file__).resolve().parent
repo=here.parents[1]
out=pathlib.Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
paths=json.loads((here/'source_paths.json').read_text())
for path in paths:
    shutil.copyfile(repo/path,out/pathlib.Path(path).name)
for name in ('tb_lsl_sync.sv','run_miter.sh'):
    shutil.copyfile(here/name,out/name)
shutil.copyfile(repo/'rtl/physical/ot_qwen_tile_lsl_sync_fault.sv',out/'ot_qwen_tile_lsl_sync_fault.sv')
(out/'sources.txt').write_text('\n'.join(pathlib.Path(p).name for p in paths)+'\n')
(out/'run_miter.sh').chmod(0o755)
