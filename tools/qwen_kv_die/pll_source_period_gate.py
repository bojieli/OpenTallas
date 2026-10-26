#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/arch/qwen_split_1014/kvsys_v1_3_candidate/pll_source_periods'
SOURCES=[ROOT/'rtl/qwen_sys/split_20261014/qkd_pll_analog_model.sv',ROOT/'rtl/test/qwen_split/tb_qkd_pll_source_periods.sv']

def main():
    receipt={'scope':'Allowed analog source periods only; actual digital reset/lifecycle and physical phi-R remain mandatory',
             'sources':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCES},'cases':[]}
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='pll-period-') as temp:
        for mutant in (0,1):
            src=Path(temp)/'pll.sv';text=SOURCES[0].read_text()
            src.write_text(text.replace('1ns/1fs','1ns/1ps') if mutant else text)
            exe=Path(temp)/'test'
            subprocess.run(['iverilog','-g2012','-s','tb_qkd_pll_source_periods','-o',str(exe),str(src),str(SOURCES[1])],check=True)
            result=subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
            (OUT/f'm{mutant}.log').write_text(result.stdout+result.stderr)
            assert (result.returncode==0)==(mutant==0),result.stdout+result.stderr
            receipt['cases'].append({'mutant':mutant,'exit_code':result.returncode,'observed':'PASS' if mutant==0 else 'FAIL'})
    (OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('PASS actual five source periods; old1ps-precision mutant observed FAIL')

if __name__=='__main__':main()
