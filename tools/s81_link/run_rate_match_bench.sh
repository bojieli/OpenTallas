#!/usr/bin/env bash
# ELEM-CENSUS 2026-10-16 (S81-LINK kit helper): unit bench of ot_s81_rate_match (rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv)
# with rtl/dsrom_sys/s81_link/tb_s81_rate_match.sv, both slip directions (FAST 1 writer fast: IDLE drop; FAST 0 writer
# slow: IDLE insert).  Mutants are applied to a COPY of the RTL in OUTDIR (the source is never edited) and the edit is
# verified to have landed.  usage: run_rate_match_bench.sh MODE OUTDIR
#   base       -> RATE_MATCH_BENCH PASS dirs=2
#   mut_drop   the write side drops ANY beat (not only IDLE) at fill >= 6       -> RATE_MATCH_BENCH FAIL ...
#   mut_noidle the read side repeats its last beat instead of an IDLE when empty -> RATE_MATCH_BENCH FAIL ...
set -u
mode=${1:?base|mut_drop|mut_noidle}; out=${2:?fresh output directory}; mkdir -p "$out"
R=$(cd "$(dirname "$0")/../.." && pwd); L=$R/rtl/dsrom_sys/s81_link
cp "$L/ot_pdie_serdes.sv" "$out/rtl.sv"
mut() { grep -qF "$1" "$out/rtl.sv" || { echo "RATE_MATCH_BENCH MUTANT_NOT_APPLIED $mode"; exit 2; }
        python3 - "$out/rtl.sv" "$1" "$2" <<'PY'
import sys
p, a, b = sys.argv[1:]
t = open(p).read(); assert t.count(a) == 1, a; open(p, "w").write(t.replace(a, b))
PY
}
case $mode in
  base) ;;
  mut_drop)   mut '!(idle && fill_w >= 4'"'"'d6)' '!(fill_w >= 4'"'"'d6)';;
  mut_noidle) mut "else r_d <= 512'd2;" "else r_d <= r_d;";;
  *) echo "RATE_MATCH_BENCH BAD_MODE $mode"; exit 2;;
esac
nf=0
for f in 1 0; do
  iverilog -g2012 -s tb_s81_rate_match -P tb_s81_rate_match.FAST=$f -o "$out/sim$f.vvp" "$L/tb_s81_rate_match.sv" "$out/rtl.sv" \
    > "$out/build$f.log" 2>&1 || { echo "RATE_MATCH_BENCH BUILD_FAIL FAST=$f"; tail -5 "$out/build$f.log"; exit 2; }
  vvp -n "$out/sim$f.vvp" > "$out/run$f.log" 2>&1
  grep '^ERR' "$out/run$f.log" | head -3
  line=$(grep '^TB_S81_RATE_MATCH' "$out/run$f.log" | tail -1); echo "$line"
  case "$line" in *" PASS") ;; *) nf=$((nf + 1));; esac
done
if [ $nf = 0 ]; then echo "RATE_MATCH_BENCH PASS dirs=2"; else echo "RATE_MATCH_BENCH FAIL mode=$mode dirs_failed=$nf"; exit 1; fi
