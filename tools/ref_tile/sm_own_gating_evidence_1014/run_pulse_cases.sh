#!/bin/bash
set -euo pipefail
image=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
for c in tt ff ss; do
 docker run --rm -v /tmp/sm-own-gating-probe:/probe "$image" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "/probe/pulse_$c.tcl" > "/tmp/sm-own-gating-probe/pulse_$c.receipt.log" 2>&1
 grep -q SM_PULSE_RESTORE_PASS "/tmp/sm-own-gating-probe/pulse_$c.receipt.log"
done
