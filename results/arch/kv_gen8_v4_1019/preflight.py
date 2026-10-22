#!/usr/bin/env python3
import subprocess,tempfile
from pathlib import Path
p=Path('tools/qwen_kv_die/chain/kvsys_prep.sh'); s=p.read_text(); fn=s[s.index('kv_orient() {'):s.index('\nif [ "${OT_KV_EXPAND:-all}" != none ]; then kv_orient expand; fi')]
with tempfile.TemporaryDirectory(prefix='orient argv ') as td:
 root=Path(td); (root/'case_kv').mkdir()
 # The shell calls its actual extracted function under nounset. Python command spy
 # validates exact argv boundaries including an output directory containing spaces.
 script='set -eu\nO='+repr(td)+'\n'+fn+'\npython3() { [ "$#" = "$EXPECTED" ]; [ "$1" = tools/qwen_kv_die/kv_place_orient.py ]; [ "$3" = "$O/case_kv" ]; [ "$5" = "$O/case_kv/place_orientations_${STAGE}.json" ]; if [ "$#" = 6 ]; then [ "$6" = --check-only ]; fi; echo ARGV_PASS; }\nEXPECTED=5 STAGE=expand; kv_orient expand\nEXPECTED=5 STAGE=prefwd; kv_orient prefwd\nEXPECTED=6 STAGE=final; kv_orient final --check-only\n'
 subprocess.run(['bash','-c',script],check=True)
 bad=subprocess.run(['bash','-c','set -eu\n'+fn+'\nkv_orient'],capture_output=True,text=True)
 assert bad.returncode!=0 and 'requires a report stage' in bad.stderr
print('SHELL_ARGV_PREFLIGHT PASS: one-argument expand/prefwd, optional final, missing-stage refusal')
