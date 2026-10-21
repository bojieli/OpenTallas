#!/bin/bash
# MU-DIE-S81/HOP fleet job (runs on the host in the lane dir): build the probed cut_7 bench (Verilator 5.050), run the
# L0 users 0/1/2 replay with the compiled TX windows on the lowered hop + the stimulus mutants on the same obj.
# usage: fleet_cut7.sh <tag> [VFLAGS]   tag base: base build + base/tagdrop/wrongcopy runs; tag rtl_tagdrop: RTL mutant build + base run
set -u
T=$1; export VFLAGS="${2:-}"; export J=16
n() { python3 -c "import json;print(json.load(open('R/$1/replay.json'))['ncyc'] + 200)"; }
run() { r=$1; o=$2; OBJ=$PWD/out_$T/obj bash K_cut_7_ep/run_dv_slice.sh K_cut_7_ep $o +IN=$PWD/R/$r/in.txt +OUT=$PWD/R/$r/out.txt \
  +NCYC=$(n $r) +TRACE=$PWD/$o/trace.txt +EP=$PWD/$o/ep.txt; echo "RUN $r -> $o rc $?"; }
mkdir -p out_$T
if [ "$T" = base ]; then
  run R_cut_7_L0_hop012 out_base
  run R_cut_7_L0_hop012_tagdrop out_base_tagdrop
  run R_cut_7_L0_hop012_wrongcopy out_base_wrongcopy
else
  run R_cut_7_L0_hop012 out_$T
fi
