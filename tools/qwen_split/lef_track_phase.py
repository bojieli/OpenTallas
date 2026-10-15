import re,collections,sys
"""Per-pin track alignment of a block LEF under R0 and MY (die tracks = the block's ORFS ASAP7 tracks)."""
P={'M3':(36,9,'V'),'M5':(48,12,'V'),'M7':(64,16,'V'),'M9':(80,116,'V'),'M2':(36,9,'H'),'M4':(48,12,'H'),'M6':(64,16,'H'),'M8':(80,116,'H')}
t=open(sys.argv[1]).read()
W=round(float(re.search(r'SIZE ([\d.]+) BY',t).group(1))*1000)
stat=collections.Counter(); ex=collections.defaultdict(list)
for m in re.finditer(r'\n  PIN (\S+)\n(.*?)\n  END (\S+)',t,re.S):
    name,body=m.group(1),m.group(2)
    pg='USE POWER' in body or 'USE GROUND' in body
    cur=None
    for line in body.splitlines():
        s=line.split()
        if not s: continue
        if s[0]=='LAYER': cur=s[1]
        elif s[0]=='RECT' and cur in P:
            x0,y0,x1,y1=[round(float(v)*1000) for v in s[1:5]]
            p,o,d=P[cur]
            if pg: stat[('PG',name,cur,d,'w%d'%(x1-x0) if d=='V' else 'h%d'%(y1-y0))]+=1; continue
            if d=='V':
                c=(x0+x1)//2; r0=(c-o)%p; my=(W-c-o)%p
                k=(cur,'R0on' if r0==0 else f'R0off{r0}','MYon' if my==0 else f'MYoff{my}')
            else:
                c=(y0+y1)//2; k=(cur,'H(y unchanged by MY)','on' if (c-o)%p==0 else 'off')
            stat[k]+=1
            if len(ex[k])<2: ex[k].append((name,x0,x1,y0,y1))
print('W',W, {l:W%P[l][0] for l in ('M3','M5','M7','M9')})
for k,v in sorted(stat.items(),key=str): print(k,v,ex.get(k,''))
