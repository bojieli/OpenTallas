import json,sys,re
A=json.load(open(sys.argv[1]));B=json.load(open(sys.argv[2]))
def fi(p):
    pt={x['name']:x['type'] for x in p['partitions']}
    ports={x['id']:x for x in p['ports']} if isinstance(p['ports'],list) else p['ports']
    out={}
    for ln in p['lanes']:
        if not ln['id'].startswith('fi_'):continue
        st=pt[ports[ln['ports'][0]]['src']['part']]
        if not st.startswith('col_h9_r0'):continue
        dt=pt[ports[ln['ports'][-1]]['dst']['part']]
        out[ln['id']]=(st,dt,p['latency']['lanes'][ln['id']],{k:v for k,v in ln.items() if k not in('ports','id')})
    return out
a,b=fi(A),fi(B)
for k in sorted(set(a)|set(b)):
    if a.get(k)!=b.get(k):
        print(k);print('  h2_2249',json.dumps(a.get(k))[:700]);print('  ready5 ',json.dumps(b.get(k))[:700])
