cd /
echo "== resign"
for r in t24c t29; do d=/srv/opentallas-scratch2/claude/kw37/eco/$r/i1; ssh -n -o ControlPath=none epyc4 "ls -d $d/resign* 2>/dev/null; ls -la --time-style=+%H:%M $d | tail -n +2 | head -30"; done
ssh -n -o ControlPath=none intel2 'python3 -I - <<PY
import json,os
s=json.load(open(os.path.expanduser("~/coord/autopilot/auto_resign_state.json")))
print(type(s), list(s)[:6] if isinstance(s,dict) else len(s))
for k in ("jobs","items","rows","running"):
    v=s.get(k) if isinstance(s,dict) else None
    if isinstance(v,dict):
        for a,b in v.items():
            if "t24__cleec" in a or "t29__clc" in a: print(k,a,json.dumps(b)[:700])
if isinstance(s,dict):
    for a,b in s.items():
        if "t24__cleec" in a or "t29__clc" in a: print(a,json.dumps(b)[:700])
PY'
