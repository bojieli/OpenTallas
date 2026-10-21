import json,re
nb=json.load(open('tools/qwen_kv_die/host_cluster/repack_1020/netbits.json'))['ports']
FACE={'N':'top','S':'bottom','E':'right','W':'left'}
def nbits(p):
    b=nb.get(p); return len(b) if isinstance(b,(list,dict)) else (b if isinstance(b,int) else 1)
for k in ['p10a','p10b']:
    kd=f'physical/ref_tile/qkd_hr_cluster_{k}'
    s=json.load(open(f'{kd}/spec.json'))
    pr=s['pin_ranges']; L={'N':s['outline']['w'],'S':s['outline']['w'],'E':s['outline']['h'],'W':s['outline']['h']}
    new={}
    for f,ps in s['pins'].items():
        lo0,hi0=21.6,L[f]-21.6
        ps=[p for p in ps if p in pr]
        if not ps: continue
        d=2.5
        while sum(max(6.0,nbits(p)/d) for p in ps)>0.92*(hi0-lo0): d+=0.25
        items=sorted([[(pr[p][0]+pr[p][1])/2-max(6.0,nbits(p)/d)/2,max(6.0,nbits(p)/d),p] for p in ps])
        x=lo0
        for it in items: it[0]=max(it[0],x); x=it[0]+it[1]
        x=hi0
        for it in reversed(items):
            if it[0]+it[1]>x: it[0]=x-it[1]
            x=it[0]
        assert items[0][0]>=lo0-1e-6
        for st,w,p in items: new[p]=[round(st,2),round(st+w,2)]
        print(k,f,len(items),'density',d)
    pr.update(new)
    json.dump(s,open(f'{kd}/spec.json','w'),indent=1); open(f'{kd}/spec.json','a').write('\n')
    sq=f'tools/ref_tile/specs_qhost_cluster/qkd_hr_cluster_{k}.json'
    try:
        s2=json.load(open(sq)); s2['pin_ranges'].update(new); json.dump(s2,open(sq,'w'),indent=1); open(sq,'a').write('\n')
    except FileNotFoundError: print('no',sq)
    env=open(f'{kd}/kit.env').read()
    face_of={p:f for f,ps in s['pins'].items() for p in ps}
    def rep(m):
        p=m.group(1)
        if p in new: return f"--pin-region '^({p})(\\[|$)={FACE[face_of[p]]}:{new[p][0]}-{new[p][1]}'"
        return m.group(0)
    env2,nsub=re.subn(r"--pin-region '\^\(([^)]+)\)\(\\\[\|\$\)=[a-z]+:[0-9.]+-[0-9.]+'",rep,env)
    print('kit.env subs',nsub,len(new))
    open(f'{kd}/kit.env','w').write(env2)
