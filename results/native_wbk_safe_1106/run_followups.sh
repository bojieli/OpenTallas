#!/usr/bin/env bash
set -eu
base=$(pwd)
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
p=results/native_wbk_safe_1106
d=rtl/hbm_accel/cores_split/reform_1106
src=("$p/tb_native_family.sv" "$p/gold_wb_kport_q.sv" "$p/gold_wb_cutthrough.sv" "$d/ot_wbk_native_safe.sv" "$d/ot_wbk_native_safe_children.sv" "$d/ot_wbk_native_elastic_out.sv" "$d/ot_hbm_face_reg.sv" "$d/ot_hbm_face_rst_relay.sv" rtl/lib/ot_reset_sync.sv rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv rtl/hbm_accel/loader/service_native/ot_hbm_svc_pc_ctrl_leaf.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v)
"$vl" --binary --timing -O1 -j 2 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_wbq --Mdir "$base/obj_normal" -o sim "${src[@]}" > normal.build.log 2>&1
for spec in m0:0:0 east:0:1 slow:1:0;do
 IFS=: read -r n s q <<< "$spec"
 "$base/obj_normal/sim" +SLOW="$s" +QUAD="$q" > "$n.run.log" 2>&1
 grep -q '^WBQ PASS' "$n.run.log"
done
for m in 1 2;do
 "$vl" --binary --timing -O1 -j 2 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_wbq -GMUT="$m" -GNB=4 --Mdir "$base/obj_mut$m" -o sim "${src[@]}" > "mut$m.build.log" 2>&1
 set +e
 "$base/obj_mut$m/sim" > "mut$m.run.log" 2>&1
 rc=$?
 set -e
 if [ "$rc" = 0 ];then echo "MUTANT ESCAPED $m";exit 1;fi
 grep -Eq 'WBQ FAIL|WBQ GLOBAL PROGRESS|WBQ_TIMEOUT|WARM_RESET_STALE_TRAFFIC|TIMEOUT|GLOBAL_DEADLINE|WBQ bounded vehicle' "mut$m.run.log"
 echo "ADAPTER_MUTANT_CAUGHT $m rc=$rc"
done
# The opposite-edge requirement and the held-head rule each have a real negative control.
for spec in phase:0:0 overwrite:1:1;do
 IFS=: read -r n e m <<< "$spec"
 "$vl" --binary --timing -O1 -j 2 -Wno-fatal -Wno-lint -Wno-style --top-module test_out_protocol -GREADY_NEGEDGE="$e" -GMUT="$m" --Mdir "$base/obj_out_$n" -o sim "$p/test_out_elastic.sv" "$p/out_providers.sv" "$p/out_elastic_native.sv" > "out_$n.build.log" 2>&1
 set +e
 "$base/obj_out_$n/sim" > "out_$n.run.log" 2>&1
 rc=$?
 set -e
 if [ "$rc" = 0 ];then echo "OUT MUTANT ESCAPED $n";exit 1;fi
 grep -q REAL_OUT_PROTOCOL_FAIL "out_$n.run.log"
 echo "OUT_MUTANT_CAUGHT $n rc=$rc"
done
