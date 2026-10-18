#!/usr/bin/env bash
# HBM-SU r5 2026-10-17: per-column cluster ot_hbm_su_programme_pslice_c5 (head + 10 pgcol leaves) vs the r4 per-quarter
# producer (pslice PIPE 2), lockstep with the SAME start edge, on every quarter of the current 7111-edge su_top_compile
# image, + 4 mutants that must FAIL (cfg: column index PC offset + dictionary word; phase; cfgany; stale).
# NATIVE-FIX3/pgs 10-18: + 4 pin-stage mutants (rstrelay: leaf reset relay bypassed; cpin: leaf cfg pin stage dropped;
# oreg: head export registers dropped; freg: head l_fault pin registers dropped; hrelay: head reset relay bypassed).
# Usage (from the repo root or an export): OUT=dir [QUARTERS="0 1 2 3"] [ONLY=cfg|phase|cfgany|stale|rstrelay|cpin|oreg|freg|hrelay] $0
set -euo pipefail
ulimit -c 0
OUT=$(mkdir -p "${OUT:?OUT required}" && realpath "$OUT")
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
s=rtl/hbm_accel/generic/adapters/static_su/programme
R=rtl/lib/ot_rst_relay.sv
M=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
[ -f "$OUT/vec/prog.mem" ] || python3 tools/hbm_static/su_top_compile.py "$OUT/vec" > "$OUT/vec.log"
python3 - "$OUT" <<'PY'
import sys; from pathlib import Path
o=Path(sys.argv[1]); rows=[int(t,16) for t in (o/'vec/prog.mem').read_text().split()]; sb=2422
for k in range(4):
    d=o/f'q{k}'; d.mkdir(exist_ok=True)
    (d/'source.mem').write_text(''.join(f'{(r>>(k*sb))&((1<<sb)-1):0{(sb+3)//4}x}\n' for r in rows))
PY
for k in ${QUARTERS:-0 1 2 3}; do
  python3 tools/hbm_static/su_programme_compile.py "$OUT/q$k/source.mem" "$OUT/q$k" --columns --line-bits 2422 \
    --mut-pc-col 3 --mut-tpl-col 2 > "$OUT/q$k/cols.log"
done
sha256sum "$R" "$s/ot_hbm_su_programme.sv" "$s/ot_hbm_su_programme_part.sv" "$s/ot_hbm_su_programme_pgcol.sv" \
  "$s/tb_hbm_su_programme_pgcol.sv" tools/hbm_static/su_programme_compile.py "$OUT/vec/prog.mem" > "$OUT/sources.sha256"
build(){ "$vl" --binary --timing -O1 -j "${JOBS:-8}" -Wno-fatal -Wno-WIDTHTRUNC -Wno-WIDTHEXPAND --top-module tb_hbm_su_programme_pgcol \
  -I"$OUT/q0" -GMUT="$1" --Mdir "$OUT/obj$1" "$R" "$s/ot_hbm_su_programme.sv" "$s/ot_hbm_su_programme_part.sv" \
  "$s/ot_hbm_su_programme_pgcol.sv" "$s/tb_hbm_su_programme_pgcol.sv" "$M" > "$OUT/build$1.log" 2>&1 \
  || { tail -20 "$OUT/build$1.log"; echo "SU_PROGRAMME_PGCOL BUILD_FAIL MUT=$1"; exit 2; }; }
run(){ set +e; "$OUT/obj$1/Vtb_hbm_su_programme_pgcol" +DIR="$OUT/q$4" $2 > "$OUT/run_$3_q$4.log" 2>&1; local rc=$?; set -e
  grep -h "SU_PROGRAMME_PGCOL" "$OUT/run_$3_q$4.log" | head -6 | sed "s/^/[$3 q$4] /"; echo "[$3 q$4] rc=$rc"; return $rc; }
# the quarters share one leaf/capacity layout (checked: identical cols_params.svh), so one build serves all four
for k in ${QUARTERS:-0 1 2 3}; do cmp -s <(head -2 "$OUT/q0/cols_params.svh" | sed 's/CL_WRITES=[0-9]*//') \
  <(head -2 "$OUT/q$k/cols_params.svh" | sed 's/CL_WRITES=[0-9]*//') || { echo "quarter $k capacity layout differs"; exit 2; }; done
if [ -n "${ONLY:-}" ]; then   # closure-loop expect=fail bench: one mutant on quarter 0, exits 1 after its verdict
  case "$ONLY" in cfg) m=0; a=+MUT_CFG;; phase) m=1; a="";; cfgany) m=2; a="";; stale) m=3; a="";;
    rstrelay) m=4; a="";; cpin) m=5; a="";; oreg) m=6; a="";; freg) m=7; a="";; hrelay) m=8; a="";; *) echo "bad ONLY"; exit 2;; esac
  build $m; run $m "$a" "$ONLY" 0 || true; exit 1
fi
for m in 0 1 2 3 4 5 6 7 8; do build $m; done
ok=1
for k in ${QUARTERS:-0 1 2 3}; do
  run 0 "" positive $k || ok=0
  grep -q "SU_PROGRAMME_PGCOL PASS" "$OUT/run_positive_q$k.log" || ok=0
done
for c in "0 +MUT_CFG cfg" "1 _ phase" "2 _ cfgany" "3 _ stale" "4 _ rstrelay" "5 _ cpin" "6 _ oreg" "7 _ freg" "8 _ hrelay"; do
  set -- $c; a=$2; [ "$a" = _ ] && a=""
  if run "$1" "$a" "$3" 0; then ok=0; echo "SU_PROGRAMME_PGCOL MUTANT $3 ESCAPED"
  elif grep -q "SU_PROGRAMME_PGCOL FAIL" "$OUT/run_$3_q0.log"; then echo "SU_PROGRAMME_PGCOL MUTANT $3 REJECTED (expected)"
  else ok=0; echo "SU_PROGRAMME_PGCOL MUTANT $3 no FAIL verdict"; fi
done
[ $ok = 1 ] && echo "SU_PROGRAMME_PGCOL_GATE PASS" && exit 0
echo "SU_PROGRAMME_PGCOL_GATE FAIL"; exit 1
