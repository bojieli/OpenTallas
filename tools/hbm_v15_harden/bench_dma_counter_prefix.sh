#!/usr/bin/env bash
set -euo pipefail
out=${1:?output}; mut=${2:-0};mkdir -p "$out"
d=rtl/hbm_accel/generic/peers/static
cp "$d/ot_hgi_dma_back_static_vp4_banks.sv" "$out/dut.sv"
if [ "$mut" = 1 ];then
 python3 - "$out/dut.sv" <<'PYCODE'
import pathlib,sys
p=pathlib.Path(sys.argv[1]);s=p.read_text();a="carry_in = ((pref_g | pref_p) << 1) | 32'd1;";assert s.count(a)==1;p.write_text(s.replace(a,a.replace("32'd1","32'd0")))
PYCODE
fi
iverilog -g2012 -s tb -o "$out/run.vvp" "$out/dut.sv" "$d/tb_dma_counter_prefix.sv"
vvp "$out/run.vvp"
