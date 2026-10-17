#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory}
mkdir -p "$out"
sha256sum rtl/test/qwen_lane_band/tb_qfd_halfband.sv rtl/physical/ot_qwen_halfband_lanes_slots.sv rtl/physical/ot_qwen_halfband_lanes_slots_b2_l2.sv rtl/qwen_split/qfd_band_upper_b2_l2.sv rtl/qwen_sys/lane_band_20261008/ot_qfd_band_lanes.sv > "$out/source.sha256"
bash rtl/test/qwen_lane_band/run_halfband.sh "$out/pass" -GNL=16 -GNOPS=3000 -GSLOT=2 -GRDMEM=1 -GLNK=2
if "$out/pass/obj/Vtb_qfd_halfband" +BREAK_RETURN > "$out/mut_return.log" 2>&1;then
 echo 'FAIL dropped native return-valid copy survived';exit 1
fi
grep -q 'FAIL qfd_halfband finite-phase fault lane 0 today 0 b2 1' "$out/mut_return.log"
sha256sum -c "$out/source.sha256"
echo 'PASS primary8xNL2 full16 exact + dropped return-valid mutant rejected'
