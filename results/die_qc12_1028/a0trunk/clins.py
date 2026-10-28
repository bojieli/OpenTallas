import re,sys,json,statistics as st
out={}
for C in ("TT","FF"):
    T={};S={}
    for l in open(f"arr_cl_nk_{C}.txt"):
        p=l.split()
        if p[0]=="T": T[p[1]]=(float(p[2]),float(p[3]))
        elif p[0]=="S":
            m=re.search(r"(a0cl\d+)$",p[3])
            if m: S.setdefault(m.group(1),[]).append(float(p[4]))
    for c,v in S.items():
        a=T[c+"_root/A"][1]
        ins=[x-a for x in v]
        out.setdefault(c,{})[C]=dict(n=len(v),mean=round(st.mean(ins),1),min=round(min(ins),1),max=round(max(ins),1))
json.dump(out,open("clins_nk.json","w"),indent=0)
for c in sorted(out,key=lambda s:int(s[4:])): print(c,out[c]["TT"],out[c]["FF"]["mean"])
