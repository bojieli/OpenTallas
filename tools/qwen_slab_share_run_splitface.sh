#!/usr/bin/env bash
# Remote-only item7 recipe1. Source is pinned before launch; output never reused.
set -uo pipefail
R=$1
name=s570_l6_splitface_m7
res=$R/runs/$name
mkdir -p "$R/runs"
mkdir "$res" || exit 3
cd "$R/src" || exit 4
test -z "$(git status --porcelain)" || { echo dirty > "$res/driver.exit"; exit 4; }
git rev-parse HEAD > "$res/source_commit.txt"
python3 tools/qwen_slab_share_splitface.py model > "$res/model.json"
eval "GEO=($(python3 tools/qwen_slab_share_splitface.py args))"
python3 tools/run_abi3_physical_persistent.py --persistent-workdir "$res/work" --launch-receipt "$res/launch.json" \
  --view asap7 --top ot_qwen_slab_port_group \
  --source rtl/physical/ot_qwen_slab_port_group.sv --source rtl/common/ot_meso_fifo.sv \
  --source rtl/hdc/ot_hdc_delay.sv --source rtl/hdc/ot_hdc_fp32_mul_lat.sv --source rtl/hdc/ot_hdc_fp32_add_lat.sv \
  --source rtl/hdc/ot_hdc_fastfp.sv --source rtl/hdc/ot_hdc_prefix.sv \
  --source physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8_bb.v \
  --param MUL_LAT=6 \
  --macro-view ot_rom_4096x266_m8=physical/asap7_memory_macros/ot_rom_4096x266_m8 --macro-place-halo 2.16 2.16 \
  "${GEO[@]}" --routing-layers M2 M7 \
  --clock-port clk --clock-period-ns 0.833333 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 \
  --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --stages pnr --hold-margin-ns 0.01 \
  --orfs-var ADDER_MAP_FILE= --orfs-var NUM_CORES=16 \
  --orfs-var SDC_FILE=/src/physical/qwen_slab_m5/port_group.sdc \
  --orfs-var PDN_TCL=/src/physical/qwen_slab_m5/pdn_m5.tcl \
  --orfs-var MACRO_PLACEMENT_TCL=/src/physical/qwen_slab_share/macro_place_h570.24.tcl \
  --nickname-tag codex_item7_s570_l6_splitface_m7 --purpose signoff_target \
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
