#!/bin/bash
# Full SFU lane reset successor that keeps the quarter's sixteen-lane column height.
export CORE_INSET_X=1.08 IOC=io_left_reset_tree.tcl
export PPA='-min_distance 3 -min_distance_in_tracks'
exec bash physical/hbm_accel_die_views/su/route_lane.sh "$1" ot_su12_sfu 237.6 330.48 --param GSH=1 --param KIMM=1 --param DENR=1 --param DRING=3 --param RSTPIPE=1
