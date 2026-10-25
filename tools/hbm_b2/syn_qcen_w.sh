#!/bin/bash
# HBM-HC: ASAP7 RVT TT area estimate of ot_hbm_hc_qcen_static W 64 vs W 128 (yosys synth, abc on SIMPLE/AO/OA/INVBUF, SEQ flops)
set -uo pipefail
out=$(realpath -m "${1:?OUT}"); w=${2:?W}; mkdir -p "$out"
L=$HOME/.cache/opentallas/asap7_nldm; T=$out/lib; mkdir -p $T
for f in SIMPLE_RVT_TT_nldm_211120 AO_RVT_TT_nldm_211120 OA_RVT_TT_nldm_211120 INVBUF_RVT_TT_nldm_220122; do
  [ -f $T/$f.lib ] || zcat $L/asap7sc7p5t_$f.lib.gz > $T/$f.lib 2>/dev/null || cp $L/asap7sc7p5t_$f.lib $T/$f.lib; done
cp $L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib $T/SEQ.lib 2>/dev/null || zcat $L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib.gz > $T/SEQ.lib
H=rtl/hbm_accel/generic/peers/static_hc
libs="-liberty $T/SIMPLE_RVT_TT_nldm_211120.lib -liberty $T/AO_RVT_TT_nldm_211120.lib -liberty $T/OA_RVT_TT_nldm_211120.lib -liberty $T/INVBUF_RVT_TT_nldm_220122.lib"
yosys -q -l $out/syn_w$w.log -p "read_verilog -sv -DOT_FP_DATA_NORST $H/ot_hbm_hc_qcen_static.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_delay.sv rtl/lib/ot_rst_relay.sv;
 chparam -set W $w -set DRLY 2 -set CHX 11 ot_hbm_hc_qcen_static; synth -top ot_hbm_hc_qcen_static -flatten; dfflibmap -liberty $T/SEQ.lib; abc $libs; opt_clean; stat $libs -liberty $T/SEQ.lib" > /dev/null 2>&1
grep -E "Chip area|Number of cells" $out/syn_w$w.log | tail -2 | sed "s/^/QCEN_W$w /"
