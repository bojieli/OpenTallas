#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
out=$(realpath -m "$1");mkdir -p "$out"
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
S=rtl/hbm_accel/generic/adapters/static_su/register_file
for mut in 0 1 2 3;do
 "$vl" --binary --timing -O1 -j 2 -CFLAGS -O0 -Wno-fatal -Wno-lint -Wno-style \
  --top-module tb_hbm_su_rf_route -GMUT="$mut" --Mdir "$out/obj$mut" \
  rtl/lib/ot_rst_relay.sv rtl/hbm_accel/die_glue/ot_hbm_rly.sv \
  rtl/hbm_accel/die_glue/hbfd_rly_masters.sv -I"$S" "$S/ot_hbm_su_rf_route.sv" "$S/tb_hbm_su_rf_route.sv" \
  > "$out/build$mut.log" 2>&1
 set +e
 "$out/obj$mut/Vtb_hbm_su_rf_route" > "$out/run$mut.log" 2>&1
 rc=$?
 set -e
 echo "exit=$rc" >> "$out/run$mut.log"
 if [ "$mut" = 0 ];then grep -q 'RF_ROUTE PASS' "$out/run$mut.log";else grep -q 'RF_ROUTE FAIL' "$out/run$mut.log";fi
done
echo RF_ROUTE_GATE_PASS
