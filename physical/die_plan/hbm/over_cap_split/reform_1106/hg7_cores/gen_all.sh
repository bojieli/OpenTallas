#!/bin/bash
# HBM-GAPS-7 11-06: GEN vA (kit_wave form, recipe util 0.45) + vB (util 0.38; wbq_sw vB = __gin recipe) for 4 cores
B=/srv/opentallas-scratch3/claude/hbm-gaps-7/cores; W=/srv/opentallas-scratch3/claude/hbm-gaps-7/wt
G=$W/physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py
gen() { # view key ver extra...
  local view=$1 key=$2 ver=$3; shift 3; local mod=${view%@*}
  mkdir -p $B/kits/${mod}_$ver
  ( cd $W && timeout 3000 prlimit --as=48000000000 python3 -I -c "import runpy,sys;sys.path[:0]=['$W/physical/die_plan/hbm_arch_cores','$W/tools/die_plan'];sys.argv=['$G']+sys.argv[1:];runpy.run_path('$G',run_name='__main__')" --views $B/views.json --view $view --recipe-key $key \
     --out $B/kits/${mod}_$ver --clock-pin-entry on --core-macros auto "$@" > $B/gen_${mod}_$ver.log 2>&1; echo "GEN $mod $ver rc=$?" )
}
gen ot_hfd_coll_q3_edge_arg@205add3d94c2 ot_hfd_coll_q3_edge_arg vA &
gen ot_hfd_coll_q3_edge_arg@205add3d94c2 ot_hfd_coll_q3_edge_arg vB --util 0.38 &
gen ot_q2nf_rest@420e7cd7fa90 ot_q2nf_rest vA &
gen ot_q2nf_rest@420e7cd7fa90 ot_q2nf_rest vB --util 0.38 &
gen ot_wbq_root@be03cffe8be6 ot_wbq_root vA &
gen ot_wbq_root@be03cffe8be6 ot_wbq_root vB --util 0.38 &
gen ot_wbq_sw@b5a602ee0024 ot_wbq_sw vA &
gen ot_wbq_sw@b5a602ee0024 ot_wbq_sw__gin vB --util 0.38 &
wait
