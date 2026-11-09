cd /
R=$1; shift
for it in "$@"; do
 n=${it%:*}; a=${it#*:}; A=$R/items/$n/attempt_$a/rtl
 python3 -I - "$A" "$n" "$a" <<'PY'
import json,sys,os,re
A,n,a=sys.argv[1:4]
d=json.load(open(A+"/kit_rtl.json"))
fl=[l.strip() for l in open(A+"/kit_rtl.f") if l.strip() and not l.startswith(("+","-","//"))]
def m(l): return l if l.startswith("/") else os.path.join(A,l)
miss=[l for l in fl if not os.path.exists(m(l))]
kv=[l for l in fl if "bind_kvcls" in l]
cw=[l for l in fl if "kv_sys_phy" in l or "codex-wave-bind-1106" in l]
print(n,"a"+a,"bind_out",d.get("bind_out"),"plan",str(d.get("plan"))[-60:],"| f lines",len(fl),"missing",len(miss),"bind_kvcls",len(kv),"cwb",len(cw),"| first missing",miss[:3])
t=json.dumps(d); print("  json mentions kvcls",t.count("bind_kvcls"),"kv_sys_phy",t.count("kv_sys_phy"))
PY
done
