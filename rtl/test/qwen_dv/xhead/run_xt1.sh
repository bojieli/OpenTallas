#!/bin/bash
# QW-XHEAD XT1 campaign (fleet, ot-epyc5 work dir W with src/ = the dv2f14bi src RTL + these bench files, prep/ from
# xt1_prep.py).  One Verilator 5.050 build of tb_xt1, then every run on the same executable.
#   run_xt1.sh W RUN...      RUN = mode:lead:gap[:maskdir]   e.g. nominal:8:4 asbuilt:8:4 romswap:8:4:prep_swap
set -u
W=$(realpath "$1"); shift
S=$W/src
export PATH=${OT_VERILATOR_BIN:-$HOME/.local/opentallas-tools/verilator-5.050/bin}:$PATH
cd "$W"
verilator --version | tee verilator.version
OBJ=$W/${XT1_OBJ:-obj_xt1}
# QW-DIEFIX ROMBIND: XT1_TB=tb_xt1_rb.sv (GEN rom_bind include) XT1_DEFS="+define+OT_XT1_NOBIND" (mutant) XT1_OBJ=<obj dir>
TB=${XT1_TB:-tb_xt1.sv}
FILES="rtl/ot_fp32_rne_pkg.sv rtl/hdc/ot_hdc_cg.sv
rtl/qwen_dv/qfd_dv_slice2.sv rtl/qwen_dv/qfd_dv_vm.sv
physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
rtl/hbm_accel/generic/collective/inverse/ot_hgi_inverse_sram_mask_sim.sv
physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
rtl/qwen_dv/qfd_dv_su8_entries.sv rtl/physical/ot_hdc_vreduce_entries64.sv rtl/hdc/ot_hdc_fastfp.sv
rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/dsrom_sys/s81_window_la/recovered_ctl_m2/ot_hdc_prefix.sv rtl/hdc/ot_hdc_delay.sv
rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/physical/ot_hdc_vstream_lane_clock_entries_candidate.sv
rtl/hdc/ot_hdc_vstream_lane_t.sv rtl/hdc/ot_hdc_vstream_lane.sv rtl/hdc/ot_hdc_sfu_q.sv rtl/hdc/ot_hdc_vstream_sfu_t.sv
rtl/hdc/ot_hdc_vreduce.sv rtl/physical/ot_hdc_vred_pending_guard.sv rtl/qwen_dv/qfd_dv_stream.sv
rtl/qwen_dv/qfd_dv_scalar2.sv rtl/qwen_dv/qfd_dv_redstn2.sv rtl/qwen_dv/qfd_dv_heads.sv
rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv rtl/lib/ot_rst_pipe.sv rtl/physical/qcluster/qfd_c_b16_dv.sv
rtl/physical/qfd_tile_nl_rp2_romleaf_rr.sv rtl/physical/qfd_tile_nl_rp2_45.sv rtl/physical/ot_qwen_rom_tile_nk.sv
rtl/hdc/ot_qwen_rom_tile_w12.sv physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v
physical/asap7_memory_macros/ot_rom_2048x266_m8/ot_rom_2048x266_m8.v rtl/hdc/ot_qwen_w12_matvec.sv
rtl/hdc/ot_hdc_fp32_add_lat_nr.sv rtl/hdc/ot_qwen_w12_arith.sv rtl/hdc/ot_hdc_fpu.sv rtl/proto/ot_fp32_add_rne_pipe.sv
rtl/physical/ot_qwen_tile_operand.sv rtl/physical/ot_qwen_tile_lsl.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv
rtl/physical/ot_qwen_tile_rqr_half.sv rtl/physical/ot_qwen_tile_rpair.sv rtl/physical/ot_qwen_tile_romleaf.sv
rtl/physical/ot_qwen_tile_node.sv rtl/lib/ot_rst_relay.sv rtl/hdc/ot_qwen_me_array_w12.sv
rtl/physical/qfd_tile_nk_rp2_romleaf_rr.sv rtl/physical/qfd_tile_nk_rp2_45.sv rtl/physical/qcluster/qfd_c_b16_dv_fabric.sv
rtl/physical/qcluster/qfd_q3h_stn.sv rtl/physical/qcluster/qfd_c_stn.sv rtl/test/qwen_dv/xhead/$TB"
INC="+incdir+physical/asap7_memory_macros/ot_rom_2048x266_m8 +incdir+physical/asap7_memory_macros/ot_rom_4096x266_m8
+incdir+physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2 +incdir+physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2
+incdir+rtl +incdir+rtl/dsrom_sys/s81_window_la/recovered_ctl_m2 +incdir+rtl/hbm_accel/generic/collective/inverse
+incdir+rtl/hdc +incdir+rtl/lib +incdir+rtl/physical +incdir+rtl/physical/qcluster +incdir+rtl/proto +incdir+rtl/qwen_dv
+incdir+rtl/qwen_split +incdir+rtl/qwen_sys/dvm_20261014 +incdir+rtl/test/qwen_dv/xhead +incdir+rtl/qwen_sys/reset_tree_20261013"
(cd "$S" && sha256sum $FILES $(ls rtl/test/qwen_dv/xhead/*.vh 2>/dev/null) rtl/test/qwen_dv/xhead/*.py rtl/test/qwen_dv/xhead/*.sh rtl/test/qwen_dv/main2.cpp \
   rtl/test/qwen_dv/dv_bench.py tools/hdc_golden.py) > "$W/sources.sha256"
if [ ! -x "$OBJ/Vtb" ]; then
  /usr/bin/time -v -o "$W/build.time" verilator --cc --exe --build -O2 -j 32 -Wno-fatal -Wno-lint -Wno-style \
     -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN ${XT1_DEFS:-} --x-assign 0 --x-initial 0 +define+OT_QFD_UP4_CK_ENTRIES \
     --top-module tb_xt1 --prefix Vtb -Mdir "$OBJ" $(cd "$S" && for f in $INC; do echo "${f/+incdir+/+incdir+$S/}"; done) \
     "$S/rtl/test/qwen_dv/main2.cpp" $(for f in $FILES; do echo "$S/$f"; done) > "$W/build.log" 2>&1 \
     || { echo BUILD_FAIL; grep -m30 -E "%Error" "$W/build.log"; exit 2; }
fi
B=$S/rtl/test/qwen_dv/xhead/xt1_bench.py
rc=0
for run in "$@"; do
  IFS=: read -r mode lead gap md <<< "$run"; md=${md:-prep}
  tag=${mode}_l${lead}_g${gap}
  python3 "$B" gen --gold prep/gold.json --out "$W/ev_$tag.txt" --mode "$mode" --lead "$lead" --gap "$gap" || { rc=1; continue; }
  NC=$(python3 -c "print(60 + 1600 * 4)")
  "$OBJ/Vtb" +EV="$W/ev_$tag.txt" +LOG="$W/log_$tag.txt" +NCYC=$NC +OT_ROM_DIR="$W/$md/masks" > "$W/sim_$tag.out" 2>&1
  echo "sim rc=$? ($tag, masks $md)" >> "$W/sim_$tag.out"
  python3 "$B" check --gold prep/gold.json --log "$W/log_$tag.txt" --mode "$mode" --lead "$lead" --gap "$gap" \
     > "$W/result_$tag.txt" 2>&1
  cat "$W/result_$tag.txt"
done
echo CAMPAIGN_DONE
