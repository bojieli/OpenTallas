import sys,re,collections
f=sys.argv[1]
c=collections.defaultdict(lambda:[0,0.0,0.0])
for l in open(f):
    p=l.split()
    if len(p)<5: continue
    try: s=float(p[-1])
    except: continue
    if s>=0: continue
    a=p[0].split('/')[0]; b=p[2].split('/')[0]
    pin=p[2].split('/')[1].split('[')[0] if '/' in p[2] else ''
    a=re.sub(r'_\d+$','',re.sub(r'__fo\d+_\d+','',a)); a=re.sub(r'\d+','#',a)
    b=re.sub(r'\d+','#',b)
    k=(a,b,pin); c[k][0]+=1; c[k][1]=min(c[k][1],s); c[k][2]+=s
tot=sum(v[0] for v in c.values()); print("violators",tot,"tns",sum(v[2] for v in c.values()))
for k,v in sorted(c.items(),key=lambda x:x[1][2])[:30]: print(v[0],round(v[1],1),round(v[2]),k)
