#!/usr/bin/env bash
# HBM-RTL5 2026-10-18: whole SU programme path r5 (ot_hbm_su_programme_root_h5 = root5 SMACROS 4x320 SDLY 2 RRLY 1 ->
# 4 x ot_hbm_su_programme_pslice_c5 with the NATIVE-FIX3 leaves) vs r4 (root_h + 4 x pslice_q4 = programme_part PIPE 2)
# on the full 7111-edge su_top_compile image, one host stimulus, DUT == REF shifted 2 edges on every edge
# (tb_hbm_su_programme_root5.sv), + 6 mutants that must FAIL.
# Usage (repo root or export, via ot-run): OUT=dir [ONLY=cfg|sdly0|decode98|rrly0|oorfd0|oldleaf] $0
set -euo pipefail
ulimit -c 0
OUT=$(mkdir -p "${OUT:?OUT required}" && realpath "$OUT")
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
s=rtl/hbm_accel/generic/adapters/static_su/programme
R=rtl/lib/ot_rst_relay.sv
M=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
[ -f "$OUT/vec/prog.mem" ] || python3 tools/hbm_static/su_top_compile.py "$OUT/vec" > "$OUT/vec.log"
python3 tools/hbm_static/su_programme_compile.py "$OUT/vec/prog.mem" "$OUT/img" --root5 --mut-q 2 > "$OUT/img.log"
SRC=("$R" "$s/ot_hbm_su_programme.sv" "$s/ot_hbm_su_programme_root.sv" "$s/ot_hbm_su_programme_part.sv"
     "$s/ot_hbm_su_programme_pgcol.sv" "$s/ot_hbm_su_programme_root_h5.sv" "$s/tb_hbm_su_programme_root5.sv")
sha256sum "${SRC[@]}" tools/hbm_static/su_programme_compile.py "$OUT/vec/prog.mem" > "$OUT/sources.sha256"
build(){ "$vl" --binary --timing -O1 -j "${JOBS:-8}" -Wno-fatal -Wno-WIDTHTRUNC -Wno-WIDTHEXPAND --top-module tb_hbm_su_programme_root5 \
  -I"$OUT/img" -GMUT="$1" -GCMUT="$2" --Mdir "$OUT/obj$1_$2" "${SRC[@]}" "$M" > "$OUT/build$1_$2.log" 2>&1 \
  || { tail -20 "$OUT/build$1_$2.log"; echo "SU_PROGRAMME_ROOT5 BUILD_FAIL MUT=$1 CMUT=$2"; exit 2; }; }
run(){ set +e; "$OUT/obj$1_$2/Vtb_hbm_su_programme_root5" +DIR="$OUT/img" $3 > "$OUT/run_$4.log" 2>&1; local rc=$?; set -e
  grep -h "SU_PROGRAMME_ROOT5" "$OUT/run_$4.log" | head -6 | sed "s/^/[$4] /"; echo "[$4] rc=$rc"; return $rc; }
MUTS=("0 0 +MUT_CFG cfg" "1 0 _ sdly0" "2 0 _ decode98" "3 0 _ rrly0" "4 0 _ oorfd0" "0 5 _ oldleaf")
if [ -n "${ONLY:-}" ]; then   # closure-loop expect=fail bench: one mutant, exits 1 after its verdict
  for c in "${MUTS[@]}"; do set -- $c; [ "$4" = "$ONLY" ] || continue; a=$3; [ "$a" = _ ] && a=""
    build $1 $2; run $1 $2 "$a" "$4" || true; exit 1; done
  echo "bad ONLY"; exit 2
fi
build 0 0
for c in "${MUTS[@]}"; do set -- $c; [ -d "$OUT/obj$1_$2" ] || build $1 $2; done
ok=1
run 0 0 "" positive || ok=0
grep -q "SU_PROGRAMME_ROOT5 PASS" "$OUT/run_positive.log" || ok=0
for c in "${MUTS[@]}"; do
  set -- $c; a=$3; [ "$a" = _ ] && a=""
  if run "$1" "$2" "$a" "$4"; then ok=0; echo "SU_PROGRAMME_ROOT5 MUTANT $4 ESCAPED"
  elif grep -q "SU_PROGRAMME_ROOT5 FAIL" "$OUT/run_$4.log"; then echo "SU_PROGRAMME_ROOT5 MUTANT $4 REJECTED (expected)"
  else ok=0; echo "SU_PROGRAMME_ROOT5 MUTANT $4 no FAIL verdict"; fi
done
[ $ok = 1 ] && echo "SU_PROGRAMME_ROOT5_GATE PASS" && exit 0
echo "SU_PROGRAMME_ROOT5_GATE FAIL"; exit 1
