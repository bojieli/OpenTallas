#!/bin/bash
set -e
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
cd /srv/opentallas-scratch2/claude/wt/kv-host-regen-1/physical/die_plan/qwen_kvsys
python3 -c "
import sys; sys.path.insert(0, \".\"); sys.path.insert(0, \"/srv/opentallas-scratch2/claude/wt/kv-host-regen-1/tools/die_plan\")
import core_pins_hr as C; from pathlib import Path
print(C.leaf_module(\"/srv/opentallas-scratch2/claude/kv-host-regen-1/kit_rtl_b3/kv3_hub_Wi/kv3_hub_Wi_part_bound.sv\")[0], C.leaf_params(\"/srv/opentallas-scratch2/claude/kv-host-regen-1/kit_rtl_b3/kv3_hub_Wi/kv3_hub_Wi_part_bound.sv\"))
print(C.elaborate(\"/srv/opentallas-scratch2/claude/kv-host-regen-1/kit_rtl/kv3_hub_Wi/kit_rtl.f\", \"/srv/opentallas-scratch2/claude/kv-host-regen-1/kit_rtl_b3/kv3_hub_Wi/kv3_hub_Wi_part_bound.sv\", Path(\"/srv/opentallas-scratch2/claude/kv-host-regen-1/elab\")))
"
