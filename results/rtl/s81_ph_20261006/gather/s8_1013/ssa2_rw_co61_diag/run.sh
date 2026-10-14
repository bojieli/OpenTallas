#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch/claude/ref_gate/dsfd_gth_rw-20261014-023401
cp "$R/routes/gate/work/orfs/results/asap7/opentallas_dsfd_gth_rw_asap7_ref_gate/base/ot_inhold_firm.txt" .
cp "$R/routes/gate/work/orfs/results/asap7/opentallas_dsfd_gth_rw_asap7_ref_gate/base/ot_out_flop_at_pins.txt" .
docker run --rm -v "$R/src:/src:ro" -v "$R/routes/gate/work/orfs:/work:ro" -v "$PWD:/probe" openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /probe/probe.tcl > probe.log 2>&1
