# PREDICTION ONLY: model the top spine as one common point (shorted M8 spine = 1-D mesh row) for landed_phase_ocv
import json,sys,shutil,os
src,dst=sys.argv[1],sys.argv[2]
T=json.load(open(src+"/clk/tree.json"))
N={int(k):v for k,v in T["nodes"].items()}
ent=[i for i,n in N.items() if n.get("region_entry")]
drv=sorted({N[i]["parent"] for i in ent})
os.makedirs(dst+"/clk",exist_ok=True)
for C in ("TT","FF"):
    os.makedirs(f"{dst}/out_{C}",exist_ok=True)
    L=open(f"{src}/out_{C}/arr_{C}.txt").read().splitlines()
    arrN={l.split()[1]:float(l.split()[2]) for l in L if l.startswith("N ")}
    a=[arrN[T["node_buf"][str(d)]] for d in drv]
    print(C,"spine drivers",len(drv),"arrival min/max",round(min(a),1),round(max(a),1))
    L.append(f"N bSPINE {sum(a)/len(a):.3f} {sum(a)/len(a):.3f}")
    open(f"{dst}/out_{C}/arr_{C}.txt","w").write("\n".join(L)+"\n")
# cut each entry chain at the spine driver: the first cell below the driver hangs off bSPINE
for e in ent:
    c=T["node_buf"][str(e)]
    pd=T["node_buf"][str(N[e]["parent"])]
    while T["parent_of"].get(c)!=pd: c=T["parent_of"][c]
    T["parent_of"][c]="bSPINE"
T["parent_of"]["bSPINE"]="b0"
ys=T["meta"]["slice_spine"]["spine_row_y_um"]; xa,xb=T["meta"]["slice_spine"]["spine_x_um"]
T["sites"]["bSPINE"]=[(xa+xb)/2,ys]
json.dump(T,open(dst+"/clk/tree.json","w"))
