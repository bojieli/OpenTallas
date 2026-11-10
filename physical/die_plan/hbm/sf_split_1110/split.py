# HBM-COLLECT-1 SF-SPLIT 11-10: east/west split of ot_smh_static_front's synthesized netlist at x = XC.
# Every seq cell takes the side of its SF-C placed x (refined by a greedy flop-level min-cut near the cut, port-adjacent
# flops locked); every comb/tie cell is copied into each side its forward cone reaches, so every seam net is driven by a
# flop output (registered launch, 0 pin cycles). Writes W/E gate netlists + the composite top for LEC.
import odb,collections,re,json,os
XC=float(os.environ.get("XC","907.2")); R=float(os.environ.get("REFINE_UM","250")); OUT="/w2/split4"; os.makedirs(OUT,exist_ok=True)
pins={p["name"]:p for p in json.load(open("/w2/pins.json"))}
dbp=odb.dbDatabase.create(); odb.read_db(dbp,"/w/3_place.odb"); P=dbp.getChip().getBlock(); u=float(P.getDbUnitsPerMicron())
pos={i.getName():((i.getBBox().xMin()+i.getBBox().xMax())/2/u,(i.getBBox().yMin()+i.getBBox().yMax())/2/u) for i in P.getInsts()}
dbs=odb.dbDatabase.create(); odb.read_db(dbs,"/w/1_synth.odb"); B=dbs.getChip().getBlock()
SEQ=re.compile(r"DFF|DHL|DLL|SDF|ASYNC|ICG")
insts=list(B.getInsts()); I={i.getName():i for i in insts}
isseq={n:bool(SEQ.search(i.getMaster().getName())) for n,i in I.items()}
psd=lambda b:"W" if pins[b]["x"]<XC else "E"
drv={};sinks=collections.defaultdict(list);netsof=collections.defaultdict(list);bport=collections.defaultdict(list)
for net in B.getNets():
    if net.getSigType() in("POWER","GROUND"): continue
    nn=net.getName()
    for it in net.getITerms():
        nm=it.getInst().getName(); netsof[nm].append((it.getMTerm().getName(),nn))
        if it.isOutputSignal(): drv[nn]=("i",nm)
        else: sinks[nn].append(("i",nm))
    for bt in net.getBTerms():
        bport[nn].append(bt.getName())
        if bt.getIoType()=="INPUT": drv[nn]=("p",bt.getName())
        else: sinks[nn].append(("p",bt.getName()))
outnets=collections.defaultdict(list)
for nn,(t,nm) in drv.items():
    if t=="i": outnets[nm].append(nn)
# flop-level endpoints of each launcher (seq Q nets, input ports) through comb
def endpoints(nets):
    E=set();seen=set();st=list(nets)
    while st:
        nn=st.pop()
        for t,nm in sinks[nn]:
            if t=="p": E.add(("p",nm))
            elif isseq[nm]: E.add(("s",nm))
            elif nm not in seen: seen.add(nm); st.extend(outnets[nm])
    return E
L={}
for n in I:
    if isseq[n]: L[("s",n)]=endpoints(outnets[n])
for nn,(t,nm) in drv.items():
    if t=="p" and nm!="clk": L[("p",nm)]=endpoints([nn])
side={}
for n in I:
    if isseq[n]: side[("s",n)]="W" if pos[n][0]<XC else "E"
for p in pins: side[("p",p)]=psd(p)
# SF-SPLIT fix 11-10 (face_guard feedthrough 32): a port's face flop goes to its PORT's side, not its placed side
for l,E in L.items():
    if l[0]=="p":
        for e in E:
            if e[0]=="s": side[e]=psd(l[1])
forced=0
for l,E in L.items():
    if l[0]=="s":
        ps=[psd(e[1]) for e in E if e[0]=="p"]
        if ps:
            t=max(set(ps),key=ps.count)
            if side[l]!=t: forced+=1
            side[l]=t
fanin=collections.defaultdict(list)
for l,E in L.items():
    for e in E: fanin[e].append(l)
locked=set()
for l,E in L.items():
    if l[0]=="p":
        for e in E: locked.add(e)
    else:
        if any(e[0]=="p" for e in E): locked.add(l)
cnt={l:collections.Counter(side[e] for e in E) for l,E in L.items()}
oth={"W":"E","E":"W"}
def cross(l): return cnt[l][oth[side[l]]]>0
c0=sum(cross(l) for l in L)
cands=[("s",n) for n in I if isseq[n] and abs(pos[n][0]-XC)<=R and ("s",n) not in locked]
nW=sum(1 for k,v in side.items() if k[0]=="s" and v=="W"); nT=sum(1 for k in side if k[0]=="s")
moves=0
for ps in range(12):
    mv=0
    for f in cands:
        s=side[f]; t=oth[s]
        if (s=="W" and nW-1<0.45*nT) or (s=="E" and nT-nW-1<0.45*nT): continue
        aff=[f]+[l for l in fanin[f] if l!=f]
        if any(l[0]=="p" for l in aff[1:]): continue
        before=sum(cross(l) for l in aff)
        for l in fanin[f]: cnt[l][s]-=1; cnt[l][t]+=1
        side[f]=t
        after=sum(cross(l) for l in aff)
        if after<before: mv+=1; nW+= -1 if s=="W" else 1
        else:
            side[f]=s
            for l in fanin[f]: cnt[l][t]-=1; cnt[l][s]+=1
    moves+=mv
    if mv==0: break
c1=sum(cross(l) for l in L)
assert not any(cross(l) for l in L if l[0]=="p"), "port feedthrough"
# comb sides
cs={n:set() for n in I if not isseq[n]}
ch=True
while ch:
    ch=False
    for n in cs:
        s=cs[n];k=len(s)
        for nn in outnets[n]:
            for t,nm in sinks[nn]:
                s |= {psd(nm)} if t=="p" else ({side[("s",nm)]} if isseq[nm] else cs[nm])
        if len(s)!=k: ch=True
for n in cs:
    if not cs[n]: cs[n]={"W"}
home=lambda n:{side[("s",n)]} if isseq[n] else cs[n]
# nets per half
nid={};
def nv(nn):
    if nn not in nid: nid[nn]="n%d"%len(nid)
    return nid[nn]
seam=[]  # (net, from, to)
def need(H):
    S=set()
    for n in I:
        if H in home(n):
            for mt,nn in netsof[n]: S.add(nn)
    for p in pins:
        if psd(p)==H or p=="clk":
            for nn,bl in bport.items():
                pass
    return S
used={H:need(H) for H in "WE"}
pnet={}
for nn,bl in bport.items():
    for b in bl: pnet[b]=nn
for H in "WE":
    for p in pins:
        if (psd(p)==H or p=="clk") and p in pnet: used[H].add(pnet[p])
seams={"W":[], "E":[]}  # outputs of H
for H in "WE":
    for nn in used[H]:
        if nn not in drv: continue
        t,nm=drv[nn]
        if t=="p":
            assert nm=="clk" or psd(nm)==H, ("port xing",nm,H)
        else:
            if H not in home(nm):
                assert isseq[nm], ("comb xing",nm)
                seams[oth[H]].append(nn)
for H in "WE": seams[H]=sorted(set(seams[H]))
def bus(names):
    g=collections.defaultdict(list)
    for b in names:
        m=re.match(r"(.*)\[(\d+)\]$",b)
        if m: g[m.group(1)].append(int(m.group(2)))
        else: g[b].append(None)
    return g
def own(H):
    names=[p for p in pins if psd(p)==H or p=="clk"]
    g=bus(names); m={}
    for base,idx in g.items():
        if idx[0] is None: m[base]=base
        else:
            for j,i in enumerate(sorted(idx)): m["%s[%d]"%(base,i)]="%s[%d]"%(base,j)
    return g,m
OWN={H:own(H) for H in "WE"}
def portdecl(H):
    out=[];g,m=OWN[H]
    for base,idx in sorted(g.items()):
        d=pins[base+("[%d]"%idx[0] if idx[0] is not None else "")]["dir"]
        out.append("%s wire %s%s"%(d,"" if idx[0] is None else "[%d:0] "%(len(idx)-1),base))
    return out
mod={"W":"ot_smh_static_front_w","E":"ot_smh_static_front_e"}
SP={"W":"seam_w2e","E":"seam_e2w"}
for H in "WE":
    o=oth[H]; f=open("%s/%s.v"%(OUT,mod[H]),"w")
    f.write("// GENERATED by HBM-COLLECT-1 SF-SPLIT split.py (11-10): %s half of ot_smh_static_front 1_synth (cut x=%.2f). Do not edit.\n"%(H,XC))
    pd=portdecl(H)+["output wire [%d:0] %s"%(len(seams[H])-1,SP[H]),"input wire [%d:0] %s"%(len(seams[o])-1,SP[o])]
    f.write("module %s(\n  %s\n);\n"%(mod[H],",\n  ".join(pd)))
    for nn in sorted(used[H],key=lambda x:nv(x)): f.write("wire %s;\n"%nv(nn))
    for p in pins:
        if (psd(p)==H or p=="clk") and p in pnet:
            hp=OWN[H][1][p]
            if pins[p]["dir"]=="input": f.write("assign %s = %s;\n"%(nv(pnet[p]),hp))
            else: f.write("assign %s = %s;\n"%(hp,nv(pnet[p])))
    for k,nn in enumerate(seams[H]): f.write("assign %s[%d] = %s;\n"%(SP[H],k,nv(nn)))
    for k,nn in enumerate(seams[o]): f.write("assign %s = %s[%d];\n"%(nv(nn),SP[o],k))
    for n in I:
        if H in home(n):
            c=",".join(".%s(%s)"%(mt,nv(nn)) for mt,nn in netsof[n])
            f.write("(* keep *) %s \\%s  (%s);\n"%(I[n].getMaster().getName(),n.replace("\\",""),c))
    f.write("endmodule\n"); f.close()
# composite (same ports as the original)
f=open(OUT+"/ot_smh_static_front_split.v","w")
g=bus(list(pins))
pd=[]
for base,idx in sorted(g.items()):
    d=pins[base+("[%d]"%idx[0] if idx[0] is not None else "")]["dir"]
    pd.append("%s wire %s%s"%(d,"" if idx[0] is None else "[%d:0] "%max(idx),base))
f.write("// GENERATED by HBM-COLLECT-1 SF-SPLIT: composite of the W/E halves, port-identical to ot_smh_static_front.\nmodule ot_smh_static_front(\n  %s\n);\n"%",\n  ".join(pd))
f.write("wire [%d:0] seam_w2e; wire [%d:0] seam_e2w;\n"%(len(seams["W"])-1,len(seams["E"])-1))
for H in "WE":
    g,m=OWN[H]; h=H.lower(); c=[]
    for base,idx in sorted(g.items()):
        if idx[0] is None: c.append(".%s(%s)"%(base,base)); continue
        f.write("wire [%d:0] %s_%s;\n"%(len(idx)-1,h,base))
        for i in idx:
            o="%s[%d]"%(base,i); hb=h+"_"+m[o]
            f.write(("assign %s = %s;\n"%(o,hb)) if pins[o]["dir"]=="output" else ("assign %s = %s;\n"%(hb,o)))
        c.append(".%s(%s_%s)"%(base,h,base))
    f.write("%s u_%s(%s,.seam_w2e(seam_w2e),.seam_e2w(seam_e2w));\n"%(mod[H],h,",".join(c)))
f.write("endmodule\n");f.close()
# seam geometry: launcher y and far endpoints y
geo=[]
for H in "WE":
    for k,nn in enumerate(seams[H]):
        t,nm=drv[nn]; ys=[pos[nm][1]]+[pos[e[1]][1] for e in L[("s",nm)] if e[0]=="s" and side[e]!=H]
        geo.append({"bus":SP[H],"bit":k,"from":nm,"y":sum(ys)/len(ys)})
st={"XC":XC,"cross_before":c0,"cross_after":c1,"moves":moves,"seq_W":sum(1 for k,v in side.items() if k[0]=="s" and v=="W"),"seq_E":sum(1 for k,v in side.items() if k[0]=="s" and v=="E"),
 "comb_W":sum(1 for n in cs if "W" in cs[n]),"comb_E":sum(1 for n in cs if "E" in cs[n]),"comb_dup":sum(1 for n in cs if len(cs[n])>1),
 "seam_w2e":len(seams["W"]),"seam_e2w":len(seams["E"]),"locked":len(locked),"forced_to_port_side":forced,"cands":len(cands)}
json.dump({"stats":st,"pinmap":{H:OWN[H][1] for H in "WE"},"seam":geo,"side":{k[1]:v for k,v in side.items() if k[0]=="s"}},open(OUT+"/split.json","w"))
print(json.dumps(st))
