#!/usr/bin/env python3
"""Same-tool mapped-area measurement; no placement, slot fit or native claim."""
import argparse,hashlib,json,pathlib,sys
p=argparse.ArgumentParser();p.add_argument('out');p.add_argument('--kind',choices=['baseline','k2'],required=True);a=p.parse_args()
r=pathlib.Path(__file__).resolve().parents[4];sys.path.insert(0,str(r/'tools'));import run_abi3_physical as D
out=pathlib.Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
s=json.loads((r/'physical/ref_tile/smh_bdc_ref_p50/spec.json').read_text())
files=s['sources']+['rtl/hbm_accel/sm/mtp_slots/ot_hbm_sm_mtp_k2.sv']
text='\n'.join('`define '+d for d in s['defines'])+'\n'+'\n'.join((r/f).read_text() for f in files)
canon=out/'canonical.sv';canon.write_text(text)
top='ot_hbm_accel_smh_bdc' if a.kind=='baseline' else 'ot_hbm_sm_mtp_k2'
block={'top':top,'sources':[str(canon)],'parameters':{}}
v=D.VIEWS['asap7'];c=v['corners']['TT'];z=D.run_synthesis(v,c,block,out,0.833333,D.expand_dont_use(v['dont_use'],c) if hasattr(D,'expand_dont_use') else [])
result={'schema':'opentallas.sm_mtp_k2_mapped_area.v1','scope':'mapped combinational/sequential area only; not routed, no SRAM-slot service or fullSM integration qualification','kind':a.kind,'top':top,'defines':s['defines'],'source_sha256':{f:hashlib.sha256((r/f).read_bytes()).hexdigest() for f in files},'canonical_sha256':hashlib.sha256(canon.read_bytes()).hexdigest(),'yosys':str(D.YOSYS),'liberty_sha256':{str(f):hashlib.sha256(pathlib.Path(f).read_bytes()).hexdigest() for f in c['liberty']},'synthesis':z['record']}
(out/'area.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
