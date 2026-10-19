#!/bin/bash
# HBM-NEXT-UNITS-SUDMA2 step 2 (2026-10-19): synthesis AREA of the new row-step control stages (fleet; yosys 0.68 + ASAP7
# RVT TT NLDM, generic flatten + abc; no macros):
#   rowx  ot_hnx_su_rowx  (vmr / vmw / control row step, one per SU quarter, REG 1, whole 2422-b line registered)
#   rowr  ot_hnx_su_rowr  (reducer / RF row class, one per SU quarter, REG 1, 128-b {rf, red} registered)
#   rstep ot_hnx_sfu_rowstep (SFU chain row step, one per SFU, REG 1: io_word + compiler_control registered)
#   bws   ot_hnx_su_wsplit DEFER 1 + bank write mux (the logic ot_hnx_su_bank6_ws adds to the d4g bank tile, macros excluded)
# Run from a bundle root:  tools/hbm_next/hnx_sudma3_synth.sh OUT
set -u
O=$(realpath -m "${1:?OUT}"); mkdir -p "$O"
Y=$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys; [ -x $Y ] || Y=yosys
LIBD=$HOME/.local/opentallas-pdk-asap7/lib/NLDM
LIBS=$(ls $LIBD/asap7sc7p5t_{AO,OA,SIMPLE,INVBUF,SEQ}_RVT_TT_nldm_*.lib 2>/dev/null | grep -v '\.gz$')
LA=""; for l in $LIBS; do LA="$LA -liberty $l"; done
RL=""; for l in $LIBS; do RL="$RL; read_liberty -lib $l"; done
syn(){ # tag top chparam files...
  local t=$1 top=$2 cp=$3; shift 3
  $Y -q -l $O/synth_$t.log -p "$RL; read_verilog -sv -DSYNTHESIS $*; $cp hierarchy -check -top $top; synth -flatten -top $top; dfflibmap $LA; abc $LA; opt_clean; stat $LA" > /dev/null 2>&1
  echo "$t $top rc=$? $(grep -i 'Chip area' $O/synth_$t.log | tail -1) cells=$(grep -E '^ +[0-9]+ +cells$|Number of cells' $O/synth_$t.log | tail -1 | tr -s ' ')" | tee -a $O/area.txt
}
: > $O/area.txt
syn rowx ot_hnx_su_rowx "" rtl/hbm_next/su/ot_hnx_su_rowx.sv &
syn rowr ot_hnx_su_rowr "" rtl/hbm_next/su/ot_hnx_su_rowr.sv &
syn rstep ot_hnx_sfu_rowstep "" rtl/hbm_next/su/ot_hnx_sfu_rowstep.sv &
syn bws ot_hnx_su_wsplit "chparam -set DEFER 1 ot_hnx_su_wsplit;" rtl/hbm_next/su/ot_hnx_su_wsplit.sv &
wait; echo done >> $O/area.txt
