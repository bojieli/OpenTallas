#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory}; mode=${2:-0}; mkdir -p "$out"
python3 - "$out" "$mode" <<'PY'
from pathlib import Path
import sys,shlex,hashlib
out=Path(sys.argv[1]); mode=int(sys.argv[2])
assert hashlib.sha256(Path('rtl/hdc/ot_qwen_w12_matvec.sv').read_bytes()).hexdigest()=='bb84cbf6b865c5c448aa31c4facdf766100fdafd712bfed18b516778c41f66f3', 'legacy arithmetic source changed'
text=Path('rtl/physical/ot_qwen_tile_lsl_fp1.sv').read_text()
if mode==1:
 text=text.replace('output reg  [7:0]','output wire [7:0]').replace('output reg           tfault','output wire          tfault')
 a=text.index('    always @(posedge clk or negedge rs)\n')
 text=text[:a]+'    assign {tfault,lfault}=fault_pin_raw;\nendmodule\n'
elif mode==3:
 text='`define OT_LSL_RST_MUT\n'+text
elif mode==2:
 text=text.replace('else begin {tfault,lfault} <= fault_pin_raw; end','else begin {tfault,lfault} <= 0; end')
(out/'wrapper.sv').write_text(text)
src=next(x for x in Path('physical/qwen_die_masters/cfg/qfd_tile_lsl6.env').read_text().splitlines() if x.startswith('SRCS='))
paths=shlex.split(src[5:])[0].split()
(out/'sources.list').write_text('\n'.join(paths)+'\n')
(out/'source_hashes.txt').write_text('\n'.join(hashlib.sha256(Path(p).read_bytes()).hexdigest()+'  '+p for p in paths+['rtl/physical/ot_qwen_tile_lsl_fp1.sv','rtl/test/qwen_split/tb_qwen_tile_lsl_fp1.sv'])+'\n')
PY
mapfile -t sources < "$out/sources.list"
# A mutant FAILS by design ($fatal -> vvp exit 1): print the simulator verdict BEFORE returning its status, so the
# loop's fail_regex sees the observed mismatch (set -e used to exit before the cat: "expected FAIL but rc=1").
# A compile error is reported as such and never matches the mutant's fail_regex.
if ! iverilog -g2012 -s tb_qwen_tile_lsl_fp1 -o "$out/sim.vvp" rtl/test/qwen_split/tb_qwen_tile_lsl_fp1.sv "$out/wrapper.sv" "${sources[@]}" > "$out/compile.log" 2>&1; then
 cat "$out/compile.log"; echo "COMPILE_ERROR lsl fault-pin bench (mode $mode)"; exit 2
fi
rc=0
vvp "$out/sim.vvp" > "$out/result.log" 2>&1 || rc=$?
cat "$out/result.log"
exit "$rc"
