import json,sys
p=json.load(open(sys.argv[1])); n=0; tot=0
cnt={x['type']:0 for x in p['partitions']}
for x in p['partitions']: cnt[x['type']]+=1
for tn,T in p['partition_types'].items():
    if not tn.startswith('col_'): continue
    W,H=T['outline_um']; B=[(c['origin_um'][0],c['origin_um'][1],c['origin_um'][0]+c['outline_um'][0],c['origin_um'][1]+c['outline_um'][1]) for c in T.get('hard_cores',[])]
    for s in T.get('ft_slots',[]):
        k=s['stations']
        f=lambda face,win:(lambda m:{'E':(W,m),'W':(0,m),'N':(m,H),'S':(m,0)}[face])((win[0]+win[1])/2)
        a=f(s['in_face'],s['in_window_um']); b=f(s['out_face'],s['out_window_um'])
        pts=[tuple(r) for r in s['regs_um'][1:]] if s.get('regs_um') else [(a[0]+(b[0]-a[0])*j/k,a[1]+(b[1]-a[1])*j/k) for j in range(1,k)]
        for x,y in pts:
            tot+=cnt[tn]
            if any(x0<x<x1 and y0<y<y1 for x0,y0,x1,y1 in B): n+=cnt[tn]
print(sys.argv[1].split('/')[-3:], 'station points on hard cores (x instances):',n,'of',tot)
