#!/bin/bash
# TOK-FUNC-QW stage "xt1" (10-21): L0 stage-1 matvec (qkv / o / gu / down) through the REAL ROM tile clusters of the Qwen
# compute release die on the RTL-only SOURCE ASSEMBLY (RUNROOT/src): slice dvs_W5 (qfd_dv_slice2_w, MU_NU 4) column heads
# -> near band-2 cluster c16_W5_2 (cid 2) -> far cluster c16_W5_3 (cid 3) -> rs reduction back to the slice, every rs word
# bit-exact vs the golden level-6 part, real TP8 rank-0 L0 code-ROM masks.  Verilator 5.050.
#
#   stage_xt1.sh RUNROOT [--die-netlist DIE_OUT] [--variants "landed nobind nl oldtags"]
#
# Bench = the existing XT1n bench (rtl/test/qwen_dv/xhead: xt1_prep.py prep_c2 / prep_c3 / prep_c3swap, xt1_bench.py gen,
# xt1n_bench.py check; tb log format of tb_xt1n.sv) on a SOURCE carve of the die (stage_xt1_carve.py): the same three
# instances + the 11 qfd_landh0 n=1 die landings between slice and clusters (g5r3-rev die plan classes, K 3; relay RTL by
# tools/qwen_split/gen_relay_rtl.py), i.e. the XT1g topology without GEN.  Variants (built in parallel, ~70 GB each):
#   landed  : source carve with landings; runs nominal 8/4, nominal 4/2, romswap 8/4 (masks of tiles 48/49 swapped: MUTANT)
#   nobind  : landed carve without the 32 ROM_TILE binds (MUTANT: empty / invalid ROM binding must FAIL)
#   nl      : no landings (the XT1n topology, release slice MU_NU 4): nominal 8/4, 4/2 -- the landing delta reference
#   oldtags : landed carve, heads without the ea371ad83 corridor retag (source transform of qfd_dv_heads.sv: MUTANT)
# Inputs: RUNROOT/src (ASM_COMMIT), RUNROOT/xt1/in/img (TP8 rank-0 L0 die0 code ROM image: layer0_rom.json +
#   matrix_int8.hex, tokpass-qwen-1018 realmem_tp8) and RUNROOT/xt1/in/fx (QW-REALSTG L0_mat_{qkv,od,gu}.npz).
# Output: RUNROOT/xt1/result.json (stage_xt1.collect.py): per variant/run near+far exact, per op first_rs / first_final /
#   last_final (edges from the hr go at the slice pin), mutants.
#
# --die-netlist DIE_OUT (closure hook): DIE_OUT = <GEN run>/out with case/die.v, case/port_dirs.json,
#   case/die.v.params.json, case/rom_bind.vh (the release compute GEN; RUNROOT/src must then be that GEN's source snapshot).
#   The carve becomes tools/qwen_tokfunc/die_carve.py (= QW-LAYERB XT1g die_carve.py) of die.v with seeds dvs_W5 c16_W5_2
#   c16_W5_3 (instance lines byte-for-byte, master params from die.v.params.json, every landing between them), relay RTL
#   from gen_relay_rtl.py, ROM binds = the GEN rom_bind.vh lines (gen_tb_xt1g.py); variants landed + nobind; grade
#   "die-netlist".  Same events, same checker, same result.json.
set -u
RUNROOT=$(readlink -f "$1"); shift
NET=""; VARS="landed nobind nl oldtags"
while [ $# -gt 0 ]; do case "$1" in
  --die-netlist) NET=$(readlink -f "$2"); shift 2;;
  --variants) VARS=$2; shift 2;;
  *) echo "bad arg $1"; exit 2;; esac; done
[ -n "$NET" ] && VARS=$(for v in $VARS; do case $v in landed|nobind) echo -n "$v ";; esac; done)
S=$RUNROOT/src; O=$RUNROOT/xt1; HERE=$(dirname "$(readlink -f "$0")"); B=$S/rtl/test/qwen_dv/xhead
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
mkdir -p "$O"; cd "$O"
verilator --version | tee verilator.version | grep -q '5.050' || { echo "need Verilator 5.050"; exit 2; }
GRADE="RTL-functional (source assembly)"; [ -n "$NET" ] && GRADE="die-netlist"
echo "{\"grade\": \"$GRADE\", \"die_netlist\": \"$NET\", \"variants\": \"$VARS\", \"start\": \"$(date -Is)\", \"host\": \"$(hostname)\"}" > run.json

# ---- prep: real TP8 rank-0 L0 ROM masks + golden level-6 words (near cid 2, far cid 3, far with tiles 48/49 swapped)
for p in "c2 2" "c3 3" "c3swap 3 48,49"; do
  set -- $p
  if [ ! -f "$O/prep_$1/gold.json" ]; then
    python3 "$B/xt1_prep.py" --img "$O/in/img" --fx "$O/in/fx" --cid "$2" --out "$O/prep_$1" ${3:+--swap $3} \
      > "$O/prep_$1.log" 2>&1 || { echo "PREP_FAIL $1"; tail -5 "$O/prep_$1.log"; exit 3; }
  fi
  grep -q 'layout mismatches 0' "$O/prep_$1.log" && ! grep -E 'layout mismatches [1-9]' "$O/prep_$1.log" \
    || { echo "PREP layout mismatch $1"; exit 3; }
done
mkdir -p masks_fixed masks_swap
ln -sfn "$O"/prep_c2/masks/* masks_fixed/; ln -sfn "$O"/prep_c3/masks/* masks_fixed/
ln -sfn "$O"/prep_c2/masks/* masks_swap/;  ln -sfn "$O"/prep_c3swap/masks/* masks_swap/

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
INC="physical/asap7_memory_macros/ot_rom_2048x266_m8 physical/asap7_memory_macros/ot_rom_4096x266_m8
physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2 physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2
rtl rtl/dsrom_sys/s81_window_la/recovered_ctl_m2 rtl/hbm_accel/generic/collective/inverse rtl/hdc rtl/lib rtl/physical
rtl/physical/qcluster rtl/proto rtl/qwen_dv rtl/qwen_dv/mu rtl/qwen_split rtl/qwen_sys/dvm_20261014 rtl/qwen_sys/reset_tree_20261013"
YD="rtl/qwen_dv rtl/qwen_dv/mu rtl/physical rtl/hdc rtl/lib rtl/qwen_split"
(cd "$S" && sha256sum $FILES rtl/test/qwen_dv/xhead/*.py rtl/test/qwen_dv/main2.cpp rtl/test/qwen_dv/dv_bench.py \
   tools/hdc_golden.py tools/qwen_split/gen_relay_rtl.py tools/qwen_split/ring_contract.py) > sources.sha256
(cd "$HERE" && sha256sum stage_xt1.sh stage_xt1_carve.py stage_xt1.collect.py die_carve.py gen_tb_xt1g.py) >> sources.sha256
(cd "$O/in" && sha256sum img/* fx/*) > inputs.sha256

# ---- one variant: carve -> relay RTL -> Verilator build -> runs -> xt1n_bench check
variant() {
  local V=$1 D=$O/$1 TOP=tb_xt1s CARVE=xt1s_carve.v HEADS=$S/rtl/qwen_dv/qfd_dv_heads.sv
  rm -rf "$D/carve"; mkdir -p "$D/carve"; cd "$D"
  if [ -n "$NET" ]; then
    TOP=tb_xt1g; CARVE=xt1g_carve.v
    sha256sum "$NET/case/die.v" "$NET/case/port_dirs.json" "$NET/case/die.v.params.json" "$NET/case/rom_bind.vh" > die_inputs.sha256
    python3 "$HERE/die_carve.py" --die "$NET/case/die.v" --dirs "$NET/case/port_dirs.json" --params "$NET/case/die.v.params.json" \
      --seed dvs_W5 --seed c16_W5_2 --seed c16_W5_3 --top xt1g_carve --out carve/xt1g_carve.v --json carve/carve.json \
      > carve.log 2>&1 || { echo "RESULT XT1S CARVE_FAIL $V" | tee "$D/variant.out"; return 3; }
    python3 "$HERE/gen_tb_xt1g.py" carve/carve.json "$NET/case/rom_bind.vh" carve >> carve.log 2>&1 \
      || { echo "RESULT XT1S TB_GEN_FAIL $V" | tee "$D/variant.out"; return 3; }
    [ "$V" = nobind ] && echo '// nobind mutant: no ROM_TILE bindings' > carve/rom_bind_xt1g.vh
  else
    local LN=1 NB=""
    [ "$V" = nl ] && LN=0
    [ "$V" = nobind ] && NB=--nobind
    python3 "$HERE/stage_xt1_carve.py" --out carve --landings $LN $NB > carve.log 2>&1 \
      || { echo "RESULT XT1S CARVE_FAIL $V" | tee "$D/variant.out"; return 3; }
    if [ "$V" = oldtags ]; then
      HEADS=$D/carve/qfd_dv_heads.sv; cp "$S/rtl/qwen_dv/qfd_dv_heads.sv" "$HEADS"
      grep -q 'retag = {t\[7\], b, t\[3\], a};' "$HEADS" || { echo "RESULT XT1S OLDTAGS_ANCHOR_MISSING" | tee "$D/variant.out"; return 3; }
      sed -i 's/retag = {t\[7\], b, t\[3\], a};/retag = t;   \/\/ TOK-FUNC xt1 mutant oldtags: no corridor retag/' "$HEADS"
    fi
  fi
  PYTHONPATH= python3 "$S/tools/qwen_split/gen_relay_rtl.py" "carve/$CARVE" carve/relays.sv > carve/relays.json 2>carve/relays.err \
    || { echo "RESULT XT1S RELAY_RTL_FAIL $V"; cat carve/relays.err; } | tee "$D/variant.out"
  [ -s carve/relays.sv ] || return 3
  (cd carve && sha256sum *) > carve.sha256
  local SRCS="" f
  for f in $FILES; do
    if [ "$f" = rtl/qwen_dv/qfd_dv_heads.sv ]; then SRCS="$SRCS $HEADS"; else SRCS="$SRCS $S/$f"; fi
  done
  if [ ! -x "$D/obj/Vtb" ]; then
    /usr/bin/time -v -o build.time verilator --cc --exe --build -O2 -j 24 -Wno-fatal -Wno-lint -Wno-style \
      -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --x-assign 0 --x-initial 0 +define+OT_QFD_UP4_CK_ENTRIES \
      --top-module $TOP --prefix Vtb -Mdir "$D/obj" +incdir+$D/carve $(for i in $INC; do echo "+incdir+$S/$i"; done) \
      $(for y in $YD; do echo "-y $S/$y"; done) "$S/rtl/test/qwen_dv/main2.cpp" $SRCS carve/relays.sv "carve/$CARVE" \
      "carve/$TOP.sv" > build.log 2>&1 \
      || { { echo "RESULT XT1S BUILD_FAIL $V"; grep -m30 -E '%Error' build.log; } | tee "$D/variant.out"; return 2; }
  fi
  local runs
  case $V in
    landed) runs="nominal:8:4 nominal:4:2 romswap:8:4:masks_swap";;
    nl) runs="nominal:8:4 nominal:4:2";;
    *) runs="nominal:8:4";;
  esac
  : > "$D/variant.out"
  local run mode lead gap ms tag
  for run in $runs; do
    IFS=: read -r mode lead gap ms <<< "$run"; ms=${ms:-masks_fixed}
    tag=${mode}_l${lead}_g${gap}
    python3 "$B/xt1_bench.py" gen --gold "$O/prep_c2/gold.json" --out "$D/ev_$tag.txt" --mode "$mode" --lead "$lead" --gap "$gap" \
      > "$D/gen_$tag.out" 2>&1 || { echo "RESULT XT1S GEN_FAIL $V $tag" >> "$D/variant.out"; continue; }
    "$D/obj/Vtb" +EV="$D/ev_$tag.txt" +LOG="$D/log_$tag.txt" +NCYC=$((60 + 1600 * 4)) +OT_ROM_DIR="$O/$ms" > "$D/sim_$tag.out" 2>&1
    echo "sim rc=$? ($V $tag masks $ms)" >> "$D/sim_$tag.out"
    [ -f "$D/log_$tag.txt" ] || : > "$D/log_$tag.txt"
    python3 "$B/xt1n_bench.py" check --gold-near "$O/prep_c2/gold.json" --gold-far "$O/prep_c3/gold.json" \
      --log "$D/log_$tag.txt" --mode "$mode" --lead "$lead" --gap "$gap" > "$D/result_$tag.txt" 2>&1
    echo "== $V $tag"; cat "$D/result_$tag.txt"
    grep -h '^RESULT' "$D/result_$tag.txt" | sed "s/^/[$V $tag] /" >> "$D/variant.out"
  done
}
for v in $VARS; do ( variant "$v" > "$O/variant_$v.log" 2>&1 ) & done
wait
cd "$O"
python3 "$HERE/stage_xt1.collect.py" "$RUNROOT" --variants "$VARS" --grade "$GRADE"
echo XT1_STAGE_DONE
