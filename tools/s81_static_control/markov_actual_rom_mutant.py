"""Fail unchanged fulllookup scoreboard by altering one real ROM via cell."""
from pathlib import Path
import argparse,hashlib,json,subprocess

def run(stage):
 stage=Path(stage).resolve();binary=stage/'evidence/obj/Vtb';original=stage/'evidence/images'
 if not binary.is_file():raise ValueError('original admitted fullshape binary is not ready')
 out=stage/'physical_data_mutant';out.mkdir(exist_ok=False)
 images=out/'images';images.mkdir()
 before=hashlib.sha256((original/'macro000.viamap.hex').read_bytes()).hexdigest()
 for p in original.glob('macro*.viamap.hex'):
  if p.name=='macro000.viamap.hex':
   rows=p.read_text().splitlines();rows[0]=f'{int(rows[0],16)^1:0548x}';(images/p.name).write_text('\n'.join(rows)+'\n')
  else:(images/p.name).symlink_to(p)
 p=subprocess.run([str(binary),f'+OT_ROM_DIR={images}','+mode=0'],cwd=stage/'evidence',capture_output=True,text=True)
 (out/'run.log').write_text(p.stdout+p.stderr)
 after=hashlib.sha256((original/'macro000.viamap.hex').read_bytes()).hexdigest()
 passed=p.returncode!=0 and 'lookup realreleasedpayload beat0'in p.stdout and before==after
 result=dict(passed=passed,exit=p.returncode,actual_mutation='flip physical macro000 arr[0] bit0; logical token0 beat0 data bit0',scoreboard_unchanged=True,original_images_unchanged=before==after,original_macro000_sha256=before,mutated_macro000_sha256=hashlib.sha256((images/'macro000.viamap.hex').read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
 (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));raise SystemExit(0 if passed else 1)

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--stage',type=Path,required=True);a=ap.parse_args();run(a.stage)
