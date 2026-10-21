#!/usr/bin/env python3
"""Minimal table-load producer bench on the exact safe10 lp9d_npl source."""
from pathlib import Path
import subprocess,sys,json,hashlib
out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
root=Path(__file__).resolve().parents[3]
def blob(p):
 q=root/p
 if q.is_file():return q.read_bytes()
 return subprocess.check_output(['git','show','HEAD:'+p])
def put(p,data):
 q=out/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(data)
kept=[]
for f in blob('results/rtl/qw_tlprod_1020/bench10.f').decode().splitlines():
 f=f.replace('rtl/qwen_dv/lp9d_np/','rtl/qwen_dv/lp9d_npl/')
 if f=='tb_np10.sv':source='results/rtl/qw_tlprod_1020/'+f
 elif f.startswith('calr/'):source='results/rtl/qw_calr_1020/ctlm9c/'+f.split('/')[-1]
 else:source=f
 put(f,blob(source));kept.append(f)
image_root=root/'results/rtl/qw_tlprod_1020/images'
if image_root.is_dir(): images=[str(p.relative_to(root)) for p in image_root.rglob('*') if p.is_file()]
else: images=subprocess.check_output(['git','ls-tree','-r','--name-only','HEAD','results/rtl/qw_tlprod_1020/images'],text=True).splitlines()
for p in images:put(p.split('/images/',1)[1],blob(p))
(out/'safe10.f').write_text('\n'.join(kept)+'\n')
try: source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True,stderr=subprocess.DEVNULL).strip()
except subprocess.CalledProcessError: source_commit='materialized closure source; per-file hashes bind inputs'
manifest={'source_commit':source_commit,'gate_source_commit':'a4723fd521f4db64b853abf7446a52a10d83b985','physical_rtl_variant':'lp9d_npl','files':{str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file()}}
(out/'source_manifest.json').write_text(json.dumps(manifest,indent=1)+'\n')
print('SAFE10_SOURCE_READY',len(kept))
