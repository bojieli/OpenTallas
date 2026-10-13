#!/usr/bin/env python3
"""Pin-to-pin Manhattan length of every 2-terminal inst-inst net in a die DEF (relay hop lint).
usage: die_hop_lint.py <dir with the *.lef> <placed.def> [limit_um=600]  (orientations N/S/FN/FS)"""
import re,sys,collections,glob,os
d=sys.argv[1]; deff=sys.argv[2]; lim=float(sys.argv[3]) if len(sys.argv)>3 else 600.
size={}; pins={}
for lef in glob.glob(os.path.join(d,'*.lef')):
    m=None;p=None
    for line in open(lef):
        s=line.split()
        if not s: continue
        if s[0]=='MACRO': m=s[1]; pins.setdefault(m,{})
        elif m and s[0]=='SIZE': size[m]=(float(s[1]),float(s[3]))
        elif m and s[0]=='PIN': p=re.sub(r'\[\d+\]$','',s[1]); bit=s[1]
        elif m and p and s[0]=='RECT' and bit not in pins[m]:
            x0,y0,x1,y1=map(float,s[1:5]); pins[m][bit]=((x0+x1)/2,(y0+y1)/2)
        elif m and s[0]=='END' and len(s)>1 and s[1]==m: m=None
dbu=1000.;comp={}
f=open(deff); sec=None; buf=''
def loc(inst,pin):
    mm,x,y,o=comp[inst]; w,h=size.get(mm,(0,0)); px,py=pins.get(mm,{}).get(pin,(w/2,h/2))
    if o=='S': px,py=w-px,h-py
    elif o=='FN': px=w-px
    elif o=='FS': py=h-py
    return x+px,y+py
stats=collections.defaultdict(lambda:[0,0.]); n2=0
for line in f:
    if line.startswith('COMPONENTS'): sec='C'; continue
    if line.startswith('END COMPONENTS'): sec=None; continue
    if line.startswith('NETS') or line.startswith('SPECIALNETS'): sec='N' if line.startswith('NETS') else None; continue
    if line.startswith('END NETS'): break
    if sec=='C':
        buf+=line
        if ';' in line:
            mt=re.match(r'\s*-\s+(\S+)\s+(\S+).*?(?:PLACED|FIXED)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*(\S+)',buf,re.S)
            if mt: comp[mt.group(1)]=(mt.group(2),int(mt.group(3))/dbu,int(mt.group(4))/dbu,mt.group(5))
            buf=''
    elif sec=='N':
        buf+=line
        if line.rstrip().endswith(';'):
            mt=re.match(r'\s*-\s+(\S+)',buf); conns=re.findall(r'\(\s*(\S+)\s+(\S+)\s*\)',buf.split('+')[0]); buf=''
            conns=[c for c in conns if c[0]!='PIN' and c[0] in comp]
            if len(conns)!=2: continue
            n2+=1
            (a,ap),(b,bp)=conns
            xa,ya=loc(a,ap); xb,yb=loc(b,bp); L=abs(xa-xb)+abs(ya-yb)
            if L>lim:
                strip=lambda s: re.sub(r'\d+','#',s)
                k=(strip(a)+'.'+re.sub(r'\[\d+\]','',ap),strip(b)+'.'+re.sub(r'\[\d+\]','',bp))
                st=stats[k]; st[0]+=1; st[1]=max(st[1],L)
print('two-pin inst nets',n2,'over',lim,'um:',sum(v[0] for v in stats.values()))
for k,v in sorted(stats.items(),key=lambda kv:-kv[1][1])[:60]: print('%7d bits max %7.0f um  %s -> %s'%(v[0],v[1],k[0],k[1]))
