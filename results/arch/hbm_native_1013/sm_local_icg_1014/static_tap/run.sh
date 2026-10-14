#!/bin/bash
set -euo pipefail
if [[ ! -f SEQ/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib ]]; then tar -xzf frozen_inputs.tar.gz; fi
image=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
for c in tt ff ss; do
 C=${c^^}
 docker run --rm "$image" zcat /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_${C}_nldm_220122.lib.gz > "INVBUF_${c}.lib"
 docker run --rm -v "$PWD:/probe" "$image" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "/probe/probe_$c.tcl" > "probe_$c.receipt.log" 2>&1
 cat "probe_$c.receipt.log"
 grep -q "SM_GATING_PASS $c" "probe_$c.receipt.log"
done
