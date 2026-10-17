#!/usr/bin/env bash
# H-NETLIST A2P 2026-10-16: SU cross-quarter RF N_Q gate (tb_hbm_su_rf_nq, Verilator 5.050).
#   run_su_rf_nq.sh OUT  -> N_Q=2 positive, N_Q=4 regression positive, N_Q=2 mutants QMUT=256 (last writer slot ignored)
#   and DROP=1 (route reducer 1 -> replica 0 missing) must FAIL with replica MISMATCH lines.
set -uo pipefail
root=$(cd "$(dirname "$0")/../../../../../.." && pwd); cd "$root"
out=$(realpath -m "${1:?out}"); mkdir -p "$out"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; [ -x "$V" ] || V=verilator
S=rtl/hbm_accel/generic/adapters/static_su
src=($S/top/tb_hbm_su_rf_nq.sv $S/top/ot_hbm_su_static_qcore.sv $S/register_file/ot_hbm_su_static_rf.sv
     $S/reduction/ot_hbm_su_reduce_static.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
     rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv)
sha256sum "${src[@]}" > "$out/sources.sha256"
run(){ # name params...
 local n=$1; shift
 "$V" --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_hbm_su_rf_nq "$@" \
   --Mdir "$out/obj_$n" -o sim "${src[@]}" > "$out/$n.build.log" 2>&1 || { tail -15 "$out/$n.build.log"; echo "BUILD_FAIL $n"; return 2; }
 "$out/obj_$n/sim" > "$out/$n.log" 2>&1; local r=$?; rm -rf "$out/obj_$n"; grep -E "SU_RF_NQ|MISMATCH|never wrote" "$out/$n.log" | head -4; return $r
}
rc=0
run pos2 -GN_Q=2 || rc=1; grep -q "^SU_RF_NQ PASS N_Q=2" "$out/pos2.log" || rc=1
run pos4 -GN_Q=4 || rc=1; grep -q "^SU_RF_NQ PASS N_Q=4" "$out/pos4.log" || rc=1
for m in "mut_slot -GN_Q=2 -GQMUT=256" "mut_drop -GN_Q=2 -GDROP=1"; do
 set -- $m; n=$1; shift
 run $n "$@"; r=$?
 if [ $r != 0 ] && grep -q "^MISMATCH replica" "$out/$n.log" && ! grep -q "^SU_RF_NQ PASS" "$out/$n.log"; then echo "MUTANT $n REJECTED"
 else echo "MUTANT $n SURVIVED_OR_NO_WITNESS"; rc=1; fi
done
[ $rc = 0 ] && echo "SU_RF_NQ_GATE PASS" || { echo "SU_RF_NQ_GATE FAIL"; exit 1; }
