echo == f hub attempts newer than 6h with real size
for r in /srv/opentallas-scratch2/claude/kw25-wave-1106 /srv/opentallas-scratch2/claude/kw26-wave-1106 /srv/opentallas-scratch3/claude/kw26-wave-1106; do
  n=$(find $r -maxdepth 9 -type d -name 'attempt_*' -mmin -360 2>/dev/null | wc -l); s=$(find $r -maxdepth 9 -type d -name 'attempt_*' -mmin -360 2>/dev/null | head -60 | xargs -r du -s -BM 2>/dev/null | awk '{sub("M","",$1);t+=$1}END{print t+0}')
  echo "$r n=$n sum_first60_MB=$s"
done
python3 -I - <<'PY'
import json,collections,time
s=json.load(open("/home/ubuntu/coord/autopilot/kit_wave_state.json"))
now=time.time();C=collections.Counter()
for v in s["items"].values():
    if now-float(v.get("started") or 0)<8*3600:
        try: h=json.load(open(v["dir"]+"/spec.json")).get("gen_host")
        except Exception: h="?"
        C[h]+=1
print("gen_host of attempts started in 8h:",dict(C))
PY
echo == structural since 11:00 top reasons per die
python3 -I - <<'PY'
import collections
C=collections.Counter()
for l in open("/home/ubuntu/coord/autopilot/structural.tsv",errors="replace"):
    f=l.rstrip("\n").split("\t")
    if len(f)>5 and f[0]>="2026-11-08 11:00": C[(f[3].split("/")[0] if "/" in f[3] else f[3],f[4][:50] if len(f)>4 else "")]+=1
for k,n in C.most_common(14): print(n,k)
PY
