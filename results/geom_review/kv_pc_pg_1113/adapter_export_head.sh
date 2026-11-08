#!/bin/bash
cd /
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-kv-types-1113-src
D=/srv/opentallas-scratch2/claude/codex-kv-types-1113/pc_pg
python3 -I "$R/tools/autopilot/export_view.py" --kit /srv/opentallas-scratch3/claude/dkv78/hhp/k4u/i1 --base /srv/opentallas-scratch3/claude/dkv78/hhp/k4u/i1/run/results/asap7/hc_qkd_kvs_pcc_h_head_p__293_76x267_84/base --signoff /srv/opentallas-scratch3/claude/auto-resign/qwen_kvsys/qkd_kvs_pcc_h_head_p__flow-20261106-c-kv__2a7cab7f/signoff/signoff.json --out "$D/views" --die qwen_kvsys --abstract-lef "$D/qkd_kvs_pcc_h_head_p.lef" --abstract-odb /srv/opentallas-scratch3/claude/dkv78/hhp/k4u/i1/run/results/asap7/hc_qkd_kvs_pcc_h_head_p__293_76x267_84/base/6_final.odb --note "PRIVATE signed-native exact-shape PG-access form; one-target PDN negative/positive control passed; no global publication or adoption"
