#!/bin/bash
# HBM-STREETS-3 KIT: shared kit preflight on one generated C18 kit (receipt never overwritten)
k=${1%/}; n=$(basename $k); D=/srv/opentallas-scratch2/claude/hbm-streets3-1027/kits/preflight
[ -f $D/$n.json ] && exit 0; [ -f $k/freeze.json ] || exit 0
cd /srv/opentallas-scratch2/claude/wt/hbm-streets3-kits-1027/tools/die_plan
timeout 1200 python3 kit_preflight.py --plan-dir /srv/opentallas-scratch2/claude/hbm-streets2-1027/c18 --out $D/$n.json $k > $D/$n.txt 2>&1
echo "$n $(head -1 $D/$n.txt)"
