#!/usr/bin/env bash
# Cycle-exact differential: fixed issuer v2 (rtl/.../ot_s81_fixed_issue.sv) against the frozen v1 structure
# (test/ot_s81_fixed_issue_v1_frozen.sv, d71ec3cfe) on the full 128-row / 13-engine / two-context program, every
# runtime mode of tb_s81_fixed_issue (0..3, 5..9). Every edge from tick 990 on compares cmd_v, cmd_d (84 x 13 bits),
# END/KIT/slot/KIT token, fault, fault code, job and command counters and busy. Mode 4 (incomplete PW) differs only in
# the arm edge (seal+128 -> seal+130, both fixtures assert their own edge). A planted v2 mutant (ISSUER_MUT=1) must
# differ. Usage: issue_v2_diff_gate.sh <outdir>
set -euo pipefail
R=$(cd "$(dirname "$0")/../.." && pwd); O=$(mkdir -p "$1" && cd "$1" && pwd); T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
S=$R/rtl/dsrom_sys/s81_static_control
(cd "$T" && python3 - "$R" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0,sys.argv[1]+'/tools/s81_static_control')
from program import encode_program
rows=[dict(engine=i%13,arg=0x010203+i*0x001523,issue=i,done=i+3)for i in range(126)]
rows += [dict(engine=14,arg=0,issue=129,done=0),dict(engine=15,arg=0,issue=130,done=0)]
Path('program.hex').write_text(''.join(f"{w['word']:09x}\n"for w in encode_program(rows,7,1)['writes']))
PY
)
cd "$T"
iverilog -g2012 -s tb_s81_fixed_issue -s tb_s81_fixed_issue_trace -o v1 $S/test/ot_s81_fixed_issue_v1_frozen.sv $S/test/tb_s81_fixed_issue_v1_frozen.sv $S/test/tb_s81_fixed_issue_trace.sv
iverilog -g2012 -s tb_s81_fixed_issue -s tb_s81_fixed_issue_trace -o v2 $S/ot_s81_fixed_issue.sv $S/test/tb_s81_fixed_issue.sv $S/test/tb_s81_fixed_issue_trace.sv
iverilog -g2012 -DISSUER_MUT=1 -s tb_s81_fixed_issue -s tb_s81_fixed_issue_trace -o v2m $S/ot_s81_fixed_issue.sv $S/test/tb_s81_fixed_issue.sv $S/test/tb_s81_fixed_issue_trace.sv
for m in 0 1 2 3 5 6 7 8 9; do
  vvp -n v1 +mode=$m | grep '^T ' > "$O/v1_mode$m.trace" & vvp -n v2 +mode=$m | grep '^T ' > "$O/v2_mode$m.trace" & wait
  n=$(wc -l < "$O/v2_mode$m.trace"); [ "$n" -ge 300 ] || { echo "ISSUE_V2_DIFF FAIL mode $m short trace $n"; exit 1; }
  cmp -s "$O/v1_mode$m.trace" "$O/v2_mode$m.trace" || { diff "$O/v1_mode$m.trace" "$O/v2_mode$m.trace" | head -5; echo "ISSUE_V2_DIFF FAIL mode $m"; exit 1; }
  echo "mode $m: $n edges identical"
done
vvp -n v2m +mode=0 2>&1 | grep '^T ' > "$O/v2_mut1.trace" || true
if cmp -s "$O/v1_mode0.trace" "$O/v2_mut1.trace"; then echo "ISSUE_V2_DIFF FAIL mutant escaped"; exit 1; fi
echo "MUT1 (commands one edge late) differs: $(diff "$O/v1_mode0.trace" "$O/v2_mut1.trace" | grep -c '^>') edges"
echo "ISSUE_V2_DIFF PASS"
