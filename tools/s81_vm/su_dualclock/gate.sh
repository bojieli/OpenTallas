#!/bin/bash
# Run only through ot-run admission, from a frozen prepare.py output directory.
set -euo pipefail
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
for name in base pad_bypass write_bit;do
 mkdir -p "$name/src"
 cp src/*.sv src/*.v "$name/src/"
 if [ "$name" != base ];then python3 - "$name" <<'PY'
from pathlib import Path
import sys
name=sys.argv[1];p=Path(name)/'src/ot_s81_su_vm_static_bridge.sv';s=p.read_text()
if name=='pad_bypass':
 old='.s_v(pad_v),.s_d(pad_data)';new='.s_v(t_rs_v[p]),.s_d(t_rs_data[512*p+:512])'
else:
 old='.s_d({s_wq_data[512*p+:512],s_wq_mask[16*p+:16],s_wq_row[14*p+:14]})'
 new=".s_d({(s_wq_data[512*p+:512]^512'd1),s_wq_mask[16*p+:16],s_wq_row[14*p+:14]})"
assert s.count(old)==1;s=s.replace(old,new);p.write_text(s)
PY
 fi
 "$V" --binary --timing -O1 -Wno-fatal -j 8 -MAKEFLAGS 'OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0' --top-module tb_su_vm_dualclock --Mdir "$PWD/$name/obj" -o tb "$name"/src/*.sv "$name"/src/*.v >"$name/build.log" 2>&1
 if [ "$name" = base ];then
  for seed in 1 2;do "$name/obj/tb" +seed=$seed >"$name/seed$seed.log" 2>&1;grep -q '^SU_VM_DUAL_PASS$' "$name/seed$seed.log";done
 else
  "$name/obj/tb" +seed=1 >"$name/run.log" 2>&1
  grep -q '^SU_VM_DUAL_FAIL$' "$name/run.log"
  if [ "$name" = write_bit ];then grep -q 'SERIAL_DATA_FAIL' "$name/run.log";fi
 fi
done
echo SU_VM_DUALCLOCK_GATE_PASS
