#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../../../../.." && pwd)
out=${1:?output directory}
mkdir -p "$out"
d="$root/rtl/hbm_accel/generic/vm/static"
iverilog -g2012 -s tb_vms_rstop_static -o "$out/exact" "$d/ot_vms_rstop_static.sv" "$d/tb_vms_rstop_static.sv"
vvp "$out/exact" >"$out/exact.log" 2>&1
cat "$out/exact.log"
iverilog -g2012 -s tb_vms_rstop_static -Ptb_vms_rstop_static.MUT=1 -o "$out/mutant" "$d/ot_vms_rstop_static.sv" "$d/tb_vms_rstop_static.sv"
if vvp "$out/mutant" >"$out/mutant.log" 2>&1; then
  cat "$out/mutant.log"
  exit 1
fi
grep -q 'STATIC_RING mismatch mirror payload' "$out/mutant.log"
printf 'VMS_STATIC_RING MUTANT observed FAIL\n'
