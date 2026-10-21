#!/bin/bash
# LEAD2-S81/TOK-B3 (10-19): cut_7 L0 users 0/1/2 HOP bench WITH the in-simulator consumer check (dv_slice_tb --ep-check):
# every compiled end-slice beat at u_s_7N/u_s_7S checked bit-exact (edge, pair, kind, MU tag) against gold epx files
# written by dv_cut_replay epx from the compiled schedule (never from a DUT trace); zero checks / beats past the run /
# MU faults te|land|mcol = TB FAIL.  Verilator 5.050 (run_dv_slice.sh default).  Runs in the fleet dir.
# usage: fleet_tokb3.sh base | rtl_tagdrop
#   base:        build; hop  = base stimulus, hop gold, EPSTRICT=0     -> expect TB_DV_SLICE PASS
#                      tagdrop / wrongcopy = mutant stimulus, hop gold  -> expect FAIL (EP_MISMATCH)
#                      all  = base stimulus, full gold, EPSTRICT=1     -> records the 78 non-hop RD beats (open finding)
#   rtl_tagdrop: +define+OT_S81SL_LEP_MUT_TAGDROP build; hop gold      -> expect FAIL
set -u
T=$1; export J=16
n() { python3 -c "import json;print(json.load(open('R/$1/replay.json'))['ncyc'] + 200)"; }
run() { r=$1; o=$2; g=$3; s=$4; OBJ=$PWD/out_$T/obj bash K_cut_7_epc/run_dv_slice.sh K_cut_7_epc $o +IN=$PWD/R/$r/in.txt \
  +OUT=$PWD/R/$r/out.txt +NCYC=$(n $r) +TRACE=$PWD/$o/trace.txt +EP=$PWD/$o/ep.txt +EPX=$PWD/gold/$g +EPSTRICT=$s
  echo "RUN $r gold $g strict $s -> $o rc $?"; }
mkdir -p out_$T
if [ "$T" = base ]; then
  run R_cut_7_L0_hop012 out_base_hop R_cut_7_L0_hop012_hop.epx 0
  run R_cut_7_L0_hop012_tagdrop out_tagdrop_hop R_cut_7_L0_hop012_tagdrop_hop.epx 0
  run R_cut_7_L0_hop012_wrongcopy out_wrongcopy_hop R_cut_7_L0_hop012_wrongcopy_hop.epx 0
  run R_cut_7_L0_hop012 out_base_all R_cut_7_L0_hop012_all.epx 1
else
  export VFLAGS=+define+OT_S81SL_LEP_MUT_TAGDROP
  run R_cut_7_L0_hop012 out_rtl_tagdrop_hop R_cut_7_L0_hop012_hop.epx 0
fi
