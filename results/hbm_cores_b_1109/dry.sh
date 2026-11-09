#!/bin/bash
# DIE-KV-96 scope 2: kit-rtl dry from staged src on 2 types, unchanged asbuilt
set -u
cd /srv/opentallas-scratch3/claude/dkv95_src_p4
for T in kv3_pc__cl254f2e73 kv3_hub_Eo; do
  rm -rf /srv/opentallas-scratch2/claude/dkv96/dry0/$T; mkdir -p /srv/opentallas-scratch2/claude/dkv96/dry0/$T
  python3 -I tools/die_plan/bind.py kit-rtl /srv/opentallas-scratch2/claude/dkv95/plan_p4/plan_c.json --out /srv/opentallas-scratch2/claude/dkv95/bind5 --asbuilt /srv/opentallas-scratch2/claude/dkv95/plan_p4/asbuilt.json --type $T --kit /srv/opentallas-scratch2/claude/dkv96/dry0/$T > /srv/opentallas-scratch2/claude/dkv96/dry0/$T.log 2>&1; echo "$T rc $?" >> /srv/opentallas-scratch2/claude/dkv96/dry0/rc.txt
done
