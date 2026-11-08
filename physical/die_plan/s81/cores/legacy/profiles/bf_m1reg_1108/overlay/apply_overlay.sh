#!/bin/bash
# Apply the bf gf3 zone overlay to a generated dsdv_gunit_l1f_bf_gf3 kit: $1 = kit dir, $2 = this overlay dir
set -euo pipefail
K=$1; O=$2
cp "$O"/zone_fence.tcl "$O"/zone_fence_release.tcl "$O"/zone_members.tcl "$O"/pre_gpl_zone.tcl "$O"/pre_dpl_zone.tcl "$K"/
grep -q "^export PRE_GLOBAL_PLACE_TCL = /work/face_flops.tcl$" "$K/config.mk"
grep -q "^export PRE_DETAIL_PLACE_TCL = /work/face_flops_release.tcl$" "$K/config.mk"
sed -i "s#^export PRE_GLOBAL_PLACE_TCL = /work/face_flops.tcl\$#export PRE_GLOBAL_PLACE_TCL = /work/pre_gpl_zone.tcl#; s#^export PRE_DETAIL_PLACE_TCL = /work/face_flops_release.tcl\$#export PRE_DETAIL_PLACE_TCL = /work/pre_dpl_zone.tcl#" "$K/config.mk"
grep -n "PRE_GLOBAL_PLACE_TCL\|PRE_DETAIL_PLACE_TCL" "$K/config.mk"
