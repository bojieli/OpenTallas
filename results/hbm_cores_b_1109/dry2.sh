#!/bin/bash
# DIE-KV-97: kit-rtl dry on src_p5 (src_p4 + kit-rtl Plan path fix), plan_p4 + bind5, unchanged asbuilt
set -u
S=/srv/opentallas-scratch3/claude/dkv97_src_p5; P=/srv/opentallas-scratch2/claude/dkv95/plan_p4; B=/srv/opentallas-scratch2/claude/dkv95/bind5
D=/srv/opentallas-scratch2/claude/dkv97/dry2; OV=/srv/opentallas-scratch2/claude/dkv96/dry1/plan_ov
mkdir -p $D; cd $S
for T in ${TYPES:-kv3_hub_Eo kv3_pc__cl254f2e73}; do
  PL=$P/plan_c.json; case $T in kv3_pc*) PL=$OV/plan_c.json;; esac
  rm -rf $D/out/$T; mkdir -p $D/out/$T
  /usr/bin/time -v python3 -I -B tools/die_plan/bind.py kit-rtl $PL --out $B --asbuilt $P/asbuilt.json --type $T --kit $D/out/$T > $D/$T.log 2>&1; echo "$T rc $? $(date)" >> $D/rc.txt
done
