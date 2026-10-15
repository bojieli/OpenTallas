#!/bin/bash
# fill2_c8_bench.sh <pass|mut_vm_absent|mut_issuer> <out>: closure-loop bench pair of the die master dsfd_stage_seq_static_c8.
#  pass          the die-name wrapper gate (rtl/dsrom_sys/s81_static_control/test/run_static_c8.sh: 3:4 clocks, PW14,
#                consecutive commands incl. VM engine 12, KIT/status, 3 modes) AND the full 128-row issuer component
#                (tb_s81_fixed_issue: 126 rows over 13 engines + KIT + END, 10 modes incl. fault witnesses) -> "C8 BENCH PASS"
#  mut_vm_absent c8 built with ENG_PRESENT lacking VM 12 (OT_SSEQS_MUT_VM_ABSENT): must lose the VM command -> "C8 BENCH FAIL"
#  mut_issuer    issuer timing mutant ISSUER_MUT=1 on the 128-row program -> "C8 BENCH FAIL"
set -u
M=$1; OUT=$(mkdir -p $2 && cd $2 && pwd); R=$(pwd); S=$R/rtl/dsrom_sys/s81_static_control
T=$(mktemp -d); trap 'rm -rf $T' EXIT
prog() { (cd $T && python3 - "$R" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1] + '/tools/s81_static_control')
from program import encode_program
rows = [dict(engine=i % 13, arg=0x010203 + i * 0x001523, issue=i, done=i + 3) for i in range(126)]
rows += [dict(engine=14, arg=0, issue=129, done=0), dict(engine=15, arg=0, issue=130, done=0)]
Path('program.hex').write_text(''.join(f"{w['word']:09x}\n" for w in encode_program(rows, 7, 1)['writes']))
base = encode_program([dict(engine=10, arg=11880, issue=4, done=7), dict(engine=15, arg=0, issue=10, done=0)], 7, 1)
Path('base_program.hex').write_text(''.join(f"{w['word']:09x}\n" for w in base['writes']))
PY
) }
case $M in
pass)
  bash $S/test/run_static_c8.sh $OUT/c8 > $OUT/c8.log 2>&1; grep -q "S81_STATIC_C8 GATE PASS" $OUT/c8.log || { tail -3 $OUT/c8.log; echo "C8 BENCH FAIL pass(c8)"; exit 1; }
  prog; (cd $T && iverilog -g2012 -s tb_s81_fixed_issue -o sim $S/ot_s81_fixed_issue.sv $S/test/tb_s81_fixed_issue.sv) || { echo "C8 BENCH BUILD_FAIL"; exit 1; }
  for mode in 0 1 2 3 4 5 6 7 8 9; do (cd $T && vvp -n sim +mode=$mode) > $OUT/issue_m$mode.log 2>&1 || { tail -2 $OUT/issue_m$mode.log; echo "C8 BENCH FAIL issuer mode $mode"; exit 1; }
    grep -q "FATAL" $OUT/issue_m$mode.log && { grep -m1 FATAL $OUT/issue_m$mode.log; echo "C8 BENCH FAIL issuer mode $mode"; exit 1; }; done
  tail -1 $OUT/issue_m0.log; echo "C8 BENCH PASS (c8 wrapper 3 modes + 128-row issuer 10 modes)"; exit 0 ;;
mut_vm_absent)
  (cd $T && iverilog -g2012 -DOT_SSEQS_MUT_VM_ABSENT -s tb_s81_static_c8 -o m $S/ot_s81_fixed_issue.sv $S/ot_s81_fixed_mailbox.sv $S/dsfd_stage_seq_static_c.sv $S/dsfd_stage_seq_static_c8.sv $S/test/tb_s81_static_c8.sv && \
   python3 - "$R" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1] + '/tools/s81_static_control')
from program import encode_program
w = encode_program([dict(engine=0, arg=0x102938, issue=0, done=3), dict(engine=12, arg=0xfa0312, issue=1, done=4), dict(engine=14, arg=0, issue=6, done=0), dict(engine=15, arg=0, issue=7, done=0)], 7, 0)
Path('c8.hex').write_text(''.join(f"{x['word']:09x}\n" for x in w['writes']))
PY
  ) || { echo "C8 BENCH BUILD_FAIL"; exit 1; }
  (cd $T && vvp -n m +mode=0) > $OUT/mut.log 2>&1; rc=$?
  if [ $rc -ne 0 ] || grep -q FATAL $OUT/mut.log; then grep -m1 FATAL $OUT/mut.log; echo "C8 BENCH FAIL mut_vm_absent"; exit 1; fi
  echo "C8 BENCH PASS mut_vm_absent (mutant escaped)"; exit 0 ;;
mut_issuer)
  prog; (cd $T && iverilog -g2012 -DISSUER_MUT=1 -s tb_s81_fixed_issue -o mu $S/ot_s81_fixed_issue.sv $S/test/tb_s81_fixed_issue.sv) || { echo "C8 BENCH BUILD_FAIL"; exit 1; }
  (cd $T && vvp -n mu +mode=0) > $OUT/mut_issuer.log 2>&1; rc=$?
  if [ $rc -ne 0 ] || grep -q FATAL $OUT/mut_issuer.log; then grep -m1 -E "FATAL|ERROR" $OUT/mut_issuer.log; echo "C8 BENCH FAIL mut_issuer"; exit 1; fi
  echo "C8 BENCH PASS mut_issuer (mutant escaped)"; exit 0 ;;
esac
