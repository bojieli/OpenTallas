import json,sys,functools,re
st=json.load(open(sys.argv[1]))["modules"]; src=json.load(open(sys.argv[2]))["macros"]
size={}
for n,v in src.items():
    t=open(v["lef"]).read(); m=re.search(r"MACRO\s+"+re.escape(n)+r".*?SIZE\s+([\d.]+)\s+BY\s+([\d.]+)",t,re.S)
    size[n]=(float(m.group(1)),float(m.group(2)))
def key(n): return n if n in st else ("\\"+n if "\\"+n in st else None)
@functools.lru_cache(None)
def sr(n):
    a=0.0;c={}
    for t,k in st[n]["num_cells_by_type"].items():
        kk=key(t)
        if kk:
            aa,cc=sr(kk); a+=aa*k
            for x,y in cc.items(): c[x]=c.get(x,0)+y*k
        elif t.lstrip("\\") in size:
            w,h=size[t.lstrip("\\")]; a+=w*h*k; c[t.lstrip("\\")]=c.get(t.lstrip("\\"),0)+k
    return a,c
for n in st:
    if any(s in n for s in sys.argv[3:]):
        a,c=sr(n); print(n[-60:], round(a), c)
for n,(w,h) in size.items(): print(n,w,h)
