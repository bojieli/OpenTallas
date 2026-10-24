import json,re,sys
p=json.load(open(sys.argv[1]+'/die_plan.json'))
W={q['id']:q['width'] for q in p['ports']}
pad=n=0
for l in p['lanes']:
  m=re.search(r'land_pad (\d+)',l.get('note',''))
  if m: pad+=int(m.group(1))*W[l['ports'][0]]; n+=1
# DFFHQNx1_ASAP7_75t_R area 0.2916 um2 (raw); placed ~1.45x as P4
print(f"pad lanes {n}, pad flop bits {pad}, raw {pad*0.2916e-6:.3f} mm2, placed ~{pad*0.2916e-6*1.45:.2f} mm2, max lane {max(v['cycles'] for v in p['latency']['lanes'].values())}")
