#!/usr/bin/env python3
"""Lint real eight-child bottom graph against immutable native trace dependencies."""
import pathlib,subprocess,sys
src=pathlib.Path(sys.argv[1]);out=pathlib.Path.cwd()
files=(src/'tools/s81_hc_trace/sources.txt').read_text().splitlines()
files=[str(src/f) for f in files if not f.endswith('tb_s81_hc_trace.sv')]
files.append(str(out/'ot_s81_hc_cnbot_roots.sv'))
vl=pathlib.Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
with(out/'lint.log').open('w')as f:r=subprocess.run([str(vl),'--lint-only','--timing','-Wno-fatal','--top-module','ot_s81_hc_cnbot_roots',*files],stdout=f,stderr=subprocess.STDOUT)
if r.returncode:raise SystemExit(r.returncode)
print('CNBOT8_NATIVE_LINT_PASS')
