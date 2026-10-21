#!/usr/bin/env python3
import json,hashlib
from pathlib import Path
import engine_native32 as E
plan=json.load(open('external_outputs.json'));E.OUT_COPIES={k:v['copies'] for k,v in plan.items()}
r=E.generate(Path('original.v'),Path('textbook_lint.py'),hashlib.sha256(Path('original.v').read_bytes()).hexdigest(),'qkd_hr_ingest_soft_n32',Path('qkd_hr_ingest_soft_n32.sv'))
print('GENERATED_CONTROLLER_WITH_CONTEXT_OUTPUT_COPIES',r['generated_cells'])
