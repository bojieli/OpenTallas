#!/usr/bin/env bash
# Invoke on a fleet host under ot-heavy; source-only transport qualification.
set -euo pipefail
run=$1
stages=${STAGES:-67}
mkdir -p "$run"
root=$(git rev-parse --show-toplevel)
src="$root/rtl/hbm_accel/generic/vm/b2"
verilator --binary --timing -DRING_REGIONAL_PHY -Wno-fatal --top-module tb_vms_elastic -GS="$stages" -j 4 --Mdir "$run/elastic" "$src/ot_vms_elastic.sv" "$src/ot_vms_elastic_regional.sv" "$src/tb_vms_elastic.sv" > "$run/compile.log" 2>&1
for mode in 0 1 2; do
 "$run/elastic/Vtb_vms_elastic" +MODE="$mode" > "$run/exact_vc$mode.log" 2>&1
 "$run/elastic/Vtb_vms_elastic" +MODE="$mode" +STALL=1 > "$run/stall_vc$mode.log" 2>&1
done
# Asymmetric VC0 traffic is essential: symmetric traffic can hide swapped credits.
for mut in 1 2; do
 set +e
 "$run/elastic/Vtb_vms_elastic" +MODE=0 +MUT="$mut" > "$run/mutant$mut.log" 2>&1
 result=$?
 set -e
 printf '%s\n' "$result" > "$run/mutant$mut.exit"
 if [ "$result" -eq 0 ]; then echo "FAIL mutant $mut survived"; exit 1; fi
done
verilator --binary --timing -DRING_REGIONAL_PHY -Wno-fatal --top-module tb_vms_endpoint_rate -GD=8 -GHF=8 -GS="$stages" -GRATE_GATE=1 -j 4 --Mdir "$run/endpoint" "$src/ot_vms_rstop.sv" "$src/ot_vms_elastic.sv" "$src/ot_vms_elastic_regional.sv" "$src/tb_vms_endpoint_rate.sv" > "$run/endpoint_compile.log" 2>&1
"$run/endpoint/Vtb_vms_endpoint_rate" > "$run/endpoint.log" 2>&1
for dir in 0 1; do
 verilator --binary --timing -DRING_REGIONAL_PHY -Wno-fatal --top-module tb_vms_endpoint_rate -GD=8 -GHF=8 -GS="$stages" -GRATE_GATE=1 -GSID=3 -GDIR="$dir" -j 4 --Mdir "$run/wrap$dir" "$src/ot_vms_rstop.sv" "$src/ot_vms_elastic.sv" "$src/ot_vms_elastic_regional.sv" "$src/tb_vms_endpoint_rate.sv" > "$run/wrap_compile$dir.log" 2>&1
 "$run/wrap$dir/Vtb_vms_endpoint_rate" > "$run/wrap$dir.log" 2>&1
done
echo 'PASS source-only elastic + candidate endpoint; physical adoption remains gated'
