#!/usr/bin/env python3
import sys,pathlib,json,hashlib,argparse,numpy as np
repo=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(repo/'tools'))
import rtl_hdc_v41x_attn_campaign as A
ap=argparse.ArgumentParser();ap.add_argument('--eb-dir',type=pathlib.Path,required=True);ap.add_argument('--out',type=pathlib.Path,required=True);a=ap.parse_args();root=a.eb_dir;out=a.out;out.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(20261015);jobs=[A.random_job(rng,16,512,T,min(128,T),'coarse') for T in (128,640)]
for i,T in enumerate((128,640)):
 eb=np.asarray([int(v,16) for v in (root/f'EB{T}.hex').read_text().split()],dtype=np.uint32).reshape(16,T)
 pv=A.golden_dot(eb.view(np.float32),jobs[i].kvm().T)
 assert np.all(np.isfinite(pv))
 (out/f'PV{T}.hex').write_text(''.join(f'{int(v):08x}\n' for v in pv.view(np.uint32).reshape(-1)))
 sink=np.arange(16,dtype=np.float32)/np.float32(16)-np.float32(.5)
 (out/f'SINK{T}.hex').write_text(''.join(f'{int(v):08x}\n' for v in sink.view(np.uint32)))
r={'scope':'Golden rawPV external component boundary, actualMachine-derivedEB + actualcanonicalstoredKV randomrecipe20261015; NOT actualPV RTL producer ornativeallocation qualification','H':16,'D':512,'T':[128,640],'precision':'canonical chunk8 FP32 golden_dot over unchangedBF16 EB and exactstoredFP8/FP4dequantization','input_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in root.glob('EB*.hex')},'output_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in out.glob('*.hex')}}
(out/'fixture.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS canonicalcompatible rawPV/SINK fixture fullH16D512T128640')
