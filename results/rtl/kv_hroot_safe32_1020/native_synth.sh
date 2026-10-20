#!/bin/bash
set -eu
docker run --rm -v "$PWD:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock make -B DESIGN_CONFIG=/work/results/rtl/kv_hroot_safe32_1020/native_synth.mk WORK_HOME=/work/native_orfs synth >native_synth_hook.log 2>&1
