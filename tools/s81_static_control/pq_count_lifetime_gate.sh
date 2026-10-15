#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:?fresh dir};mkdir "$out";cd "$out"
files=("$root/physical/s81_pq_hier/pinned/rtl/ot_rst_relay.sv" "$root/physical/s81_pq_hier/pinned/rtl/v41rom/ot_v41_kreg.sv" "$root/physical/s81_pq_hier/pinned/rtl/hdc/ot_hdc_delay.sv" "$root/rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_rwbc.sv" "$root/rtl/dsrom_sys/s81_static_control/test/tb_s81_pq_count_lifetimes.sv")
for mut in 0 1;do
 defs=();if [[ "$mut" == 1 ]];then defs=(-DOT_S81_PQ_RWBC_MUT_GA);fi
 iverilog -g2012 "${defs[@]}" -s tb_s81_pq_count_lifetimes -o gate.sim "${files[@]}" > "compile_$mut.log" 2>&1
 if [[ "$mut" == 0 ]];then modes='0 1 2';else modes=0;fi
 for mode in $modes;do
  if vvp gate.sim +mode="$mode" > "mode_${mut}_$mode.log" 2>&1;then rc=0;else rc=$?;fi
  echo "$rc" > "mode_${mut}_$mode.exit"
  if [[ "$mut" == 0 ]];then test "$rc" == 0;else test "$rc" != 0;grep -q 'count leaf' "mode_${mut}_$mode.log";fi
  cat "mode_${mut}_$mode.log"
 done
done
sha256sum "${files[@]}" > source.sha256;rm gate.sim
