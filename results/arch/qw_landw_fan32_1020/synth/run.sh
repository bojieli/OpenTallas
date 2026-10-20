#!/bin/bash
set -euo pipefail
python3 results/arch/qw_landw_fan32_1020/synth/prepare.py
export SRC="$PWD" SYNTH_TIMEOUT=unlimited OT_ORFS_CORNER_OVERRIDE=TC
sha256sum tools/run_abi3_physical.py tools/run_abi3_landw_synth.py > results/arch/qw_landw_fan32_1020/synth/helper.sha256
bash results/arch/qw_landw_fan32_1020/synth/ref_synth.sh results/arch/qw_landw_fan32_1020/synth/kit.env landw116v2 "$PWD/native_synth_out" floorplan
