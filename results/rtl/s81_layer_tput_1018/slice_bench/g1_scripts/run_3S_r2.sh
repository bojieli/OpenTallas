#!/bin/bash
R=/srv/opentallas-scratch/claude/s81-lbgap-g1; cd $R
for m in replay2 replay2_shift1 replay2_hops; do
  OBJ=$R/out3S_idle/obj bash run_dv_slice.sh K3S out3S_$m +IN=$R/K3S/$m/in.txt +OUT=$R/K3S/$m/out.txt +NCYC=255 +TRACE=$R/out3S_$m/trace.txt; echo "$m rc $?"
done
