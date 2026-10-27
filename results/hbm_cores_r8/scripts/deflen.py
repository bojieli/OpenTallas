import re,sys
B=sys.argv[1]; nets=sys.argv[2:]
out={}; cur=None; buf=None; insec=False
for line in open(B):
    s=line.strip()
    if s.startswith("NETS "): insec=True; continue
    if not insec: continue
    if s.startswith("END NETS"): break
    if s.startswith("- "):
        cur=s.split()[1]
        buf=[s] if any(cur.endswith(n) for n in nets) else None
        if buf is not None and s.endswith(";"): out[cur]=s; buf=None
        continue
    if buf is not None:
        buf.append(s)
        if s.endswith(";"): out[cur]=" ".join(buf); buf=None
for k,v in out.items():
    lens={}; vias=0
    for seg in re.split(r"\b(?:ROUTED|NEW)\b",v)[1:]:
        m=re.match(r"\s*(M\d)\s+(?:\d+\s+)?(?:\+ SHAPE \w+\s+)?(.*)",seg)
        if not m: continue
        L=m.group(1); pts=re.findall(r"\(\s*(\S+)\s+(\S+)(?:\s+\S+)?\s*\)",m.group(2))
        px=py=None
        for x,y in pts:
            x=px if x=="*" else int(x); y=py if y=="*" else int(y)
            if px is not None: lens[L]=lens.get(L,0)+abs(x-px)+abs(y-py)
            px,py=x,y
        vias+=len(re.findall(r"\)\s+[A-Za-z]\w*",m.group(2)))
    print(k.split("/")[-1], re.search(r"g_bank\\\[(\d+)",k).group(1), {L:round(x/1000,1) for L,x in sorted(lens.items())}, "total_um", round(sum(lens.values())/1000,1), "vias", vias)
