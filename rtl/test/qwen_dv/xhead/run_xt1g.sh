#!/bin/bash
# QW-LAYERB 10-20 XT1g campaign: the XT1n near+far matvec on the GEN DIE NETLIST (carve of out/case/die.v: dvs_W5 +
# c16_W5_2 + c16_W5_3 + the die landings between them, die.v.params.json master params (slice MU_NU 4), rom_bind.vh lines).
#   run_xt1g.sh W DIE_OUT RUN...      W = work dir with src/ (= the die run's source snapshot + these bench files) and
#   prep_c2 prep_c3 masks_fixed masks_swap (XT1n prep, real TP8 rank-0 L0 ROM masks);  DIE_OUT = <die run>/out
#   RUN = variant:mode:lead:gap[:maskset]   variant fixed | nobind (rom_bind lines dropped -> empty code ROMs, must FAIL)
set -u
W=$(realpath "$1"); D=$(realpath "$2"); shift 2
S=$W/src
export PATH=${OT_VERILATOR_BIN:-$HOME/.local/opentallas-tools/verilator-5.050/bin}:$PATH
cd "$W"
verilator --version | tee verilator.version
B=$S/rtl/test/qwen_dv/xhead
C=$W/carve; mkdir -p "$C"
sha256sum "$D/case/die.v" "$D/case/port_dirs.json" "$D/case/die.v.params.json" "$D/case/rom_bind.vh" > "$W/die_inputs.sha256"
python3 "$S/tools/qwen_layerbench/die_carve.py" --die "$D/case/die.v" --dirs "$D/case/port_dirs.json" \
   --params "$D/case/die.v.params.json" --seed dvs_W5 --seed c16_W5_2 --seed c16_W5_3 --top xt1g_carve \
   --out "$C/xt1g_carve.v" --json "$C/carve.json" || { echo CARVE_FAIL; exit 3; }
python3 "$S/tools/qwen_split/gen_relay_rtl.py" "$C/xt1g_carve.v" "$C/xt1g_relays.sv" > "$C/relays.json" || { echo RELAY_RTL_FAIL; exit 3; }
python3 "$B/gen_tb_xt1g.py" "$C/carve.json" "$D/case/rom_bind.vh" "$C" || { echo TB_GEN_FAIL; exit 3; }
mkdir -p "$C/nobind"; cp "$C/tb_xt1g.sv" "$C/nobind/"; echo '// nobind mutant: no ROM_TILE bindings' > "$C/nobind/rom_bind_xt1g.vh"
FILES="rtl/ot_fp32_rne_pkg.sv rtl/hdc/ot_hdc_cg.sv
rtl/qwen_dv/qfd_dv_slice2.sv rtl/qwen_dv/qfd_dv_slice2_faces.sv rtl/qwen_dv/mu/qfd_dv_amax_mu.sv rtl/qwen_dv/qfd_dv_vm.sv
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
rtl/physical/qcluster/qfd_q3h_stn.sv rtl/physical/qcluster/qfd_c_stn.sv rtl/qwen_split/qfd_fwd_lane.sv"
INC="+incdir+physical/asap7_memory_macros/ot_rom_2048x266_m8 +incdir+physical/asap7_memory_macros/ot_rom_4096x266_m8
+incdir+physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2 +incdir+physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2
+incdir+rtl +incdir+rtl/dsrom_sys/s81_window_la/recovered_ctl_m2 +incdir+rtl/hbm_accel/generic/collective/inverse
+incdir+rtl/hdc +incdir+rtl/lib +incdir+rtl/physical +incdir+rtl/physical/qcluster +incdir+rtl/proto +incdir+rtl/qwen_dv
+incdir+rtl/qwen_dv/mu +incdir+rtl/qwen_split +incdir+rtl/qwen_sys/dvm_20261014 +incdir+rtl/qwen_sys/reset_tree_20261013"
YD="-y $S/rtl/qwen_dv -y $S/rtl/qwen_dv/mu -y $S/rtl/physical -y $S/rtl/hdc -y $S/rtl/lib -y $S/rtl/qwen_split"
(cd "$S" && sha256sum $FILES rtl/test/qwen_dv/xhead/*.py rtl/test/qwen_dv/xhead/*.sh rtl/test/qwen_dv/main2.cpp \
   tools/qwen_layerbench/die_carve.py tools/qwen_split/gen_relay_rtl.py) > "$W/sources.sha256"
(cd "$C" && sha256sum xt1g_carve.v xt1g_relays.sv tb_xt1g.sv rom_bind_xt1g.vh) >> "$W/sources.sha256"
build() {  # $1 variant, $2 tb dir
  local OBJ=$W/obj_$1
  [ -x "$OBJ/Vtb" ] && return 0
  /usr/bin/time -v -o "$W/build_$1.time" verilator --cc --exe --build -O2 -j 32 -Wno-fatal -Wno-lint -Wno-style \
     -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --x-assign 0 --x-initial 0 +define+OT_QFD_UP4_CK_ENTRIES \
     --top-module tb_xt1g --prefix Vtb -Mdir "$OBJ" +incdir+$2 $(cd "$S" && for f in $INC; do echo "${f/+incdir+/+incdir+$S/}"; done) $YD \
     "$S/rtl/test/qwen_dv/main2.cpp" $(for f in $FILES; do echo "$S/$f"; done) "$C/xt1g_relays.sv" "$C/xt1g_carve.v" "$2/tb_xt1g.sv" \
     > "$W/build_$1.log" 2>&1 || { echo "BUILD_FAIL $1"; grep -m30 -E "%Error" "$W/build_$1.log"; return 2; }
}
if [ "${OT_XT1G_LINT:-0}" = 1 ]; then   # quick elaboration check only
  verilator --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN +define+OT_QFD_UP4_CK_ENTRIES \
     --top-module tb_xt1g +incdir+$C $(cd "$S" && for f in $INC; do echo "${f/+incdir+/+incdir+$S/}"; done) $YD \
     $(for f in $FILES; do echo "$S/$f"; done) "$C/xt1g_relays.sv" "$C/xt1g_carve.v" "$C/tb_xt1g.sv" > "$W/lint.log" 2>&1
  echo "LINT rc=$?"; grep -m40 -E "%Error" "$W/lint.log"; exit 0
fi
build fixed "$C" || exit 2
for run in "$@"; do
  IFS=: read -r V mode lead gap ms <<< "$run"; ms=${ms:-masks_fixed}
  if [ "$V" = nobind ]; then build nobind "$C/nobind" || { echo "RESULT XT1G BUILD_FAIL nobind"; continue; }; fi
  tag=${V}_${mode}_l${lead}_g${gap}_${ms}
  python3 "$B/xt1_bench.py" gen --gold prep_c2/gold.json --out "$W/ev_$tag.txt" --mode "$mode" --lead "$lead" --gap "$gap" || continue
  NC=$(python3 -c "print(60 + 1600 * 4)")
  "$W/obj_$V/Vtb" +EV="$W/ev_$tag.txt" +LOG="$W/log_$tag.txt" +NCYC=$NC +OT_ROM_DIR="$W/$ms" > "$W/sim_$tag.out" 2>&1
  echo "sim rc=$? ($tag)" >> "$W/sim_$tag.out"
  python3 "$B/xt1n_bench.py" check --gold-near prep_c2/gold.json --gold-far prep_c3/gold.json --log "$W/log_$tag.txt" \
     --mode "$mode" --lead "$lead" --gap "$gap" > "$W/result_$tag.txt" 2>&1
  echo "== $tag"; cat "$W/result_$tag.txt"
done
echo CAMPAIGN_DONE
