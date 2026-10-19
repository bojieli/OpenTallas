#!/bin/bash
# HBM-NATIVE5/RLY4 step 2: EW / WE take RS_RELAY=1 too (CTS probe rs capture 191.8 / 215.5 after the output-stage re-kit)
set -u
R=$PWD/bench_out2; mkdir -p $R
T=rtl/hbm_accel/die_glue/test
run() { local tag=$1; shift; echo "=== $tag: $*"; "$@" > $R/$tag.log 2>&1; echo "rc=$?" >> $R/$tag.log; tail -2 $R/$tag.log; }
for fl in EW WE; do
  run ${fl}_rr_pass  bash $T/bench_rly.sh pass  hbfd_rly_136_$fl 136 $R/w_${fl}_p 3
  run ${fl}_rr_mut   bash $T/bench_rly.sh mut   hbfd_rly_136_$fl 136 $R/w_${fl}_m 3
  run ${fl}_rr_rrmut bash $T/bench_rly.sh rrmut hbfd_rly_136_$fl 136 $R/w_${fl}_r 3
  run ${fl}_rr_rel0  bash $T/bench_rly.sh pass  hbfd_rly_136_$fl 136 $R/w_${fl}_z
  # regression: closed EW/WE fc / fcf benches (REL 0) with their old tile now relayed (OREL 3)
  run fc_${fl}_rel0  bash $T/bench_rly_fc.sh pass 136 $fl $R/w_fc_${fl}_z
  run f2_${fl}_rel0  bash $T/bench_rly_fcf.sh pass 136 $fl 2 $R/w_f2_${fl}_z
  run f4_${fl}_rel0  bash $T/bench_rly_fcf.sh pass 136 $fl 4 $R/w_f4_${fl}_z
done
echo ALL_DONE
