#!/bin/bash
# KV-KITS-21 (2026-10-29): qkd_ahub kit on event27 FINAL (DIE-KV-28 plan_e27f, ahub pins event27/qkd_ahub_pins_r27s.json = r27 snapped by snap_ahub_pins.py) with the
# ck7 RTL (clock_split7.py).  Same generator form as the Codex ck3c kit (hard children, am-g-drop, sigmax M7, util 0.6,
# plan_inst ahub of type kv3_hub_C) + --cts-setup-only --two-mode-grt (kit_modes stage: measured hold by default) + OWNER 12.19 hold
# margin 10 ps.  usage (intel2, this branch): gen_ahub_e27.sh PLAN_DIR KIT_RTL OUT
set -euo pipefail
REPO=$(git rev-parse --show-toplevel)
P=${1:?PLAN_DIR}; KR=${2:?KIT_RTL}; O=${3:?OUT}
H=$REPO/physical/die_plan/qwen_kvsys/cores/harden
cd "$P"   # plan pins_file paths are relative to the plan dir
python3 "$H/gen_core_kit_kv.py" --core-json "$REPO/results/kv_kits_21_1029/askc/ck7/core.json" --plan "$P/plan_e27f_ahubs.json" \
  --out "$O" --kit-rtl "$KR" --hard-children "$H/qkd_ahub_hard_children.json" --am-g-drop --sigmax M7 --util 0.6 \
  --plan-inst ahub --cts-setup-only --two-mode-grt --hold-ff-margin 10
