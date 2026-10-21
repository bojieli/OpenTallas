#!/bin/bash
# LEAD2-S81/TOK3 (10-19): TOK.DS.BENCH.3 rerun after the lower_vpx post-XR2 fix (Codex 73879e4d2: CFG_AT 4, LO 16, RX 6,
# P 6). Inputs only change (replays regenerated from the recompiled prog_L0_mu_A); the obj dirs are the existing probed
# cut_7 builds in ../mu-die-s81-hop (base + OT_S81SL_LEP_MUT_TAGDROP), Verilator 5.050, reused (no build).
# Four runs in parallel; the consumer check (dv_cut_replay epcheck on ep.txt, scope all/hop) runs on the client.
set -u
HP=/srv/opentallas-scratch/claude/mu-die-s81-hop
n() { python3 -c "import json;print(json.load(open('R/$1/replay.json'))['ncyc'] + 200)"; }
run() { r=$1; o=$2; ob=$3; OBJ=$HP/$ob/obj bash $HP/K_cut_7_ep/run_dv_slice.sh $HP/K_cut_7_ep $PWD/$o +IN=$PWD/R/$r/in.txt \
  +OUT=$PWD/R/$r/out.txt +NCYC=$(n $r) +TRACE=$PWD/$o/trace.txt +EP=$PWD/$o/ep.txt > $PWD/$o.client.log 2>&1
  echo "RUN $r obj $ob -> $o rc $?"; }
run R_cut_7_L0_hop012 out_base out_base &
run R_cut_7_L0_hop012_tagdrop out_base_tagdrop out_base &
run R_cut_7_L0_hop012_wrongcopy out_base_wrongcopy out_base &
run R_cut_7_L0_hop012 out_rtl_tagdrop out_rtl_tagdrop &
wait
