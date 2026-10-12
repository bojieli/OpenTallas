#!/usr/bin/env python3
"""CPU exactness, fault and mutant gates for the opt-in G25 inverse mechanism."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from uarch_model_hgi_inverse import model


def main():
    root=Path(__file__).resolve().parents[1]
    out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
    src=[root/'rtl/common/ot_secded.sv']+sorted((root/'rtl/hbm_accel/generic/collective/inverse').glob('*.sv'))
    variants={'positive':[], 'default_off':['-Ptb_hgi_inverse_selected.ENABLETEST=0'],
              'wrong_selected_index':['-Ptb_hgi_inverse_selected.MUT=1'],
              'dropped_filtered':['-Ptb_hgi_inverse_selected.MUT=2'],
              'ignored_write_mask':['-DMASKMUT=1']}
    records={}
    for name,flags in variants.items():
        binary=out/f'{name}.vvp'
        cmd=['iverilog','-g2012','-I'+str(root/'rtl/common'),'-s','tb_hgi_inverse_selected',*flags,'-o',str(binary),*map(str,src)]
        with (out/f'{name}.build.log').open('w') as f:
            subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
        with (out/f'{name}.run.log').open('w') as f:
            run=subprocess.run(['vvp',str(binary)],stdout=f,stderr=subprocess.STDOUT)
        log=(out/f'{name}.run.log').read_text()
        expected='PASS INVERSE_SELECTED' if name=='positive' else 'PASS DEFAULT_OFF'
        if name in ('positive','default_off'):
            if run.returncode or expected not in log:raise RuntimeError(name+' failed')
        elif not run.returncode or 'FATAL:' not in log:raise RuntimeError(name+' mutant not detected')
        records[name]={'returncode':run.returncode,'gate':'PASS' if name in ('positive','default_off') else 'EXPECTED_FAIL','build_argv':cmd}
        print(name,records[name]['gate'],flush=True)
    pinned=src+[root/'rtl/common/ot_secded_cols.svh',Path(__file__).resolve(),root/'tools/uarch_model_hgi_inverse.py']
    record={'schema':'hgi.inverse-selected.exact-gate.v1','base_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
            'source_sha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in pinned},
            'simulator':subprocess.check_output(['iverilog','-V'],stderr=subprocess.DEVNULL,text=True).splitlines()[0],
            'variants':records,'model':model(),'physical_qualified':False,
            'measured_build_K512_G8_cycles':16527,'measured_build_K2048_G96_cycles':67263,
            'measured_lookup_clock_stages':14,'interface_contract':'four independent requests/cycle, return always consumed; immutable protected R source span/version held through retire; faults sticky until reset'}
    (out/'gate.json').write_text(json.dumps(record,indent=2)+'\n')


if __name__=='__main__':main()
