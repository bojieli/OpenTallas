#!/bin/bash
# TOK-DS 10-24: fc31 per-layer cut vehicles from the recovered fc30 cuts (die fc31 35ba1ef7 = cap30 64d4be888 + 59 chained-frame
# reset stations, S81-P9-FC). Each fc30 cut slice_top gets the fc31 die delta via results/rtl/s81_chaincal_fc31_1023/cut_3S_ctl/
# patch_cut.py (station lines byte-exact from the fc31 die); kits = fc30 kits with only src/top/slice_top.sv replaced (tb is
# port-only, unchanged). Then the die tree (mk_tree) on fc31 + cap30 GEN plan/land.
# Usage: prep_fc31.sh <worktree> <run dir>     (inputs: /srv/opentallas-scratch/claude/{stw-s81d-tok,s81-p9-fc-1023,stw-s81c-cap30})
set -eu
T=$(realpath $1); W=$(realpath -m $2); S=/srv/opentallas-scratch/claude
C30=$S/stw-s81d-tok/fc30/cuts; F31=$S/s81-p9-fc-1023/fc31; G=$S/stw-s81c-cap30/gen-main
mkdir -p $W/cuts
sha256sum $F31/die.v $G/plan.json $G/land.json > $W/inputs.sha256
for c in cut_0S cut_0N cut_7 cut_3S_ctl; do
  rm -rf $W/cuts/$c $W/cuts/K_$c
  cp -a $C30/$c $W/cuts/$c; cp -a $C30/K_$c $W/cuts/K_$c
  python3 $T/results/rtl/s81_chaincal_fc31_1023/cut_3S_ctl/patch_cut.py $C30/$c/slice_top.sv $F31/die.v \
    $F31/frame_chain_reset_v2.json $W/cuts/$c/slice_top.sv > $W/cuts/$c.patch.json
  cp $W/cuts/$c/slice_top.sv $W/cuts/K_$c/src/top/slice_top.sv
  cp $T/tools/s81_dv/run_dv_slice.sh $W/cuts/K_$c/run_dv_slice.sh
  echo "$c patched: $(cat $W/cuts/$c.patch.json | python3 -c 'import json,sys; d=json.load(sys.stdin); print(len(d), "frames", sum(x["stations_added"] for x in d), "stations")') slice_top $(sha256sum $W/cuts/$c/slice_top.sv | cut -c1-8) (fc30 $(sha256sum $C30/$c/slice_top.sv | cut -c1-8))"
done
cd $T && python3 tools/s81_dv/tokfunc/mk_tree.py --die-v $F31/die.v --plan $G/plan.json --land $G/land.json --out $W/tree_fc31 --tag fc31 > $W/mk_tree.log 2>&1
echo "MK_TREE rc $? $(tail -1 $W/mk_tree.log)"
