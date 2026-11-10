# HBM-COLLECT-1 SF-SPLIT structural equivalence: composite(W,E) == gold 1_synth.v under comb duplication.
# Independent text parse of both files. For every cell input pin and every output port of the composite, the driver
# (cell output pin or input port, resolved through assigns, half ports and the seam) must be the gold driver of the
# same pin; every gold cell must exist with the same master. Sound: duplicated comb copies get identical inputs.
import re,sys,collections
def norm(s): return s.replace("\\","").strip()
TOK=re.compile(r"\\\S+|[A-Za-z_][\w$]*(?:\[\d+\])?")
def parse(path):
    mods={};cur=None;buf=""
    for line in open(path):
        line=line.split("//")[0].strip()
        if not line: continue
        buf+=" "+line
        if not buf.rstrip().endswith(";") and not buf.rstrip().endswith(")") : continue
        st=buf.strip();buf=""
        if st.startswith("module"):
            name=st.split()[1].split("(")[0]; cur={"ports":{},"assign":[],"cells":[]}; mods[name]=cur
            for d,w,n in re.findall(r"(input|output)\s+wire\s*(\[\d+:\d+\])?\s*([\w$]+)",st):
                cur["ports"][n]=(d,int(w[1:].split(":")[0])+1 if w else None)
            # verilog-1995 style port list handled below
            continue
        if cur is None: continue
        for d,w,ns in re.findall(r"^(input|output)\s*(\[\d+:\d+\])?\s*([^;]+);",st):
            for n in ns.split(","): cur["ports"][norm(n)]=(d,int(w[1:].split(":")[0])+1 if w else None)
        if st.startswith("endmodule"): cur=None; continue
        if st.startswith(("wire","input","output","reg")): continue
        if st.startswith("assign"):
            m=re.match(r"assign\s+(.+?)\s*=\s*(.+?)\s*;",st); cur["assign"].append((norm(m.group(1)),norm(m.group(2)))); continue
        st=re.sub(r"^\(\*[^*]*\*\)\s*","",st)
        m=re.match(r"(\S+)\s+(\\\S+|[^\s(]+)\s*\((.*)\)\s*;",st)
        if m:
            conns=dict((p,norm(n)) for p,n in re.findall(r"\.(\w+)\s*\(\s*(\\\S+\s|[^()\s]*)\s*\)",m.group(3)))
            cur["cells"].append((m.group(1),norm(m.group(2)),conns))
    return mods
import json
def bits(ports):
    for n,(d,w) in ports.items():
        if w is None: yield n,d
        else:
            for k in range(w): yield "%s[%d]"%(n,k),d
class UF:
    def __init__(s): s.p={}
    def f(s,x):
        s.p.setdefault(x,x)
        while s.p[x]!=x: s.p[x]=s.p[s.p[x]]; x=s.p[x]
        return x
    def u(s,a,b): s.p[s.f(a)]=s.f(b)
OUTP=set()
def load_outpins(lib_cells):pass
def flat_driver_map(mods,top,outpin):
    """returns: cells {(scope,name):(master,conns_global)}, driver of each global net class, port bits"""
    uf=UF();cells=[]
    T=mods[top]
    def inst(modname,scope):
        M=mods[modname]
        for a,b in M["assign"]: uf.u(scope+a,scope+b)
        for master,name,conns in M["cells"]:
            if master in mods:
                sub=mods[master]
                for p,(d,w) in sub["ports"].items():
                    rng=[None] if w is None else range(w)
                    for k in rng:
                        pb=p if k is None else "%s[%d]"%(p,k)
                        ab=conns[p] if k is None else "%s[%d]"%(conns[p],k)
                        uf.u(scope+name+"/"+pb, scope+ab)
                inst(master,scope+name+"/")
            else: cells.append((scope,master,name,{p:scope+n for p,n in conns.items()}))
    inst(top,"")
    drv=collections.defaultdict(list)
    for b,d in bits(T["ports"]):
        if d=="input": drv[uf.f(b)].append(("port",b))
    for scope,master,name,conns in cells:
        for p,n in conns.items():
            if (master,p) in outpin: drv[uf.f(n)].append((name,p))
    return uf,cells,drv,T
def main(gold,comp_files,libpins):
    outpin=set(tuple(x) for x in json.load(open(libpins)))
    G=parse(gold); C={}
    for f in comp_files: C.update(parse(f))
    gtop="ot_smh_static_front"
    guf,gcells,gdrv,GT=flat_driver_map(G,gtop,outpin)
    cuf,ccells,cdrv,CT=flat_driver_map(C,gtop,outpin)
    err=collections.Counter();ex=[]
    def one(d,uf,n):
        L=d.get(uf.f(n),[])
        names=set(L)
        return ("NONE",) if not names else (sorted(names)[0] if len(names)==1 else ("MULTI",tuple(sorted(names))))
    gm={name:(master,conns) for s,master,name,conns in gcells}
    seen=set()
    for scope,master,name,conns in ccells:
        seen.add(name)
        if name not in gm: err["extra_cell"]+=1; ex.append(("extra",name)); continue
        gmast,gconns=gm[name]
        if gmast!=master: err["master"]+=1; ex.append(("master",name)); continue
        for p,n in conns.items():
            if (master,p) in outpin: continue
            if p not in gconns: err["pin"]+=1; continue
            a=one(cdrv,cuf,n); b=one(gdrv,guf,gconns[p])
            if a!=b: err["driver"]+=1; ex.append(("drv",name,p,a,b))
    for name in gm:
        if name not in seen: err["missing_cell"]+=1; ex.append(("missing",name))
    for b,d in bits(GT["ports"]):
        if d=="output":
            a=one(cdrv,cuf,b); g=one(gdrv,guf,b)
            if a!=g: err["outport"]+=1; ex.append(("out",b,a,g))
    multi=sum(1 for v in cdrv.values() if len(set(v))>1)
    print(json.dumps({"gold_cells":len(gcells),"comp_cells":len(ccells),"dup_copies":len(ccells)-len(set(n for _,_,n,_ in ccells)),"multi_driven":multi,"errors":err,"examples":[str(e)[:200] for e in ex[:6]]}))
    print("VERDICT", "EQUIVALENT" if not err and not multi else "NOT_EQUIVALENT")
main(sys.argv[1],sys.argv[2:-1],sys.argv[-1])
