#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=$1
mkdir -p "$out"
python3 "$root/tools/hbm_io/make_gearbox_vectors.py" "$out/vectors"
for mut in 0 1 2 3; do
  iverilog -g2012 -s tb_static_gearbox -Ptb_static_gearbox.MUT="$mut" -o "$out/m$mut.vvp" "$root/rtl/hbm_accel/io_static_20261015/ot_hbm_static_gearbox.sv" "$root/rtl/hbm_accel/io_static_20261015/tb_static_gearbox.sv"
  rc=0
  vvp "$out/m$mut.vvp" +VEC="$out/vectors" > "$out/m$mut.log" 2>&1 || rc=$?
  if [[ $mut == 0 ]]; then
    [[ $rc == 0 ]]
    grep -q 'PASS actual612/487gearbox frames=2922' "$out/m$mut.log"
  else
    [[ $rc != 0 ]]
    grep -q 'FATAL' "$out/m$mut.log"
  fi
  cat "$out/m$mut.log"
done
