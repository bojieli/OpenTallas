#!/bin/bash
# Reproduce the minimum payload gate. Refuse to overwrite prior evidence.
set -euo pipefail
out=${1:?Pass a NEW output directory for immutable campaign evidence}
if [[ -e "$out" ]]; then echo "Refusing to overwrite existing evidence: $out" >&2; exit 2; fi
mkdir -p "$out"
build=$(mktemp -d /tmp/dsrom-egress-gate.XXXXXXXX)
trap 'rm -rf "$build"' EXIT
src=(
rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv
rtl/hbm_accel/service/ot_hbm_accel_r5a_ecc_pkg.sv
rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank.sv
rtl/hbm_accel/collective_clock_entry_20261007/ot_hbm_collective_reset_entry.sv
rtl/hbm_accel/collective_cdc_20261007/ot_hbm_collective_protected_cdc.sv
physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
rtl/experimental/dsrom_softmax_transport_20261007/ot_dsrom_softmax_ecc_lane.sv
rtl/experimental/dsrom_softmax_transport_20261007/ot_dsrom_softmax_serial_row.sv
rtl/experimental/dsrom_softmax_transport_20261007/ot_dsrom_softmax_egress_payload.sv
rtl/experimental/dsrom_softmax_transport_20261007/tb_egress_payload.sv
)
sha256sum "${src[@]}" > "$out/source_sha256.txt"
for variant in positive early_negative half_negative; do
 flags=()
 [[ "$variant" != early_negative ]] || flags+=(-DSOFTMAX_EGRESS_EARLY_RECEIPT)
 [[ "$variant" != half_negative ]] || flags+=(-DSOFTMAX_EGRESS_SWAP_HALVES)
 iverilog -g2012 -DOT_MEM_NO_INIT "${flags[@]}" -s tb_egress_payload -o "$build/$variant.vvp" "${src[@]}" > "$out/${variant}_compile.log" 2>&1
 rc=0
 vvp "$build/$variant.vvp" > "$out/$variant.log" 2>&1 || rc=$?
 if [[ "$variant" == positive ]]; then
  [[ "$rc" == 0 ]] && rg -q 'PASS egress actual destination SRAM rows=80 bytes=81920' "$out/$variant.log"
 elif [[ "$variant" == early_negative ]]; then
  [[ "$rc" != 0 ]] && rg -q 'RECEIPT_BEFORE_DESTINATION_WRITE' "$out/$variant.log"
 else
  [[ "$rc" != 0 ]] && rg -q 'DESTINATION_PAYLOAD row112 lane0' "$out/$variant.log"
 fi
done
echo 'PASS exact actual SRAM payload and both expected negative controls'
