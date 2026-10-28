import json,sys,collections
P=json.load(open(sys.argv[1])); t=json.load(open(sys.argv[2]))
xy={tp["part"]:tp["xy"] for tp in t["taps"]}
# region of a part = clock_region of its leaf node (kit tree nodes)
nodes=t.get("nodes")
reg={}
if isinstance(nodes,dict): nodes=list(nodes.values())
for n in nodes or []:
    if n.get("part") and n.get("clock_region"): reg[n["part"]]=n["clock_region"]
print("regions", len(set(reg.values())), "parts with region", len(reg))
tot=inb=0; bm_in=bm_x=0; cx=collections.Counter(); xings=0
for p in P["ports"]:
    a,b=p["src"]["part"],p["dst"]["part"]; w=p.get("width",1)
    L=(abs(xy[a][0]-xy[b][0])+abs(xy[a][1]-xy[b][1]))/1000
    tot+=w
    if reg.get(a)==reg.get(b): inb+=w; bm_in+=w*L
    else: bm_x+=w*L; xings+=1
print(f"bits total {tot} inside {inb} ({100*inb/tot:.1f}%), bit-mm inside {bm_in:.0f} across {bm_x:.0f} ({100*bm_in/(bm_in+bm_x):.1f}% inside), crossing ports {xings} of {len(P['ports'])}")
