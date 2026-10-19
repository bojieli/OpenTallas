#!/bin/bash
# HBM-NEXT-UNITS-SUDMA2 2026-10-19: synthesis AREA DELTA (fleet; yosys 0.68 + ASAP7 RVT TT NLDM, generic flatten + abc,
# no macros in these blocks) of the two new mechanisms against their d4g / SUDMA references:
#   ws1 / ws0   ot_hnx_su_wsplit DEFER 1 (an HI = 0 bank: deferral register + muxes) / DEFER 0 (an HI = 1 bank)
#   am8 / am64  ot_hnx_argmax_static_rows (1 sector an edge, engine LP 8) / ot_hnx_argmax_wide_rows (8 sectors, LP 64)
# Run from a bundle root:  tools/hbm_next/hnx_sudma2_synth.sh OUT
set -u
O=$(realpath -m "${1:?OUT}"); mkdir -p "$O"
Y=$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys; [ -x $Y ] || Y=yosys
LIBD=$HOME/.local/opentallas-pdk-asap7/lib/NLDM
LIBS=$(ls $LIBD/asap7sc7p5t_{AO,OA,SIMPLE,INVBUF,SEQ}_RVT_TT_nldm_*.lib 2>/dev/null | grep -v '\.gz$')
LA=""; for l in $LIBS; do LA="$LA -liberty $l"; done
RL=""; for l in $LIBS; do RL="$RL; read_liberty -lib $l"; done
AM=(physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_m.sv physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_value_m.sv
 physical/hbm_mtp/rtl/ot_dshbm_argmax_m.sv rtl/gpu/ot_gpu_fadd.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
 rtl/hdc/ot_hdc_prefix.sv)
syn(){ # tag top chparam files...
  local t=$1 top=$2 cp=$3; shift 3
  $Y -q -l $O/synth_$t.log -p "$RL; read_verilog -sv -DSYNTHESIS $*; $cp hierarchy -check -top $top; synth -flatten -top $top; dfflibmap $LA; abc $LA; opt_clean; stat $LA" > /dev/null 2>&1
  echo "$t $top rc=$? $(grep -i 'Chip area' $O/synth_$t.log | tail -1) cells=$(grep -E '^ +[0-9]+ +cells$|Number of cells' $O/synth_$t.log | tail -1 | tr -s ' ')" | tee -a $O/area.txt
}
: > $O/area.txt
syn ws1 ot_hnx_su_wsplit "chparam -set DEFER 1 ot_hnx_su_wsplit;" rtl/hbm_next/su/ot_hnx_su_wsplit.sv &
syn ws0 ot_hnx_su_wsplit "chparam -set DEFER 0 ot_hnx_su_wsplit;" rtl/hbm_next/su/ot_hnx_su_wsplit.sv &
syn am8 ot_hnx_argmax_static_rows "" rtl/hbm_next/argmax/ot_hnx_argmax_static_rows.sv "${AM[@]}" &
syn am64 ot_hnx_argmax_wide_rows "" rtl/hbm_next/argmax/ot_hnx_argmax_wide_rows.sv "${AM[@]}" &
wait; echo done >> $O/area.txt
