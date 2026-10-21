#!/bin/bash
# S81-DIE11 10-20: plan-level STAND-IN GRT diagnostic (dv_diecase --bind standin) with M8 signals + M8 repeater RC,
# for geometry comparison 116-frame idx3 (in-line readers; RTL bind owed) vs 122-frame idxrd 0. NOT a die result.
# usage: run_sgrt.sh SRC_SHA IDXRD K TAG
set -uo pipefail
D=$(cd "$(dirname "$0")" && pwd)
SRC=${1:?src}; IDX=${2:?idxrd}; K=${3:?vcol}; TAG=${4:?tag}
export OT_GIT_DIR=/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git; G=$OT_GIT_DIR
export OT_DIE_REPAIR_CORRIDOR=1
BASE=results/arch/s81_dv_1016
W=$D/$TAG; mkdir -p "$W"; S=$W/steps.log
git --git-dir=$G cat-file -e "$SRC^{commit}" 2>/dev/null || git --git-dir=$G fetch -q origin "$SRC" || git --git-dir=$G fetch -q origin
rm -rf "$W/src"; mkdir -p "$W/src"
git --git-dir=$G archive "$SRC" tools $BASE results/arch/die_reach_1016.json | tar -xf - -C "$W/src" || exit 2
cd "$W/src" || exit 2
args=(--layout p4 --tier-w 276 --lanes 4 --p4l --p4h-drop 6 --frame-w 1436.832 --mu 1 --pathfix --lk-slots $BASE/p4l_lkcol/plan.json --ctrl-view-size 388.8 324 --array-y-shift 86.4 --idxrd "$IDX" --rsv-vcol "$K")
python3 tools/s81_dv/dv_plan.py "${args[@]}" --revision dv-p4l-mu1-$TAG --out "$W/plan" > "$W/plan.log" 2>&1; RC=$?
echo "SRC $SRC IDXRD $IDX K $K PLAN_RC $RC $(date)" >> "$S"; [ $RC -eq 0 ] || exit $RC
python3 -c "import json;f=json.load(open('$W/plan/plan.json'))['facts'];print('PLAN_FACTS n_frames',f.get('n_frames'),'rom_slots',f.get('rom_slots'),'worst_cut',f.get('worst_cut'),'relays',f.get('relays'),'bit_mm',f.get('bit_mm'))" >> "$S"
python3 tools/s81_dv/dv_diecase.py --plan "$W/plan/plan.json" --out "$W/case" --die-repair --dieflow-ref "$SRC" --signal-top-layer M8 > "$W/case_gen.log" 2>&1
RC=$?; echo "CASE_RC $RC standin M8" >> "$S"; [ $RC -eq 0 ] || exit $RC
grep -o "signal M2-M[0-9] -clock M5-M9\|set_wire_rc -signal -layer M[0-9]" "$W/case/run.tcl" | sort -u >> "$S"; grep -o "rc_layer {M[0-9]}" "$W/case/die_repeaters_step.tcl" | sort -u >> "$S"
CPUS=16 MEMG=110 bash "$W/case/run.sh"; echo "RUN_RC $TAG $? $(date)" >> "$S"
