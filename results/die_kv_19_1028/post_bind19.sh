#!/bin/bash
# DIE-KV-19 post-bind checks on bind6 (wired existing checks, COORD 20:10 (6) + TOK-QK-PEER-1 ruling 20:4x):
#   V-D-H (kv_pv_v_pads check) + KV-15 v_offset + KV regen_constants / image assets (run_constants2 + emit_assets, = DIE-KV-16)
#   + image byte-compare vs img5 + the QC<->KV pair image derived from both current binds (peer_link.sh).
# count_align_bind: the clock event is unchanged (plan clock/ports/lanes/partitions identical to DIE-KV-15; only pv contents
# + kv3_pv_pair pins differ) -> the gate of record st_fall_bind.log stands (copied to logs/).
set -u
W=/srv/opentallas-scratch2/claude/wt/die-kv-16; R=/srv/opentallas-scratch2/claude/die-kv-19-1028; B=${1:-$R/bind6}; I=${2:-$R/img6}
cd $W
python3 physical/die_plan/qwen_kvsys/r8/kv_pv_v_pads.py check $B --json $R/vdh_$(basename $B).json; echo VDH_RC=$?
python3 results/die_kv_15_1028/v_offset_check.py $B --json $R/v_offset_$(basename $B).json | head -3; echo VOFF_RC=$?
OUT=$I KV_BIND=$B QC_BIND=/srv/opentallas-scratch2/claude/die-kv-13-1028/qc_fresh_v3 QC_SRC=$W bash results/kv_native_image_13/run_constants2.sh
OUT=$I python3 results/kv_native_image_13/emit_assets.py; echo EMIT_RC=$?
echo "KV constants: $(grep -c '^\[OK' $I/kv_constants2.log) OK"; grep -v '^\[OK' $I/kv_constants2.log | grep '^\[' | head
I5=/srv/opentallas-scratch2/claude/die-kv-16-1028/img5
diff -rq $I5/assets $I/assets > $R/img_diff_$(basename $I).txt; echo IMG_ASSETS_DIFF_RC=$? $(wc -l < $R/img_diff_$(basename $I).txt) files differ
cmp $I5/kv_constants2.svh $I/kv_constants2.svh && echo KV_CONSTANTS_SVH_SAME
bash results/die_kv_19_1028/peer_link.sh $B $R/peer_$(basename $B)
