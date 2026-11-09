cd /srv/opentallas-scratch2/claude/kw35/us
ls -la | cut -c30-; cat integ.sh | cut -c1-220 | head -30; echo ---msg; cat msg.txt | cut -c1-700; echo ---stage; ls stage kvmerge | head -30
cd /srv/opentallas-scratch2/claude/kw36/wt; git fetch -q origin 2>/dev/null
for s in fea7df0c0a6 6e207 e4d7b61 239f665 09c1c7e; do git merge-base --is-ancestor $s origin/main 2>/dev/null && echo "merged $s" || echo "open $s"; done
python3 -I - <<'PY'
import json,collections
c=json.load(open("/home/ubuntu/coord/autopilot/kit_wave.json"))
for k,d in c["dies"].items():
    if isinstance(d,dict): print(k,d.get("src"),d.get("enabled"),len(d.get("gen_hosts") or []),d.get("resume_source") and "resume_source" or "")
st=json.load(open("/home/ubuntu/coord/autopilot/kit_wave_state.json"))
n=collections.Counter()
for v in st["items"].values():
    if str(v.get("started","")).startswith("11-08") or str(v.get("started_pst","")).startswith("11-08"):
        n[str(v.get("kit",""))[:6]]+=1
print(n)
print(list(st["items"].values())[0].keys())
PY
