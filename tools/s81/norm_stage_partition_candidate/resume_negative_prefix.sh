#!/bin/bash
# Continue ONLY after the original immutable positive-prefix job is terminal.
# Do not launch if a vvp from that job is still live. Run through ot-run admission.
set -euo pipefail
python3 - <<'CHECK'
import pathlib,hashlib,re
p=pathlib.Path('.')
assert hashlib.sha256((p/'ot_s81_hc_ctfn_columns_candidate.sv').read_bytes()).hexdigest()=='51a1c53ef84e2a948a0479a56a3a71967de94828228c7b576e1a7b3f70879786'
assert re.search(r'^LOCKSTEP_PASS cycles=2048 checks=5970192 mutant=0$',(p/'positive.log').read_text(),re.M)
assert re.search(r'^OBSERVED_MISMATCH mutant=1 cycle=100 ',(p/'mutant1.log').read_text(),re.M)
assert 'FATAL:' in (p/'mutant1.log').read_text()
CHECK
for m in 2 3 4 5 6 7 8; do
 if test -e mutant$m.log; then echo "Refusing to overwrite existing mutant$m.log";exit 1;fi
 set +e
 vvp proof.vvp +MUTANT=$m > mutant$m.log 2>&1
 rc=$?
 set -e
 test "$rc" -ne 0
 python3 -c 'import pathlib,re,sys;m=int(sys.argv[1]);cycle=100 if m<=4 else 99;s=pathlib.Path("mutant"+str(m)+".log").read_text();assert re.search(r"^OBSERVED_MISMATCH mutant="+str(m)+r" cycle="+str(cycle)+" ",s,re.M);assert "FATAL:" in s' "$m"
 echo "MISSING_CLOCK_MUTANT_FAIL_OBSERVED $m"
done
