#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch/claude/codex-q-obs-unit5-1021
COMMON="qfd_status_obs_hold_chunk.sv qfd_mu_ctx_rx.sv qfd_mu_ctx_rx_obs1.sv qfd_sys_face_mu_dhuser.sv qfd_sys_face_mu_dhuser_obs1.sv qfd_native59_static_service.sv"
iverilog -g2012 -s tb -o positive.vvp $COMMON qfd_native59_static_service_obs1.sv tb.sv > positive_compile.log 2>&1
vvp positive.vvp > positive.log 2>&1
iverilog -g2012 -s tb -o mutant.vvp $COMMON native_wrong_tag_mut.sv tb.sv > mutant_compile.log 2>&1
set +e
vvp mutant.vvp > mutant.log 2>&1
rc=$?
set -e
[ "$rc" -ne 0 ]
grep -q 'actual accepted native completion identity' mutant.log
! grep -q 'original-output differential' mutant.log
cat positive.log
printf 'WRONG_NATIVE_TAG_CAUSAL_MUTANT_REJECTED rc=%s
' "$rc"
