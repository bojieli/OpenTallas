#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
image=openroad/orfs:asap7lock
mkdir -p src/physical/qwen_die_masters src/physical/common_flow
for pair in c:e d:f; do
 old=${pair%:*}; new=${pair#*:}
 for mutant in none missing_list duplicate_anchor missing_anchor unfixed_anchor unexpected_hold unowned_fixed duplicate_hook; do
  case_dir=$PWD/cases/${new}_${mutant}
  mkdir -p "$case_dir"
  ln -sf "/stage/${old}.odb" "$case_dir/input.odb"
  cp "${old}_anchors.txt" "$case_dir/expected_anchors.txt"
  cp "band_n32${new}.tcl" "$case_dir/band.tcl"
  cp proof.tcl "$case_dir/proof.tcl"
  set +e
  docker run --rm --cpus=2 --memory=8g -e MUTANT="$mutant" -v "$PWD:/stage" -v "$PWD/src:/src:ro" -v "$case_dir:/work" "$image" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/proof.tcl > "$case_dir/run.log" 2>&1
  rc=$?
  set -e
  if [[ $mutant == none ]]; then
   [[ $rc == 0 ]] && grep 'ORDER_HARDBAND_PROOF PASS' "$case_dir/run.log" || { tail -n 12 "$case_dir/run.log";exit 1;}
  else
   [[ $rc != 0 ]] && ! grep -q 'MUTANT_SURVIVED' "$case_dir/run.log" || { tail -n 12 "$case_dir/run.log";exit 1;}
   grep 'Error:.*ORDER_BAND' "$case_dir/run.log" | tail -n 1 || { tail -n 12 "$case_dir/run.log";exit 1;}
   echo "ORDER_HARDBAND_NEGATIVE REFUSED variant=$new mutant=$mutant rc=$rc"
  fi
 done
done
