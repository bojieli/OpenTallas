#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
OUT=$(realpath -m "$1")
mkdir -p "$OUT"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$VL" --version | tee "$OUT/verilator.version"
python3 tools/hbm_layer_vehicle/gather_fixture_2000.py inputs "$OUT/fixtures" > "$OUT/prepare.log" 2>&1
cat "$OUT/prepare.log"
for mut in 0 1 2 3; do
 "$VL" --binary --timing -j 2 -Wno-fatal --top-module tb_route_gather_fixture -GMUT="$mut" -Mdir "$OUT/obj$mut" \
  rtl/hbm_accel/generic/adapters/static_su/gather/ot_hbm_su_indexed_scalar.sv \
  rtl/hbm_accel/generic/adapters/static_su/gather/tb_route_gather_fixture.sv \
  rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv \
  physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v > "$OUT/build$mut.log" 2>&1
 set +e
 "$OUT/obj$mut/Vtb_route_gather_fixture" "+DIR=$OUT/fixtures" > "$OUT/run$mut.log" 2>&1
 status=$?
 set -e
 printf '%s\n' "$status" > "$OUT/run$mut.exit"
 if [[ "$mut" == 0 ]]; then
  test "$status" = 0
  grep -q 'ROUTE_GATHER_FIXTURE PASS' "$OUT/run$mut.log"
 else
  test "$status" != 0
  grep -q 'ROUTE_GATHER_FIXTURE FAIL' "$OUT/run$mut.log"
 fi
 tail -3 "$OUT/run$mut.log"
done
sha256sum rtl/hbm_accel/generic/adapters/static_su/gather/ot_hbm_su_indexed_scalar.sv \
 rtl/hbm_accel/generic/adapters/static_su/gather/tb_route_gather_fixture.sv \
 rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv \
 tools/hbm_layer_vehicle/su_indexed_gather_2000.py tools/hbm_layer_vehicle/layer_images.py > "$OUT/source.sha256"
printf '%s\n' 'MINIMUM_ROUTE_GATHER_PASS: 18 authentic fixture cases, three causal source mutants; full token remains unqualified'
