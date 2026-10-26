#!/usr/bin/env python3
"""Prepare default-depth actual SRAM calendar proof and a broken bank-select DUT."""
import argparse,hashlib,json,shutil
from pathlib import Path
R=Path(__file__).resolve().parents[2]
FILES=['rtl/dsrom_sys/s81_suhc/test/tb_s81_su_calendar_store.sv','rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_calendar_store.sv','rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_calendar_ctl.sv','rtl/hdc/ot_sram_bank.sv','physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v']
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 for path in FILES:
  q=out/path;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/path,q)
 tb=(R/FILES[0]).read_text().replace('module tb_s81_su_calendar_store;','module tb_s81_su_calendar_store_depth;\n    localparam integer DEPTH=4096, AW=12;').replace('reg[5:0]addr=0','reg[AW-1:0]addr=0').replace('.DEPTH(64)', '.DEPTH(DEPTH)').replace('n==63','n==DEPTH-1').replace('seen==63','seen==DEPTH-1').replace('i<64','i<DEPTH').replace('repeat(68)','repeat(DEPTH+4)').replace('seen!=64','seen!=DEPTH').replace('cycle!=64','cycle!=DEPTH')
 (out/'tb_depth.sv').write_text(tb);bank=(R/'rtl/hdc/ot_sram_bank.sv').read_text();old='bs <= ra >> 6;';assert bank.count(old)==1;(out/'bank_mutant.sv').write_text(bank.replace(old,"bs <= {AW{1'b0}};"))
 src=' '.join(p for p in FILES[1:] if p!='rtl/hdc/ot_sram_bank.sv')
 run='''#!/bin/bash
set -euo pipefail
mkdir -p out
iverilog -g2012 -s tb_s81_su_calendar_store_depth -o out/positive tb_depth.sv '''+src+''' rtl/hdc/ot_sram_bank.sv
vvp out/positive >out/positive.log 2>&1
grep -q 'MAPPED_CALENDAR PASS' out/positive.log
iverilog -g2012 -s tb_s81_su_calendar_store_depth -o out/bank_mutant tb_depth.sv '''+src+''' bank_mutant.sv
set +e
vvp out/bank_mutant >out/bank_mutant.log 2>&1
rc=$?
set -e
[ "$rc" -ne 0 ]
grep -q 'calendar read address/order mismatch' out/bank_mutant.log
printf '%s\n' "$rc" >out/bank_mutant.rc
echo 'DEFAULT_DEPTH_CALENDAR_GATE PASS'
'''
 (out/'run.sh').write_text(run);receipt=dict(scope='Standalone actual default4096x1024 SRAM calendar+native controller; externalboot only, not canonical full-SU calendar/program fit or physical qualification',words=4096,actual_macros=128,sources={p:hashlib.sha256((R/p).read_bytes()).hexdigest() for p in FILES},generated={p:hashlib.sha256((out/p).read_bytes()).hexdigest() for p in ['tb_depth.sv','bank_mutant.sv','run.sh']});(out/'source_identity.json').write_text(json.dumps(receipt,indent=1)+'\n');print(json.dumps(dict(words=4096,macros=128,out=str(out))))
if __name__=='__main__':main()
