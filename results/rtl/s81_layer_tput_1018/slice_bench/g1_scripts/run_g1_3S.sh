#!/bin/bash
# S81-LBGAP/G1: cut_3S on bind9_g1 die.v (hop-0 gates + calendar), TT cycle flight: idle, L0 CTL replay, 2 mutants (one build)
R=/srv/opentallas-scratch/claude/s81-lbgap-g1; cd $R
J=32 bash run_dv_slice.sh K3S out3S_idle +NCYC=2000 +TRACE=$R/out3S_idle/trace.txt; echo "IDLE rc $?"
for m in replay replay_shift1 replay_hops; do
  OBJ=$R/out3S_idle/obj bash run_dv_slice.sh K3S out3S_$m +IN=$R/K3S/$m/in.txt +OUT=$R/K3S/$m/out.txt +NCYC=255 +TRACE=$R/out3S_$m/trace.txt; echo "$m rc $?"
done
