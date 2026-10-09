#!/bin/bash
set -eu
out=$1
mut=${2:-0}
mkdir -p "$out"
leaf=rtl/hdc/ot_hdc_accept.sv
if [ "$mut" = 1 ]; then
  sed 's/(s\[i + 1\] == t\[i\])/(s[i + 1][16:0] == t[i][16:0])/' "$leaf" > "$out/leaf_mut.sv"
  leaf="$out/leaf_mut.sv"
elif [ "$mut" = 2 ]; then
  sed 's/bonus <= t\[a_c\];/bonus <= t[a_c ^ 1];/' "$leaf" > "$out/leaf_mut.sv"
  leaf="$out/leaf_mut.sv"
fi
/usr/bin/time -v iverilog -g2012 -s tb_hgi_accept18 -o "$out/sim.vvp" "$leaf" rtl/hbm_accel/generic/ot_hgi_mtp_accept18.sv rtl/test/hbm_generic/tb_hgi_accept18.sv > "$out/build.log" 2>&1
set +e
/usr/bin/time -v vvp "$out/sim.vvp" > "$out/run.log" 2>&1
rc=$?
cat "$out/run.log"
exit "$rc"
