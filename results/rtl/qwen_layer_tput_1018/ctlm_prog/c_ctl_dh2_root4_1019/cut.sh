#!/bin/bash
# ROOT4-QWPOST: cut the c_ctl slice (qfd_sys_face + qfd_tt_ctlm_dv + die relays) from the dv2f18dh2 die of record with main 0408184bd RTL
L=/srv/opentallas-scratch/claude/root4-qwpost; cd $L/src
GR='qfd_(rly|rlyh|rlyh0|land|landh|landh0)_.*|qfd_rst_rep(_p8)?'
M="--map /srv/opentallas-scratch/claude/mu-die-qw/dv2f18dh2/chain/port_bind=$L/dh2 --map /srv/opentallas-scratch/claude/mu-die-qw/dv2f18dh2/src=$L/src --map /srv/opentallas-scratch/claude/qwen-split-compute/dv2f18dh2/src=$L/src"
for m in 0 1; do
  O=(); [ $m = 1 ] && O=(--override "tt_ctlm:MUT=1:mutant witness (tt_ctlm RTL calendar one edge late)")
  python3 tools/qwen_layerbench/slice_cut.py --die-v $L/dh2/die.v --bind $L/dh2/port_bind.json --src $L/src $M \
    --master 'qfd_(tt_ctlm_dv|sys_face)' --grow "$GR" --top qwc_slice_ctl "${O[@]}" --out $L/out/c_ctl_m$m > $L/out_cut_m$m.txt 2>&1; echo "cut m$m rc $?"
done
