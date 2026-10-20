#!/bin/bash
set -uo pipefail
python3 results/rtl/qlb_c4b_1018/lmh_cal/native_synth/prepare.py
export SRC="$PWD" SYNTH_TIMEOUT=unlimited OT_ORFS_CORNER_OVERRIDE=TC
sha256sum tools/run_abi3_physical.py tools/run_abi3_segcal_synth.py > results/rtl/qlb_c4b_1018/lmh_cal/native_synth/helper.sha256
bash results/rtl/qlb_c4b_1018/lmh_cal/native_synth/ref_synth.sh results/rtl/qlb_c4b_1018/lmh_cal/native_synth/kit.env segcal "$PWD/native_synth_out" floorplan
