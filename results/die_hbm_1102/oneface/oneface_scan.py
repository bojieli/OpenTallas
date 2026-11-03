import json,collections,sys
v=json.load(open('core_views.json'))
cm=json.load(open('d44o_cm/core_macros.json'))['cores']
rows=[]
for x in v['view_list']:
    p=json.load(open('d44o_cm/'+x['pins_file']))
    W,H=x['outline_um']; c=collections.Counter()
    for q in p:
        d={'W':q['x'],'E':W-q['x'],'S':q['y'],'N':H-q['y']}
        c[min(d,key=d.get)]+=1
    n=sum(c.values()); f,m=c.most_common(1)[0]
    mod=x['module']; mac=cm.get(mod) or {}
    nm=len(mac.get('macros',[])); st=mac.get('status','-')
    rows.append((m/n,mod,W,H,n,dict(c),nm,st,f))
rows.sort(key=lambda r:-r[0])
for r in rows:
    if r[0]>=0.9 or r[6]>0: print('%.3f %-55s %7.1fx%-7.1f n=%5d mac=%2d %-8s %s'%(r[0],r[1],r[2],r[3],r[4],r[6],r[7],r[5]))
