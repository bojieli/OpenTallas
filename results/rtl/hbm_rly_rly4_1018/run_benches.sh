#!/bin/bash
# HBM-NATIVE5/RLY4 fleet bench driver: runs in a copy of the repo subset (cwd = repo root)
set -u
R=$PWD/bench_out; mkdir -p $R
T=rtl/hbm_accel/die_glue/test
run() { local tag=$1; shift; echo "=== $tag: $*"; "$@" > $R/$tag.log 2>&1; echo "rc=$?" >> $R/$tag.log; tail -2 $R/$tag.log; }
# changed base masters (RS_RELAY=1): REL 3 pass, bit0 mutant, reset-relay-bypass mutant; REL 0 form still PASS
for fl in NS SN; do
  run ${fl}_pass  bash $T/bench_rly.sh pass  hbfd_rly_136_$fl 136 $R/w_${fl}_p 3
  run ${fl}_mut   bash $T/bench_rly.sh mut   hbfd_rly_136_$fl 136 $R/w_${fl}_m 3
  run ${fl}_rrmut bash $T/bench_rly.sh rrmut hbfd_rly_136_$fl 136 $R/w_${fl}_r 3
  run ${fl}_rel0  bash $T/bench_rly.sh pass  hbfd_rly_136_$fl 136 $R/w_${fl}_z
done
# unchanged RTL base masters (kit re-generated only): the old bench form
for fl in EW WE; do
  run ${fl}_pass bash $T/bench_rly.sh pass hbfd_rly_136_$fl 136 $R/w_${fl}_p
  run ${fl}_mut  bash $T/bench_rly.sh mut  hbfd_rly_136_$fl 136 $R/w_${fl}_m
  run ${fl}_rel3_neg bash $T/bench_rly.sh pass hbfd_rly_136_$fl 136 $R/w_${fl}_n 3
done
# regression: the fc / fcf benches whose OLD tile is now a RS_RELAY master (OREL 3), exactly as their closed job specs call them
run fc_NS_pass    bash $T/bench_rly_fc.sh pass  136 NS $R/w_fc_NS_p 3
run fc_SN_rrmut   bash $T/bench_rly_fc.sh rrmut 136 SN $R/w_fc_SN_r 3
run fc_SN_mut     bash $T/bench_rly_fc.sh mut   136 SN $R/w_fc_SN_m 3
run fc_SN_pass    bash $T/bench_rly_fc.sh pass  136 SN $R/w_fc_SN_p 3
run f2_NS_pass    bash $T/bench_rly_fcf.sh pass 136 NS 2 $R/w_f2_NS_p 3
run f4_SN_pass    bash $T/bench_rly_fcf.sh pass 136 SN 4 $R/w_f4_SN_p 3
run f4_NS_rel0    bash $T/bench_rly_fcf.sh pass 136 NS 4 $R/w_f4_NS_z
run f3_SN_rel0    bash $T/bench_rly_fcf.sh pass 136 SN 3 $R/w_f3_SN_z
run fc_EW_rel0    bash $T/bench_rly_fc.sh pass 136 EW $R/w_fc_EW_z
run fc_624_rel0   bash $T/bench_rly_fc.sh pass 624 NS $R/w_fc_624_z
echo ALL_DONE
