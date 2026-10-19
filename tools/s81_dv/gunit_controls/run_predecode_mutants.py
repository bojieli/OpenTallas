#!/usr/bin/env python3
"""Run on fleet from lane root containing src/, tb_predecode.sv."""
from pathlib import Path
import subprocess
source=Path('src/rtl/hdc/v41/ot_hdc_skp_predecode.sv').read_text()
variants={
 'wrong_value': source.replace("assign q[0] = |(row", "assign q[0] = ~|(row", 1),
 'wrong_age': source.replace('always @(posedge clk) q <= d;', 'reg [23:0] q2; always @(posedge clk) begin q2 <= d; q <= q2; end', 1),
}
for name,text in variants.items():
    assert text != source
    out=Path('predecode_'+name);out.mkdir(exist_ok=True)
    variant=out/'mutant.sv';variant.write_text(text)
    cmd=['verilator','--binary','--timing','-j','4','-Wno-fatal','--top-module','tb_predecode','tb_predecode.sv',str(variant),'src/rtl/hdc/v41/ot_hdc_sk_recip_rom.sv','--Mdir',str(out/'obj')]
    with (out/'build.log').open('w') as f:
        subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
    run=subprocess.run([str((out/'obj/Vtb_predecode').resolve())],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    (out/'run.log').write_text(run.stdout)
    assert run.returncode != 0 and 'PREDECODE FAIL errors=' in run.stdout, (name,run.returncode,run.stdout)
    print(name+': expected PREDECODE FAIL detected', flush=True)
print('PREDECODE MUTANTS PASS wrong-value + extra-age rejected', flush=True)
