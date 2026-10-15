#!/usr/bin/env python3
"""Canonical Machine attend.max/exp_sum/bf16_p expected data.

Only raw SC is an external stimulus. MB, E, SE and EB are expected answers;
they must never initialize DUT internal memories. Scale must be supplied from
the actual model's m.attn_scale, preserving its literal FP32 bits.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import hdc_isa_v41 as I
from hgi_sim.machine import Machine, Die, u_su_vop
from hgi_sim.records import MDesc, Rec, sut_decode


def generate(out, scale):
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(15101571)
    cases = []
    for rows in (128, 640):
        for head in range(16):
            die = Die(0, None)
            machine = Machine([die])
            raw = (rng.integers(-32768, 32768, rows).astype(np.float32) / np.float32(4096)).astype(np.float32)
            die.vm[:rows] = raw.view(np.uint32)
            V = lambda base,n=rows,**kw: MDesc(base=base,n=n,**kw)
            def run(tag, desc, **fields):
                sut = sut_decode(0); sut.update(fields)
                rec = Rec('SU','VOP',sut=sut,desc=desc,tag=tag)
                u_su_vop(machine, rec, 0)
                return rec
            # Literal canonical three-record chain, tools/hgi_sim/ds_native.py.
            run('attend.max',{'A':V(0),'R':V(4096,1)},
                m1=I.M1_AIMM,imm1=scale,red=I.RED_MAX,red_whole=1)
            run('attend.exp_sum',{'A':V(0),'B':V(4096,ibcast=1),'O':V(8192),'R':V(4097,1)},
                m1=I.M1_AIMM,imm1=scale,ad=I.AD_NEGB,sfu=I.SFU_EXP,
                red=I.RED_SUM,red_whole=1,dst=I.DST_VM)
            run('attend.bf16_p',{'A':V(8192),'O':V(16384)},rnd=1,dst=I.DST_VM)
            # Expected-only observation for the actual scaled-SC transport.
            run('expected.scaled_sc',{'A':V(0),'O':V(24576)},m1=I.M1_AIMM,imm1=scale,dst=I.DST_VM)
            case = out/f't{rows}_h{head:02d}'; case.mkdir(exist_ok=True)
            for name,base,count in [('raw_sc',0,rows),('expected_mb',4096,1),('expected_se',4097,1),
                                    ('expected_e',8192,rows),('expected_eb',16384,rows),('expected_scaled_sc',24576,rows)]:
                (case/f'{name}.hex').write_text(''.join(f'{int(w):08x}\n' for w in die.vm[base:base+count]))
            cases.append({'rows':rows,'head':head,'directory':case.name})
    sources = ['hgi_sim/ds_native.py','hgi_sim/machine.py','hgi_sim/lib.py','hdc_golden.py','hdc_golden_v41.py']
    manifest = {'scale_fp32_hex':f'{scale:08x}','heads':16,'profiles':[128,640],'cases':cases,
                'oracle':'actual hgi_sim.machine.u_su_vop attend.max / attend.exp_sum / attend.bf16_p',
                'dut_initialization_allowed':['raw_sc.hex'],
                'expected_only':['expected_mb','expected_se','expected_e','expected_eb','expected_scaled_sc'],
                'source_sha256':{f:hashlib.sha256((TOOLS/f).read_bytes()).hexdigest() for f in sources},
                'native_whole_kernel_qualified':False}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('out',type=Path)
    parser.add_argument('--scale-bits',required=True,type=lambda x:int(x,16))
    args=parser.parse_args();generate(args.out,args.scale_bits)
