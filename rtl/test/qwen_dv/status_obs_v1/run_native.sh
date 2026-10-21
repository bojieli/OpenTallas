#!/bin/bash
# Bounded native codec census only; no placement or timing claim.
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/yosys-0.68/bin:$PATH
root=$(pwd)
mkdir -p native
for top in ot_qwen_status_obs_v1_state ot_qwen_d2d_status_tx_s7_obs1 ot_qwen_d2d_status_rx_sfm3_obs1; do
  out=$root/native/$top
  mkdir -p "$out"
  {
    for lib in "$root"/libs/*.lib; do printf 'read_liberty -lib %s\n' "$lib"; done
    printf 'read_verilog -sv -DSYNTHESIS %s %s\n' rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_safe7.sv rtl/qwen_sys/d2d_static_20261015/ot_qwen_status_observers_v1.sv
    printf 'hierarchy -check -top %s\nsynth -top %s -flatten\n' "$top" "$top"
    printf 'dfflibmap -liberty %s/libs/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib\n' "$root"
    printf 'abc'
    for family in SIMPLE INVBUF AO OA; do printf ' -liberty %s' "$root"/libs/asap7sc7p5t_${family}_RVT_TT_*.lib; done
    printf '\nopt_clean -purge\nautoname\nwrite_verilog -noattr %s/mapped.v\nstat\n' "$out"
  } > "$out/run.ys"
  yosys -ql "$out/synth.log" "$out/run.ys"
  args=()
  for lib in "$root"/libs/*.lib; do args+=(--liberty "$lib"); done
  set +e
  python3 tools/ref_tile/native_census.py --netlist "$out/mapped.v" --top "$top" --out "$out/census.json" "${args[@]}" > "$out/census.log" 2>&1
  rc=$?
  set -e
  printf 'NATIVE_CENSUS top=%s exit=%s\n' "$top" "$rc"
  cat "$out/census.log"
done
