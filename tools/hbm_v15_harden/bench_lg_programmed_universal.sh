#!/usr/bin/env bash
# The actual NE 812-word LG production programme (results/arch/hbm_vm_lg_split_1015/programme/NE_812.hex) re-packed
# from the NE layout into the universal layout and played by the ONE master hfd_hgi_vm_calendar inside the real LG
# split/bank composition (tb_hbm_vm_lg_static_programmed, controller rebound; host waits the 2 release edges).
# mut 0 exact; mut 1 = the tb's own dropped-response mutant (must FAIL).
set -euo pipefail
out=$(realpath -m "${1:?out}"); mut=${2:-0}; mkdir -p "$out"
d=rtl/hbm_accel/generic/vm/static
python3 - "$out" <<'PY'
import json, sys
from pathlib import Path
sys.path.insert(0, 'tools'); import hbm_vm_static_calendar as C
abi = json.loads(Path('results/arch/hbm_vm_static_1014/quadrant_abi.json').read_text())
Q, U = C.layout(abi, 'NE'), C.layout(abi, 'NE', universal=True)
out = []
for line in Path('results/arch/hbm_vm_lg_split_1015/programme/NE_812.hex').read_text().split():
    w = int(line, 16); v = 0
    for fq, fu in zip(Q['fields'], U['fields']):
        v |= ((w >> fq['lo']) & ((1 << fq['bits']) - 1)) << fu['lo']
    assert (w >> Q['bits']) & ((1 << (224 - Q['bits'])) - 1) == 0
    out.append(f'{(w >> 224 << 224) | v:064x}')
Path(sys.argv[1], 'NE_812.hex').write_text('\n'.join(out) + '\n')
print('repacked', len(out), 'words NE ->', U['bits'], 'bit universal layout')
PY
sed -e 's/hfd_hgi_vm_calendar_NE controller(.clk(clk),/hfd_hgi_vm_calendar controller(.clk(clk),.clk_cap(clk),/' -e 's/repeat(8)tick();rst_n=1;/repeat(8)tick();rst_n=1;tick();tick();/' \
    $d/tb_hbm_vm_lg_static_programmed.sv > "$out/tb.sv"
grep -q 'hfd_hgi_vm_calendar controller(.clk(clk),.clk_cap(clk),' "$out/tb.sv" && grep -q 'rst_n=1;tick();tick();' "$out/tb.sv"
srcs=("$PWD/$d/ot_hbm_vm_lg_static_bank.sv" "$PWD/$d/ot_hbm_vm_lg_static_split.sv" "$PWD/$d/ot_vms_bank_static.sv"
      "$PWD/$d/ot_vms_calendar_static_xcap.sv" "$PWD/$d/hfd_hgi_vm_calendar.sv"
      "$PWD/physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v" "$out/tb.sv")
cd "$out"
iverilog -g2012 -s tb_hbm_vm_lg_static_programmed -Ptb_hbm_vm_lg_static_programmed.MUT=$mut -o sim "${srcs[@]}"
vvp sim > sim.log 2>&1 || true
cat sim.log | tail -3
grep -q '^VM_LG_PROGRAMMED PASS' sim.log && echo "VM_LG_PROGRAMMED_UNIVERSAL PASS"
