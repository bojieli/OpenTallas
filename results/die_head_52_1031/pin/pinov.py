"""Same-layer pin rectangle overlap check over every partition type's io.tcl (generated from the plan)."""
import sys,re,json,collections
sys.path.insert(0,sys.argv[1]+"/tools/die_plan")
import schema as S, gen_phys as G
P=S.Plan(S.load(sys.argv[2]))
rx=re.compile(r"place_pin -pin_name \{?([^ }]+)\}? -layer (\S+) -location \{([-\d.]+) ([-\d.]+)\} -pin_size \{([-\d.]+) ([-\d.]+)\}(.*)")
res={}
for tn in sorted(P.types):
    if P.types[tn].get("hard"): continue
    try: txt=G.io_tcl(P,tn,G.type_pins(P,tn))
    except Exception as e: res[tn]={"error":repr(e)};continue
    rects=[]
    for l in txt.splitlines():
        m=rx.match(l)
        if not m: continue
        n,ly,x,y,w,h,c=m.groups();x,y,w,h=map(float,(x,y,w,h))
        rects.append((n,ly,x-w/2,y-h/2,x+w/2,y+h/2,c.strip(" ;#")))
    grid=collections.defaultdict(list);hits=[]
    for i,r in enumerate(rects):
        for gx in range(int(r[2]//2),int(r[4]//2)+1):
            for gy in range(int(r[3]//2),int(r[5]//2)+1):
                grid[(r[1],gx,gy)].append(i)
    seen=set()
    for k,ids in grid.items():
        for a in range(len(ids)):
            for b in range(a+1,len(ids)):
                i,j=ids[a],ids[b]
                if (i,j) in seen: continue
                seen.add((i,j));A,B=rects[i],rects[j]
                if A[2]<B[4]-1e-6 and B[2]<A[4]-1e-6 and A[3]<B[5]-1e-6 and B[3]<A[5]-1e-6 and A[0]!=B[0]:
                    hits.append([A[0],B[0],A[1],[round(v,4) for v in A[2:6]],[round(v,4) for v in B[2:6]],A[6],B[6]])
    res[tn]={"pins":len(rects),"overlaps":hits}
json.dump(res,open(sys.argv[3],"w"),indent=1)
for tn,r in res.items():
    if "error" in r: print(tn,"ERROR",r["error"][:200]);continue
    print(tn,r["pins"],"overlaps",len(r["overlaps"]))
    for h in r["overlaps"][:20]: print("   ",h)
