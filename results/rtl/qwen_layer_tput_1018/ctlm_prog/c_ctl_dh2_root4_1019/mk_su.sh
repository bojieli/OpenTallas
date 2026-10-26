#!/bin/bash
# single-user variant of the dh2 c_ctl slice: tt_ctlm NU 4 -> 1, OPSEG 1 -> 0, sys_face MU 1 -> 0 (the dv2f14bn configuration the
# c_ctl bench replays); every relay / landing / XPF_TRANSPORT_EDGES 21 / STAGE_ME 1 as the dh2 die.  DIAGNOSTIC (not the MU die config).
L=/srv/opentallas-scratch/claude/root4-qwpost
for m in 0 1; do S=$L/out/c_ctl_m$m; D=$L/out/c_ctl_m${m}su; rm -rf $D; cp -r $S $D
  sed -i "s#$S/#$D/#g" $D/qwc_slice_ctl.f
  sed -i 's/qfd_tt_ctlm_dv #(.NU(4), .OPSEG(1), /qfd_tt_ctlm_dv #(.NU(1), .OPSEG(0), /; s/qfd_sys_face #(.MU(1))/qfd_sys_face #(.MU(0))/' $D/qwc_slice_ctl.sv
  grep -o 'qfd_tt_ctlm_dv #([^)]*([^)]*)[^)]*([^)]*)[^)]*([^)]*)[^)]*([^)]*)[^)]*\(([^)]*)\)\?)' $D/qwc_slice_ctl.sv; grep -o 'qfd_sys_face #([^;]\{0,40\}' $D/qwc_slice_ctl.sv
done
