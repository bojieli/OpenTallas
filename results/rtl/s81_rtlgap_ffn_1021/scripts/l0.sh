#!/bin/bash
# RG-FFN: the existing L0 MU per-layer bench (TOK.DS.BENCH.3 cut_7 L0, S81-TOK4 63b8a0d5e: replays R_cut_7_L0_hop012 +
# tagdrop / wrongcopy input mutants, run_dv_slice.sh, dv_cut_replay epcheck scope all / hop) rebuilt on kit K_<k>:
#   K_ctl = cut_7 kit with the die72 base (4ee613834) ot_s81sl_xr / rstop / xg   (control)
#   K_new = cut_7 kit with the slice bound to ot_s81sl_xgt (rstopt) + ot_s81sl_xrt1/3 (transport + SAFE)  (the change)
# l0.sh <k>   (cwd = this dir; Verilator 5.050 per run_dv_slice.sh)
set -u; k=$1; H=$(pwd); K=$H/K_$k; O=$H/out_$k; mkdir -p $O
n() { python3 -c "import json;print(json.load(open('$H/R/$1/replay.json'))['ncyc'] + 200)"; }
J=32 bash $K/run_dv_slice.sh $K $O/base +IN=$H/R/R_cut_7_L0_hop012/in.txt +OUT=$H/R/R_cut_7_L0_hop012/out.txt \
  +NCYC=$(n R_cut_7_L0_hop012) +EP=$O/base/ep.txt > $O/base.client.log 2>&1; echo "RUN base rc $?"
for m in tagdrop wrongcopy; do r=R_cut_7_L0_hop012_$m
  OBJ=$O/base/obj bash $K/run_dv_slice.sh $K $O/$m +IN=$H/R/$r/in.txt +OUT=$H/R/$r/out.txt +NCYC=$(n $r) +EP=$O/$m/ep.txt \
    > $O/$m.client.log 2>&1 & done; wait
ec() { o=$1; r=$2; s=$3; shift 3; python3 $H/dv_cut_replay.py epcheck --replay $H/R/$r --run $O/$o --scope $s \
  --out $O/epcheck_${s}_$o.json "$@" > $O/epcheck_${s}_$o.log 2>&1; echo "$k $o $s $* rc $? | $(tail -n1 $O/epcheck_${s}_$o.log | cut -c1-200)"; }
ec base R_cut_7_L0_hop012 all; ec base R_cut_7_L0_hop012 hop
ec tagdrop R_cut_7_L0_hop012_tagdrop hop --expect-fail; ec wrongcopy R_cut_7_L0_hop012_wrongcopy hop --expect-fail
cat $O/base/status; echo "L0_DONE $k"
