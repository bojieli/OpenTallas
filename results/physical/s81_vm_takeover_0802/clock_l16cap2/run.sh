#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
for variant in base collapse; do
 mkdir -p "src_$variant"
 cp src/* "src_$variant/"
 if [ "$variant" = collapse ]; then
  python3 - <<'MUT'
from pathlib import Path
p=Path('src_collapse/dsfd_vm_static512_suhc.sv');s=p.read_text();old='.ck_bank(ck_bank[32*s+:32])';assert s.count(old)==1;s=s.replace(old,'.ck_bank({32{ck_bank[32*s]}})');p.write_text(s)
MUT
 fi
 files=();while read -r f; do files+=("src_$variant/$f");done < files.txt
 "$V" +define+DSFD_SP_VM_MIX4 --binary --timing -O1 -Wno-fatal -j 2 -MAKEFLAGS "OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0" --top-module tb_vm_native_clock_pins --Mdir "$PWD/obj_$variant" -o tb tb_vm_native_clock_pins.sv "${files[@]}" > "build_$variant.log" 2>&1
 "$PWD/obj_$variant/tb" > "run_$variant.log" 2>&1
 if [ "$variant" = base ];then grep -q '^VM_NATIVE_PIN_PASS$' "run_$variant.log";! grep -q '^VM_NATIVE_PIN_FAIL$' "run_$variant.log";else grep -q '^VM_NATIVE_PIN_FAIL$' "run_$variant.log";! grep -q '^VM_NATIVE_PIN_PASS$' "run_$variant.log";fi
 cat "run_$variant.log"
done
echo VM_NATIVE_L16_CAP2_CLOCK_GATE_PASS
