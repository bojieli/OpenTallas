#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory}
mkdir -p "$out"
bash rtl/test/qwen_lane_band/run_b2_frame.sh "$out/pass"
for mut in 1 2;do
 if bash rtl/test/qwen_lane_band/run_b2_frame.sh "$out/mut$mut" -GMUT="$mut";then
  echo "FAIL frame consumer mutant$mut survived";exit 1
 fi
 grep -q 'frame s' "$out/mut$mut/run.log"
 echo "PASS rejected real consumer mutant$mut"
done
