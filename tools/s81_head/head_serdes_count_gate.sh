#!/usr/bin/env bash
set -u
out=${1:?fresh output directory}
root=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$out"
link=$root/rtl/dsrom_sys/s81_link
# Frozen actual source before the arithmetic-only candidate, not a restated model.
git -C "$root" show b5c9faba035cf124b8ecea8b4003a63f4192df50:rtl/dsrom_sys/s81_link/ot_s81_kp4_dchn.sv | sed 's/module ot_s81_kp4_dchn /module ot_s81_kp4_dchn_count_gold /' > "$out/gold.sv"
python3 - "$root" "$out" <<'PY'
from pathlib import Path
import sys
root,out=map(Path,sys.argv[1:]);s=(root/'rtl/dsrom_sys/s81_head/tb_head_serdes_dchn.sv').read_text()
s=s.replace('ot_s81_kp4_dchn #(.MUT(0)) a(','ot_s81_kp4_dchn_count_gold #(.MUT(0)) a(')
(out/'tb.sv').write_text(s)
(out/'count_miter.sv').write_text('''module root_count_miter(input[54:0]roots,input last_chunk,output eq);
wire[5:0]got;ot_s81_kp4_root_count u(.roots(roots),.last_chunk(last_chunk),.count(got));
reg[6:0]pt[0:126];integer i;
always@*begin
for(i=0;i<64;i=i+1)pt[63+i]=(i<55)?{6'd0,(roots[i]&&!(i>=49&&last_chunk))}:7'd0;
for(i=62;i>=0;i=i-1)pt[i]=pt[2*i+1]+pt[2*i+2];
end
assign eq=got==pt[0][5:0];endmodule
''')
PY
timeout 300 yosys -Q -T -p "read_verilog -sv -I$link $link/ot_s81_kp4_dchn.sv $out/count_miter.sv; hierarchy -top root_count_miter; proc; flatten; opt; techmap; opt; sat -verify -prove eq 1 -show-inputs" > "$out/formal.log" 2>&1 & formal=$!
verilator --binary --timing -j 4 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style --top-module tb_head_serdes_dchn +incdir+"$link" --Mdir "$out/obj" -o tb "$link/ot_s81_kp4_common.sv" "$link/ot_s81_kp4_dchn.sv" "$out/gold.sv" "$out/tb.sv" > "$out/build.log" 2>&1
build_rc=$?
if [ "$build_rc" = 0 ]; then "$out/obj/tb" > "$out/run.log" 2>&1; bench_rc=$?; else bench_rc=$build_rc; fi
wait "$formal"; formal_rc=$?
printf '{"formal_rc":%s,"bench_rc":%s,"added_cycles":0,"physical_timing":"PENDING","signed":false}\n' "$formal_rc" "$bench_rc" > "$out/verdict.json"
cat "$out/verdict.json"
cat "$out/run.log" 2>/dev/null
[ "$formal_rc" = 0 ] && [ "$bench_rc" = 0 ]
