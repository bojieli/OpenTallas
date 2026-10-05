#!/bin/bash
# retry of the qwen build (first attempt hit a parallel-make PCH race: runs/build_qwen.log kept as build_qwen_attempt1.log)
cd ~/claude-ha2ar
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
SRC="src/rtl/link/ot_link_afifo.sv src/rtl/hdc/ot_hdc_fastfp.sv src/rtl/hdc/ot_hdc_prefix.sv src/rtl/hdc/ot_hdc_fp32_add_lat.sv src/rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv src/rtl/hbm_accel/ha2_ar/ot_ha2_link.sv src/rtl/hbm_accel/ha2_ar/ot_ha2_ar_endpoint.sv src/rtl/hbm_accel/ha2_ar/tb_ha2_ar.sv"
D() { for kv in "$@"; do printf -- "+define+HA2_%s " "$kv"; done; }
mv runs/build_qwen.log runs/build_qwen_attempt1.log; mv runs/build_qwen.exit runs/build_qwen_attempt1.exit
rm -rf b/qwen
( /usr/bin/time -v $V --binary --timing --hierarchical -j 1 -Wno-fatal -Wno-lint -Wno-style --x-assign fast --x-initial fast --top-module tb_ha2_ar --Mdir b/qwen $(D GS=2 NG=1 NC=2 NOG=1 E=4096 LANES=256 ONESHOT=1 BF16=0 INJ=1 DEL=1 HUBW=37 WSTG=14 BITS_X100=1308000 PWB=8217 PHY_L=5 PHY_G=5 JS=1 DMAX=16 T_PHY=0.4) $SRC ) > runs/build_qwen.log 2>&1
echo $? > runs/build_qwen.exit
for s in $(seq 1 10); do b/qwen/Vtb_ha2_ar +VEC=fx/qwen +SEED=$s > runs/qwen_central_s$s.log 2>&1; done
echo done > runs/qwen.done
