#!/bin/bash
# TOK-QW-5: whole-QC frontend bisection (verilator --json-only, top = reduced qwen_compute_bound_top copy)
set -uo pipefail
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
V=$1; R=/srv/opentallas-scratch2/claude/tok-qk-2/stage1; C=/srv/opentallas-scratch2/claude/tok-qw-5/bisect/$V; cd $R
echo "START $(date -Is)" >$C/status
/usr/bin/time -v -o $C/json.time verilator --json-only --json-only-output $C/tree.json --json-only-meta-output $C/meta.json \
  -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --x-assign 0 --x-initial 0 --Mdir $C/obj \
  $(cat defines.f) +define+OT_S6_SIM $(cat incdirs.f) +incdir+../veh0 +incdir+../qc59q --top-module qwen_compute_bound_top \
  $(grep -v "qfd_sys_face_lctx3_core.sv\|qfd_dv_head_safe1.sv\|bound/rtl/qwen_compute_bound_top.sv" files.f) $C/top.sv ../qc59q/qfd_sys_face_lctx3_core.sv ../qc59q/qfd_sysface_cseq_single.sv ../qc59q/qfd_dv_head_safe1.sv >$C/json.log 2>&1
rc=$?; echo "JSON_RC=$rc $(date -Is) $(grep -o "Maximum resident set size (kbytes): [0-9]*" $C/json.time) $(grep -o "Elapsed.*" $C/json.time) $(ls -la $C/tree.json 2>/dev/null | awk "{print \$5}")" >>$C/status
rm -f $C/tree.json
exit $rc
