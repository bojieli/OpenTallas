#!/bin/bash
set -euo pipefail
cd /
S=$(dirname "$(readlink -f "$0")")
mkdir -p "$S/out"
touch "$S/.keep" "$S/out/.keep"
for m in 0 26 27; do
 docker run --rm --memory=8g --cpus=2 -v "$S:/s" -w /s --entrypoint bash verilator/verilator:v5.032 -lc "set -euo pipefail; verilator --binary --timing -j 2 -O1 -Wno-fatal -Wno-lint -Wno-style --top-module tb_hbm_svc_vmks_forms --Mdir /s/out/obj-m$m -o sim -GCHECK=2 -GMUT=$m /s/tb_hbm_svc_vmks_f3.sv /s/ot_hbm_svc_vmks_f3.sv /s/ot_hbm_svc_vmks_forms.sv /s/ot_hbm_svc_vm_kshare_splitstrap.sv /s/ot_hbm_svc_pc_ctrl_leaf.sv /s/ot_hbm_svc_async_fifo.sv /s/ot_hbm_svc_ring_h9b_ff.sv /s/ot_reset_sync.sv > /s/out/m$m.build.log 2>&1; /s/out/obj-m$m/sim +WINDOWS=24 +SEED=1 +VMBURST=1 > /s/out/m$m.log 2>&1"
 if [ "$m" = 0 ]; then grep '^PASS' "$S/out/m$m.log"; else grep '^FAIL' "$S/out/m$m.log"; fi
done
