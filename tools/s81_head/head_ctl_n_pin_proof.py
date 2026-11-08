#!/usr/bin/env python3
"""Emit native actual-kit CA +1 input PIN/K+2 proof, separate from same-cycle tail proof."""
from pathlib import Path
import argparse,re
a=argparse.ArgumentParser();a.add_argument('--baseline-rtl',type=Path,required=True);a.add_argument('--out',type=Path,required=True);p=a.parse_args()
r=p.out;r.mkdir(parents=True,exist_ok=False)
src=Path(__file__).resolve().parents[2]/'rtl/common'
old=(p.baseline_rtl/'ot_dp_clk_landing_ca.sv').read_text()
names=re.findall(r'^module\s+(\w+)',old,re.M)
for name in sorted(names,key=len,reverse=True):old=re.sub(r'\b'+re.escape(name)+r'\b',name+'_ref',old)
old=old.replace('OT_MESO_CA_MUTANT_','OT_MESO_CA_REFERENCE_DISABLED_MUTANT_')
(r/'ca_reference.sv').write_text(old)
(r/'patched_ca.sv').write_bytes((src/'ot_dp_clk_landing_ca.sv').read_bytes())
for n in ['ot_meso_fifo.sv','ot_dp_clk_landing.sv']:(r/n).write_bytes((p.baseline_rtl/n).read_bytes())
(r/'tb.sv').write_bytes((Path(__file__).parent/'tb_head_ctl_n_pin.sv').read_bytes())
(r/'run.sh').write_text("""#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
for spec in 515:0 517:1 615:0;do
 w=${spec%:*}; ct=${spec#*:}
 docker run --rm --memory=8g --cpus=4 -v "$PWD:/proof" -w /proof verilator/verilator:v5.032 \
  --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb -GW=$w -GCONSTTAIL=$ct \
  --Mdir obj_$w -o tbx tb.sv patched_ca.sv ca_reference.sv ot_meso_fifo.sv ot_dp_clk_landing.sv > build_$w.log 2>&1
 ./obj_$w/tbx +seed=11 +n=32 > run_$w.log 2>&1
 grep -q ' PASS$' run_$w.log
 tail -2 run_$w.log
done
docker run --rm --memory=8g --cpus=4 -v "$PWD:/proof" -w /proof verilator/verilator:v5.032 \
 --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb -GW=515 +define+OT_MESO_CA_MUTANT_FREG \
 --Mdir obj_mut -o tbx tb.sv patched_ca.sv ca_reference.sv ot_meso_fifo.sv ot_dp_clk_landing.sv > build_mut.log 2>&1
if ./obj_mut/tbx +seed=11 +n=32 > run_mut.log 2>&1;then echo MUTANT_SURVIVED;exit 1;fi
grep -q 'FAIL' run_mut.log
tail -4 run_mut.log
echo 'PASS native input PIN+1 K+2 proof and mutant'
""")
print(r)
