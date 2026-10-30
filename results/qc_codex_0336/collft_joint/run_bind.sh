#!/bin/bash
set -u
QC_BIND_WT=/srv/opentallas-scratch2/claude/wt/codex-qc-collft-bind-1030
QC_BIND_RUN=/srv/opentallas-scratch2/claude/codex-qc-collft-bind-1030
python3 "$QC_BIND_WT/tools/die_plan/bind.py" bind "$QC_BIND_WT/physical/die_plan/qwen_compute/plan_of_record/plan_qc46_collft_boot_prep.json" --out "$QC_BIND_RUN/out" --asbuilt "$QC_BIND_WT/results/qc_codex_0336/collft_joint/asbuilt.json" --strict > "$QC_BIND_RUN/bind2.log" 2>&1
QC_BIND_RC=$?
echo "bind_exit=$QC_BIND_RC"
exit "$QC_BIND_RC"
