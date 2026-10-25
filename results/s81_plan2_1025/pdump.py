import json
CK={"ft_slots","contents","hard_cores"}
def _d(x, lvl, key=None):
    pad=" "*lvl; pad1=" "*(lvl+1)
    if isinstance(x, dict):
        if not x: return "{}"
        return "{\n"+",\n".join(pad1+json.dumps(k)+": "+_d(v,lvl+1,k) for k,v in x.items())+"\n"+pad+"}"
    if isinstance(x, list):
        if not x: return "[]"
        if key in CK:
            return "[\n"+",\n".join(pad1+json.dumps(v,separators=(",",":")) for v in x)+"\n"+pad+"]"
        return "[\n"+",\n".join(pad1+_d(v,lvl+1) for v in x)+"\n"+pad+"]"
    return json.dumps(x)
def dumps(raw): return _d(raw,0)+"\n"
if __name__=="__main__":
    import sys; s=open(sys.argv[1]).read(); t=dumps(json.loads(s)); print(len(s),len(t),s==t)
    if s!=t:
        import difflib
        a=s.splitlines(); b=t.splitlines()
        for i,(p,q) in enumerate(zip(a,b)):
            if p!=q: print(i,p[:200]); print(i,q[:200]); break
