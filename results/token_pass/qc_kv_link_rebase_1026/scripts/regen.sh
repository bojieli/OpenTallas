#!/bin/bash
# TOK-QK-XD3 10-26: regen_constants (claude/tok-qk-kvchk2-1026@aac29eda2d, pc833 group) on the binds used:
#  QC = v7 final strict bind (codex/qc-phase-2209@13f33606a) with KV peer b23h2; KV = b23h2 (claude/tok-kv-b23h-1026@c6602a6ae8)
set -u
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
X=/srv/opentallas-scratch2/claude/tok-qk-xd3; T=$X/kvchk2_src; KB=/srv/opentallas-scratch2/claude/tok-kv-b23h/b23h2
cd $T
python3 tools/die_plan/regen_constants.py --die qwen_compute --bound $X/qc_v7_final --peer $KB --src-root /srv/opentallas-scratch2/claude/wt/tok-qk-xd3 --out-json $X/constants/constants_v7_peer_b23h2.json > $X/constants/regen_v7_peer_b23h2.log 2>&1; echo rc=$? >> $X/constants/regen_v7_peer_b23h2.log
python3 tools/die_plan/regen_constants.py --die qwen_kvsys --bound $KB --src-root $X/b23h_src --kv-image /srv/opentallas-scratch2/claude/tok-qk-kvimg19/img --out-json $X/constants/constants_kv_b23h2.json > $X/constants/regen_kv_b23h2.log 2>&1; echo rc=$? >> $X/constants/regen_kv_b23h2.log
python3 tools/die_plan/regen_constants.py --die qwen_kvsys --bound $KB --src-root $X/b23h_src --out-json $X/constants/constants_kv_b23h2_noimg.json > $X/constants/regen_kv_b23h2_noimg.log 2>&1; echo rc=$? >> $X/constants/regen_kv_b23h2_noimg.log
exit 0
