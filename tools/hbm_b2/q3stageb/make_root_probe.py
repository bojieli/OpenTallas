#!/usr/bin/env python3
"""A G4/N1/K1 deterministic diagnostic fixture for the selected TP192 root."""
import pathlib,sys
p=pathlib.Path(sys.argv[1]);p.mkdir(parents=True,exist_ok=False)
cfg=[4,1,1,0,0,1,0,0x20000,0x10000,64,128,0,0]
(p/'cfg.hex').write_text(''.join(f'{x:08x}\n' for x in cfg))
for name in ['a','b']:
 words=[0xffffffff]*(4*2048)
 for rank in range(4):words[rank*2048]=(0x40800000-rank*0x00800000) if name=='a' else 20+rank
 (p/(name+'.hex')).write_text(''.join(f'{x:08x}\n' for x in words))
(p/'n.hex').write_text(''.join(f'{(1 if r<4 else 0):08x}\n' for r in range(192)))
(p/'o.hex').write_text('00000014\n');(p/'r.hex').write_text('00000000\n')
