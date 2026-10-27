#!/bin/bash
# PG-ACTIVITY-KVHBM 10-27: REDUCED pv bench (the full 32-column tb_qwen_tp8_pv_wide_pair non-hierarchical Verilator build
# exceeds 30 min elaboration / 59 GB). Copy of ot_qwen_tp8_pv_wide_pair with columns 0-1 only (cv[31:2] = cv[0] copies,
# cf[31:2] = 0, out_leaf of columns 2-31 = 0); tb compares only words 0-31 (= columns 0-1) to gold. Same ctl, same commands,
# same golden V/e vectors (pv_pair_ref.py). VCD of u.g_col[0].u_col.g_bank[0|1].u_bank (= kv3_pv_pair u_s0/u_s1).
#   kv_pv2_activity_sim.sh OUTDIR [T]
set -eu
R=$(cd "$(dirname "$0")/../../.." && pwd); O=$(realpath -m "$1"); T=${2:-1000}; mkdir -p "$O"; cd $R
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
sed -e 's|for(s=0;s<32;s=s+1)begin:g_col|assign cv[31:2]={30{cv[0]}}; assign cf[31:2]=30'"'"'d0; assign out_leaf[16383:1024]=0;\n generate for(s=0;s<2;s=s+1)begin:g_col|' \
    -e 's|^ generate assign cv|assign cv|' rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_pair.sv > $O/pair2.sv
grep -n "g_col" $O/pair2.sv | head -3
sed -e 's|^\( initial begin\)$|  initial begin $dumpfile("'$O'/pv.vcd"); $dumpvars(0, tb_qwen_tp8_pv_wide_pair.u.g_col[0].u_col.g_bank[0].u_bank); $dumpvars(0, tb_qwen_tp8_pv_wide_pair.u.g_col[0].u_col.g_bank[1].u_bank); end\n\1|' \
    -e 's|if(out_leaf\[32\*i+:32\]!==gold\[i\])|if(i<32 \&\& out_leaf[32*i+:32]!==gold[i])|' rtl/test/nearhbm/tb_qwen_tp8_pv_wide_pair.sv > $O/tb_vcd.sv
grep -q dumpvars $O/tb_vcd.sv && grep -q "i<32" $O/tb_vcd.sv || { echo NO_HOOK; exit 5; }
$V --binary --timing -O1 --trace --trace-max-width 20000 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH --build-jobs 16 \
 --top-module tb_qwen_tp8_pv_wide_pair -GPAIR=0 -GMUT=0 -GCTL_RESET_PIN=1 -GLEAF_RESET_PIN=1 --Mdir $O/obj \
 $O/pair2.sv rtl/hdc/nearhbm/ot_qwen_tp8_pv16_slice_gen.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_prod.sv \
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fpu.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v $O/tb_vcd.sv > $O/build.log 2>&1 || { tail -20 $O/build.log; echo BUILD_FAILED; exit 3; }
python3 tools/qwen_attention_native/rate_1015/pv_pair_ref.py --ctx $T --pair 0 --seed $T --out $O/vec > $O/ref.log
$O/obj/Vtb_qwen_tp8_pv_wide_pair +VEC=$O/vec +CTX=$T +MODE=steady > $O/run.log 2>&1 || true
grep -E "^PV_PAIR|MISMATCH" $O/run.log | tail -3; ls -la $O/pv.vcd
