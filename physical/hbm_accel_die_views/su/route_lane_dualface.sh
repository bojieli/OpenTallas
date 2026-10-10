#!/bin/bash
# SU lane pin-density successor: both horizontal layers expose the W face.
# M6 signal routing permits the M6 pins to escape the access keepout before
# dropping to M5. Core PG is inset1.08um from the face pin stubs.
export CORE_INSET_X=1.08 IOC=io_left_reset_tree.tcl
export PINL='M4 M6' MAXL=M6 PPA='-min_distance 2 -min_distance_in_tracks'
exec bash physical/hbm_accel_die_views/su/route_lane.sh "$1" ot_su12_light 85.32 162.0
