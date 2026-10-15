#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=$1
mkdir -p "$out"
<<<<<<< HEAD:tools/hbm_io/run_frame_transport_gate.sh
python3 "$root/tools/hbm_io/make_gearbox_vectors.py" "$out/vectors" --frame 613
for mut in 0 1 2 3; do
  iverilog -g2012 -s tb_static_frame_transport -Ptb_static_frame_transport.MUT="$mut" -o "$out/m$mut.vvp" "$root/rtl/hbm_accel/io_static_20261015/ot_hbm_static_gearbox.sv" "$root/rtl/hbm_accel/io_static_20261015/ot_hbm_static_frame_transport.sv" "$root/rtl/hbm_accel/io_static_20261015/tb_static_frame_transport.sv"
=======
frame=${2:-612}
python3 "$root/tools/hbm_io/make_gearbox_vectors.py" "$out/vectors" --frame "$frame"
for mut in 0 1 2 3; do
  iverilog -g2012 -s tb_static_gearbox -Ptb_static_gearbox.MUT="$mut" -Ptb_static_gearbox.F="$frame" -o "$out/m$mut.vvp" "$root/rtl/hbm_accel/io_static_20261015/ot_hbm_static_gearbox.sv" "$root/rtl/hbm_accel/io_static_20261015/tb_static_gearbox.sv"
>>>>>>> 2e216a971 (Preserve endpoint valid in explicit 613-bit static transport and reprove gearbox ratios):tools/hbm_io/run_gearbox_gate.sh
  rc=0
  vvp "$out/m$mut.vvp" +VEC="$out/vectors" > "$out/m$mut.log" 2>&1 || rc=$?
  if [[ $mut == 0 ]]; then
    [[ $rc == 0 ]]
<<<<<<< HEAD:tools/hbm_io/run_frame_transport_gate.sh
    grep -q 'PASS actual613validtransport' "$out/m$mut.log"
=======
    grep -q "PASS actualgearbox framebits=$frame wordbits=487 frames=2922" "$out/m$mut.log"
>>>>>>> 2e216a971 (Preserve endpoint valid in explicit 613-bit static transport and reprove gearbox ratios):tools/hbm_io/run_gearbox_gate.sh
  else
    [[ $rc != 0 ]]
    grep -q 'FATAL' "$out/m$mut.log"
  fi
  cat "$out/m$mut.log"
done
