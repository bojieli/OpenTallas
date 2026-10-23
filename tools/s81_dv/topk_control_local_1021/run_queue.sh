#!/usr/bin/env bash
set -euo pipefail
out=$1
mkdir -p "$out"
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
src=(rtl/lib/ot_sram_showahead_1r1w.sv rtl/dsrom_sys/s81_dv/unit/bk/plana/n32/ot_s81pa_queue.sv physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1_p192_rc/ot_sram_1r1w_32x128_m1_p192_rc.v tools/s81_dv/topk_control_local_1021/tb_queue.sv)
sha256sum "${src[@]}" > "$out/sources.sha256"
"$VL" --version > "$out/verilator.version"
for mut in 0 1 2 3;do
 "$VL" --binary --timing -j "${J:-4}" -DOT_SRAM_P192 -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN --top-module tb_queue -GMUT="$mut" "${src[@]}" -Mdir "$out/obj$mut" > "$out/build$mut.log" 2>&1
 rc=0
 "$out/obj$mut/Vtb_queue" > "$out/run$mut.log" 2>&1 || rc=$?
 printf '%s\n' "$rc" > "$out/rc$mut.txt"
 if [ "$mut" = 0 ];then
  if [ "$rc" != 0 ];then cat "$out/run$mut.log";exit 1;fi
  grep -q QUEUE_PASS "$out/run$mut.log"
 else
  if [ "$rc" = 0 ];then echo "MUTANT_ESCAPE $mut";exit 1;fi
  grep -q HEAD "$out/run$mut.log"
 fi
 echo "QUEUE_CASE mut=$mut rc=$rc accepted"
done
