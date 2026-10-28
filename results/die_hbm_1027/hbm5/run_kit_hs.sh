#!/bin/bash
# DIE-HBM-5: GRT-only kit with v1c5 + hub W/E split (orient-corrected hso) region trees. usage: run_kit_hs.sh PLANDIR OUTDIR
B=/srv/opentallas-scratch2/claude/die-hbm-5; H=$B/r5/region3/r5/hso; WT=/srv/opentallas-scratch2/claude/wt/die-hbm-5; T=$WT/tools/die_plan
PL=$1; O=$2; mkdir -p $O
echo START $(date) plan=$(sha256sum $PL/die_plan.json | cut -c1-12) src=$(git -C $WT rev-parse --short HEAD)
cd $WT
OT_HS_NO_STA=1 nice python3 $B/kit_hs.py $T $H/map_hubsplit.json $H/hubsplit_report.json $O/map_v1c5_hso.json -- kit $PL/die_plan.json --out $O/kit --region-trees $O/map_v1c5_hso.json
echo KIT rc=$? $(date)
