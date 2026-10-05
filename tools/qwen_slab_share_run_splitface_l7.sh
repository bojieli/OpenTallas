#!/usr/bin/env bash
# Remote-only item7 prescribed CTS LAT7 fallback. Source is pinned before launch; output never reused.
set -uo pipefail
R=$1
name=s570_l7_splitface_m7
res=$R/runs/$name
mkdir -p "$R/runs"
mkdir "$res" || exit 3
cd "$R/src" || exit 4
test -z "$(git status --porcelain)" || { echo dirty > "$res/driver.exit"; exit 4; }
git rev-parse HEAD > "$res/source_commit.txt"
python3 tools/qwen_slab_share_splitface_l7.py model > "$res/model.json"
eval "GEO=($(python3 tools/qwen_slab_share_splitface_l7.py args))"
# This parameter changes result latency: gate the selected LAT7 against the
# existing source oracle before physical work; no LAT6 replay or host math.
iverilog -g2012 -s tb_qwen_slab_port_group -P tb_qwen_slab_port_group.MUL_LAT=7 \
  -o "$res/bench.vvp" rtl/test/tb_qwen_slab_port_group.sv \
  rtl/physical/ot_qwen_slab_port_group.sv rtl/common/ot_meso_fifo.sv \
  rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv \
  rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fpu.sv \
  rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv > "$res/bench_build.log" 2>&1
rc=$?; echo "$rc" > "$res/bench_build.exit"
if [ "$rc" != 0 ]; then echo "$rc" > "$res/driver.exit"; exit "$rc"; fi
vvp "$res/bench.vvp" > "$res/bench.log" 2>&1
rc=$?; echo "$rc" > "$res/bench.exit"
if [ "$rc" != 0 ] || grep -q 'FAIL' "$res/bench.log" || ! grep -q 'PASS' "$res/bench.log"; then
  echo 86 > "$res/driver.exit"; exit 86
fi
python3 tools/run_abi3_physical_persistent.py --persistent-workdir "$res/work" --launch-receipt "$res/launch.json" \
  --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited \
  --view asap7 --top ot_qwen_slab_port_group \
  --source rtl/physical/ot_qwen_slab_port_group.sv --source rtl/common/ot_meso_fifo.sv \
  --source rtl/hdc/ot_hdc_delay.sv --source rtl/hdc/ot_hdc_fp32_mul_lat.sv --source rtl/hdc/ot_hdc_fp32_add_lat.sv \
  --source rtl/hdc/ot_hdc_fastfp.sv --source rtl/hdc/ot_hdc_prefix.sv \
  --source physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8_bb.v \
  --param MUL_LAT=7 \
  --macro-view ot_rom_4096x266_m8=physical/asap7_memory_macros/ot_rom_4096x266_m8 --macro-place-halo 2.16 2.16 \
  "${GEO[@]}" --routing-layers M2 M7 \
  --clock-port clk --clock-period-ns 0.833333 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --stages pnr --hold-margin-ns 0.01 \
  --orfs-var ADDER_MAP_FILE= --orfs-var NUM_CORES=16 \
  --orfs-var SDC_FILE=/src/physical/qwen_slab_m5/port_group.sdc \
  --orfs-var PDN_TCL=/src/physical/qwen_slab_m5/pdn_m5.tcl \
  --orfs-var MACRO_PLACEMENT_TCL=/src/physical/qwen_slab_share/macro_place_h570.24.tcl \
  --nickname-tag codex_item7_s570_l7_splitface_m7 --purpose signoff_target \
  --output "$res/physical.json" > "$res/driver.log" 2>&1
rc=$?
echo "$rc" > "$res/driver.exit"
if compgen -G "$res/work/orfs/results/asap7/*/base/6_final.odb" > /dev/null; then
  python3 tools/w18/corner_sta.py --orfs-dir "$res/work/orfs" \
    --macro physical/asap7_memory_macros/ot_rom_4096x266_m8 \
    --output "$res/corner_sta.json" > "$res/corner.log" 2>&1
  echo $? > "$res/corner.exit"
fi
exit "$rc"
