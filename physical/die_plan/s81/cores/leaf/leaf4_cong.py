import re,sys,collections
from pathlib import Path
for d in sys.argv[1:]:
    d=Path(d)
    bl=[tuple(map(float,m)) for m in re.findall(r"create_blockage -region \{(\S+) (\S+) (\S+) (\S+)\}",(d/"probe.tcl").read_text())]
    f=d/"grt_congestion.rpt"
    if not f.exists(): print(d.name,"no rpt"); continue
    txt=f.read_text()
    n=inb=cap0=0; cells=collections.Counter(); ov=0
    for m in re.finditer(r"capacity:(\d+) usage:(\d+) congestion:(\d+)\s*\n\s*bbox = \((\S+), (\S+)\) - \((\S+), (\S+)\)",txt):
        c,u,g=map(int,m.group(1,2,3)); x=(float(m.group(4))+float(m.group(6)))/2; y=(float(m.group(5))+float(m.group(7)))/2
        n+=1; ov+=u-c
        if c==0: cap0+=1
        if any(b[0]-2<=x<=b[2]+2 and b[1]-2<=y<=b[3]+2 for b in bl): inb+=1
        cells[(int(x//100),int(y//100))]+=u-c
    top=cells.most_common(6)
    print(d.name, "gcells",n,"ov",ov,"in/near blockage %.0f%%"%(100*inb/max(n,1)),"cap0 %.0f%%"%(100*cap0/max(n,1)),"hot100um",[(k[0]*100,k[1]*100,v) for k,v in top])
