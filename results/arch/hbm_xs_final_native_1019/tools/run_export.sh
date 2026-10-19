#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch/claude/ref_gate/smh_xs_ring_c32k_1019-20261019-115411
A=/srv/opentallas-scratch/claude/hbm-xs-final-native-1019
IMG=openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
docker run --rm -v "$R:/gate:ro" -v "$A:/audit" "$IMG" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit -python /audit/export_raw.py /gate/routes/gate/work/orfs/results/asap7/opentallas_ot_hbm_accel_smh_xs_asap7_ref_gate/base/4_cts.odb /audit/out
docker run --rm -v "$A:/audit" "$IMG" bash -c 'cp /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT*TT* /audit/out/'
cp "$R"/src/physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/*_tt.lib "$A/out/"
cp "$R"/src/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/*_tt.lib "$A/out/"
cp "$R/routes/gate/work/orfs/gate_dump.json" "$A/out/pin_dump.json"
sha256sum "$A"/out/* > "$A/out/SHA256SUMS"
