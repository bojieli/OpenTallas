#!/bin/bash
# render93.sh KIT LABEL(place|grt|route) ODB_RELATIVE_NAME OUTDIR
K=$1; L=$2; ODBN=$3; O=$4
mkdir -p "$O"
R=$(ls -d "$K"/run/results/asap7/*/base | head -1); RIN=${R#$K}
T=$(ls -d /srv/opentallas-scratch3/claude/die-hbm-93-open/tools_fn/physical/common_flow)
docker run --rm --memory=12g --cpus=2 -e QT_QPA_PLATFORM=offscreen -e XDG_RUNTIME_DIR=/tmp -e OT_LR_ODB="/work$RIN/$ODBN" -e OT_LR_OUT=/out -e OT_LR_LABEL="$L" -e OT_LR_TOOLS=/tools -e OT_LR_SMELL_TIMEOUT=200 -v "$K":/work:ro -v "$O":/out -v "$T":/tools:ro openroad/orfs:asap7lock bash -c 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; cd /out; timeout 400 openroad -no_splash -no_init -threads 1 -gui /tools/layout_render.tcl </dev/null >/out/render.log 2>&1; echo rc=$?'
cat "$O"/smells.one 2>/dev/null | cut -c1-260; ls "$O"
