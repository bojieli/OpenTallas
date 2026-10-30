import hashlib,json,pathlib,re
from pin_plan import M,build,MW
HERE=pathlib.Path(__file__).parent
p=pathlib.Path('/home/ubuntu/OpenTallas/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.lef');s=p.read_text();pins={}
for bit in range(256):
 body=re.search(r'PIN rd_out\['+str(bit)+r'\]\s+(.*?)END rd_out\['+str(bit)+r'\]',s,re.S).group(1)
 rect=tuple(map(float,re.search(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',body).groups()));pins[bit]=rect
report={}
for mod,(W,H)in zip(M,[(414.72,207.36),(440.64,207.36),(760.32,725.76),(440.64,457.92)]):
 pts,macros,_=build(mod,W,H);lookup={p['name']:p for p in pts};rows=[]
 for m in macros:
  x,y=m['xy_um'];b,r=m['bank'],m['reader']
  for bit in range(32):
   target=lookup['bank_read_data['+str(b*192+r*32+bit)+']'];tx=W-4.32 if target['face']=='E'else 4.32;ty=target['y'];dist=[]
   for word in range(8):
    rect=pins[word*32+bit];corners=[(rect[a],rect[b])for a in(0,2)for b in(1,3)]
    dist.extend(abs(tx-(x+(MW-px if m['orient']=='MY'else px)))+abs(ty-(y+py))for px,py in corners)
   rows.append(dict(output_bit=b*192+r*32+bit,macro=m['inst'],raw_source_bits=[word*32+bit for word in range(8)],planned_distance_bound_um=round(max(dist)+.05,3)))
 report[mod]=dict(bits=len(rows),maximum_um=max(r['planned_distance_bound_um']for r in rows),rows=rows)
assert all(r['maximum_um']<405 for r in report.values())
(HERE/'read_reach_receipt.json').write_text(json.dumps(dict(status='PASS_PLANNED_ENDPOINT_DISTANCE_ONLY',lef=str(p),lef_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),source='Actual selected replicated_bank raw[{ks,5\'d0}+:32] means each output bit may use eight raw SRAM pins; every actual LEF rectangle corner checked under R0/MY',target='Planned boundary FF4.32um from corresponding edge at pin y, not actual placement',modules=report),indent=1)+'\n');print([(k,v['maximum_um'])for k,v in report.items()])
