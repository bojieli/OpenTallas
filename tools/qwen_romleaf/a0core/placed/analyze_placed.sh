#!/bin/bash
# analyze_placed.sh nk|nl : placed (3_place) density, cuts, hops, picture -- read-only on the run
set -euo pipefail
K=$1; P=/srv/opentallas-scratch2/claude/qc/a0v8place; RUN=$P/run_${K}_v8b/a0cv8b_${K}_place; SRC=$P/src_2dfc218
A=$P/ana_${K}; mkdir -p $A
ODB=$(ls $RUN/work/orfs/results/asap7/*/base/3_place.odb)
B=$(dirname $ODB)
docker run --rm --memory 16g -e ODB=/b/3_place.odb -e OUT=/a/inst.tsv -v $B:/b:ro -v $A:/a -v $P:/p:ro openroad/orfs:latest \
  /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /p/dump_inst.tcl > $A/dump.log 2>&1
cd $P
PLACE=$SRC/physical/ref_tile/qfd_tile_${K}_a0cv8/place.tcl V7POS=$A/inst.tsv DIAGMIN=300 ./rundiag.sh $K $P/regions_empty.tcl ${K}_placed \
  --diag "g_hd\.(g_tx9\.(u_qlr2|tc\[|g_r\[1\]\.u_tx/)|g_out9\.u_ql|g_lrr)|u_me\.fault_q" --moves "$( [ $K = nl ] && cat $P/nl_tout_moves.json || echo [])" > $A/budget.log 2>&1
cp out/${K}_placed.json $A/budget.json
python3 render_placed.py $K $A/inst.tsv $SRC/tools/qwen_romleaf/repack/qfd_tile_${K}_a0v8_regions.tcl $A/budget.json $SRC/tools/qwen_romleaf/a0core/a0c8_${K}_taps.json \
  $A/budget.log $A/qfd_tile_${K}_a0cv8b_placed "A0 ${K^^} v8b (claude/qc-a0v8-1024@2dfc218c4c) ORFS 3_place (PLACE-ONLY, no CTS/GRT)" > $A/render.log 2>&1
cp $(ls $RUN/work/orfs/qrl_parent_regions.tsv $RUN/work/orfs/*/qrl_parent_regions.tsv 2>/dev/null | head -1) $A/ 2>/dev/null || find $RUN/work -name qrl_parent_regions.tsv -exec cp {} $A/ \; 
echo done $K
