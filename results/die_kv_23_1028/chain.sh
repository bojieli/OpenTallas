#!/bin/bash
# DIE-KV-23 KV RTL event bind chain (tree c + bind b): t1 (stale R8) -> R8 regen -> t2 -> PV column pads on t2 -> b7 (strict)
# -> post checks (V-D-H, v_offset, KV regen_constants + image assets, peer link).  = DIE-KV-15/19 recipe order, paths changed.
set -u
W=/srv/opentallas-scratch2/claude/wt/die-kv-23; R=/srv/opentallas-scratch2/claude/die-kv-23-1028; Q=results/die_kv_23_1028
P=$Q/event/plan.json; RD=physical/die_plan/qwen_kvsys/dcal_rom/bind/position2144b19
cd $W
bind() { O=$1; RC=$2; mkdir -p $O
  if [ ! -s $O/asbuilt.json ]; then echo "$(date) elab $O"; python3 tools/die_plan/bind.py elab $P --asbuilt $RC --out $O --mem 48 > $O/elab.log 2>&1 || { echo ELAB_RC=$? $O; tail -n 5 $O/elab.log; return 4; }; fi
  echo "$(date) bind $O"; python3 tools/die_plan/bind.py bind $P --asbuilt $RC --out $O --mem 48 --strict > $O/bind.log 2>&1; echo BIND_RC=$? $O; head -c 1500 $O/bind.log; echo; }
[ -s $R/bind_t1/bus_groups.json ] || bind $R/bind_t1 $RD/recipe_kv23_t1.json
bash $Q/r8_23.sh $R/bind_t1 $W/$Q/r8_t1 || { echo R8_FAIL; exit 3; }
bind $R/bind_t2 $RD/recipe_kv23_t2.json
python3 physical/die_plan/qwen_kvsys/r8/kv_pv_col_pads.py $R/bind_t2 $Q/r8_t1/qwen_kvsys_r8_landing_bind.json $Q/pv_col_pads_t2.json > $R/colpads_t2.log 2>&1; echo COLPADS_RC=$?; tail -n 5 $R/colpads_t2.log
bind $R/bind7 $RD/recipe_kv23_b7.json
python3 physical/die_plan/qwen_kvsys/r8/kv_pv_v_pads.py check $R/bind7 --json $R/vdh_bind7.json; echo VDH_RC=$?
python3 results/die_kv_15_1028/v_offset_check.py $R/bind7 --json $R/v_offset_bind7.json | head -3; echo VOFF_RC=$?
I=$R/img7
OUT=$I KV_BIND=$R/bind7 QC_BIND=/srv/opentallas-scratch2/claude/die-kv-13-1028/qc_fresh_v3 QC_SRC=$W bash results/kv_native_image_13/run_constants2.sh
OUT=$I python3 results/kv_native_image_13/emit_assets.py; echo EMIT_RC=$?
echo "KV constants: $(grep -c '^\[OK' $I/kv_constants2.log) OK"; grep -v '^\[OK' $I/kv_constants2.log | grep '^\[' | head
I6=/srv/opentallas-scratch2/claude/die-kv-19-1028/img6
diff -rq $I6/assets $I/assets > $R/img_diff_img7.txt; echo IMG_ASSETS_DIFF_RC=$? $(wc -l < $R/img_diff_img7.txt) files differ
bash results/die_kv_23_1028/peer_link.sh $R/bind7 $R/peer_bind7; echo PEER_RC=$?
echo CHAIN_DONE $(date)
