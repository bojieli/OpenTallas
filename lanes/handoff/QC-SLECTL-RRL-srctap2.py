"""QC-RST-SRCTAP row v2 (QC-SLECTL-RRL).  Cause: landing collector sources name their reset node by tap index (sidecar
collector.types[].local_sources, read by bind/gen) while the tree comes from the plan (landing_collector.effective_tree);
the plan tree was re-numbered (reset solve / tap re-grid) and the sidecar indices were not reattached, so
u_cland_collect_<node> and the raw copy u_cland_rst_<bus> are SEATED at a far relay (landing_place) while the RTL raw copy
taps the ring tap nearest the pin (clock_landings) -> long ready/fault and raw-reset hops (slw_sc_v1 rrl_197 1463 um,
cl5e017c6f collect -156 ps).  Fix: node := the ring tap the RTL already uses (nearest rst_n_t<i> of the plan tree to the
bus pin) for every source whose effective hop fails (raw > 300 um or status > 405 um), same depth required; children
whose node is absent / over reach: nearest same-depth relay.  Writes node/tap only, in plan AND sidecar.
argv: plan sidecar plan_out sidecar_out row_out"""
import json,sys,re,hashlib,copy
D=lambda a,b: abs(a[0]-b[0])+abs(a[1]-b[1])
plan=json.load(open(sys.argv[1])); side=json.load(open(sys.argv[2])); st=side["collector"]["types"]
def view(p, s_types):
    """effective (plan tree, sidecar node) per source -> list of dict"""
    out=[]
    for tn,t in sorted(p["partition_types"].items()):
        lc=(t.get("clock") or {}).get("landing_contract")
        if not isinstance(lc,dict) or not isinstance(lc.get("collector_tree"),dict) or lc["collector_tree"].get("hard") or tn not in s_types: continue
        tr=lc["collector_tree"]; rel={r["q"]:r for r in tr.get("relays",[])}
        if not rel: continue
        xy={"rst_root_n":tr["root"],**{q:r["xy"] for q,r in rel.items()}}
        taps={q:r for q,r in rel.items() if re.fullmatch(r"rst_n_t\d+",q)}
        sby={s["name"]:s for s in s_types[tn].get("local_sources") or []}
        for s in lc.get("collector_local_sources") or []:
            ss=sby.get(s["name"])
            if ss is None or (ss.get("tap") is None and ss.get("node") and not ss["node"].startswith("rst_n_t")): continue
            node=ss.get("node",f"rst_n_t{ss.get('tap',0)}")
            pin=s.get("pin_xy_um") or s["xy_um"]; pts=s.get("status_pins_xy_um",[s["xy_um"]])
            rt=min(taps,key=lambda q:D(taps[q]["xy"],pin)); pxy=xy.get(rel[rt]["d"])
            seat=xy.get(node)
            a=D(seat,pxy) if seat and pxy else 1e9; b=max(D(q,seat) for q in pts) if seat else 1e9
            out.append(dict(type=tn,name=s["name"],node=node,rtap=rt,raw_um=round(a,1),status_um=round(b,1),
                            depth=rel[node]["depth"] if node in rel else None,rtap_depth=rel[rt]["depth"],rtap_status_um=round(max(D(q,taps[rt]["xy"]) for q in pts),1)))
    return out
def setnode(r,q):
    if "node" in r or not re.fullmatch(r"rst_n_t\d+",q): r["node"]=q
    if re.fullmatch(r"rst_n_t\d+",q): r["tap"]=int(q[7:])
    else: r.pop("tap",None)
before=view(plan,st)
P2=copy.deepcopy(plan); S2=copy.deepcopy(side); st2=S2["collector"]["types"]; changes={}
for v in before:
    if v["raw_um"]<=300 and v["status_um"]<=405: continue
    if v["depth"] is not None and v["rtap_depth"]!=v["depth"]: raise SystemExit(f"DEPTH {v}")
    if v["rtap_status_um"]>405: raise SystemExit(f"REACH {v}")
    tn=v["type"]; new=v["rtap"]
    for s in st2[tn]["local_sources"]:
        if s["name"]==v["name"]: setnode(s,new)
    changes.setdefault(tn,{})[v["name"]]=dict(node_old=v["node"],node=new,raw_um_old=v["raw_um"],status_um_old=v["status_um"],status_um=v["rtap_status_um"])
# children with absent / over-reach node (sidecar view): nearest same-depth relay
kids={}
for tn,t in sorted(P2["partition_types"].items()):
    lc=(t.get("clock") or {}).get("landing_contract")
    if not isinstance(lc,dict) or not isinstance(lc.get("collector_tree"),dict) or lc["collector_tree"].get("hard") or tn not in st2: continue
    tr=lc["collector_tree"]; rel={r["q"]:r for r in tr.get("relays",[])}
    if not rel: continue
    tapdep={r["depth"] for q,r in rel.items() if re.fullmatch(r"rst_n_t\d+",q)}
    sk=st2[tn].get("children") or []
    for i,(c,cs) in enumerate(zip(lc.get("collector_children") or [], sk)):
        n=cs.get("node",f"rst_n_t{cs.get('tap',0)}"); pts=c.get("status_pins_xy_um",[c["xy_um"]])
        hop=lambda q: max(D(p,rel[q]["xy"]) for p in pts)
        if n in rel and hop(n)<=405: continue
        dep=rel[n]["depth"] if n in rel else (next(iter(tapdep)) if len(tapdep)==1 else None)
        if dep is None: raise SystemExit(f"CHILD depth {tn} {i}")
        h,q=min((hop(q),q) for q,r in rel.items() if r["depth"]==dep)
        if h>405: raise SystemExit(f"CHILD reach {tn} {i}")
        setnode(cs,q)
        kids.setdefault(tn,[]).append(dict(index=i,node_old=n,node=q,status_um=round(h,1)))
synced=0
for tn,row_ in st2.items():
    t=P2["partition_types"].get(tn); lc=((t or {}).get("clock") or {}).get("landing_contract")
    if not isinstance(lc,dict): continue
    by={x["name"]:x for x in row_.get("local_sources") or []}
    pairs=[(s_,by.get(s_.get("name"))) for s_ in lc.get("collector_local_sources") or []]+list(zip(lc.get("collector_children") or [],row_.get("children") or []))
    for a_,b_ in pairs:
        if b_ is None: continue
        for k in ("node","tap"):
            if b_.get(k)!=a_.get(k):
                if k in b_: a_[k]=b_[k]
                else: a_.pop(k,None)
                synced+=1
print("plan fields synced to sidecar",synced)
# (c) u_cland_rst_<bus> seat overrides (landing_contract.group_rects_um) that put the raw copy > 300 um from its RTL D
# source (the raw parent of the ring tap nearest the pin): removed, so landing_place seats the copy at its node relay.
dropped={}
for tn,t in sorted(P2["partition_types"].items()):
    lc=(t.get("clock") or {}).get("landing_contract")
    if not isinstance(lc,dict) or not lc.get("group_rects_um") or not isinstance(lc.get("collector_tree"),dict) or tn not in st2: continue
    rel={r["q"]:r for r in lc["collector_tree"].get("relays",[])}
    xy={"rst_root_n":lc["collector_tree"].get("root"),**{q:r["xy"] for q,r in rel.items()}}
    taps={q:r for q,r in rel.items() if re.fullmatch(r"rst_n_t\d+",q)}
    by={x["name"]:x for x in lc.get("collector_local_sources") or []}
    sby={x["name"]:x for x in st2[tn].get("local_sources") or []}
    for g in sorted(lc["group_rects_um"]):
        if not (g.startswith("u_cland_rst_") and g[12:] in by and g[12:] in sby): continue
        r=lc["group_rects_um"][g]; c=((r[0]+r[2])/2,(r[1]+r[3])/2); s_=by[g[12:]]
        pin=s_.get("pin_xy_um") or s_["xy_um"]; rt=min(taps,key=lambda q:D(taps[q]["xy"],pin)); par=xy[rel[rt]["d"]]
        if D(c,par)<=300: continue
        node=sby[g[12:]].get("node",f"rst_n_t{sby[g[12:]].get('tap',0)}"); seat=xy[node]
        b=(s_.get("band") or {}).get("rect_um"); bc=((b[0]+b[2])/2,(b[1]+b[3])/2) if b else pin
        dh=D(seat,par)
        if dh>300: raise SystemExit(f"OVR default seat still far {tn} {g} {dh}")
        dropped.setdefault(tn,{})[g]=dict(rect_old=r,d_hop_old_um=round(D(c,par),1),d_hop_um=round(dh,1),q_to_band_old_um=round(D(c,bc),1),q_to_band_um=round(D(seat,bc),1))
        del lc["group_rects_um"][g]
print("overrides dropped",sum(map(len,dropped.values())),"types",len(dropped),"max q_to_band",max((v["q_to_band_um"] for d in dropped.values() for v in d.values()),default=0))
after=view(P2,st2)
def summ(v): return dict(sources=len(v),raw_over300=sum(x["raw_um"]>300 for x in v),status_over405=sum(x["status_um"]>405 for x in v),
                         raw_max=max(x["raw_um"] for x in v),status_max=max(x["status_um"] for x in v))
json.dump(P2,open(sys.argv[3],"w"),separators=(",",":")); json.dump(S2,open(sys.argv[4],"w"),separators=(",",":"))
sh=lambda f: hashlib.sha256(open(f,"rb").read()).hexdigest()[:12]
row=dict(schema="qc_row.collector_source_node.v2",row="QC-RST-SRCTAP",lane="QC-SLECTL-RRL",
  base=dict(plan=sh(sys.argv[1]),sidecar=sh(sys.argv[2])),out=dict(plan=sh(sys.argv[3]),sidecar=sh(sys.argv[4])),
  apply="(a) plan collector_local_sources/collector_children node+tap := sidecar (one identity; plan copies were stale); (b) landing_contract.collector_local_sources[name].tap (and collector_children[i].tap/node) in the plan, (c) delete group_rects_um[u_cland_rst_<bus>] overrides whose seat is > 300 um from the RTL raw parent, and the SAME fields in sidecar collector.types[type].local_sources/children; nothing else; 0 cycles (depth preserved)",
  cause=__doc__.split("Fix:")[0].strip(), rule="Fix:"+__doc__.split("Fix:")[1].split("argv:")[0].strip(),
  check=dict(before=summ(before),after=summ(after)),changes=changes,children=kids,overrides_dropped=dropped)
json.dump(row,open(sys.argv[5],"w"),indent=1,sort_keys=True)
print("BEFORE",summ(before)); print("AFTER",summ(after)); print("types",len(set(changes)|set(kids)|set(dropped)),"sources",sum(map(len,changes.values())),"children",sum(map(len,kids.values())))
for x in sorted(after,key=lambda x:-x["raw_um"])[:5]: print(" worst_after",x)
print("ROW",sh(sys.argv[5]),"plan",sh(sys.argv[3]),"sidecar",sh(sys.argv[4]))
