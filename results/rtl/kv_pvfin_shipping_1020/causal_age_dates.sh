#!/bin/bash
set -eu
# Run from the immutable source root. Each causal mutant is a separate source copy.
base=$PWD
out=$1
mkdir -p "$out"
for kind in age date; do
 v="$out/$kind";mkdir -p "$v"
 rsync -a --exclude='/shipping_proof' --exclude='/shipping_calendar' --exclude='*.log' "$base/rtl" "$base/physical" "$base/results" "$v/"
 python3 - "$v/rtl/qwen_sys/split_20261014/qkd_pv_fin_s32.sv" "$kind" <<'PYM'
from pathlib import Path
import sys,hashlib
p=Path(sys.argv[1]);s=p.read_text();before=hashlib.sha256(s.encode()).hexdigest()
a,b=('else if(command_accept[0])age_operand<=0;','else if(command_accept[0])age_operand<=16\'d1;') if sys.argv[2]=='age' else ('.C(1),.IGNORE_R(1)) u_add_date','.C(2),.IGNORE_R(1)) u_add_date')
assert s.count(a)==1;s=s.replace(a,b);p.write_text(s)
p.with_suffix('.mutation.txt').write_text(before+' '+hashlib.sha256(s.encode()).hexdigest()+' '+a+' -> '+b+'\n')
PYM
 (set +e; cd "$v"; JOBS=4 bash results/rtl/kv_pvfin_shipping_1020/run_shipping.sh "$v/proof" 0 >"$v/run.log" 2>&1; echo $? >"$v/rc") &
done
wait
for kind in age date; do
 v="$out/$kind";test "$(cat "$v/rc")" = 1
 grep -Eq 'COLD MISMATCH|MISMATCH|DUT fault|fault raised unexpectedly' "$v/run.log"
 ! grep -q 'FAIL mut=0 build' "$v/run.log"
 echo "CAUSAL $kind DETECTED"
done
