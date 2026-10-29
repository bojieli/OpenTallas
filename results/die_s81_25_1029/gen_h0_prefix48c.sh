#!/bin/bash
set -eu
W=/srv/opentallas-scratch2/claude/wt/die-s81-25-h0src
cd $W
python3 physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py --module dsdv_eng_rr_h0 --recipes results/codex_s81_cores_resume1029/h0_prefix_recipe.json --out /srv/opentallas-scratch2/claude/die-s81-25-cores/h0/kits --suffix prefix48c_d25 --master-slice /srv/opentallas-scratch2/claude/die-s81-25-cores/h0/slices --trial
K=/srv/opentallas-scratch2/claude/die-s81-25-cores/h0/kits/dsdv_eng_rr_h0_prefix48c_d25
python3 -c "import json,shutil,sys; f=json.load(open(sys.argv[1]+\"/freeze.json\")); shutil.copy2(\"physical/die_plan/s81/\"+f[\"pins_file\"], sys.argv[1]+\"/plan_pins.json\")" $K
