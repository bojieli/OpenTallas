#!/usr/bin/env python3
"""Opt in an OWN copied runner to the parent-approved exact-logic proof checker."""
from pathlib import Path
import sys

p=Path(sys.argv[1])/'run_kit_hbm.sh'
t=p.read_text()
old='if [ \\$rc = 0 ] && [ -f /work/lec.py ]'
assert t.count(old)==1
new=('if [ \\$rc = 0 ] && [ -f /work/lec/reuse.json ]; then '
     'python3 -I /work/check_logic_reuse.py /work > /work/lec_reuse.log 2>&1; rr=\\$?; '
     'cat /work/lec_reuse.log; if [ \\$rr != 0 ]; then '
     "echo 'FAIL_PREFLOOR logic-proof reuse mismatch' | tee -a /work/FAIL_PREFLOOR; rc=3; fi; fi; \\\n  "
     'if [ \\$rc = 0 ] && [ ! -f /work/lec/reuse.json ] && [ -f /work/lec.py ]')
p.write_text(t.replace(old,new))
