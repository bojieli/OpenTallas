import json,sys,statistics as st,collections
base=json.load(open(sys.argv[1])); new=json.load(open(sys.argv[2]))
for C,f in (("TT","meas_ck_TT.tsv"),("FF","meas_ck_FF.tsv")):
    agg=collections.defaultdict(list)
    for ln in open(f):
        if ln[0]=='#':continue
        t=ln.split('\t'); lf=t[1][6:-4]
        agg[lf].append(float(t[2]) if C=="TT" else min(float(t[4]),float(t[5])))
    pb,pn=base[C+"_leaf"],new[C+"_leaf"]
    ks=[k for k in agg if k in pb and k in pn and not k.startswith('m')]
    meas={k:st.mean(agg[k]) for k in ks}
    est={k:pn[k]+meas[k]-pb[k] for k in ks}
    v=list(est.values()); m=list(meas.values())
    print(C,"R7 meas leaf-mean w%.2f | sized pred w%.2f | sized + R7 per-leaf residual: mean %.2f w%.2f"%(max(m)-min(m),max(pn[k] for k in ks)-min(pn[k] for k in ks),st.mean(v),max(v)-min(v)))
