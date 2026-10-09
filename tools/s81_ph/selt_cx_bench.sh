#!/usr/bin/env bash
# Remote admitted build only. Preserve every distinct build/run directory.
set -euo pipefail
out=$1; tag=$2; pace=${3:-2}; mutant=${4:-}
mkdir -p "$out/$tag"
flags=(); if [[ -n "$mutant" ]]; then flags+=("+define+$mutant"); fi
verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style \
  --top-module tb_s81ph_sel -GREADLAT=2 -GSTATIC_MAP=1 -GPIPE2=1 -GCMP_RETIME=1 \
  -GSEARCH_PIPE=1 -GSLAT=3 -GPACE="$pace" "${flags[@]}" -Mdir "$out/$tag/obj" \
  rtl/common/ot_fwd_link_stage.sv rtl/hdc/ot_hdc_prefix.sv \
  physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v \
  rtl/hdc/v41x/ot_hdc_v41x_sel_lib.sv rtl/hdc/v41x/ot_hdc_v41x_sel_slice.sv rtl/hdc/v41x/ot_hdc_v41x_sel.sv \
  rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel.sv \
  rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_lib.sv \
  rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_slice.sv \
  rtl/dsrom_sys/s81_ph/ot_s81ph_sel_pipeline.sv \
  rtl/dsrom_sys/s81_ph/ot_s81ph_sel_ctl_half.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel_ctl_pp.sv \
  rtl/dsrom_sys/s81_ph/ot_s81ph_sel.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel_tile.sv \
  rtl/dsrom_sys/s81_ph/dsfd_bk_selector.sv rtl/dsrom_sys/s81_ph/test/tb_s81ph_sel.sv \
  >"$out/$tag/build.log" 2>&1
"$out/$tag/obj/Vtb_s81ph_sel" >"$out/$tag/run.log" 2>&1
python3 - "$out/$tag/run.log" "$mutant" <<'CHECK'
import sys
from pathlib import Path
text=Path(sys.argv[1]).read_text()
passed='RESULT PASS' in text
if sys.argv[2]:
    if passed or not ('RESULT FAIL' in text or 'FAIL ' in text):
        raise SystemExit('MUTANT NOT REJECTED')
    print('MUTANT REJECTED',sys.argv[2])
else:
    if not passed: raise SystemExit('POSITIVE FAIL')
    print(next(l for l in text.splitlines() if l.startswith('RESULT PASS')))
CHECK
