#!/usr/bin/env python3
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'tools/ref_tile'))
import gray_fifo_cdc_constraints as G
s=json.loads(Path('rtl/test/host_cdc_safe_1020/host_sram1.json').read_text())
r=G.lint(s,Path.cwd());Path('lint_host.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS ACTUAL HOST CDC LINT')
