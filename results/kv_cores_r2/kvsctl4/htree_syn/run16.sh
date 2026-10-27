#!/bin/sh
n=$1; shift
python3 /w/tools/die_plan/core_infra_htree.py /d/syn.geo /d/v_$n.tcl --libtt /nldm/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib --libff /nldm/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib --islands "47.52,47.52;47.52,138.24;47.52,233.28;47.52,324.0;138.24,47.52;138.24,138.24;138.24,233.28;138.24,324.0;233.28,47.52;233.28,138.24;233.28,233.28;233.28,324.0;324.0,47.52;324.0,138.24;324.0,233.28;324.0,324.0" --hb-axes x,y,x,y "$@" > /d/v_$n.out 2>&1
