#!/bin/bash
# KV-ATTN7 10-20: standard LEC of the CLOSED attention rv5 view (qkd_kvs_attn_rv5-rv5-2cdc6bb28) at the die params (unpinned ot-run)
D=/srv/opentallas-scratch/claude/kv-attn7-1020
LG=/home/ubuntu/artifacts/kv-attn7-1020/logs
T=tools/qwen_kv_die/kv_leaf_lec.py
go(){ tag=$1; shift; nohup /home/ubuntu/bin/ot-run --mem 48 --threads 2 --dir $D -- python3 $T --work w_$tag --out $tag.lec.json "$@" > $LG/$tag.otrun.log 2>&1 & echo "$tag $!"; }
AT='--wrapper attn/ot_rst_land_wrapper.v --src attn/src --top qkd_kvs_attn_fl --physical-json attn/physical.json --gate attn/6_final.v --gate-top qkd_kvs_attn_fl --clock ck --reset-cycles 16'
P='{"RETIRE_STATIC":1,"STATUS_DELAY":213}'; PM='{"RETIRE_STATIC":1,"STATUS_DELAY":212}'
PS='read_aiger lec.aig; print_stats; strash; &get; &scorr -F 4 -C 1000 -p -S 2000 -v; &put; dc2; scorr -F 2; dc2; print_stats; dprove -v -T 3600'
for x in "$@"; do case "$x" in
pos)   go attn_w_pos $AT --params "$P" ;;
mut)   go attn_w_sd212 --expect fail $AT --params "$PM" ;;
part)  go attn_w_part $AT --timeout 43200 --abc-script "$PS" --params "$P" ;;
partc) go attn_w_sd212_part --expect fail $AT --timeout 43200 --abc-script "$PS" --params "$PM" ;;
mut1)  go attn_w_mut1 --expect fail $AT --params '{"MUT":1,"RETIRE_STATIC":1,"STATUS_DELAY":213}' ;;
esac; done
