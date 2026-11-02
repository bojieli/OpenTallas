#!/usr/bin/env python3
"""Add an executable causal write/refill component gate to a fresh prepared vehicle.

The preparation is simulation only. All memory effects and ACKs use the pinned
real RTL; explicitly staged native DQ is unit stimulus, not a production COPY.
"""
import argparse,json,shlex,shutil
from pathlib import Path


def prepare(prepared,case):
    plan=json.loads((prepared/'vehicle_plan.json').read_text())
    selected=next(x for x in plan['cases'] if x['label']==case)
    if selected['VM_SID'] != selected['STK'] or selected['VM_SID'] != 3:
        raise ValueError('DBK source SID is its STK strap; prepared scratch SID is incompatible. No alias allowed.')
    dest=prepared/'sources'/'tb_source_write_causal_1101.sv'
    if dest.exists():raise ValueError('Fresh prepared output required; preserve earlier run')
    repo=Path(__file__).resolve().parents[2]
    shutil.copyfile(repo/'rtl/test/hbm_layer'/dest.name,dest)
    files=[str(p.relative_to(prepared)) for p in sorted((prepared/'sources').iterdir()) if p.suffix in ('.sv','.v')]
    (prepared/'causal_files.f').write_text('\n'.join(files)+'\n')
    s=selected;quad=int(s['PHY_QUAD']);stack=int(s['STK']);window=s['window'];label=shlex.quote(s['label'])
    script=f'''#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
verilator --binary --timing -j 2 -CFLAGS "-O1 -fno-var-tracking" --output-split 10000 -Wno-fatal --top-module tb_source_write_causal_1101 -GSTK={stack} -GPHY_QUAD={quad} -Mdir causal_obj -f causal_files.f > causal_build.log 2>&1
./causal_obj/Vtb_source_write_causal_1101 +CASE=cases/{label} +SECTORS={s['sectors']} +ROW={window['row']} +COL={window['col']} +HBM_IMG_DIR="$PWD/images" > causal_positive.log 2>&1
grep 'CAUSAL_WRITE_REFILL PASS' causal_positive.log
if ./causal_obj/Vtb_source_write_causal_1101 +CASE=cases/{label} +SECTORS={s['sectors']} +ROW={window['row']} +COL={window['col']} +HBM_IMG_DIR="$PWD/images" +MUT_STALE=1 > causal_stale_mutant.log 2>&1;then
 echo 'STALE MUTANT ESCAPED';exit 2
fi
grep 'CAUSAL_READBACK' causal_stale_mutant.log
'''
    (prepared/'run_causal.sh').write_text(script);(prepared/'run_causal.sh').chmod(0o755)
    (prepared/'causal_scope.json').write_text(json.dumps(dict(status='PREP_ONLY',case=s,
        test='old real cache -> explicit new native DQ -> real WB/PC/persistent DRAM completion -> new epoch refill -> native SRAM readback',
        independent_ACK_oracle=True,negative='omit invalidation; stale old cache must fail new-data oracle',
        production_COPY=False,scratch_reserved=False,numeric_token_pass=False),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepared',type=Path,required=True);p.add_argument('--case',default='stack0_q0');a=p.parse_args();prepare(a.prepared,a.case)
