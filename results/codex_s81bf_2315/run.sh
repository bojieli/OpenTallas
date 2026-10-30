#!/bin/bash
set -eu
cd /srv/opentallas-scratch2/claude/codex-s81bf-2315/xpos
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
python3 - <<'PY'
from pathlib import Path
p=Path('rtl/ot_v41_segtree5.sv');s=p.read_text();assert s.count('.d(x_pos_d)')==1
Path('mut/ot_v41_segtree5.sv').write_text(s.replace('.d(x_pos_d)',".d(x_pos_d ^ 3'b001)"))
PY
COMMON="rtl/ot_v41_kreg.sv rtl/ot_v41_fadd.sv rtl/ot_prefix.sv rtl/ot_hdc_delay.sv tb_xpos.sv"
$V --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_xpos --Mdir obj_pass -j 4 -CFLAGS -O1 $COMMON rtl/ot_v41_segtree5.sv > build_pass.log 2>&1
for s in 1 7 23; do obj_pass/Vtb_xpos +seed=$s > pass_s$s.log 2>&1; grep XPOS_PASS pass_s$s.log; done
$V --binary --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_xpos --Mdir obj_mut -j 4 -CFLAGS -O1 $COMMON mut/ot_v41_segtree5.sv > build_mut.log 2>&1
set +e
obj_mut/Vtb_xpos +seed=1 > mutant.log 2>&1
m=$?
set -e
test "$m" != 0
grep XPOS_BAD_PAYLOAD mutant.log
echo XPOS_MUTANT_CAUGHT
