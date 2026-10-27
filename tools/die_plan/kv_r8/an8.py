import json,sys,statistics as st
d=sys.argv[1]; C=sys.argv[2]
M=json.load(open(f"{d}/b5/mesh.json")); band=set(sys.argv[3].split(","))
tp={t["stub"]:t for t in M["taps"]}
S=json.load(open(f"{d}/lin/die_{C}.json"))["samples"]
R=json.load(open(f"{d}/b5/mesh_{C}.json"))["stubs"]
def split(a):
    b=[v for k,v in a.items() if tp[k]["part"] in band or tp[k]["part"].startswith(("hroot","hub","sys","io_"))]
    r=[v for k,v in a.items() if not (tp[k]["part"] in band or tp[k]["part"].startswith(("hroot","hub","sys","io_")))]
    return r,b
for name,a in (("sim nominal",S[0]["tap_arr_ps"]),("routed late",{k:v["late"] for k,v in R.items()})):
    r,b=split(a); print(C,name,"array n=%d %.1f..%.1f (%.1f)"%(len(r),min(r),max(r),max(r)-min(r)),"band n=%d %.1f..%.1f"%(len(b),min(b),max(b)),"band-array median %.1f"%(st.median(b)-st.median(r)))
r,b=split(S[0]["tap_arr_ps"])
w=[]
for s in S[1:]:
    r_,b_=split(s["tap_arr_ps"]); w.append(max(r_)-min(r_))
print(C,"MC array-only tap skew max %.1f"%max(w))
