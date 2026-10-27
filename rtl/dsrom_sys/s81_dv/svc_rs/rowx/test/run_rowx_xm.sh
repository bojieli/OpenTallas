#!/usr/bin/env bash
# S81-ROWX3 (10-26): build + run the 16-owner rank-order row transport bench (tb_dsdv_rowx_xm: export -> re-pair ->
# OR-merge chain -> broadcast -> egress, all 16 receivers scored) and its negative controls / mutants.
# usage: run_rowx_xm.sh <outdir> [variant ...]; variants base (must PASS every run), mut1..mut4 (must FAIL).
# Prints ROWXM_GATE PASS when base passes every run and every listed mutant fails.  Verilator = the pinned 5.050.
set -u
R=$(cd "$(dirname "$0")/../../../../../.." && pwd); O=$1; shift; VARS=${*:-"base mut1 mut2 mut3 mut4 mut5"}
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
D=rtl/dsrom_sys/s81_dv/svc_rs/rowx
SRC="$D/dsdv_rowx_lc.sv $D/dsdv_rowx_rp.sv $D/dsdv_rowx_xm.sv $D/test/tb_dsdv_rowx_xm.sv"
F=$R/results/rtl/s81_rowx2_1026/fix
mkdir -p "$O"; bad=0
for v in $VARS; do
  case $v in base) M=0;; mut*) M=${v#mut};; *) echo "variant? $v"; exit 2;; esac
  B=$O/$v; mkdir -p "$B"
  if [ ! -x "$B/obj/Vtb_dsdv_rowx_xm" ]; then
    $VL --binary --timing -j "${J:-4}" --build-jobs "${BJ:-4}" -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-TIMESCALEMOD \
      -DTB_MUT=$M --top-module tb_dsdv_rowx_xm -Mdir "$B/obj" $(for f in $SRC; do echo "$R/$f"; done) > "$O/build_$v.log" 2>&1 \
      || { echo "BUILD_FAIL $v"; tail -20 "$O/build_$v.log"; bad=1; continue; }
  fi
  RUNS=""
  case $v in
    base) for s in 1 2 3 4 5; do RUNS="$RUNS s$s|+seed=$s+j=$(( s % 4 ))"; done
          RUNS="$RUNS s6_id|+seed=6+perm=0+j=0 s7_lx40|+seed=7+lx=40+lon=6+j=3"
          for L in 02 08 14 20 24 28 32 36; do RUNS="$RUNS fxL$L|+seed=$L+fix=$F/gid_L$L.hex+j=2"; done
          RUNS="$RUNS neg_ovl1|+seed=1+ovl=1+j=1 neg_ovl2|+seed=2+ovl=1 neg_short|+seed=3+short=1+j=2 neg_skew|+seed=4+skew=1"
          # ROWX-3b link packing at the lep lane rate (0.764): PK = 1 runs (die-to-die LX 37 = U_WIRE 34 + lep 3)
          for s in 1 2 3 4 5; do RUNS="$RUNS pk_s$s|+seed=$s+pk=1+rate=764+j=$(( s % 5 ))+lx=37"; done
          for L in 02 14 28 36; do RUNS="$RUNS pk_fxL$L|+seed=$L+pk=1+rate=764+fix=$F/gid_L$L.hex+j=4+lx=37"; done
          RUNS="$RUNS pk_neg_ovl|+seed=1+pk=1+rate=764+ovl=1+j=2+lx=37 pk_neg_short|+seed=3+pk=1+rate=764+short=1+j=2+lx=37"
          RUNS="$RUNS pk_neg_skew|+seed=4+pk=1+rate=764+skew=1+lx=37 neg_rate|+seed=5+neg_rate=1+j=2+lx=37"
          # 16 dies (all 15 links die-to-die L 37, all capped at 0.764): the priced span
          RUNS="$RUNS pk16_s9|+seed=9+pk=1+rate=764+rall=1+lon=37+lx=37+j=4 pk16_fxL20|+seed=20+pk=1+rate=764+rall=1+lon=37+lx=37+j=4+fix=$F/gid_L20.hex"
          RUNS="$RUNS neg_rate16|+seed=9+neg_rate=1+rall=1+lon=37+lx=37+j=4";;
    mut5) RUNS="pk_s1|+seed=1+pk=1+rate=764+j=1+lx=37";;
    mut2) RUNS="neg_ovl1|+seed=1+ovl=1+j=1";;
    mut*) RUNS="s1|+seed=1+j=1";;
  esac
  for rr in $RUNS; do
    n=${rr%%|*}; pa=${rr#*|}; pa=${pa//+/ +}
    "$B/obj/Vtb_dsdv_rowx_xm" $pa > "$O/run_${v}_$n.log" 2>&1
    l=$(grep -h '^ROWXM ' "$O/run_${v}_$n.log" | tail -1); t=$(grep -h '^TRANSPORT_TIMING' "$O/run_${v}_$n.log" | tail -1)
    echo "$v $n: $l"; [ "$v" = base ] && echo "   $t"
    if [ "$v" = base ]; then case "$l" in *verdict=PASS*) ;; *) bad=1;; esac
    else case "$l" in *verdict=FAIL*) ;; *) echo "MUTANT_NOT_CAUGHT $v $n"; bad=1;; esac; fi
  done
done
[ $bad = 0 ] && echo "ROWXM_GATE PASS" || echo "ROWXM_GATE FAIL"; exit $bad
