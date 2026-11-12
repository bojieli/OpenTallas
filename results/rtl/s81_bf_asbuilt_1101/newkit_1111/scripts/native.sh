#!/bin/bash
# native.sh OUT: BF native family hold gate on the selected slice ctl (ot_s81sl_xs4_ctl of the new-kit root):
#  positive = tools/s81_dv/bf_asbuilt_1101/tb_native_family.sv (family held from go through the samples);
#  control  = the same bench with the legacy one-edge family PULSE (family cleared on the edge after go): must fail.
set -u
O=$1; D=/srv/opentallas-scratch2/claude/s81-bfasb-1111; R=$D/root; C=$D/code
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
mkdir -p $O; cd $O || exit 4
TB=$C/tools/s81_dv/bf_asbuilt_1101/tb_native_family.sv
cp $TB tb_hold.sv
python3 -I - <<'PY'
from pathlib import Path
t=Path('tb_hold.sv').read_text();old='@(negedge clk);go=0;action=0;'
assert t.count(old)==1
Path('tb_pulse.sv').write_text(t.replace(old,'@(negedge clk);go=0;action=0;family=0; // CONTROL: legacy one-edge family pulse'))
PY
SRC="$R/rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs4.sv $R/rtl/common/ot_prefix.sv"
for k in hold pulse; do
  $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_native_family \
    -Mdir obj_$k $SRC tb_$k.sv --build-jobs 2 > build_$k.log 2>&1; echo "BUILD $k rc=$?"
  ./obj_$k/Vtb_native_family > run_$k.log 2>&1; echo "RUN $k rc=$?"; grep -m2 "NATIVE_FAMILY" run_$k.log
done
sha256sum $SRC $TB tb_hold.sv tb_pulse.sv > sources.sha256
python3 -I - <<'PY'
import json,re
from pathlib import Path
h=Path('run_hold.log').read_text();p=Path('run_pulse.log').read_text()
pos=re.search(r'^NATIVE_FAMILY_PASS samples=(\d+) clock_ps=833$',h,re.M)
neg=re.search(r'NATIVE_FAMILY_FAIL[^\n]*',p)
rec=dict(status='PASS' if pos and neg and 'NATIVE_FAMILY_FAIL' not in h else 'FAIL',
         bench='tools/s81_dv/bf_asbuilt_1101/tb_native_family.sv',dut='ot_s81sl_xs4_ctl (rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs4.sv)',
         clock_ps=833,hold_samples=int(pos[1]) if pos else None,pulse_family_fault_caught=bool(neg),
         pulse_control=neg[0] if neg else None,
         sources={l.split()[1]:l.split()[0] for l in Path('sources.sha256').read_text().splitlines()})
Path('check.json').write_text(json.dumps(rec,indent=2)+'\n');print(rec['status'],rec['hold_samples'],rec['pulse_control'])
PY
