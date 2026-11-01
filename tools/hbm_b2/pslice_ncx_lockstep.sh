#!/usr/bin/env bash
set -euo pipefail
: "${OUT:?set OUT}"
mkdir -p "$OUT"
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
s=rtl/hbm_accel/generic/adapters/static_su/programme
sources=(rtl/lib/ot_rst_relay.sv "$s/ot_hbm_su_programme.sv" "$s/ot_hbm_su_programme_pgcol.sv"
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
 tools/hbm_b2/tb_pslice_ncx_lockstep.sv)
for m in 0 1; do
 "$vl" --binary --timing -j "${JOBS:-8}" -Wno-fatal --top-module tb_pslice_ncx_lockstep -GPHASE_MUT="$m" \
  --Mdir "$OUT/obj$m" "${sources[@]}" > "$OUT/build$m.log" 2>&1
 if "$OUT/obj$m/Vtb_pslice_ncx_lockstep" > "$OUT/run$m.log" 2>&1; then rc=0;else rc=$?;fi
 if [ "$m" = 0 ];then test "$rc" = 0;grep 'PSLICE_NCX PASS' "$OUT/run$m.log"
 else test "$rc" != 0;grep 'PSLICE_NCX FAIL' "$OUT/run$m.log";echo 'PSLICE_NCX MUTANT caught';fi
done
