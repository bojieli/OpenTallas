#!/bin/bash
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
cd /srv/opentallas-scratch2/claude/wt/kv-host-regen-1
python3 physical/die_plan/qwen_kvsys/cores/harden/kv_core_rtl.py --plan /srv/opentallas-scratch2/claude/kv-host-regen-1/pd/hm_r26q5c39.json --type kv3_hub_Wi --out /srv/opentallas-scratch2/claude/kv-host-regen-1/rtl --hr-elab /srv/opentallas-scratch2/claude/kv-host-regen-1/elab/host_elab.json --hr-kit-f /srv/opentallas-scratch2/claude/kv-host-regen-1/kit_rtl/kv3_hub_Wi/kit_rtl.f --hr-part /srv/opentallas-scratch2/claude/kv-host-regen-1/kit_rtl_b3/kv3_hub_Wi/kv3_hub_Wi_part_bound.sv
