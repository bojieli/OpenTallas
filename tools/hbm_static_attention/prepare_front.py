#!/usr/bin/env python3
import sys,json,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from hbm_attention_static_calendar import outer_program,resident_event_frames,schedule
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
frames=resident_event_frames();config=[1|(ad<<4)|(fr<<12) for ad,fr in enumerate(frames)]
(a.out/'config.hex').write_text(''.join(f'{w:056x}\n' for w in config+[0]*(256-len(config))))
for k,(T,mode) in enumerate([(128,'qk'),(128,'pv'),(640,'qk'),(640,'pv')]):
 op=outer_program(T=T,mode=mode,query_base_sector=(k//2)*1024,query_epoch=k//2)
 w=op['outer_words'];(a.out/f'outer{k}.hex').write_text(''.join(f'{x:056x}\n' for x in w+[0]*(256-len(w))))
 ne=[0]*400
 if mode=='qk':
  for cycle in range(186,314):ne[cycle]=(255<<25)|(sum(3<<(b*3) for b in range(8))<<41)
 (a.out/f'ne{k}.hex').write_text(''.join(f'{x:056x}\n' for x in ne))
 cal=schedule(T=T,mode=mode)['words'];(a.out/f'event{k}.hex').write_text(''.join(f'{x:02x}\n' for x in cal+[0]*(256-len(cal))))
(a.out/'sizes.json').write_text(json.dumps(dict(config=len(config),outer=[len(outer_program(T=T,mode=m)['outer_words']) for T in (128,640) for m in ('qk','pv')]),indent=2)+'\n')
