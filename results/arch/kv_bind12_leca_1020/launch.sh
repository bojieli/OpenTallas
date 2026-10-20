#!/bin/bash
# KV-BIND12-LECA 10-20: route A standard LEC of the EXISTING closed views the die places (unpinned ot-run; data staged on ep5+ep6)
D=/srv/opentallas-scratch/claude/kv-bind12-leca-1020
LG=/home/ubuntu/artifacts/kv-bind12-leca-1020/logs
T=tools/qwen_kv_die/kv_leaf_lec.py
go(){ tag=$1$SUF; shift; nohup /home/ubuntu/bin/ot-run --mem 48 --threads 2 --dir $D -- python3 $T --work w_$tag --out $tag.lec.json "$@" > $LG/$tag.otrun.log 2>&1 & echo "$tag $!"; }
L8='--src lane8/src --top ot_qkh_lane8 --physical-json lane8/physical.json --gate lane8/6_final.v --gate-top ot_qkh_lane8 --reset-cycles 16'
KT='--src ktreelk/src --top ot_qkh_ktree_lk --physical-json ktreelk/physical.json --gate ktreelk/6_final.v --gate-top ot_qkh_ktree_lk --reset-cycles 16'
PJ='--src pvjoin/src --top ot_qwen_tp8_pv_join_t --physical-json pvjoin/physical.json --gate pvjoin/6_final.v --gate-top ot_qwen_tp8_pv_join_t --reset-cycles 16'
for x in "$@"; do case "$x" in
lane8)   go lane8_pos   $L8 --params '{"ADD_LAT":7,"LTW":12}' ;;
lane8c)  go lane8_al6   --expect fail $L8 --params '{"ADD_LAT":6,"LTW":12}' ;;
ktree)   go ktreelk_pos $KT --params '{"ADD_LAT":7,"MUL_LAT":6,"MUT":0,"SCALE":1035273459}' ;;
ktreec)  go ktreelk_sc1 --expect fail $KT --params '{"ADD_LAT":7,"MUL_LAT":6,"MUT":0,"SCALE":1035273458}' ;;
pvjoin)  go pvjoin_pos  $PJ --params '{"J_LAT":7,"MUT":0,"RESET_PIN":1}' ;;
pvjoinc) go pvjoin_mut1 --expect fail $PJ --params '{"J_LAT":7,"MUT":1,"RESET_PIN":1}' ;;
esac; done
# lane8h: same closed sources but rtl/hdc/ot_hdc_fp32_mul_lat.sv at the branch HEAD (changed since e5e8e058b; not instantiated
# by ot_qkh_lane8) so the receipt's worktree-source check matches; ep5 only (lane8h staged there)
L8H='--src lane8h/src --top ot_qkh_lane8 --physical-json lane8h/physical.json --gate lane8h/6_final.v --gate-top ot_qkh_lane8 --reset-cycles 16'
for x in "$@"; do case "$x" in
lane8h)  go lane8h_pos  $L8H --params '{"ADD_LAT":7,"LTW":12}' ;;
lane8hc) go lane8h_al6  --expect fail $L8H --params '{"ADD_LAT":6,"LTW":12}' ;;
esac; done
# ktree_lk fallback engine (dprove default >40 min): partitioned &scorr + scorr + CEC (the engine that closed KV-LEC8 lane8 nc32c)
KTP="$KT --timeout 43200 --abc-script"
for x in "$@"; do case "$x" in
ktreep)  go ktreelk_part $KTP 'read_aiger lec.aig; print_stats; strash; &get; &scorr -F 4 -C 1000 -p -S 2000 -v; &put; dc2; scorr -F 2; dc2; print_stats; pdr -v -T 36000' --params '{"ADD_LAT":7,"MUL_LAT":6,"MUT":0,"SCALE":1035273459}' ;;
esac; done
for x in "$@"; do case "$x" in
ktreep2) go ktreelk_part2 $KTP 'read_aiger lec.aig; print_stats; strash; &get; &scorr -F 4 -C 1000 -p -S 2000 -v; &put; dc2; scorr -F 2; dc2; print_stats; dprove -v -T 3600' --params '{"ADD_LAT":7,"MUL_LAT":6,"MUT":0,"SCALE":1035273459}' ;;
esac; done
for x in "$@"; do case "$x" in
ktreep2c) go ktreelk_sc1_part2 --expect fail $KTP 'read_aiger lec.aig; print_stats; strash; &get; &scorr -F 4 -C 1000 -p -S 2000 -v; &put; dc2; scorr -F 2; dc2; print_stats; dprove -v -T 3600' --params '{"ADD_LAT":7,"MUL_LAT":6,"MUT":0,"SCALE":1035273458}' ;;
esac; done
