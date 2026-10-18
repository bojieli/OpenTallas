#!/bin/bash
# NATIVE-FIX3/rly fleet bench driver: runs in a copy of the repo subset (cwd = repo root)
set -u
R=$PWD/bench_out; mkdir -p $R
T=rtl/hbm_accel/die_glue/test
run() { local tag=$1; shift; echo "=== $tag: $*"; "$@" > $R/$tag.log 2>&1; echo "rc=$?" >> $R/$tag.log; tail -2 $R/$tag.log; }
for fl in NS SN; do
  run fc_${fl}_pass   bash $T/bench_rly_fc.sh pass  136 $fl $R/w_fc_${fl}_p 3
  run fc_${fl}_mut    bash $T/bench_rly_fc.sh mut   136 $fl $R/w_fc_${fl}_m 3
  run fc_${fl}_ckmut  bash $T/bench_rly_fc.sh ckmut 136 $fl $R/w_fc_${fl}_c 3
  run fc_${fl}_rrmut  bash $T/bench_rly_fc.sh rrmut 136 $fl $R/w_fc_${fl}_r 3
  run fc_${fl}_rel0   bash $T/bench_rly_fc.sh pass  136 $fl $R/w_fc_${fl}_z 0
done
for x in NS:2 NS:3 SN:2 SN:4; do fl=${x%:*}; n=${x#*:}
  run f${n}_${fl}_pass  bash $T/bench_rly_fcf.sh pass  136 $fl $n $R/w_f${n}_${fl}_p 3
  run f${n}_${fl}_mut   bash $T/bench_rly_fcf.sh mut   136 $fl $n $R/w_f${n}_${fl}_m 3
  for k in $(seq 0 $((n-1))); do run f${n}_${fl}_ckmut$k bash $T/bench_rly_fcf.sh ckmut$k 136 $fl $n $R/w_f${n}_${fl}_c$k 3; done
  run f${n}_${fl}_rrmut bash $T/bench_rly_fcf.sh rrmut 136 $fl $n $R/w_f${n}_${fl}_r 3
done
# unchanged masters, old bench form (REL 0): must still PASS
run fc_EW_rel0  bash $T/bench_rly_fc.sh pass 136 EW $R/w_fc_EW_z
run f4_NS_rel0  bash $T/bench_rly_fcf.sh pass 136 NS 4 $R/w_f4_NS_z
run f3_SN_rel0  bash $T/bench_rly_fcf.sh pass 136 SN 3 $R/w_f3_SN_z
run fc_624_rel0 bash $T/bench_rly_fc.sh pass 624 NS $R/w_fc_624_z
echo ALL_DONE
