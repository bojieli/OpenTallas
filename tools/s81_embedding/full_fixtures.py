#!/usr/bin/env python3
"""External token stimuli and expected-only checkpoint scoreboard rows."""
import argparse,pathlib,sys,json,hashlib
ROOT=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from dsrom_checkpoint import Checkpoint,DEFAULT_CHECKPOINT
TOKENS=[0,12,25,10777,21555,32319,32320,64640,96960,129279,16754,21946,128799]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--checkpoint',type=pathlib.Path,default=DEFAULT_CHECKPOINT);ap.add_argument('--out',type=pathlib.Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 c=Checkpoint(a.checkpoint); records=[]
 with (a.out/'expected.mem').open('w') as f:
  for token in TOKENS:
   raw=c.raw('embed.weight',token*10240,10240)
   row=[int.from_bytes(raw[2*n:2*n+2],'little') for n in range(5120)]
   for q in range(640):
    word=sum(row[8*q+b]<<(16*(4*b+k)) for b in range(8) for k in range(4))
    f.write(f'{word:0128x}\n')
   records.append(dict(token=token,raw_bf16_sha256=hashlib.sha256(raw).hexdigest()))
 c.close();(a.out/'tokens.mem').write_text(''.join(f'{n:05x}\n' for n in TOKENS))
 (a.out/'fixtures.json').write_text(json.dumps(dict(checkpoint=str(a.checkpoint),tokens=records,oracle_only=True),indent=2)+'\n')
if __name__=='__main__':main()
