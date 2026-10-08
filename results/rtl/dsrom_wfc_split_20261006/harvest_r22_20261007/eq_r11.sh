#!/bin/bash
# r9: phase 2 (8ce5513b7): LINK_REG + VM_REG + RD_PIPE + SLEW_COPY over the r7 MARGIN set; negatives must FAIL
S=f316f0271; E=/srv/opentallas-scratch/claude/dsrom-wfc-split/eq.sh
K="-DOT_WFC_REC_SRAM=1 -DOT_WFC_UPOS_LWR=1 -DOT_WFC_CONTROL_PIPE=1 -DOT_WFC_CFG_Q=1 -DOT_WFC_PRECOMP=1 -DOT_WFC_IN_DEC=1 -DOT_WFC_TXQ_SLICE=1 -DOT_WFC_RDY_LT=1 -DOT_WFC_FANOUT_COPY=1 -DOT_WFC_MARGIN=1"
K2="$K -DOT_WFC_LINK_REG=1 -DOT_WFC_VM_REG=1 -DOT_WFC_RD_PIPE=1 -DOT_WFC_SLEW_COPY=1 -DOT_WFC_LINK_SEL=1"
S1="-GSOURCE=1 -GLOCKSTEP=0 -GMAXU=866 -GUSERS=866 -GSEED=11 -GCLAT=6 -GPDLY=40"
S0="-GSOURCE=0 -GLOCKSTEP=0 -GSTREAM=1 -GMAXU=866 -GUSERS=866 -GSEED=13 -GNJOBS=20000 -GXWORDS=46 -GRXWORDS=41"
LAT="-GSOURCE=1 -GLOCKSTEP=0 -GMAXU=866 -GUSERS=32 -GSEED=21 -GCLAT=12000 -GPDLY=600 -GPLEN=2 -GGEN=10 -GMAXCYC=100000000"
$E $S r11_s1_all $S1 $K2 &
$E $S r11_s1_all_seed7 $S1 $K2 -GSEED=7 &
$E $S r11_s0_all $S0 $K2 &
$E $S r11_s0_all_seed5 $S0 $K2 -GSEED=5 &
$E $S r11_lat_all $LAT $K2 &
$E $S r11_neg_s1_row2 $S1 $K2 -DOT_WFC_NEG_ROW2 &
$E $S r11_neg_s0_upos $S0 $K2 -DOT_WFC_NEG_UPOS &
$E $S r11_neg_s0_link $S0 $K2 -DOT_WFC_NEG_LINK &
$E $S r11_neg_s1_link $S1 $K2 -DOT_WFC_NEG_LINK &
$E $S r11_neg_s0_vmrd $S0 $K2 -DOT_WFC_NEG_VMRD &
$E $S r11_neg_s1_rdp $S1 $K2 -DOT_WFC_NEG_RDP &
wait
grep -H "EQUIV \(PASS\|FAIL\|STATS\|STREAM\)\|LINK_REG FAIL\|^rc\|build rc" /srv/opentallas-scratch/claude/dsrom-wfc-split/eq/r11_*/run.log > /srv/opentallas-scratch/claude/dsrom-wfc-split/eq/summary_r11.txt
echo done > /srv/opentallas-scratch/claude/dsrom-wfc-split/eq/r11.done
