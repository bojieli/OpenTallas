#!/bin/sh
# $1 name, rest args
n=$1; shift
ISL="47.52,90.72;47.52,276.48;138.24,90.72;138.24,276.48;233.28,90.72;233.28,276.48;324.0,90.72;324.0,276.48"
python3 /w/tools/die_plan/core_infra_htree.py /d/syn.geo /d/v_$n.tcl --libtt /nldm/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib --libff /nldm/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib --islands "$ISL" --hb-axes x,y,x "$@" > /d/v_$n.out 2>&1
