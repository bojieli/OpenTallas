#!/bin/bash
set -uo pipefail
D=/srv/opentallas-scratch2/claude/codex-kvtok-2249
export IMG=$D/vimg_Wc_ofs-2_pinned
export KV_DCAL_VIAMAP=$D/dcal_Wc_ofs-2_pinned/kv_dcal_r0_c0.viamap.hex
export PHY_MAP=$D/bWc_o2/phy_slice_map.json
export CTX=8192 POST=$3
[ -z "${4:-}" ] || export MUT_KSWAP=$4
bash $D/compiler_root2/tools/qwen_layerbench/kv_dieslice/run_kvl.sh "$1" /srv/opentallas-scratch2/claude/tok-kv-2-1028/vec $D/kvl "$2" d0_g0
rc=$?; printf 'run_kvl rc=%s %s\n' "$rc" "$(date)" >$D/kvl/$2.rc
exit $rc
