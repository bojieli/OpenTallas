#!/bin/bash
# LB2-S81/REPLAY 10-18: dv_cut_replay witness runs on the G1 cut_3S build (bind9_g1, Verilator 5.050, prebuilt obj)
R=/srv/opentallas-scratch/claude/s81-lbgap-g1; Q=/srv/opentallas-scratch/claude/lb2-s81-replay; cd $R
for m in w_sched w_lane w_mshift w_mcorrupt; do
  OBJ=$R/out3S_idle/obj bash run_dv_slice.sh K3S $Q/out_$m +IN=$Q/$m/in.txt +OUT=$Q/$m/out.txt +NCYC=255 +TRACE=$Q/out_$m/trace.txt; echo "$m rc $?"
done
