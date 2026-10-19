#!/bin/bash
# S81-LBGAP/G8 cut_3S on the G8 die.v: build + idle 2000, L0 CTL replay, mutants shift1 / hops (one build)
cd /srv/opentallas-scratch/claude/s81-lbgap-g8
J=32 bash K_cut_3S/run_dv_slice.sh K_cut_3S out_3S_idle +NCYC=2000 +TRACE=/srv/opentallas-scratch/claude/s81-lbgap-g8/out_3S_idle/trace.txt; echo "IDLE rc $?"
for m in replay replay_shift1 replay_hops; do
  OBJ=/srv/opentallas-scratch/claude/s81-lbgap-g8/out_3S_idle/obj bash K_cut_3S/run_dv_slice.sh K_cut_3S out_3S_$m +IN=/srv/opentallas-scratch/claude/s81-lbgap-g8/K_cut_3S/$m/in.txt +OUT=/srv/opentallas-scratch/claude/s81-lbgap-g8/K_cut_3S/$m/out.txt +NCYC=255 +TRACE=/srv/opentallas-scratch/claude/s81-lbgap-g8/out_3S_$m/trace.txt; echo "$m rc $?"
done
