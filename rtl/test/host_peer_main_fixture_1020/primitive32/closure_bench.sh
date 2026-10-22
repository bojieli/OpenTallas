#!/bin/bash
# KV-HOST7 closure bench for qkd_hr_core_peer_n32 (Codex primitive32 miter, V5.050):
#   closure_bench.sh REPO OUT exact|invert_d|hold_clk
# exact     : original mapped peer vs n32 copy source, real p192 SRAM model, copy-state monitor -> PEER_NATIVE PASS
# invert_d  : one copied flop's D inverted   -> PEER_NATIVE FAIL COPY_STATE (witness native_invert_d/run_peer_native.log)
# hold_clk  : one copied flop's CLK tied 0   -> PEER_NATIVE FAIL COPY_STATE (witness native_hold_clk/run_peer_native.log)
set -euo pipefail
R=$(cd "$1" && pwd); OUT=$2; MODE=$3
P=$R/rtl/test/host_peer_main_fixture_1020/primitive32
mkdir -p "$OUT/models"; cd "$OUT"
zcat "$P/original.v.gz" > original.v
cp "$R/rtl/qwen_sys/host_peer_n32_1020/qkd_hr_core_peer_n32.sv" qkd_hr_core_peer_n32.sv
cp "$P/canonical_ASR_normalized.v" "$P/canonical_DFF_normalized.v" .
cp "$P/models/comb_models.v" models/
cp "$R/physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1_p192_mir/ot_sram_1r1w_32x546_m1_p192_mir.v" macro_bb.v
cp "$P/tb_peer_native_copycheck.sv" tb_peer_native.sv
python3 - "$MODE" <<'PY'
import re,sys
from pathlib import Path
mode=sys.argv[1]
s=Path('original.v').read_text(); assert 'module qkd_hr_core_peer_sram(' in s
Path('reference_native.v').write_text(s.replace('module qkd_hr_core_peer_sram(','module qkd_hr_core_peer_ref_native(',1))
if mode!='exact':
  p=Path('qkd_hr_core_peer_n32.sv'); t=p.read_text(); hit=re.search(r"(?m)^.*\bu59981_c1 \(.*?\);$",t); assert hit
  old=hit.group()
  new,n=(re.subn(r"\.D\(([^()]+)\)",r".D(~\1)",old) if mode=='invert_d' else re.subn(r"\.CLK\(([^()]+)\)",".CLK(1'b0)",old))
  assert n==1; p.write_text(t[:hit.start()]+new+t[hit.end():])
PY
V=/opt/verilator-5.050/bin/verilator; [ -x "$V" ] || V=$(command -v verilator)
"$V" --version
"$V" --binary --timing --x-initial unique --x-assign unique -Wno-fatal -DOT_MEM_NO_INIT -j 4 --top-module tb_peer_native --Mdir obj reference_native.v qkd_hr_core_peer_n32.sv models/comb_models.v canonical_ASR_normalized.v canonical_DFF_normalized.v macro_bb.v tb_peer_native.sv > build.log 2>&1
obj/Vtb_peer_native +verilator+seed+27 +verilator+rand+reset+2 2>&1 | tee run.log
