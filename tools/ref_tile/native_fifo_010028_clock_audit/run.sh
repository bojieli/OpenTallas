#!/bin/bash
set -euo pipefail
root=/srv/opentallas-scratch/claude/ref_gate/qfd_coll_xfifo_native-20261014-010028
docker run --rm -v "$root/routes/gate/work/orfs:/work:ro" -v "$root/src:/src:ro" -v /tmp/native-010028-audit:/out openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /out/audit.tcl > /tmp/native-010028-audit/audit.receipt.log 2>&1
grep -q NATIVE_AUDIT_PASS /tmp/native-010028-audit/audit.receipt.log
