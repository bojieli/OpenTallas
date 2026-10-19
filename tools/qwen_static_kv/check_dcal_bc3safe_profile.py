#!/usr/bin/env python3
"""Reject primitive/image drift, including expanded OVL inputs, before generation."""
from pathlib import Path
import importlib.util,tempfile,subprocess,json,shutil,sys
root=Path(__file__).resolve().parents[2]
cert=json.loads((root/'results/arch/kv_dcal_bc3safe_1019/supported_profile.json').read_text())
import hashlib
for n,h in cert['primitive_sha256'].items():
 p=root/'rtl/qwen_sys/d2d_static_20261015'/n
 if hashlib.sha256(p.read_bytes()).hexdigest()!=h:raise SystemExit('BC3SAFE_PROFILE_FAIL '+n)
print('BC3SAFE_PROFILE_PASS exact ordinary primitives/image')
if '--negative' in sys.argv:
 for n in ['d2d_cal_image_mu.svh','ot_qwen_d2d_cal_seq.sv']:
  with tempfile.TemporaryDirectory() as t:
   w=Path(t); d=w/'rtl/qwen_sys/d2d_static_20261015';d.mkdir(parents=True)
   for f in cert['primitive_sha256']:shutil.copy2(root/'rtl/qwen_sys/d2d_static_20261015'/f,d/f)
   p=w/'tools/qwen_static_kv';p.mkdir(parents=True);shutil.copy2(root/'tools/qwen_static_kv/gen_dcal_bc3safe.py',p/'gen_dcal_bc3safe.py')
   with (d/n).open('a') as f:f.write('\n// unsupported profile drift\n')
   r=subprocess.run([sys.executable,str(p/'gen_dcal_bc3safe.py')],capture_output=True,text=True)
   assert r.returncode and 'unsupported primitive/image' in r.stderr,(n,r.returncode,r.stdout,r.stderr)
   print('BC3SAFE_PROFILE_NEGATIVE_PASS '+n)
