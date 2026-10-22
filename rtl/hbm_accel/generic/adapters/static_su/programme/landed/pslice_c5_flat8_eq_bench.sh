#!/usr/bin/env bash
# L2H-PSLICE 10-19 (r8): per-leaf-command flat wires-only parent flat8 == ot_hbm_su_programme_pslice_c5 (MUT 0 PASS; MUT 1 phase mutant FAIL). Fleet only.
set -u; cd "${LP_ROOT:?}"; OUT=${1:?}; mkdir -p "$OUT"; rc=0
s=rtl/hbm_accel/generic/adapters/static_su/programme
SRCS="rtl/lib/ot_rst_relay.sv $s/ot_hbm_su_programme.sv $s/ot_hbm_su_programme_part.sv $s/ot_hbm_su_programme_pgcol.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v $s/ot_hbm_su_programme_pslice_c5_flat8.sv \
 $s/tb_hbm_su_programme_pslice_c5_flat8_eq.sv"
for m in ${ONLY:-0 1}; do
  verilator --binary -j 8 -Wno-fatal --top-module tb_hbm_su_programme_pslice_c5_flat8_eq -GMUT=$m $SRCS -Mdir "$OUT/eqobj$m" \
    > "$OUT/eq_build_$m.log" 2>&1 && "$OUT/eqobj$m/Vtb_hbm_su_programme_pslice_c5_flat8_eq" > "$OUT/eq_mut$m.log" 2>&1
  r=$(grep -o 'FLAT_EQ [A-Z]*' "$OUT/eq_mut$m.log" 2>/dev/null | head -1); echo "EQ MUT $m: ${r:-NO_RESULT}"
  if [ $m -eq 0 ]; then [ "$r" = "FLAT_EQ PASS" ] || rc=1; else [ "$r" = "FLAT_EQ FAIL" ] || rc=1; fi
done
echo "EQ_EXIT $rc"; exit $rc
