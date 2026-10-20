#!/bin/bash
# TOKSIM-S81B/FGU 10-19 (2nd agent): diagnose the experts_gu phase-sequence hang (job 3: 13 legs ran >2 h with no output)
# and extend the go-period sweep below 200.  Reuses job 3's exe (OUT/obj) and vectors; line-buffered stdout + timeouts.
# cwd = src root; args: VEC OUT DOUT
set -u
VEC=$1; O=$2; D=$3; mkdir -p $D; Q=tools/s81_dv/layer_prog/qf_producer; X=$O/obj/Vtb_toksim_fgu_seq
run() { # name rom_dir nph ph0 per
  timeout ${TMO:-240} stdbuf -oL -eL $X +OT_ROM_DIR=$2 +T=1600 +K=5120 +OPS=4 +PH=$4 +NPH=$3 +PER=$5 > $D/run_$1.log 2>&1; echo "$1 rc=$?"; }
export -f run; export X D
{
 # experts prefixes at P=600 (where does it stop?)
 for n in 2 3 4 6 8 12 24; do echo "ex_n${n}_P600 $VEC/seq_experts_gu $n 20 600"; done
 # shared sweep below 200
 for P in 180 160 140 120 100 80 60 40; do echo "sh_P$P $VEC/seq_shared_gu 4 16 $P"; done
} | xargs -P 16 -L1 bash -c 'run "$@"' _ | sort -V
for f in $D/run_*.log; do echo "== $(basename $f): $(grep -cE '^RET' $f) RET; $(grep -E '^(GO_LATE|END|FAULT)' $f | head -3 | tr '\n' ' ') lastGO: $(grep -E '^GO ' $f | tail -1)"; done
for P in 180 160 140 120 100 80 60 40; do python3 $Q/toksim_fgu_check.py seq --seq $VEC/seq_shared_gu --vec $VEC --log $D/run_sh_P$P.log --out $D/res_sh_P$P.json --per $P --ref-go 63 2>&1 | tail -1; done
echo TOKSIM_FGU_DIAG_DONE
