#!/usr/bin/env bash
# ot_hbm_svc_fault_cdc bench: 2 clock directions x MUT 0..5 (MUT0 PASS, every mutant must be rejected).
# QF-SFAULT 2026-10-18: Verilator 5.050 by default (the closure daemon's version); SIM=iverilog keeps the old path.
set -euo pipefail
out=${1:?output directory required};mkdir -p "$out";out=$(realpath "$out")
d=rtl/hbm_accel/loader/service_native
src=(rtl/lib/ot_reset_sync.sv "$d/ot_hbm_svc_async_fifo.sv" "$d/tb_hbm_svc_fault_cdc.sv")
sha256sum "${src[@]}" > "$out/source.sha256"
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
if [[ ${SIM:-verilator} != iverilog ]]; then
 [[ -x $vl ]] || { echo "BUILD_FAIL verilator 5.050 not found at $vl"; exit 2; }
 "$vl" --version | tee "$out/verilator.version"; grep -q '^Verilator 5.050' "$out/verilator.version" || { echo "BUILD_FAIL not Verilator 5.050"; exit 2; }
fi
for direction in 0 1;do
 if ((direction==0));then wh=512;rh=416.666667;else wh=416.666667;rh=512;fi
 for m in 0 1 2 3 4 5;do
  t=d${direction}_m$m
  if [[ ${SIM:-verilator} == iverilog ]]; then
   iverilog -g2012 -s tb_hbm_svc_fault_cdc -Ptb_hbm_svc_fault_cdc.MUT=$m -Ptb_hbm_svc_fault_cdc.WR_HALF=$wh -Ptb_hbm_svc_fault_cdc.RD_HALF=$rh -o "$out/$t.vvp" "${src[@]}"
   rc=0;vvp "$out/$t.vvp" > "$out/$t.log" 2>&1||rc=$?
  else
   "$vl" --binary --timing -j "${JOBS:-2}" -O1 -Wno-fatal -Wno-lint -Wno-style --top-module tb_hbm_svc_fault_cdc \
    -GMUT=$m -GWR_HALF=$wh -GRD_HALF=$rh --Mdir "$out/obj_$t" -o sim "${src[@]}" > "$out/$t.build.log" 2>&1 \
    || { tail -30 "$out/$t.build.log"; echo "BUILD_FAIL $t"; exit 2; }
   rc=0;"$out/obj_$t/sim" > "$out/$t.log" 2>&1||rc=$?
   rm -rf "$out/obj_$t"
  fi
  if ((m==0));then test "$rc" = 0;grep -q 'PASS STATUS_FIFO' "$out/$t.log";cat "$out/$t.log"
  else test "$rc" != 0;grep -q 'STATUS' "$out/$t.log";echo "STATUS_FIFO mutant$m direction$direction rejected: $(grep -m1 STATUS "$out/$t.log")";fi
 done
done
echo "FAULT_CDC_BENCH PASS"
