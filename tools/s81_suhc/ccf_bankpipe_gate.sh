#!/bin/bash
set -euo pipefail
out=${1:?output directory required}
# $2 = EXTRA (HC-COMB 2026-10-16): 2 = PINREG 0 source (default), 3 = PINREG 1 (every leaf pin registered, uniform +3)
extra=${2:-2}
mkdir -p "$out"
root=$(pwd)
old=rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_ccf.sv
new=rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_ccf_bankpipe.sv
fifo=rtl/link/ot_fifo_sram_fwft.sv
macro="physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"
tb=rtl/dsrom_sys/s81_suhc/test/tb_ccf_bankpipe.sv
compile() {
  iverilog -g2012 -s tb_ccf_bankpipe -Ptb_ccf_bankpipe.EXTRA=$extra -o "$out/$1.vvp" "$old" "$2" "$fifo" $macro "$tb" > "$out/$1.build.log" 2>&1
}
compile positive "$new"
for seed in 1 17 91; do
  vvp "$out/positive.vvp" +MODE=0 +SEED="$seed" > "$out/positive_seed$seed.log" 2>&1
  grep -q '^CCF_BANKPIPE_PASS' "$out/positive_seed$seed.log"
  echo "CCF_POSITIVE seed=$seed PASS"
done
for faultcase in 1 2 3 4 5; do
  vvp "$out/positive.vvp" +MODE=0 +SEED=17 +FAULTCASE="$faultcase" > "$out/faultcase$faultcase.log" 2>&1
  grep -q '^CCF_BANKPIPE_PASS' "$out/faultcase$faultcase.log"
  echo "CCF_FAULTCASE case=$faultcase PASS"
done
for mode in 1 2 3 4 5 6 7; do
  set +e
  vvp "$out/positive.vvp" +MODE="$mode" +SEED=17 > "$out/clockstop$mode.log" 2>&1
  neg_rc=$?
  set -e
  test "$neg_rc" -ne 0
  grep -q 'CCF_BANKPIPE_FAIL' "$out/clockstop$mode.log"
  echo "CCF_CLOCKSTOP root=$mode OBSERVED_FAIL"
done
python3 - "$new" "$out" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text();out=Path(sys.argv[2])
for name,old,new in [('wrongpop','.pop(pop_q)',".pop(1'b0)"),('wronghead','head_o<=head;',"head_o<=head ^ 512'b1;"),('earlymetadata','fd_p <= fd_mid;','fd_p <= fd_i;'),('wrongfaultphase','pop_p<=pop_mid;','pop_p<=fv_q[POPBIT];'),('ignorebankovf',' || yf_ovf)',')'),('ignorebankhv',' || (pop_o && !yf_hv)',''),('statusskew','bo=PINREG ? bo_q : bank_overflow','bo=bank_overflow'),('popskew','wire pop_o=PINREG ? pop_p2 : pop_p','wire pop_o=pop_p'),('headskew','bank_heads = PINREG ? bh_q : bank_heads_pin','bank_heads = bank_heads_pin')]:
 assert s.count(old)==1,(name,s.count(old))
 (out/(name+'.sv')).write_text(s.replace(old,new))
PY
mutants="wrongpop wronghead earlymetadata wrongfaultphase ignorebankovf ignorebankhv"
[ "$extra" = 3 ] && mutants="$mutants statusskew popskew headskew"
for mutant in $mutants; do
  compile "$mutant" "$out/$mutant.sv"
  fault_probe=0
  if [ "$mutant" = wrongfaultphase ]; then fault_probe=1; fi
  if [ "$mutant" = ignorebankovf ]; then fault_probe=3; fi
  if [ "$mutant" = ignorebankhv ]; then fault_probe=4; fi
  if [ "$mutant" = statusskew ]; then fault_probe=3; fi
  if [ "$mutant" = popskew ]; then fault_probe=1; fi
  set +e
  vvp "$out/$mutant.vvp" +MODE=0 +SEED=17 +FAULTCASE="$fault_probe" > "$out/$mutant.log" 2>&1
  neg_rc=$?
  set -e
  test "$neg_rc" -ne 0
  grep -q 'CCF_BANKPIPE_FAIL' "$out/$mutant.log"
  echo "CCF_MUTANT $mutant OBSERVED_FAIL"
done
echo 'CCF_BANKPIPE_COMPONENT_GATE PASS'
