#!/usr/bin/env bash
set -euo pipefail
# Run through ot-run in an ORFS image. Source commits are required; no unstaged RTL.
repo=$1; old=$2; new=$3; out=$4
mkdir -p "$out"
for spec in "old:$old" "new:$new"; do
 name=${spec%%:*}; commit=${spec#*:}
 git -C "$repo" show "$commit:physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_tree13.sv" > "$out/$name.sv"
done
for spec in 'physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_scale13.sv' 'rtl/hdc/ot_hdc_delay.sv'; do
 git -C "$repo" show "$new:$spec" > "$out/${spec##*/}"
done
cp "$(dirname "$0")/build.py" "$out/build.py"
python3 "$out/build.py"
cd "$out"
yosys -s new.ys > new.log 2>&1
if yosys -s mut.ys > mut.log 2>&1; then echo 'FAIL: format inversion mutant survived';exit 1;fi
sed 's/-seq 20/-seq 2 -tempinduct -maxsteps 20/' new.ys > induct.ys
yosys -s induct.ys > induct.log 2>&1
echo 'PASS: exact-source format-valid equivalence, induction, inversion control'
