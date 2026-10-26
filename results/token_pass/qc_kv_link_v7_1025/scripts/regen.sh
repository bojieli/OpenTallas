#!/bin/bash
set -u
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
cd /srv/opentallas-scratch2/claude/wt/tok-qk-xd2
python3 tools/die_plan/regen_constants.py --die qwen_compute --bound /srv/opentallas-scratch2/claude/tok-qk-xd2/qc_v7_final --peer /srv/opentallas-scratch2/claude/codex-kv-bind-bank-2144/b19 --src-root /srv/opentallas-scratch2/claude/wt/tok-qk-xd2 --out-json /srv/opentallas-scratch2/claude/tok-qk-xd2/constants_v7_peer_b19.json > /srv/opentallas-scratch2/claude/tok-qk-xd2/regen_v7_peer_b19.log 2>&1; echo rc=$? >> /srv/opentallas-scratch2/claude/tok-qk-xd2/regen_v7_peer_b19.log
python3 tools/die_plan/regen_constants.py --die qwen_kvsys --bound /srv/opentallas-scratch2/claude/codex-kv-bind-bank-2144/b19 --src-root /srv/opentallas-scratch2/claude/wt/tok-qk-xd2 --out-json /srv/opentallas-scratch2/claude/tok-qk-xd2/constants_kv_b19.json > /srv/opentallas-scratch2/claude/tok-qk-xd2/regen_kv_b19.log 2>&1; echo rc=$? >> /srv/opentallas-scratch2/claude/tok-qk-xd2/regen_kv_b19.log
