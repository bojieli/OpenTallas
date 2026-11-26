#!/bin/bash
# usage: pre_cut2.sh DIE PLAN TREE ASBUILT|- CHECKS OUTDIR   (pre_cut.sh + plan sha record)
DIE=$1; PLAN=$2; TREE=$3; ASB=$4; CHECKS=$5; OUT=$6
mkdir -p "$OUT"
RT=/srv/opentallas-scratch2/claude/rt/current/tools/die_plan
A=(); [ "$ASB" != "-" ] && A=(--asbuilt "$ASB")
sha256sum "$PLAN" | cut -c1-12 > "$OUT/$DIE.sha"
OT_PLAN_ADVISORY_JOBS=4 python3 -I $RT/plan_advisory.py --plan "$PLAN" --tree "$TREE" "${A[@]}" --checks "$CHECKS" --all --json "$OUT/$DIE.json" > "$OUT/$DIE.txt" 2>&1
echo "rc=$? $DIE" >> "$OUT/done.txt"
