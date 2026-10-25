#!/bin/bash
# PATH-QC-NK2 R6 CTS step (run.sh place step done 10:41; its CTS tail was lost to a quoting error): CTS
# (SKIP_CTS_REPAIR_TIMING=1, as the autopilot adapter) from the R6 3_place -> FF hold gate (RC before SDC) on the v10 signoff.sdc.
B=/srv/opentallas-scratch2/claude/path-qc-nk2/r6
W=$B/run/r6/work/orfs; SRC=$B/src
IMAGE=openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
cp "$B/hold_gate_ref.tcl" "$W/hold_gate.tcl"
docker run --rm --name pathqcnk2-r6-cts-$$ --cpus=16 --memory=24g --memory-swap=24g -v "$SRC":/src:ro -v "$W":/work \
  -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc "trap 'chmod -R a+rwX /work >/dev/null 2>&1 || true' EXIT; \
  source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts && \
  python3 /src/tools/orfs_allcorner_spef.py /OpenROAD-flow-scripts/flow/scripts/final_outputs.tcl || exit 3; \
  M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=16'; \
  \$M cts SKIP_CTS_REPAIR_TIMING=1; rc=\$?; \
  if [ \$rc = 0 ]; then C=\$(ls /work/results/asap7/*/base/4_cts.odb | head -1); \
    \$M print-BC_LIB_FILES 2>/dev/null | sed -n 's/^BC_LIB_FILES *[:=] *//p' > /work/plibs.txt; \
    PLIBS=\"\$(cat /work/plibs.txt)\" ODB=\"\$C\" SDC=/src/physical/ref_tile/qfd_tile_nk_a0cv10/signoff.sdc \
      PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/asap7 openroad -exit /work/hold_gate.tcl > /work/hold_gate.log 2>&1; \
    tail -3 /work/hold_gate.log; fi; exit \$rc" > "$B/cts.log" 2>&1
echo "cts rc $? $(date -Is)" >> "$B/cts.log"
