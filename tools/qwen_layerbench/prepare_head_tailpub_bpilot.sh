#!/usr/bin/env bash
# Derive the Codex B-pilot packet with the rc16 TAILPUB PART1 copy in place of src/015 (same file name, SHA line
# updated): run.sh (unchanged Codex gate, TAILPUB default 0) and run_define.sh (canonical-event define selection).
# usage: prepare_head_tailpub_bpilot.sh <codex-B-pilot-packet> <out-dir>
set -euo pipefail
B=$1; O=$2; R=$(cd "$(dirname "$0")/../.." && pwd)
test ! -e "$O"; cp -a "$B" "$O"; cd "$O"
cp "$R/rtl/physical/a0_rc16_head_tailpub/ot_qwen_w12_matvec_land32.sv" src/015_ot_qwen_w12_matvec_land32.sv
h=$(sha256sum src/015_ot_qwen_w12_matvec_land32.sv | cut -d' ' -f1)
sed -i "s#^[0-9a-f]\{64\}\( \+\*\?src/015_ot_qwen_w12_matvec_land32.sv\)#$h\1#" SHA256SUMS
sha256sum -c SHA256SUMS > /dev/null
cp "$R/tools/qwen_layerbench/run_head_tailpub_define_selection.sh" run_define.sh
echo "packet $O"
