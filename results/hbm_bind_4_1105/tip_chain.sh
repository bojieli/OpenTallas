set -u
R=/srv/opentallas-scratch2/claude/hbm-bind-4; W=$R/tip; O=$R/e2
M=$W/physical/die_plan/hbm/bind/d44v/inputs/map_recovered.json
mkdir -p $O/dce $O/norm $O/fus
python3 -I $W/tools/hbm_b2/dead_scorer_loop_index.py $O/out/asbuilt.json --out $O/dce/asbuilt.json --receipt $O/dce/receipt.json 2>&1 | tail -3 | cut -c1-300; echo DCE ${PIPESTATUS[0]}
python3 $W/results/hbm_bind_4_1029/normalize_mem.py $O/dce/asbuilt.json --out $O/norm/asbuilt.json --receipt $O/norm/receipt.json --map-in $M --map-out $O/norm/map_norm.json 2>&1 | tail -4 | cut -c1-300; echo NORM ${PIPESTATUS[0]}
python3 $W/tools/hbm_b2/fused_lower_tree_splice.py splice $O/norm/asbuilt.json $O/fus/asbuilt.json $O/fus/receipt.json 2>&1 | tail -3 | cut -c1-300; echo FUS ${PIPESTATUS[0]}
