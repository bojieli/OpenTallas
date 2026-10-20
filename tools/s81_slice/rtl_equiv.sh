#!/usr/bin/env bash
# ROOT4-S81POST (10-19): sequential RTL equivalence of a closed tile's source (gold) vs a newer source (gate).
# usage: rtl_equiv.sh OUTDIR TOP "DEFINES" GOLD_DIR GATE_DIR file...   (files are paths relative to GOLD_DIR / GATE_DIR)
# Both sides: read_verilog -sv -DSYNTHESIS DEFINES, hierarchy -top TOP, proc, flatten, opt -full, opt_dff -sat (constant /
# dead state removed, e.g. logic a parameter strips), async2sync, then equiv_make gold gate / equiv_simple -seq 8 /
# equiv_induct -seq 8 / equiv_status -assert over every port and every name-matched register bit.
# Prints EQUIV_PROVEN <top> or EQUIV_NOT_PROVEN <top> (unproven count) and both sides' generic `synth -flatten` stat.
set -u
OUT=$1; TOP=$2; DEFS=$3; G=$4; N=$5; shift 5
mkdir -p "$OUT"
YS=${YOSYS:-$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys}; [ -x "$YS" ] || YS=yosys
D=""; for d in $DEFS; do D="$D -D$d"; done
gf=""; nf=""; for f in "$@"; do gf="$gf $G/$f"; nf="$nf $N/$f"; done
side() { # $1 = files, $2 = name
cat <<YS
read_verilog -sv -DSYNTHESIS $D $1
hierarchy -check -top $TOP
proc; flatten; opt -full; opt_dff -sat; opt -full; opt_clean -purge; async2sync; opt_clean
rename $TOP $2
design -stash $2
YS
}
{ side "$gf" gold; side "$nf" gate
  echo "design -copy-from gold -as gold gold"; echo "design -copy-from gate -as gate gate"
  echo "equiv_make gold gate equiv"; echo "hierarchy -top equiv"; echo "equiv_simple -seq 8"; echo "equiv_induct -seq 8"
  echo "tee -o $OUT/equiv_status.txt equiv_status"; echo "equiv_status -assert"; } > "$OUT/equiv.ys"
"$YS" -q -l "$OUT/equiv.log" "$OUT/equiv.ys" > /dev/null 2>&1; rc=$?
for s in gold gate; do
  f=$gf; [ $s = gate ] && f=$nf
  "$YS" -q -l "$OUT/synth_$s.log" -p "read_verilog -sv -DSYNTHESIS $D $f; synth -flatten -top $TOP; opt_clean -purge; tee -o $OUT/stat_$s.txt stat" >/dev/null 2>&1
done
"$YS" -V > "$OUT/yosys_version.txt" 2>&1
sha256sum $gf $nf > "$OUT/sources.sha256"
if [ $rc -eq 0 ]; then echo "EQUIV_PROVEN $TOP"; else echo "EQUIV_NOT_PROVEN $TOP rc=$rc $(grep -m1 -E 'unproven' $OUT/equiv_status.txt)"; fi
if diff -q <(grep -E '^\s+(Number of cells|\$_|[A-Za-z_]+\s+[0-9]+$)' $OUT/stat_gold.txt) <(grep -E '^\s+(Number of cells|\$_|[A-Za-z_]+\s+[0-9]+$)' $OUT/stat_gate.txt) >/dev/null; then echo "SYNTH_STAT_IDENTICAL $TOP"; else echo "SYNTH_STAT_DIFFERS $TOP"; fi
