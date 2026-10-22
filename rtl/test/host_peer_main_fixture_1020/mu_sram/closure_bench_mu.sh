#!/bin/bash
# KV-PEER12 closure bench for qkd_hr_core_peer_mu_n32 (the KV-HOST7 / Codex primitive32 miter, V5.050), MU 1 PEER:
#   closure_bench_mu.sh REPO OUT exact|invert_d|hold_clk
# exact    : original mapped MU 1 peer (evidence/original.v.gz, top qkd_hr_core_peer_sram_mu) vs the n32 copy, real p192
#            SRAM model, copy-state monitor on the coordinator reset copies u86452_c0/_c1 -> PEER_NATIVE PASS
# invert_d : one copied flop's D inverted (u86452_c1) -> PEER_NATIVE FAIL COPY_STATE
# hold_clk : one copied flop's CLK tied 0 (u86452_c1) -> PEER_NATIVE FAIL COPY_STATE
set -euo pipefail
R=$(cd "$1" && pwd); OUT=$2; MODE=$3
P=$R/rtl/test/host_peer_main_fixture_1020/primitive32; E=$R/rtl/qwen_sys/host_peer_mu_n32_1020
mkdir -p "$OUT/models"; cd "$OUT"
zcat "$E/evidence/original.v.gz" > original.v
cp "$E/qkd_hr_core_peer_mu_n32.sv" qkd_hr_core_peer_mu_n32.sv
cp "$P/canonical_ASR_normalized.v" "$P/canonical_DFF_normalized.v" .
cp "$P/models/comb_models.v" models/
cp "$R/physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1_p192_mir/ot_sram_1r1w_32x546_m1_p192_mir.v" macro_bb.v
python3 - "$MODE" "$P/tb_peer_native_copycheck.sv" <<'PY'
import re,sys
from pathlib import Path
mode,tb=sys.argv[1],sys.argv[2]
s=Path('original.v').read_text(); assert 'module qkd_hr_core_peer_sram_mu(' in s
Path('reference_native.v').write_text(s.replace('module qkd_hr_core_peer_sram_mu(','module qkd_hr_core_peer_ref_native(',1))
t=Path(tb).read_text()
for a,b in (('qkd_hr_core_peer_n32 dut(','qkd_hr_core_peer_mu_n32 dut('),('dut.u59981_c0.u_cell.QN!==dut.u59981_c1.u_cell.QN','dut.u86452_c0.u_cell.QN!==dut.u86452_c1.u_cell.QN')):
  assert t.count(a)==1,a; t=t.replace(a,b)
Path('tb_peer_native.sv').write_text(t)
if mode!='exact':
  p=Path('qkd_hr_core_peer_mu_n32.sv'); t=p.read_text(); hit=re.search(r"(?m)^.*\bu86452_c1 \(.*?\);$",t); assert hit
  old=hit.group()
  new,n=(re.subn(r"\.D\(([^()]+)\)",r".D(~\1)",old) if mode=='invert_d' else re.subn(r"\.CLK\(([^()]+)\)",".CLK(1'b0)",old))
  assert n==1; p.write_text(t[:hit.start()]+new+t[hit.end():])
PY
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x "$V" ] || V=/opt/verilator-5.050/bin/verilator; [ -x "$V" ] || V=$(command -v verilator)
"$V" --version
"$V" --binary --timing --x-initial unique --x-assign unique -Wno-fatal -DOT_MEM_NO_INIT -j ${VJ:-8} --top-module tb_peer_native --Mdir obj reference_native.v qkd_hr_core_peer_mu_n32.sv models/comb_models.v canonical_ASR_normalized.v canonical_DFF_normalized.v macro_bb.v tb_peer_native.sv > build.log 2>&1 || { grep -m20 '%Error' build.log; exit 1; }
obj/Vtb_peer_native +verilator+seed+27 +verilator+rand+reset+2 2>&1 | tee run.log
rm -rf obj
