#!/usr/bin/env python3
"""Lossless retained prior-history packing and actual native operand transport.
No inference, quantization, current-token oracle, DUT output or response callback.
"""
import argparse, hashlib, json, struct
from pathlib import Path

def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def inverse(b):
    s=b>>31;e=(b>>23)&255;m=b&0x7fffff
    if e==0 and m==0:return s<<7
    if 121<=e<=135 and not m&0xfffff:return (s<<7)|((e-120)<<3)|(m>>20)
    if e==120 and not m&0x1fffff:return (s<<7)|4|(m>>21)
    if e==119 and not m&0x3fffff:return (s<<7)|2|(m>>22)
    if e==118 and m==0:return (s<<7)|1
    raise ValueError('retained history is not exactly E4M3')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--history',required=True,type=Path)
    ap.add_argument('--history-sha',required=True);ap.add_argument('--native-x',required=True,type=Path)
    ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
    raw=a.history.read_bytes()
    if len(raw)!=4194304*4 or hashlib.sha256(raw).hexdigest()!=a.history_sha:raise ValueError('prior history identity/shape')
    xraw=a.native_x.read_bytes();x=[int(v,16) for v in xraw.decode().split()]
    if len(x)!=4096 or any(v<0 or v>0xffffffff for v in x):raise ValueError('actual producer X4096 rawU32 required')
    if a.out.exists():raise FileExistsError(a.out)
    a.out.mkdir(parents=True)
    lines=[]
    for sector in (0,1,32768,32769):
        codes=bytes(inverse(v) for v in struct.unpack_from('<32I',raw,sector*32*4))
        lines.append(codes[::-1].hex())
    (a.out/'prior_sectors.hex').write_text('\n'.join(lines)+'\n')
    (a.out/'native_operand.hex').write_text(''.join(f'{v:08x}\n' for v in x[:1024]))
    rec=dict(history=str(a.history.resolve()),history_sha256=a.history_sha,native_operand_source=str(a.native_x.resolve()),
             native_operand_source_sha256=hashlib.sha256(xraw).hexdigest(),layer=0,rank=0,position=8191,tile=0,
             sectors=[0,1,32768,32769],bytes=128,current_lane_preloaded=False,arithmetic='diagnostic partialK with actual native X operand; not canonical QR',
             fulltoken=False,canonical_query=False,inputs_sha256={p.name:digest(p) for p in a.out.glob('*.hex')})
    (a.out/'inputs.json').write_text(json.dumps(rec,indent=2)+'\n')
    print('retained prior4sectors128B +actualnativeoperand1024words; no canonical query claim')
if __name__=='__main__':main()
