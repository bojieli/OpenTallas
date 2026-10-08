#!/usr/bin/env python3
"""Minimum real-root ABI proof, two negatives, and source-bound elaboration."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--native-elaboration',action='store_true')
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    source=['rtl/proto/ot_fp32_add_rne_pipe.sv','rtl/hdc/ot_hdc_delay.sv',
            'rtl/v41rom/ot_v41_ret.sv','rtl/dsrom_sys/s81_pq_parent/ot_s81_pq_root_adapter.sv',
            'tests/rtl/s81_pq_parent/root_adapter_tb.sv']
    rows=[]
    for mode in ('positive','wrong_tag','drop_fault'):
        files=[str(ROOT/p) for p in source]
        if mode!='positive':
            text=Path(files[3]).read_text()
            old,new=(('66*r+1 +: 32','66*r+2 +: 32') if mode=='wrong_tag' else
                     ('fault | upstream_fault[r]','fault'))
            assert old in text
            mutant=a.out/(mode+'.sv');mutant.write_text(text.replace(old,new));files[3]=str(mutant)
        exe=a.out/(mode+'.vvp')
        c=subprocess.run(['iverilog','-g2012','-s','root_adapter_tb','-o',str(exe),*files],capture_output=True,text=True)
        (a.out/(mode+'.compile.log')).write_text(c.stdout+c.stderr)
        if c.returncode:raise RuntimeError('compile failure is not an expected negative')
        r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
        (a.out/(mode+'.log')).write_text(r.stdout+r.stderr)
        ok=(r.returncode==0 and 'PASS root adapter 130 rows' in r.stdout) if mode=='positive' else (
            r.returncode!=0 and ('ABI mismatch' if mode=='wrong_tag' else 'upstream fault lost')in r.stdout)
        rows.append(dict(case=mode,exit_code=r.returncode,PASS=ok))
    if a.native_elaboration:
        manifest=json.loads((ROOT/'physical/s81_pq_r128_expanded/source_binding.json').read_text())
        files=[]
        for p in manifest['files']:
            if p['role']!='RTL' or 'screen' in p['original_path']:continue
            path=ROOT/p['path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==p['sha256']
            files.append(str(path))
        files.append(str(ROOT/'rtl/dsrom_sys/s81_pq_parent/ot_s81_pq_native_partition.sv'))
        c=subprocess.run(['iverilog','-g2012','-DOT_PQ_ROM_PORTS','-s','ot_s81_pq_native_partition',
                          '-o',str(a.out/'native.vvp'),*files],capture_output=True,text=True)
        (a.out/'native.compile.log').write_text(c.stdout+c.stderr)
        rows.append(dict(case='native_R128_PHW9_SAW11_KMAX6144_elaboration',exit_code=c.returncode,PASS=c.returncode==0))
    record=dict(schema='opentallas.s81.pq-parent-proof.v1',cases=rows,
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in source},
        scope='MinimumR2 realROOTD128 numerical packing/error proof; optional fullR128 native elaboration only',
        whole_parent_exactness=False,physical_adopted=False)
    (a.out/'record.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(rows));return 0 if all(r['PASS']for r in rows)else 1


if __name__=='__main__':raise SystemExit(main())
