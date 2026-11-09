cd /srv/opentallas-scratch2/claude/kw35/us
python3 -I - <<'PY'
import json,subprocess
c=json.load(open("/home/ubuntu/coord/autopilot/kit_wave.json"))
for k,d in c["dies"].items():
    if not isinstance(d,dict): continue
    hs=[h for h in (d.get("gen_hosts") or []) if h!="intel2"]
    out=[]
    for h in hs:
        r=subprocess.run(["ssh","-n","-o","ControlPath=none","-o","ConnectTimeout=8",h,f"S=$(realpath {d['src']} 2>/dev/null); echo $S $(grep -c 'class LeafFollow' $S/tools/die_plan/bind.py 2>/dev/null) $(cat $S/SOURCE_COMMIT 2>/dev/null | cut -c1-11)"],capture_output=True,text=True,timeout=40)
        out.append(h+":"+r.stdout.strip())
    print(k,d.get("event"),out)
PY
sed -n 1,30p scan.py | cut -c1-160
ls -la --time-style=+%H:%M affected.tsv summary.txt | cut -c25-
grep -n "LeafFollow\|src_.*us\|US batch\|leaf follow" ~/coord/autopilot/kit_wave.json | cut -c1-240 | head
