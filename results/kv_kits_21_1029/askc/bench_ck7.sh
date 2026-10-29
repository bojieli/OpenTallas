#!/bin/bash
# bench_ck7.sh OUT CKMUT [MUT]: tb_qkd_ahub_static_dw on qkd_ahub_static_dw_ck7 with every clock entry tied to ck
# (CKMUT 0) or entry k-1 stopped (held 0; CKMUT k=1..4: S-W, S-E, E-S, E-N; must FAIL) or the north zh pair stopped (CKMUT 5).
# Same sources/flags as tools/qwen_kv_die/ahub_static_dw_bench.sh; run from the repository root.
set -u
O=$1; C=$2; M=${3:-0}
mkdir -p "$O"
D=results/kv_kits_21_1029/askc
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
sed -e 's/    qkd_ahub_static_dw #(.AP_OFS(AP_OFS), .FR_OFS(FR_OFS), .MUT(MUT)) dut (.ck(ck), .rst_n(rst_n),/    wire [3:0] ck_ent = {4{ck}} \& ~((CKMUT >= 1 \&\& CKMUT <= 4) ? (4'"'"'b1 << (CKMUT - 1)) : 4'"'"'b0);\n    wire [1:0] ck_zh = {2{ck}} \& ~((CKMUT == 5) ? 2'"'"'b10 : 2'"'"'b00);\n    qkd_ahub_static_dw_ck7 #(.AP_OFS(AP_OFS), .FR_OFS(FR_OFS), .MUT(MUT)) dut (.ck(ck), .ck_zh(ck_zh), .ck_ent(ck_ent), .rst_n(rst_n),/' \
    -e 's/^    parameter integer MUT = 0;/    parameter integer MUT = 0;\n    parameter integer CKMUT = 0;/' \
    rtl/test/qwen_kv_die/tb_qkd_ahub_static_dw.sv > "$O/tb_ck7.sv"
grep -q qkd_ahub_static_dw_ck7 "$O/tb_ck7.sv" || { echo "AHUB_DW FAIL tb sed"; exit 1; }
SRC="rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
rtl/hdc/ot_hdc_fp32_add_lat_nr.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_delay.sv
rtl/hdc/nearhbm/ot_qwen_nearhbm_sfu_p.sv rtl/lib/ot_rst_relay.sv rtl/lib/ot_rst_pipe.sv
rtl/hdc/nearhbm/ot_qkd_ahub_static_cal_gen.sv rtl/hdc/nearhbm/ot_qkd_ahub_core.sv rtl/hdc/nearhbm/ot_nhb_tiles.sv
rtl/hdc/nearhbm/ot_qkh_recip_leaf.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_hub_p.sv $D/ck7/qkd_ahub_static_dw.sv
rtl/qwen_sys/split_20261014/qkd_attn_service_root.sv rtl/qwen_sys/split_20261014/qkd_pv_fin_s.sv $O/tb_ck7.sv"
sha256sum $SRC "$0" > "$O/source.sha256"
$VL --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH --build-jobs 4 \
  --top-module tb_qkd_ahub_static_dw -GMUT=$M -GCKMUT=$C --Mdir "$O/obj" $SRC > "$O/build.log" 2>&1 \
  || { echo "AHUB_DW FAIL build"; grep -m8 '%Error' "$O/build.log"; exit 1; }
"$O/obj/Vtb_qkd_ahub_static_dw" > "$O/run.log" 2>&1
line=$(grep -E '^AHUB_DW (PASS|FAIL)' "$O/run.log" | tail -1)
echo "CKMUT=$C MUT=$M ${line:-AHUB_DW FAIL no verdict line}"
