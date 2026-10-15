#!/usr/bin/env python3
"""Prepare actual producer programmes plus expected-only Machine answers.

Only raw QK scores become VM initialization. All MB/E/SE/EB files are observer
answers, never native DUT operand initialization.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hgi_sim import machine as MC
from hgi_sim.records import Rec,MDesc,sut_decode
import hdc_isa_v41 as I
from make_p_producer_calendar import compile_head

a=argparse.ArgumentParser();a.add_argument('--fixture',type=Path,required=True);a.add_argument('--sfu-tools',type=Path,required=True);a.add_argument('--out',type=Path,required=True)
args=a.parse_args()
meta=json.loads((args.fixture/'fixture.json').read_text())
if meta['scale_fp32_hex']!='3d3504f3' or meta['head_dim']!=512:raise ValueError('requires full canonical head_dim512 fixture')
for rows in (128,640):
    vectors={name:[int(x,16) for x in (args.fixture/f'{name}{rows}.hex').read_text().split()] for name in ('SC','MB','E','SE','EB')}
    for head in range(16):
        out=args.out/f't{rows}_h{head:02d}'
        compile_head(rows,head,args.sfu_tools,out)
        raw=vectors['SC'][head*rows:(head+1)*rows]
        (out/'raw_sc_sectors.hex').write_text(''.join(f'{sum(raw[8*s+w]<<(32*w) for w in range(8)):064x}\n' for s in range(rows//8)))
        for name in ('MB','SE','E','EB'):
            words=vectors[name][head:head+1] if name in ('MB','SE') else vectors[name][head*rows:(head+1)*rows]
            (out/f'expected_{name.lower()}.hex').write_text(''.join(f'{w:08x}\n' for w in words))
        die=MC.Die(0,None);die.vm[:rows]=raw
        sut=sut_decode(0);sut.update(m1=I.M1_AIMM,imm1=0x3d3504f3,dst=I.DST_VM)
        MC.u_su_vop(MC.Machine([die]),Rec('SU','VOP',sut=sut,desc={'A':MDesc(base=0,n=rows),'O':MDesc(base=1024,n=rows)},tag='expected.scale'),0)
        (out/'expected_scaled.hex').write_text(''.join(f'{int(w):08x}\n' for w in die.vm[1024:1024+rows]))
args.out.mkdir(parents=True,exist_ok=True)
(args.out/'fixture_source.json').write_text(json.dumps({'upstream_fixture':meta,'upstream_fixture_sha256':hashlib.sha256((args.fixture/'fixture.json').read_bytes()).hexdigest(),'DUT_initialization':['raw_sc_sectors.hex'],'expected_only':['MB','SE','E','EB','scaled'],'native_whole_kernel_qualified':False},indent=2)+'\n')
