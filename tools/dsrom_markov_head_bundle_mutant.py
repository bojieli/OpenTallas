#!/usr/bin/env python3
"""Admitted negative gate: actual B lane-compatible images with wrong row order.
Reuse completed minimum-bundle executable; no new synthesis or whole-array sim.
"""
import argparse,hashlib,json,subprocess
from pathlib import Path
import numpy as np
from dsrom_markov_head_bundle_image import viamap

def run(case,window,out):
 out.mkdir(parents=True,exist_ok=False);images=out/'images';images.mkdir()
 for p in (case/'images').glob('*.viamap.hex'):
  if not p.name.startswith('hb_'):(images/p.name).symlink_to(p.resolve())
 h=np.fromfile(window/'head.bin',dtype='<u2').reshape(128,5120)
 perm=np.array([32*q+k for k in range(32) for q in range(4)])
 badperm=np.roll(perm,1);logical=h[badperm,4096:].reshape(8192,16)
 p=np.arange(8192)[:,None];j=np.arange(16)[None,:]
 phys=logical[(p-11*(j%8))%8192,np.broadcast_to(j,(8192,16))]
 for half in (0,1):viamap(images/f'hb_{half}.viamap.hex',phys[half::2])
 proc=subprocess.run([str(case/'obj/Vtb'),f'+DIR={case}',f'+OT_ROM_DIR={images}'],capture_output=True,text=True)
 (out/'sim.log').write_text(proc.stdout+proc.stderr)
 detected=proc.returncode!=0 and 'actual B root/row order' in proc.stdout+proc.stderr
 rec=dict(passed=detected,expected='FAIL actual B root/row order',exit=proc.returncode,mutation='cyclic shift n=4*k+q by one row in actual released B image, same SK11',images={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in images.glob('hb_*.viamap.hex')},executable_sha256=hashlib.sha256((case/'obj/Vtb').read_bytes()).hexdigest(),physical_qualified=False)
 (out/'verdict.json').write_text(json.dumps(rec,indent=2)+'\n');print(proc.stdout);return detected
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--case',type=Path,required=True);ap.add_argument('--window',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();raise SystemExit(0 if run(a.case.resolve(),a.window,a.out.resolve()) else 1)
