#!/bin/bash
set -eu
cd /srv/opentallas-scratch2/claude/qct12/repo
git checkout -q -B claude/qc-types-12-sta-1108 claude/qc-types-12-wave-src-1108
md5sum rtl/qwen_dv/qfd_dv_redstn2_gsafe.sv
cp rtl/qwen_dv/qfd_dv_redstn2_gsafe.sv ../gsafe.orig.sv
python3 -I tools/qwen_dv/gen_station_csafe.py --bounded 2>&1 | tail -2
md5sum rtl/qwen_dv/qfd_dv_redstn2_gsafe.sv
git status --short | head
grep -rn "redstn2_gsafe" tools/ physical/die_plan/qwen_compute 2>/dev/null | grep -v "^tools/qwen_dv/gen_station_csafe.py" | head -12 | cut -c1-200
