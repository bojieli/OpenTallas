#!/usr/bin/env python3
"""Stage exact current-repository host component sources; execute via ot-run."""
import json,sys,shutil
from pathlib import Path
here=Path(__file__).resolve().parent
repo=here.parents[1]
out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
for f in json.loads((here/'source_profile.json').read_text())["source_files"]+['rtl/lib/ot_rst_relay.sv']:
 shutil.copy2(repo/f,out/Path(f).name)
shutil.copy2(here/'tb_host_delivered_reset.sv',out/'tb.sv')
for f in ['run_staged.sh','mutant3.sh']:shutil.copy2(here/f,out/f)
print(f'cd {out} && bash run_staged.sh && bash mutant3.sh')
