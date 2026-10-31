import re,sys,collections
def parse(f):
    yb=collections.Counter(); ln=collections.Counter(); tot=0
    srcs=None
    for line in open(f):
        line=line.strip()
        if line.startswith("srcs:"):
            srcs=re.findall(r"L(\d+m?)x?",line)
            srcs=[s for s in re.findall(r"net:(?:nq_st_)?(L\d+m?)",line)]
        elif line.startswith("comment:"):
            c=int(re.search(r"congestion:(\d+)",line).group(1))
        elif line.startswith("bbox"):
            x0,y0=map(float,re.findall(r"\(([\d.]+), ([\d.]+)\)",line)[0])
            yb[int(y0//100)*100]+=c; tot+=c
            n=len(srcs) or 1
            for s in set(srcs): ln[s]+=c*srcs.count(s)/len(srcs) if srcs else 0
    return tot,yb,ln
for f in sys.argv[1:]:
    tot,yb,ln=parse(f)
    print("==",f,"total",tot)
    print(" y-bands:",sorted(yb.items()))
    print(" lanes:",[(k,int(v)) for k,v in ln.most_common(12)])
