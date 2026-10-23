#!/usr/bin/env python3
from pathlib import Path
import subprocess,sys
args=['python3','native_census.py','--netlist','resynth.v','--top',sys.argv[1]if len(sys.argv)>1 else'qkd_hr_core_prompt_n32','--out','native32_macros.json']
for p in sorted(list(Path('libs').glob('*.lib'))+list(Path('macro_libs').glob('*.lib'))):args+=['--liberty',str(p)]
raise SystemExit(subprocess.run(args).returncode)
