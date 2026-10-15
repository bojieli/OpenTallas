#!/usr/bin/env bash
# Static transport compaction gate; synthetic identity payload, not token proof.
set -euo pipefail
out=$(realpath -m "$1")
mode=${2:-pass}
mkdir -p "$out"
defs=()
if [[ "$mode" == mut ]]; then defs=(+define+MUT_RANK); elif [[ "$mode" != pass ]]; then exit 2; fi
verilator --binary --timing -j 2 -Wno-fatal "${defs[@]}" --top-module tb_s81_hcx_gatherpack --Mdir "$out/obj" \
 rtl/dsrom_sys/s81_hcx/ot_s81_hcx_gatherpack.sv rtl/dsrom_sys/s81_hcx/test/tb_s81_hcx_gatherpack.sv > "$out/build.log" 2>&1
"$out/obj/Vtb_s81_hcx_gatherpack" | tee "$out/run.log"
