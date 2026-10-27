import csv,json,sys,os
out={}
for d in sys.argv[1:]:
    f=os.path.join(d,'grt/heat_routing.csv')
    if not os.path.exists(f): continue
    m=json.load(open(os.path.join(d,'station_probe.json'))); bx=m['part_bounds_um']
    v=[]
    for r in list(csv.reader(open(f)))[1:]:
        x0,y0,x1,y1,val=map(float,r)
        cx,cy=(x0+x1)/2,(y0+y1)/2
        if bx[0]<=cx<=bx[2] and bx[1]<=cy<=bx[3]: v.append(val)
    v.sort()
    out[os.path.basename(d.rstrip('/'))]=dict(gcells=len(v),max_pct=round(v[-1],1),p99=round(v[int(.99*len(v))],1),over100=sum(x>100 for x in v),over90=sum(x>90 for x in v))
print(json.dumps(out,indent=0))
