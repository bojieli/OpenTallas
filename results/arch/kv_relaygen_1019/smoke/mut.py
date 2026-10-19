import json
d=json.load(open('post.json')); m=d['modules']['top']; c=m['cells']
relay=[(n,x) for n,x in c.items() if 'u_rst_relay' in n and 'slice' in n]
sync=[x for n,x in c.items() if 'u_rst_relay' in n and 'slice' not in n and 'DFF' in x['type']]
q1=relay[1][1]['connections']['Q'][0]; sq=relay[1][1]['connections']['D'][0]
for n,x in c.items():
  if 'u_rst_relay' not in n and x['connections'].get('R')==[q1]:
    x['connections']['R']=[sq]; print('MUTANT re-pointed',n,'from relay copy to its D (one edge early)'); break
json.dump(d,open('post_mut.json','w'))
