#!/usr/bin/env python3
"""Apply four reviewed L14 leaf geometry candidates; native CS forwarding is separate.

Only hard cores, internal station contracts, exact FT slots and priced FT lane
cycles change. Pin contracts require rxsf north/W-seed successor 1317cfd094
and VN_a S-clock 616d52b509. No signed-view or native RTL realization claim.
"""
import gzip,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
plan=Path(sys.argv[1]) if len(sys.argv)>1 else HERE/'die_plan.json'
P=json.loads(plan.read_text());D=json.load(gzip.open(HERE/'delta_leaf_l14_0719.json.gz','rt'))
derived={'stations','regs_um','bit_sites_um','bit_site_cell_um'}
for n,t in D['types'].items():
 old=P['partition_types'][n]
 assert {c['inst'] for c in old['hard_cores']}=={c['inst'] for c in t['hard_cores']},n
 assert [{k:v for k,v in s.items() if k not in derived} for s in old['ft_slots']]==[{k:v for k,v in s.items() if k not in derived} for s in t['ft_slots']],n
 old.update(t)
for n,(old,new) in D['latency'].items():
 e=P['latency']['lanes'][n];assert e['cycles']==old,(n,e['cycles'],old)
 for k in ('cycles','natural','stations'):e[k]+=new-old
 if 'word_cycles'in e:e['word_cycles']+=new-old
plan.write_text(json.dumps(P,separators=(',',':'))+'\n')
print('L14 leaf candidate:4 types,',len(D['latency']),'FT lane latency changes; native CS forwarding remains required')
