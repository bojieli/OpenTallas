#!/bin/bash
# KV-FN-3: same bWc_o3_kv49fn model binary + gate as KV-49-FN / KV-FN-2; harness main = main_kvfn3.cpp (LD_PRELOAD libkvfn3b.so):
# START queued only after the die reports ready (mode status), +HOST_TOKEN_READY_MARGIN 32; no fixed delay.
cd /srv/opentallas-scratch2/claude/kv-fn-3/w_status2
/usr/bin/time -v stdbuf -oL sh -c 'LD_PRELOAD="$0:$LD_PRELOAD" exec "$@"' /srv/opentallas-scratch2/claude/kv-fn-3/libkvfn3b.so /srv/opentallas-scratch2/claude/codex-kvtok-2249/bWc_o3_kv49fn/obj/Vtb_kvslice +PHASE=boot +FRAMES=/srv/opentallas-scratch2/claude/codex-kvtok-2249/vimg_Wc_ofs-2_pinned/frames.hex +EXPECT=/srv/opentallas-scratch2/claude/codex-kvtok-2249/vimg_Wc_ofs-2_pinned/expect.txt +EPOCH=$(cat /srv/opentallas-scratch2/claude/codex-kvtok-2249/vimg_Wc_ofs-2_pinned/epoch.txt) +START_AFTER_SETUP +FAR=1 +VECL=/srv/opentallas-scratch2/claude/codex-kvtok-2249/kvl/probe_kv49fn/vecl +CTX=8192 +POST=2000 +HBM_LOG=16 +HBM_PRELOAD=/srv/opentallas-scratch2/claude/codex-kvtok-2249/kvl/probe_kv49fn/preload.txt +HB=20000 +HOST_TOKEN_WAIT=status +HOST_TOKEN_READY_MARGIN=32 > sim.log 2> time.log
echo "rc=$? $(date)" > probe.rc
