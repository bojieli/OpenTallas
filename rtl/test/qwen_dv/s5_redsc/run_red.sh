#!/usr/bin/env bash
set -euo pipefail
work=$1
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version | grep '5.050'
leaf=rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv
python3 rtl/test/qwen_dv/s5_redsc/generate.py "$leaf" "$work/generated"
# Extract only the actual red and reset leaf; unrelated leaf masters are outside this vehicle.
python3 - "$leaf" "$work/generated/dut.sv" <<'PY'
from pathlib import Path
import re,sys
s=Path(sys.argv[1]).read_text()
Path(sys.argv[2]).write_text('\n'.join(re.search(r'module '+n+r'\b.*?endmodule',s,re.S).group() for n in ('qfd_dv_s5_rst2','qfd_dv_s5_red')))
PY
for ring in 0 1; do
 for mut in 0 1; do
  dir="$work/ring${ring}_mut${mut}"
  mkdir -p "$dir"
  defs=(+define+MUT=0)
  [[ $ring == 0 ]] || defs+=(+define+OT_S5_RED_RING)
  [[ $mut == 0 ]] || defs+=(+define+OT_S5_RED_MUT)
  verilator --binary --timing -j 4 -Wno-fatal "${defs[@]}" --top-module tb_red --Mdir "$dir/obj" "$work/generated/dut.sv" "$work/generated/references.sv" "$work/generated/tb_red.sv" rtl/qwen_dv/s5/qfd_dv_s5_vreduce_rb.sv rtl/hdc/{ot_hdc_vreduce,ot_hdc_fastfp,ot_hdc_fp32_add_lat,ot_hdc_fp32_mul_lat,ot_hdc_prefix,ot_hdc_delay,ot_hdc_sfu,ot_hdc_sfu_q}.sv > "$dir/build.log" 2>&1
  set +e
  "$dir/obj/Vtb_red" > "$dir/run.log" 2>&1
  rc=$?
  set -e
  if [[ $mut == 0 ]]; then [[ $rc == 0 ]]; grep 'PASS' "$dir/run.log"; else [[ $rc != 0 ]]; grep 'MISMATCH' "$dir/run.log"; fi
 done
done
