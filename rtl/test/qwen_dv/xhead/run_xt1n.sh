#!/bin/bash
# QW-DIEFIX-NFAR XT1n campaign (fleet, ot-epyc5 work dir W; src/ = branch claude/qw-diefix-nfar-1019 sources incl. the
# dv2f16 cluster RTL; prep_c2 / prep_c3 / prep_c3swap from xt1_prep.py --cid 2 / 3 / 3 --swap 48,49).
#   run_xt1n.sh W VARIANT RUN...   VARIANT = fixed (heads as in src) | oldtags (heads without the ea371ad83 retag: a
#   source transform of a copy, src_oldtags/ -- bench mutant, no RTL define)    RUN = mode:lead:gap[:maskset]
set -u
W=$(realpath "$1"); V=$2; shift 2
S=$W/src
export PATH=${OT_VERILATOR_BIN:-$HOME/.local/opentallas-tools/verilator-5.050/bin}:$PATH
cd "$W"
verilator --version | tee verilator.version
if [ "$V" = oldtags ]; then
  rm -rf "$W/src_oldtags"; cp -a "$S" "$W/src_oldtags"; S=$W/src_oldtags
  grep -q 'retag = {t\[7\], b, t\[3\], a};' "$S/rtl/qwen_dv/qfd_dv_heads.sv" || { echo "OLDTAGS transform anchor missing"; exit 3; }
  sed -i 's/retag = {t\[7\], b, t\[3\], a};/retag = t;   \/\/ XT1n mutant oldtags: no corridor retag/' "$S/rtl/qwen_dv/qfd_dv_heads.sv"
fi
OBJ=$W/obj_$V
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
rtl/physical/qcluster/qfd_c_land.sv
rtl/physical/qfd_tile_nl_rp2_romleaf_rr.sv rtl/physical/qfd_tile_nl_rp2_45.sv rtl/physical/ot_qwen_rom_tile_nk.sv
rtl/hdc/ot_qwen_rom_tile_w12.sv physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v
physical/asap7_memory_macros/ot_rom_2048x266_m8/ot_rom_2048x266_m8.v rtl/hdc/ot_qwen_w12_matvec.sv
rtl/hdc/ot_hdc_fp32_add_lat_nr.sv rtl/hdc/ot_qwen_w12_arith.sv rtl/hdc/ot_hdc_fpu.sv rtl/proto/ot_fp32_add_rne_pipe.sv
rtl/physical/ot_qwen_tile_operand.sv rtl/physical/ot_qwen_tile_lsl.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv
rtl/physical/ot_qwen_tile_rqr_half.sv rtl/physical/ot_qwen_tile_rpair.sv rtl/physical/ot_qwen_tile_romleaf.sv
rtl/physical/ot_qwen_tile_node.sv rtl/lib/ot_rst_relay.sv rtl/hdc/ot_qwen_me_array_w12.sv
rtl/physical/qfd_tile_nk_rp2_romleaf_rr.sv rtl/physical/qfd_tile_nk_rp2_45.sv rtl/physical/qcluster/qfd_c_b16_dv_fabric.sv
rtl/physical/qcluster/qfd_q3h_stn.sv rtl/physical/qcluster/qfd_c_stn.sv rtl/test/qwen_dv/xhead/tb_xt1n.sv"
INC="+incdir+physical/asap7_memory_macros/ot_rom_2048x266_m8 +incdir+physical/asap7_memory_macros/ot_rom_4096x266_m8
+incdir+physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2 +incdir+physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2
+incdir+rtl +incdir+rtl/dsrom_sys/s81_window_la/recovered_ctl_m2 +incdir+rtl/hbm_accel/generic/collective/inverse
+incdir+rtl/hdc +incdir+rtl/lib +incdir+rtl/physical +incdir+rtl/physical/qcluster +incdir+rtl/proto +incdir+rtl/qwen_dv
+incdir+rtl/qwen_split +incdir+rtl/qwen_sys/dvm_20261014 +incdir+rtl/qwen_sys/reset_tree_20261013"
(cd "$S" && sha256sum $FILES rtl/test/qwen_dv/xhead/*.py rtl/test/qwen_dv/xhead/*.sh rtl/test/qwen_dv/main2.cpp \
   rtl/test/qwen_dv/dv_bench.py tools/hdc_golden.py) > "$W/sources_$V.sha256"
if [ ! -x "$OBJ/Vtb" ]; then
  /usr/bin/time -v -o "$W/build_$V.time" verilator --cc --exe --build -O2 -j 32 -Wno-fatal -Wno-lint -Wno-style \
     -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --x-assign 0 --x-initial 0 +define+OT_QFD_UP4_CK_ENTRIES \
     --top-module tb_xt1n --prefix Vtb -Mdir "$OBJ" $(cd "$S" && for f in $INC; do echo "${f/+incdir+/+incdir+$S/}"; done) \
     "$S/rtl/test/qwen_dv/main2.cpp" $(for f in $FILES; do echo "$S/$f"; done) > "$W/build_$V.log" 2>&1 \
     || { echo BUILD_FAIL; grep -m30 -E "%Error" "$W/build_$V.log"; exit 2; }
fi
B=$S/rtl/test/qwen_dv/xhead
rc=0
for run in "$@"; do
  IFS=: read -r mode lead gap ms <<< "$run"; ms=${ms:-masks_fixed}
  tag=${V}_${mode}_l${lead}_g${gap}
  python3 "$B/xt1_bench.py" gen --gold prep_c2/gold.json --out "$W/ev_$tag.txt" --mode "$mode" --lead "$lead" --gap "$gap" || { rc=1; continue; }
  NC=$(python3 -c "print(60 + 1600 * 4)")
  "$OBJ/Vtb" +EV="$W/ev_$tag.txt" +LOG="$W/log_$tag.txt" +NCYC=$NC +OT_ROM_DIR="$W/$ms" > "$W/sim_$tag.out" 2>&1
  echo "sim rc=$? ($tag, masks $ms)" >> "$W/sim_$tag.out"
  python3 "$B/xt1n_bench.py" check --gold-near prep_c2/gold.json --gold-far prep_c3/gold.json --log "$W/log_$tag.txt" \
     --mode "$mode" --lead "$lead" --gap "$gap" > "$W/result_$tag.txt" 2>&1
  cat "$W/result_$tag.txt"
done
echo CAMPAIGN_DONE
