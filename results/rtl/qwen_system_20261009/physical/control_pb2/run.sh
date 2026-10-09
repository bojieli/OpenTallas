#!/bin/bash
set -euo pipefail
cd /srv/opentallas-scratch/codex/sysctl-pb2-19699b86e
trap 'rc=$?; printf "{\"source\":\"19699b86e\",\"rc\":%s}\n" "$rc" > terminal.json' EXIT
find rtl -type f -print0 | sort -z | xargs -0 sha256sum > source.sha256
python3 tools/qwen_system/emit_sysctl_prompt_read.py > emit.log
find rtl -type f -print0 | sort -z | xargs -0 sha256sum > generated.sha256
cmp source.sha256 generated.sha256
bash rtl/test/qwen_system/run_prompt_sram_pb2_fault.sh fault > fault_campaign.log 2>&1
bash rtl/test/qwen_system/run_ctl_stn_pb2.sh control > control_campaign.log 2>&1
