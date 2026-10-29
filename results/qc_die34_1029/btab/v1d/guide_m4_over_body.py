import sys, re, collections
M=[(17280,17280,112104,58344),(159840,17280,254664,58344),(17280,90720,112104,131784),(159840,90720,254664,131784)]
v=open(sys.argv[1]).read()
mac=set()
for m in re.finditer(r'ot_sram_1r1w_128x256_m1_r2c2\s+\S+\s*\((.*?)\);', v, re.S):
    body=re.sub(r'\.\w+\s*\(', ' ', m.group(1))
    for n in re.split(r'[\s,{}()]+', body):
        n=n.replace('\\','').strip()
        if n and not re.match(r"^\d+'", n): mac.add(n)
print('macro pin nets', len(mac))
for p in sys.argv[2:]:
    net=None; c=collections.Counter(); bad=collections.defaultdict(list)
    for l in open(p):
        t=l.split()
        if len(t)==1 and t[0] not in '()': net=t[0].replace('\\',''); continue
        if len(t)!=5 or t[4] not in ('M4',): continue
        x0,y0,x1,y1=map(int,t[:4])
        for (a,b,cc,d) in M:
            if x0<cc and x1>a and y0<d and y1>b and net not in mac:
                c['nonmacro_m4_over_body']+=1; bad[net].append((x0,y0,x1,y1))
    print(p.split('/')[-5], dict(c), 'nets', len(bad), list(bad.items())[:6])
