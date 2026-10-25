#!/bin/bash
# TOK-QK/C 10-24: build + sweep the FDI CDC unit bench (tb_fdicdc.sv).   run.sh OUT [J]
#   builds OUT/obj (real CDC) and OUT/obj_mut (mutant ii: direct wiring); runs the ratio x phase x seed sweep + mutants,
#   writes OUT/summary.txt.  Light: ~1 GB, minutes.
set -u
H=$(cd "$(dirname "$0")" && pwd); R=$(cd $H/../../../.. && pwd); O=$(mkdir -p $1 && readlink -f $1); J=${2:-16}
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
F="-Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --timing --binary -O1 --top-module tb_fdicdc $R/rtl/lib/ot_reset_sync.sv $R/rtl/lib/ot_async_fifo.sv $R/rtl/physical/ot_fdi_join2.sv $R/rtl/physical/ot_fdi_tx_pace.sv $H/tb_fdicdc.sv"
( cd $O && $VL $F $R/rtl/physical/ot_fdi_phy_cdc.sv -Mdir obj > build.log 2>&1 ) || { echo "BUILD FAIL"; tail $O/build.log; exit 2; }
( cd $O && $VL $F $H/mut_direct.sv -Mdir obj_mut > build_mut.log 2>&1 ) || { echo "BUILD MUT FAIL"; tail $O/build_mut.log; exit 2; }
mkdir -p $O/runs; : > $O/jobs.txt
k=0
for tp in 870 950 1000 1043 1050; do for s in 1 2 3 4 5 6; do
  k=$((k+1)); ph=$(( (s * 1777 + tp * 13) % tp ))
  lw=$(( 20 + s % 9 )); le=$(( 20 + (s * 5) % 13 ))
  echo "nom_tp${tp}_s$s obj +TP_PS=$tp +PHASE_PS=$ph +SEED=$((s*101+tp)) +RXDENS=$((60 + s*7)) +TXDENS=$((70 + s*5)) +LW=$lw +LE=$le +TW=$le +TE=$lw" >> $O/jobs.txt
done; done
# expected: nom_* PASS; every mut* FAIL.  mutants: (i) C1 valid skew +4, (ii) direct wiring, (iii) PHY slower than the pacing bound (tp 1100 > 1052.6) -> TX FIFO loss
for s in 1 2 3; do
  echo "mutC1_s$s obj +TP_PS=1043 +PHASE_PS=$((s*311)) +SEED=$((s*7)) +MUT_C1" >> $O/jobs.txt
  echo "mutDIRECT_s$s obj_mut +TP_PS=1043 +PHASE_PS=$((s*311)) +SEED=$((s*7))" >> $O/jobs.txt
  echo "mutSLOWPHY_s$s obj +TP_PS=1100 +PHASE_PS=$((s*311)) +SEED=$((s*7)) +TXDENS=100 +N=8000" >> $O/jobs.txt
done
run1() { n=$1; b=$2; shift 2; mkdir -p $O/runs/$n; ( cd $O/runs/$n && timeout 1200 $O/$b/Vtb_fdicdc +verilator+error+limit+1000000 "$@" > sim.log 2>&1 ); }
export -f run1; export O
cat $O/jobs.txt | xargs -P $J -L 1 bash -c 'run1 "$@"' _
: > $O/summary.txt
while read n b rest; do
  v=$(grep -m1 -oE 'FDICDC (PASS|FAIL.*)$' $O/runs/$n/sim.log | head -1); c=$(grep -m1 '^FDICDC RX sent' $O/runs/$n/sim.log); l=$(grep -m1 '^FDICDC LAT' $O/runs/$n/sim.log)
  e=$(grep -c '%Error' $O/runs/$n/sim.log)
  echo "$n | ${v:-NO VERDICT} | errors $e | $c | $l" >> $O/summary.txt
done < $O/jobs.txt
cat $O/summary.txt
