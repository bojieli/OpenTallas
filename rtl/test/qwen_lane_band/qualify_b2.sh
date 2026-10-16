#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory}
mkdir -p "$out"
root=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$root"
sha256sum rtl/test/qwen_lane_band/tb_qfd_halfband.sv rtl/test/qwen_lane_band/tb_qfd_b2_frame.sv rtl/hdc/ot_qwen_me_spine_h_w12.sv rtl/qwen_sys/lane_band_20261008/ot_qfd_band_lanes.sv > "$out/source.sha256"
bash rtl/test/qwen_lane_band/run_halfband.sh "$out/full16" -GNL=16 -GNOPS=3000
for mut in 1 2 5; do
 if bash rtl/test/qwen_lane_band/run_halfband.sh "$out/mut$mut" -GNL=4 -GNOPS=1000 -GMUT="$mut"; then
  echo "FAIL mutant $mut survived"; exit 1
 fi
 grep -q 'FAIL qfd_halfband .*mismatching words' "$out/mut$mut/run.log"
 echo "PASS rejected arithmetic/frame mutant $mut"
done
bash rtl/test/qwen_lane_band/run_b2_frame.sh "$out/frame"
for mut in 1 2; do
 if bash rtl/test/qwen_lane_band/run_b2_frame.sh "$out/frame_mut$mut" -GMUT="$mut"; then
  echo "FAIL production frame mutant $mut survived";exit 1
 fi
 grep -q 'frame s' "$out/frame_mut$mut/run.log"
 echo "PASS rejected real consumer mutant $mut"
done
sha256sum -c "$out/source.sha256"
echo 'PASS b2 exact fullshape + arithmetic/frame/consumer negatives'
