#!/bin/bash
set -uo pipefail
python3 results/rtl/qw_head_safe32_1020/native_synth/prepare.py
export SRC="$PWD" SYNTH_TIMEOUT=unlimited OT_ORFS_CORNER_OVERRIDE=TC
sha256sum tools/run_abi3_physical.py tools/run_abi3_segcal_synth.py > results/rtl/qw_head_safe32_1020/native_synth/helper.sha256
bash results/rtl/qw_head_safe32_1020/native_synth/ref_synth.sh results/rtl/qw_head_safe32_1020/native_synth/kit_bound.env boundr3 "$PWD/safe32_native_synth_out" floorplan
