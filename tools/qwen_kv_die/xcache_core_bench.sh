#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
out=$(mktemp -d /tmp/qwen-xcore-bench.XXXXXX)
sources=(rtl/test/qwen_kv_die/tb_qwen_xcache_core.sv rtl/physical/ot_qwen_xcache_seam.sv rtl/hdc/ot_qwen_w12_matvec.sv rtl/hdc/ot_qwen_w12_arith.sv rtl/hdc/ot_hdc_matvec.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_add_lat_nr.sv rtl/hdc/ot_hdc_prefix.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/lib/ot_rst_relay.sv rtl/physical/ot_qwen_tile_lsl.sv)
sha256sum "${sources[@]}" > "$out/provenance.sha256"
git rev-parse HEAD > "$out/source.commit"
vlt=${QWEN_XCACHE_VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
# Compile/run under ot-run admission; this script is the admitted command.
for mode in native mem8 mutant; do
  args=()
  if [ "$mode" = mem8 ]; then args=(-GMEM_EXTRA=8); fi
  if [ "$mode" = mutant ]; then args=(-GMUT=1); fi
  "$vlt" --binary --timing -j 4 -Wno-fatal -Wno-lint --top-module tb_qwen_xcache_core --Mdir "$out/obj_$mode" "${args[@]}" "${sources[@]}" >"$out/build_$mode.log" 2>&1
  if [ "$mode" = mutant ]; then
    if "$out/obj_$mode/Vtb_qwen_xcache_core" >"$out/mutant.log" 2>&1; then echo 'FAIL address-row mutant escaped'; exit 1; fi
    if command -v rg >/dev/null 2>&1; then
      rg -q 'production matvec output mismatch' "$out/mutant.log"
    else
      grep -q 'production matvec output mismatch' "$out/mutant.log"
    fi
  else
    "$out/obj_$mode/Vtb_qwen_xcache_core" | tee "$out/$mode.log"
  fi
done
echo "PASS production arithmetic mutant rejected; source/evidence $out"
