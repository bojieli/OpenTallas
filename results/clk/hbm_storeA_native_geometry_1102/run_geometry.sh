#!/bin/bash
set -euo pipefail
KIT=/srv/opentallas-scratch2/claude/codex-storeA-native-sourceproof-0048/kits/ot_hnx_sfu_store_a__da81d76763c9_4b48edda3499-source_eq
cp "$KIT/macros/ot_sram_1r1w_256x256_m2_r2c2.lef" sram.lef
docker run --rm --memory=1g --memory-swap=1g --cpus=1 -v "$PWD:/out" openroad/orfs:asap7lock cp /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef /out/std.lef
python3 -u capture_geometry.py
