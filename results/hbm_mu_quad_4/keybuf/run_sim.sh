#!/bin/bash
# HBM-MU-QUAD-4 keybuf serialisation: iverilog 12 random equivalence sim, old keybuf vs tx->core->rx, NB = 2 3 4
set -e; WT=/srv/opentallas-scratch2/claude/wt/hbm-mu-quad-4-1027; K=$WT/results/hbm_mu_quad_4/keybuf; cd $K
SRAM=$K/ref_sram_256x256.v; RTL="$WT/rtl/hbm_next/idxn/ot_hnx_idxn_keybuf.sv $WT/rtl/hbm_next/idxn/ot_hnx_idxn_keybuf_ser.sv"
for nb in ${NBS:-2 3 4}; do
 iverilog -g2012 -o sim_nb$nb.vvp -Ptb.NB=$nb -s tb $SRAM $RTL tb_keybuf_ser.sv
 for s in ${SEEDS:-1 2}; do prlimit --as=8000000000 vvp -n sim_nb$nb.vvp +seed=$s | tee sim_nb${nb}_s$s.log | tail -2; done
 iverilog -g2012 -o sp_nb$nb.vvp -Ptb_sp.NB=$nb -s tb_sp $RTL tb_spacing.sv && vvp -n sp_nb$nb.vvp | tee sp_nb$nb.log | tail -1
 rm -f sim_nb$nb.vvp sp_nb$nb.vvp
done
