#!/bin/bash
# HBM-MU-QUAD-4 keybuf: yosys ASAP7 RVT TT synth of the serialisation logic (inner ot_hnx_idxn_keybuf = blackbox, its
# 34 macros + logic are unchanged), the producer shim and the consumer shim, NB=3.
WT=/srv/opentallas-scratch2/claude/wt/hbm-mu-quad-4-1027; K=$WT/results/hbm_mu_quad_4/keybuf
docker run --rm --memory=16g --cpus=4 -u $(id -u):$(id -g) -v $WT:/wt -w /wt/results/hbm_mu_quad_4/keybuf openroad/orfs:asap7lock bash -c '
L=$(ls /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT*.lib* | head -1); echo SEQLIB $L
for top in ot_hnx_idxn_keybuf_ser ot_hnx_idxn_kb_tx ot_hnx_idxn_kb_rx; do
yosys -q -l synth_$top.log -p "read_verilog -sv -lib /wt/rtl/hbm_next/idxn/ot_hnx_idxn_keybuf.sv; read_verilog -sv /wt/rtl/hbm_next/idxn/ot_hnx_idxn_keybuf_ser.sv; chparam -set NB 3 $top; synth -top $top -flatten; stat" >/dev/null 2>&1
grep -E "Number of cells|_DFF_|DFF" synth_$top.log | tail -n 6 | sed "s/^/$top /"
done'
