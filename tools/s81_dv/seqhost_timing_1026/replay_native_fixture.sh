#!/bin/bash
# Run ONLY through ot-run in a fresh prepared source directory with the
# generated mux_boot.memh from native_boot_fixture.json. Fixed fixture dates.
set -euo pipefail
mkdir run
$HOME/.local/opentallas-tools/bin/verilator --binary --timing -Wno-fatal -Wno-WIDTH -Wno-PINMISSING -Wno-TIMESCALEMOD --top-module tb_seqhost_timing --build-jobs 4 -MAKEFLAGS 'OPT_FAST=-O1 OPT_SLOW=-O0' --Mdir run/obj -f defines.f -f files.f >run/build.log 2>&1
run/obj/Vtb_seqhost_timing >run/reference.log 2>&1
grep -q '^PASS' run/reference.log
run/obj/Vtb_seqhost_timing +mux_boot=mux_boot.memh +mux_boot_words=35 +ks0_pin_edge=901 +ks_gap=152 >run/native.log 2>&1
grep -q '^PASS' run/native.log
python3 - <<'PY'
from pathlib import Path
ref=[x for x in Path('run/reference.log').read_text().splitlines() if x.startswith('SEQ_')]
nat=[x for x in Path('run/native.log').read_text().splitlines() if x.startswith('SEQ_')]
assert ref==nat, 'generated boot changed real seqhost edge or payload'
p=Path('mux_boot.memh');words=[int(x,16) for x in p.read_text().split()]
words[2]^=1<<33
Path('mut_rl.memh').write_text(''.join(f'{x:0129x}\n' for x in words))
print('NATIVE_BOOT_MITER PASS exact whole trace')
PY
run/obj/Vtb_seqhost_timing +mux_boot=mut_rl.memh +mux_boot_words=35 +ks0_pin_edge=901 +ks_gap=152 >run/mut_rl.log 2>&1
grep -q '^FAIL' run/mut_rl.log
grep -E '^SEQ_TIMING|^PASS|^FAIL' run/native.log run/mut_rl.log
