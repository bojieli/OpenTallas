#!/usr/bin/env bash
set -eu
work=${1:?work directory};mkdir -p "$work"
sources=(rtl/test/dsrom_sys/tb_s81_pq_ctl_static.sv rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_ctl_static_native.sv physical/s81_pq_hier/pinned/rtl/v41die/ot_v41_pqc_tiles.sv physical/s81_pq_hier/pinned/rtl/ot_rst_relay.sv physical/s81_pq_hier/pinned/rtl/hdc/ot_hdc_delay.sv rtl/v41rom/ot_v41_kreg.sv rtl/common/ot_prefix.sv)
# PQ_CTL_DEFS: profile defines, e.g. "-DOT_PQ_CTL_INCAP -DOT_PQ_AQ_PIN_LAUNCH" (canonical captured-input leaf)
read -r -a defs <<< "${PQ_CTL_DEFS:-}"
mutants=(OT_S81_PQ_STATIC_MUT_TAG OT_S81_PQ_STATIC_MUT_PHW OT_S81_PQ_STATIC_MUT_SAW)
if [[ " ${defs[*]-} " == *" -DOT_PQ_CTL_INCAP "* ]];then mutants+=(OT_S81_PQ_INCAP_MUT_NOGA);fi
iverilog -g2012 ${defs[@]+"${defs[@]}"} -s tb_s81_pq_ctl_static -o "$work/exact.vvp" "${sources[@]}"
for mode in positive badvm badcount;do
 args=();if [[ $mode != positive ]];then args=("+$mode=1");fi
 vvp "$work/exact.vvp" "${args[@]}" > "$work/$mode.log";cat "$work/$mode.log"
done
for mutant in "${mutants[@]}";do
  iverilog -g2012 ${defs[@]+"${defs[@]}"} -s tb_s81_pq_ctl_static -D"$mutant" -o "$work/$mutant.vvp" "${sources[@]}"
  set +e
  vvp "$work/$mutant.vvp" > "$work/$mutant.log" 2>&1;rc=$?
  set -e
  if [[ $rc == 0 ]] || ! grep -q 'STATIC_CTL FAIL' "$work/$mutant.log";then cat "$work/$mutant.log";exit 1;fi
  cat "$work/$mutant.log"
done
echo "STATIC_CTL_GATE PASS positive=1 fault_only_timeline=2 actual_source_mutants=${#mutants[@]} PHW=10 SAW=14 defs=${PQ_CTL_DEFS:-none}"
