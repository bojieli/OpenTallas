#!/usr/bin/env python3
import argparse,json
from pathlib import Path
from physical_calendar import resident_event_frames,schedule,outer_record
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--sid',type=int,default=3);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
profiles,config=resident_event_frames()
(a.out/'config.hex').write_text(''.join(f'{x:056x}\n' for x in config+[0]*(512-len(config))))
sizes=[]
for k,p in enumerate(profiles):
 w=outer_record(k,k//2,query_base_sector=a.sid*8192+(k//2)*1024,P_base_sector=a.sid*8192+4096+(k//2)*2048)
 (a.out/f'outer{k}.hex').write_text(''.join(f'{x:056x}\n' for x in w+[0]*(256-len(w))))
 reads=128 if p['mode']=='qk' else 16*p['T']//64
 ne=[0]*900
 for c in range(343,343+reads):ne[c]=(255<<25)|(sum(3<<(b*3) for b in range(8))<<41)
 (a.out/f'ne{k}.hex').write_text(''.join(f'{x:056x}\n' for x in ne))
 cal=p['words'];(a.out/f'event{k}.hex').write_text(''.join(f'{x:02x}\n' for x in cal+[0]*(512-len(cal))))
 sizes.append(len(w))
(a.out/'sizes.json').write_text(json.dumps(dict(config=len(config),outer=sizes,actualPsource='headmajorFP32,descriptorheadstride80sectors'),indent=2)+'\n')
