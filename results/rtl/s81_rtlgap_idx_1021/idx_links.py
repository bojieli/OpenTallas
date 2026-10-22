import json,sys
p=json.load(open(sys.argv[1]))
bl=p['blocks']
out={}
for l in p['links']:
    i=l['i']
    if i.startswith(('hrrq','hrrd','iq_','is_','hrq_00','hrd_00')):
        r={k:l[k] for k in l if k not in('e','endpoint_faces','path','route','pts','n')}
        r['ends']=[(bl[e[0]]['name'],e[1]) for e in l['e']]
        out[i]=r
k0=next(iter(out)); print(json.dumps(out[k0])[:1500])
json.dump(out,open(sys.argv[2],'w'),indent=1)
