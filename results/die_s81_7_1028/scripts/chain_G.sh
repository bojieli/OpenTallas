#!/bin/bash
# DIE-S81-7 chain: kit G = kit F signal kit + G clock (fE3_p2_b0 DME on the routed stage fit) -> GRT with clock (2W2S NDR,
# 50 it, crit 0, TT+FF) -> post (main die_sta_related x1.00 + spice, landed_phase_ocv, count_align_plan) -> hold/in-region.
set -u
O=/srv/opentallas-scratch2/claude/die-s81-7; O5=/srv/opentallas-scratch2/claude/die-s81-5
R=/srv/opentallas-scratch2/claude/wt/die-s81-7/results/die_s81_7_1028/scripts; cd $O
echo START $(date)
rm -rf kit_G; cp -al $O5/kit_F kit_G; rm -rf kit_G/clock; cp -r G_clock kit_G/clock
cp $O5/kit_F/clock/make_tracks.tcl kit_G/clock/ 2>/dev/null
CKNDR=1 ~/.local/bin/ot-run --mem 120 --threads 16 --dir $O -- env CKNDR=1 bash $R/go_grt.sh G > grt_G.log 2>&1
~/.local/bin/ot-run --mem 48 --threads 8 --dir $O -- bash $R/post.sh G > post_G.log 2>&1
~/.local/bin/ot-run --mem 32 --threads 1 --dir $O -- bash $R/hh.sh G > hh_G.log 2>&1
~/.local/bin/ot-run --mem 64 --threads 4 --dir $O -- bash $R/ca_gate.sh G > ca_gate_G.log 2>&1
echo CHAIN_G_DONE $(date)
