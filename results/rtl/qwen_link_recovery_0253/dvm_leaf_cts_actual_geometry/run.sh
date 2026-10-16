#!/bin/bash
set -eu
p=/srv/opentallas-scratch/claude/ref_gate/qfd_xs_leaf_m6_138-20261016-034400
out=/srv/opentallas-scratch/codex/dvm_leaf_raw_0253
mkdir -p "$out"
docker run --rm -v "$p":/work:ro -v "$out":/out openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -threads 1 -exit /out/export.tcl > "$out/export.log" 2>&1
sha256sum "$p/routes/gate/work/orfs/results/asap7/opentallas_ot_qfd_xs_leaf_asap7_ref_gate/base/4_1_cts.odb" "$out/actual_cts.def" "$out/actual_cts.lef" > "$out/artifact.sha256"
