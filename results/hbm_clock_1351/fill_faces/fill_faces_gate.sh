#!/bin/bash
set -eu
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
D=/srv/opentallas-scratch2/claude/codex-hbm-clock-1351
S=/srv/opentallas-scratch2/claude/wt/codex-hbm-clock-1351/rtl/hbm_accel/loader/service_native/split/ot_hbm_svc_vmdel_lane_n_faces.sv
yosys -Q -p "read_verilog -sv $S $D/fill_faces_miter.sv; hierarchy -top fill_faces_miter; proc; flatten; opt; sat -verify -prove mismatch 0 -show-inputs" > "$D/fill_faces_positive.log"
if yosys -Q -p "read_verilog -sv $D/fill_faces_mutant.sv $D/fill_faces_miter.sv; hierarchy -top fill_faces_miter; proc; flatten; opt; sat -verify -prove mismatch 0 -show-inputs" > "$D/fill_faces_mutant.log" 2>&1; then
 echo MUTANT_UNEXPECTED_PASS
 exit 1
fi
grep -q "proof did fail" "$D/fill_faces_mutant.log"
echo FILL_FACES_POSITIVE_PASS_MUTANT_CAUGHT
