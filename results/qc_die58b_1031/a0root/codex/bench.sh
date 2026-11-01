#!/bin/bash
set -eu
b=/srv/opentallas-scratch2/claude/codex-qca0/icg-bench
# The upstream bench deliberately $finish-es for both verdicts; the marker is the contract, never process status alone.
for m in 0 12 2; do
 "$b/Vtb_a0_icg" +OT_ROM_DIR="$b/rom" +ICG_MUT=$m > "$b/m$m.log" 2>&1
done
python3 - "$b" <<'PY2'
from pathlib import Path
import json,re,sys
p=Path(sys.argv[1]);out={}
for m in [0,12,2]:
 s=(p/f'm{m}.log').read_text()
 if m==0: assert re.search(r'A0ICG_PASS.*qualified_errors=0',s),s
 else:
  q=re.search(r'A0ICG_FAIL.*qualified_errors=(\d+)',s)
  assert q and int(q[1])>0,s
 out[str(m)]={'expected':'PASS' if m==0 else 'FAIL_CAUGHT','matched':True,'summary':[l for l in s.splitlines() if 'A0ICG_COUNTS' in l or 'A0ICG_PASS' in l or 'A0ICG_FAIL' in l]}
(p/'qualified_receipt.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out))
PY2
