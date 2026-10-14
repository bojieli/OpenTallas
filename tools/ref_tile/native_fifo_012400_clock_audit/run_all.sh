#!/bin/bash
set -euo pipefail
root=/srv/opentallas-scratch/claude/ref_gate/qfd_coll_xfifo_native-20261014-012400
image=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
docker image inspect "$image" > /tmp/native-012400-audit/image_inspect.json
for c in tt ff ss; do
 docker run --rm -v "$root/routes/gate/work/orfs:/work:ro" -v "$root/src:/src:ro" -v /tmp/native-012400-audit:/out "$image" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "/out/audit_$c.tcl" > "/tmp/native-012400-audit/audit_$c.receipt.log" 2>&1
 grep -q "FIXED_NATIVE_PASS $c" "/tmp/native-012400-audit/audit_$c.receipt.log"
done
