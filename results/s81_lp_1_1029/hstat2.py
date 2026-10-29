import json,sys,functools
M=json.load(open(sys.argv[1]))["modules"]; top=sys.argv[2]; maxd=int(sys.argv[3]); minc=int(sys.argv[4])
def key(n): return n if n in M else ("\\"+n if "\\"+n in M else None)
@functools.lru_cache(None)
def tot(n):
    c=f=s=0; a=0.0
    for t,k in M[n]["num_cells_by_type"].items():
        kk=key(t)
        if kk:
            x=tot(kk); c+=x[0]*k; f+=x[1]*k; s+=x[2]*k
        elif "_ASAP7_" in t:
            c+=k; f+=k if t.startswith(("DFF","ASYNC","DHL","DLL","SDF")) else 0
        else: s+=k
    return c,f,s
def show(n,mult,d,inst=""):
    c,f,s=tot(n)
    print("  "*d+f"{mult}x {n[-64:]}  std={c} ff={f} macros={s} (each; x{mult}={c*mult})")
    if d<maxd:
        subs=[(key(t),k) for t,k in M[n]["num_cells_by_type"].items() if key(t)]
        for t,k in sorted(subs,key=lambda x:-tot(x[0])[0]*x[1]):
            if tot(t)[0]*k>=minc: show(t,k,d+1)
r=key(top); show(r,1,0)
own=sum(k for t,k in M[r]["num_cells_by_type"].items() if "_ASAP7_" in t); print("top-level own std cells:",own)
