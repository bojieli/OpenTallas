import sys
sys.path.insert(0,"kitlec"); import lec, re
d=lec.read_aig(sys.argv[1]); m=lec.read_map(sys.argv[2])
pis,cps,xs,anon,alias=lec.key_points(d,m)
R=lec.reset_vars(d,pis,None,{})
st,first=lec.reset_state(d,R,int(sys.argv[3]))
pat=re.compile(sys.argv[4])
for k,lit in sorted(pis.items()):
    if k.startswith("ff:") and pat.search(k):
        v=lit>>1; print(k, "const" if v in st else "UNKNOWN", st.get(v) if v in st else "", first.get(v))
