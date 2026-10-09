#!/usr/bin/env python3
"""Check full per-SM Qwen TP4 shapes and RTL canonical operand addressing."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import numpy as np
import qwen_r25_int8_image as P
ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    rng=np.random.default_rng(20261008)
    results=[]
    shapes=P.qwen_tp4_shapes()
    for name,model in shapes.items():
        g=P.Geometry(model['rows_per_sm'],model['k'])
        codes=rng.integers(-128,128,size=(g.rows,g.k),dtype=np.int8)
        recovered=P.unpack_lines(P.pack_lines(codes,g),g)
        assert np.array_equal(codes,recovered),name
        results.append(dict(name=name,canonical_bytes=codes.nbytes,roundtrip='PASS',
                            sha256=hashlib.sha256(codes.tobytes()).hexdigest()))
    # Tail padding and both scheduler modes, independent of target alignment.
    for gs in (False,True):
        for rows,k in ((3,1024),(9,576),(1,64)):
            g=P.Geometry(rows,k,group_slot=gs)
            codes=rng.integers(-128,128,size=(rows,k),dtype=np.int8)
            assert np.array_equal(codes,P.unpack_lines(P.pack_lines(codes,g),g))
    with tempfile.TemporaryDirectory(prefix='qwen-fmt3-image-') as td:
        td=Path(td);codes=rng.integers(-128,128,size=(6,1024),dtype=np.int8)
        scales=rng.integers(0,65536,size=6,dtype=np.uint16)
        np.save(td/'codes.npy',codes);np.save(td/'scales.npy',scales)
        manifest=P.emit(td/'codes.npy',td/'scales.npy',td/'installed',sm=1,sms=2,stride=160)
        installed=(td/'installed/weights.bin').read_bytes()
        lines=[installed[i:i+136] for i in range(0,len(installed),160)]
        assert all(not any(installed[i+136:i+160]) for i in range(0,len(installed),160))
        assert np.array_equal(P.unpack_lines(lines,P.Geometry(3,1024)),codes[3:])
        assert (td/'installed/row_scales_bf16.bin').read_bytes()==scales[3:].astype('<u2').tobytes()
        (td/'canonical.hex').write_text(''.join(f'{int(v):04x}\n' for v in
            (codes[3:].astype(np.float32).view(np.uint32)>>16).reshape(-1)))
        src=['rtl/hbm_accel/sm/ot_hbm_accel_int8_line.sv','rtl/hbm_accel/sm/ot_hbm_accel_issue_pq.sv',
             'rtl/test/tb_qwen_r25_int8_image.sv']
        subprocess.run(['iverilog','-g2012','-s','tb_qwen_r25_int8_image','-o',str(td/'run')]+[str(ROOT/s) for s in src],check=True,capture_output=True)
        rtl=[]
        for variant in ('correct','negative_row_major'):
            actual=lines if variant=='correct' else [codes[3:].tobytes()[i:i+128]+bytes(8)
                for i in range(0,3*1024,128)]
            (td/'image.hex').write_text(''.join(f'{int.from_bytes(line,"little"):0272x}\n' for line in actual))
            run=subprocess.run(['vvp',str(td/'run')],cwd=td,capture_output=True,text=True)
            (a.out/f'{variant}.log').write_text(run.stdout+run.stderr)
            ok=run.returncode==0 if variant=='correct' else run.returncode!=0 and 'canonical operand mismatch' in run.stdout
            assert ok,variant+run.stdout
            rtl.append(dict(name=variant,returncode=run.returncode,gate_pass=ok))
    paths=['tools/qwen_r25_int8_image.py','tools/test_qwen_r25_int8_image.py',*src,
           'results/arch/qwen_on_r25_20261008/PLAN.md']
    record=dict(verdict='PASS',scope='all eight full per-SM TP4 matvec shapes roundtrip; minimum real issuer operand gate',
        symmetry='32 identical SMs with contiguous equal output-row partitions; no full-die simulation',
        full_die_shapes=shapes,full_per_sm_roundtrips=results,rtl=rtl,
        scales='opaque BF16 bits preserved byte-for-byte; no scale arithmetic or norm folding',
        installed_image_test=manifest,source_sha256={p:P.sha(ROOT/p) for p in paths})
    (a.out/'verdict.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(dict(verdict='PASS',tested_code_bytes=sum(r['canonical_bytes'] for r in results),rtl=rtl)))
if __name__=='__main__':main()
