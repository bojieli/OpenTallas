#!/usr/bin/env python3
"""Verify the real548-bit boundary on both dies; no integration qualification."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/arch/qwen_split_1014/kvsys_v1_3_candidate/native_record'
SOURCES=[ROOT/'rtl/qwen_sys/split_20261014/qkd_native_attention_record.sv',
         ROOT/'rtl/test/qwen_split/tb_native_attention_record.sv']

def main():
    receipt={'scope':'component boundary only; actual clock crossings, static link/calendar and native service integration required',
             'sources':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCES},'cases':[]}
    with tempfile.TemporaryDirectory(prefix='native-record-') as temp:
        for side in (0,1):
            for mutant in range(3):
                exe=Path(temp)/f's{side}m{mutant}'
                subprocess.run(['iverilog','-g2012','-s','tb_native_attention_record',
                    f'-Ptb_native_attention_record.MUT={mutant}',f'-Ptb_native_attention_record.SIDE={side}',
                    '-o',str(exe),*[str(s) for s in SOURCES]],check=True)
                result=subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
                (OUT/f's{side}m{mutant}.log').write_text(result.stdout+result.stderr)
                assert (result.returncode==0)==(mutant==0),result.stdout+result.stderr
                receipt['cases'].append({'kv_side':side,'mutant':mutant,'exit_code':result.returncode,
                                        'observed':'PASS' if mutant==0 else 'FAIL'})
    (OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('PASS compute/KV native record boundaries; both schedule/context mutants observed FAIL')

if __name__=='__main__':main()
