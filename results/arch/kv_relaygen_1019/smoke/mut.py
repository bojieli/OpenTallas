import json
d=json.load(open('split/post.json')); m=d['modules']['top']; c=m['cells']
copy=[n for n in c if 'slice$122' in n and 'u_rst_relay' not in n][0]
q=c[copy]['connections']['Q'][0]; dd=c[copy]['connections']['D'][0]
for n,x in c.items():
  if n!=copy and x['connections'].get('R')==[q]:
    x['connections']['R']=[dd]; print('MUTANT', n, 'reset moved from landing copy to the copy D (one edge early)'); break
json.dump(d,open('split/post_mut.json','w'))
