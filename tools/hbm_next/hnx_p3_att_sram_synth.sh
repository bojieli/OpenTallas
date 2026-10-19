#!/bin/bash
# HBM-NEXT-P3-UNITS (2026-10-19, owner P3 decision 0le): synthesis AREA of the shared PV merge tile ot_hnx_att4_spvm at
# NL = 3 (P3 production) and NL = 4 (old P4, same flow = the ratio applied to the gated P4 figure); yosys 0.68 + ASAP7
# RVT TT NLDM, generic flatten + abc,18 hard SRAM blackboxes excluded from standard cell area.  Run from a bundle root:  hnx_p3_att_synth.sh OUT
set -u
O=$(realpath -m "${1:?OUT}"); mkdir -p "$O"
Y=$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys; [ -x $Y ] || Y=yosys
LIBD=$HOME/.local/opentallas-pdk-asap7/lib/NLDM
LIBS=$(ls $LIBD/asap7sc7p5t_{AO,OA,SIMPLE,INVBUF,SEQ}_RVT_TT_nldm_*.lib 2>/dev/null | grep -v '\.gz$')
LA=""; for l in $LIBS; do LA="$LA -liberty $l"; done
RL=""; for l in $LIBS; do RL="$RL; read_liberty -lib $l"; done
SRC="physical/hbm_next/att4/macros/hnx_sram_1r1w_128x256_r43/hnx_sram_1r1w_128x256_r43_bb.v rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/gpu/ot_gpu_fadd.sv rtl/hbm_next/att/ot_hnx_att4_smerge.sv rtl/hbm_next/att/ot_hnx_att4_spvm.sv"
syn(){ # tag NL
  local t=$1 nl=$2
  $Y -q -l $O/synth_$t.log -p "$RL; read_verilog -sv -DSYNTHESIS $SRC; chparam -set NL $nl ot_hnx_att4_spvm; hierarchy -check -top ot_hnx_att4_spvm; synth -flatten -top ot_hnx_att4_spvm; dfflibmap $LA; abc $LA; opt_clean; stat $LA" > /dev/null 2>&1
  echo "$t NL=$nl rc=$? $(grep -i 'Chip area' $O/synth_$t.log | tail -1) cells=$(grep -E '^ +[0-9]+ +cells$|Number of cells' $O/synth_$t.log | tail -1 | tr -s ' ')" | tee -a $O/area.txt
  grep -E 'DFF[A-Za-z0-9_]*RVT|DHL' $O/synth_$t.log | tail -6 >> $O/area.txt
}
: > $O/area.txt
syn spvm_sram_nl3 3; echo done >> $O/area.txt
