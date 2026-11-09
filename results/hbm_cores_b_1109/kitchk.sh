cd /
R=$1; shift
for it in "$@"; do
 n=${it%:*}; a=${it#*:}; G=$R/items/$n/attempt_$a/gen/$n
 echo "== $n a$a $(ls -d $G 2>&1 | cut -c1-40)"
 for f in $G/kit_rtl.json $G/kit_rtl.f; do [ -f $f ] && echo "$(grep -c 'bind_kvcls' $f) kvcls, $(grep -c 'kv_sys_phy\|codex-wave-bind-1106' $f) kvsysphy/cwb in $(basename $f)"; done
 python3 -I - "$G" <<'PY'
import json,sys,os,re
G=sys.argv[1]
p=G+"/kit_rtl.json"
if not os.path.exists(p): print(" no kit_rtl.json"); raise SystemExit
d=json.load(open(p))
print(" keys",[k for k in d][:12], {k:d[k] for k in ("bind_out","plan","asbuilt") if k in d})
t=json.dumps(d)
paths=sorted(set(re.findall(r'/srv/[A-Za-z0-9_./-]+',t)))
miss=[x for x in paths if not os.path.exists(x)]
print(" abs paths",len(paths),"missing",len(miss),miss[:5])
PY
done
