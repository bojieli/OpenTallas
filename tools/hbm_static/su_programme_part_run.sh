#!/usr/bin/env bash
# H-SU 2026-10-16: partitioned whole-SU programme producer (ot_hbm_su_programme_part) vs the monolithic
# ot_hbm_su_programme, lockstep on every edge of the current 7111-edge su_top_compile image, + 3 mutants that must FAIL.
# Usage (run through ot-run, from the repo root or a non-git export): OUT=dir [PARTS=4] [DEPTH=2] [ONLY=template|pcoff|phase] $0
# ONLY=<mutant>: build/run that one mutant only (closure-loop expect=fail bench); exits 1 after printing its verdict.
# Prints one SU_PROGRAMME_PART line per case to stdout and SU_PROGRAMME_PART_GATE PASS|FAIL.
set -euo pipefail
ulimit -c 0
OUT=$(mkdir -p "${OUT:?OUT required}" && realpath "$OUT")
PARTS=${PARTS:-4}; DEPTH=${DEPTH:-2}
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
s=rtl/hbm_accel/generic/adapters/static_su/programme
M=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
[ -f "$OUT/vec/prog.mem" ] || python3 tools/hbm_static/su_top_compile.py "$OUT/vec" > "$OUT/vec.log"
python3 tools/hbm_static/su_programme_compile.py "$OUT/vec/prog.mem" "$OUT/mono" > "$OUT/mono.log"
python3 tools/hbm_static/su_programme_compile.py "$OUT/vec/prog.mem" "$OUT" --partition "$PARTS" --start-depth "$DEPTH" --mut-pc-slice 3 > "$OUT/part.log"
sha256sum "$s/ot_hbm_su_programme.sv" "$s/ot_hbm_su_programme_part.sv" "$s/tb_hbm_su_programme_part.sv" tools/hbm_static/su_programme_compile.py "$OUT/vec/prog.mem" > "$OUT/sources.sha256"
build(){ "$vl" --binary --timing -O1 -j "${JOBS:-8}" -Wno-fatal -Wno-WIDTHTRUNC -Wno-WIDTHEXPAND --top-module tb_hbm_su_programme_part -I"$OUT" -GMUT="$1" \
  --Mdir "$OUT/obj$1" "$s/ot_hbm_su_programme.sv" "$s/ot_hbm_su_programme_part.sv" "$s/tb_hbm_su_programme_part.sv" "$M" > "$OUT/build$1.log" 2>&1 || { tail -20 "$OUT/build$1.log"; echo "SU_PROGRAMME_PART BUILD_FAIL MUT=$1"; exit 2; }; }
run(){ set +e; "$OUT/obj$1/Vtb_hbm_su_programme_part" +DIR="$OUT" $2 > "$OUT/run_$3.log" 2>&1; local rc=$?; set -e
  grep -h "SU_PROGRAMME_PART" "$OUT/run_$3.log" | head -6 | sed "s/^/[$3] /"; echo "[$3] rc=$rc"; return $rc; }
if [ -n "${ONLY:-}" ]; then
  case "$ONLY" in template) m=0; a=+MUT_TEMPLATE;; pcoff) m=0; a=+MUT_PCOFF;; phase) m=1; a="";; *) echo "bad ONLY"; exit 2;; esac
  build $m; run $m "$a" "$ONLY" || true; exit 1
fi
build 0
build 1
ok=1
run 0 "" positive || ok=0
grep -q "SU_PROGRAMME_PART PASS" "$OUT/run_positive.log" || ok=0
for c in "0 +MUT_TEMPLATE template" "0 +MUT_PCOFF pcoff" "1 _ phase"; do
  set -- $c; a=$2; [ "$a" = _ ] && a=""
  if run "$1" "$a" "$3"; then ok=0; echo "SU_PROGRAMME_PART MUTANT $3 ESCAPED"
  elif grep -q "SU_PROGRAMME_PART FAIL" "$OUT/run_$3.log"; then echo "SU_PROGRAMME_PART MUTANT $3 REJECTED (expected)"
  else ok=0; echo "SU_PROGRAMME_PART MUTANT $3 no FAIL verdict"; fi
done
[ $ok = 1 ] && echo "SU_PROGRAMME_PART_GATE PASS" && exit 0
echo "SU_PROGRAMME_PART_GATE FAIL"; exit 1
