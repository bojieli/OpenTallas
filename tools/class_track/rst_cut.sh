#!/bin/bash
# usage: rst_cut.sh DIE PLAN TREE ELAB|- OUTDIR
DIE=$1; PLAN=$2; TREE=$3; ELAB=$4; OUT=$5
RT=/srv/opentallas-scratch2/claude/rt/current/tools/die_plan
mkdir -p "$OUT"
E=(); [ "$ELAB" != "-" ] && E=(--elab-dir "$ELAB")
python3 -I $RT/derived_drop.py --plan "$PLAN" --tree "$TREE" "${E[@]}" --classes RSTREACH > "$OUT/rst_$DIE.txt" 2>&1
echo "rc=$? rst_$DIE" >> "$OUT/done.txt"
