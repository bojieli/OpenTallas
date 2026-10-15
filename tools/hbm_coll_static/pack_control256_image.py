#!/usr/bin/env python3
"""Pack actual raw256 control-ordinal frames into native512 host write pairs."""
import argparse,hashlib,json
from pathlib import Path

def pack(path,banks=19):
 values=[int(line.strip(),16) for line in path.read_text().splitlines() if line.strip()]
 if len(values)!=128*banks or len(values)%2:raise ValueError('image must initialize complete actualnative catalogue')
 if any(not 0<=value<1<<238 for value in values):raise ValueError('raw control256 reservedtop18bits nonzero')
 packed=[values[i]|values[i+1]<<256 for i in range(0,len(values),2)]
 assert [((word>>(half*256))&((1<<256)-1))for word in packed for half in range(2)]==values
 return packed
if __name__=='__main__':
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('raw',type=Path);a.add_argument('packed',type=Path);a.add_argument('--banks',type=int,default=19);x=a.parse_args()
 x.packed.write_text(''.join(f'{word:0128x}\n'for word in pack(x.raw,x.banks)))
 print(json.dumps({'raw':str(x.raw),'packed':str(x.packed),'raw_sha256':hashlib.sha256(x.raw.read_bytes()).hexdigest(),'packed_sha256':hashlib.sha256(x.packed.read_bytes()).hexdigest(),'banks':x.banks}))
