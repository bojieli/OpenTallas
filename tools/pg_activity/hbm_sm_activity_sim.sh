#!/usr/bin/env bash
# PG-ACTIVITY-KVHBM (10-27): measured HBM SM switching activity. tb_hgi_sm_e2e (records -> sm_record -> xload -> 2 REAL
# ot_hbm_accel_smh in the OT_SMH_HIER hard-master form (u_bdc / u_tcc{u_h0,u_h1,u_tr}) -> pub -> real VM; golden check,
# HGI_SM_E2E PASS) with --ds (FP8/FP4 block-dot DS cases + INT8/BF16) and Verilator --trace; VCD of real SM g_sm[0].u_sm.
#   hbm_sm_activity_sim.sh OUTDIR    (cwd = repo root, Verilator 5.050)
set -eu
O=$(realpath -m "${1:?outdir}"); mkdir -p "$O"
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
python3 tools/hgi_adapters/sm_e2e_bench.py --ds --out "$O/vec" > "$O/gen.log"
TB0=rtl/hbm_accel/generic/adapters/tb/tb_hgi_sm_e2e.sv
sed "s|^\(    initial begin\)$|    initial begin \$dumpfile(\"$O/sm.vcd\"); \$dumpvars(0, tb_hgi_sm_e2e.g_sm[0].u_sm); end\n\1|" $TB0 | awk "!(/dumpvars/ && n++)" > "$O/tb_hgi_sm_e2e_vcd.sv"
# only hook once (the first "initial begin" line)
grep -c dumpvars "$O/tb_hgi_sm_e2e_vcd.sv"
SRC="rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v rtl/link/ot_fifo_sram_fwft.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v rtl/hbm_accel/generic/vm/ot_hgi_vm_lanearb.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v rtl/hbm_accel/generic/adapters/ot_hgi_sm_record.sv rtl/hbm_accel/generic/ot_hgi_sm_leaf.sv rtl/hdc/v41/ot_hdc_actquant.sv rtl/hbm_accel/generic/peers/ot_hgi_sm_xload.sv rtl/hbm_accel/generic/peers/ot_hgi_sm_pub.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_core.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_unit.sv $(python3 -c "import sys; sys.path.insert(0,\"tools\"); import dshbm_sm_pq_seq as Q; print(\" \".join(s for s in Q.SRC + Q.SMH_SRC if \"rtl/test/\" not in s))")"
# kit defines of the SM hard masters (path-hbm-sm kits config.mk) minus SYNTHESIS
D="${XDEF:--DOT_SMH_CG_ENREG -DOT_SMH_XLK -DOT_FP_DATA_NORST -DOT_SMH_DRST0 -DOT_SMH_RSTRELAY -DOT_SMH_RSTPIN -DOT_SMH_HIER -DOT_SMH_PTW_OHDLY -DOT_SMH_PINREG -DOT_SMH_XREL -DOT_SMH_PRODUCTION_SHAPE -DOT_SMH_COMPACT_PT -DOT_SMH_GROUP_TRANSPORT -DOT_SMH_WEST_SPLIT -DOT_SMH_TRANSPORT_KEEP -DOT_SMH_RP4_SRST}"
$VL --version
$VL --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN --trace --trace-max-width 2048 \
  --top-module tb_hgi_sm_e2e -I"$O/vec" $D -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" -Mdir "$O/obj" $SRC "$O/tb_hgi_sm_e2e_vcd.sv" -j ${J:-16} > "$O/build.log" 2>&1 || { grep -m10 %Error "$O/build.log"; echo BUILD_FAILED; exit 3; }
"$O/obj/Vtb_hgi_sm_e2e" +DIR="$O/vec" > "$O/run.log" 2>&1; tail -5 "$O/run.log"; ls -la "$O/sm.vcd"
