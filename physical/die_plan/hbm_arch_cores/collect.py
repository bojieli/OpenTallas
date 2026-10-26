#!/usr/bin/env python3
"""ELEM-HBM: collect signoff verdicts of launched B2l core kits from their hosts into results/b2l_verdicts.json.
    collect.py [--kits /srv/opentallas-scratch/claude/elem-hbm/kits_b2l]
Per kit: host (launch.log), every signoff*/signoff.json in the run dir (newest last), verdict SIGNED / NOT SIGNED with
reasons, run state.  A recorded NOT SIGNED is never replaced by a later record: the history keeps every record."""
import argparse, json, subprocess, re
from pathlib import Path
H = Path(__file__).resolve().parent
ap = argparse.ArgumentParser(); ap.add_argument("--kits", default="/srv/opentallas-scratch/claude/elem-hbm/kits_b2l")
a = ap.parse_args()
B = Path("/srv/opentallas-scratch/claude/elem-hbm"); ROOT = "/srv/opentallas-scratch/claude/elem-hbm/runs"
host = {}
for l in open(B / "launch.log"):
    m = re.match(r"\S+ \S+ (\S+) -> (\S+?):", l)
    if m: host[m.group(1)] = m.group(2)
out = H / "results" / "b2l_verdicts.json"; out.parent.mkdir(exist_ok=True)
old = json.load(open(out)) if out.is_file() else {}
for kd in sorted(Path(a.kits).iterdir()):
    if not (kd / "freeze.json").is_file() or kd.name not in host: continue
    h = host[kd.name]; rd = f"{ROOT}/{kd.name}"
    cmd = f"for f in $(ls -d {rd}/signoff* 2>/dev/null); do [ -f $f/signoff.json ] && echo \"@@$f\" && cat $f/signoff.json; done"
    r = subprocess.run(cmd if h == "localhost" else ["ssh", h, cmd], shell=(h == "localhost"), capture_output=True, text=True)
    recs = []
    for chunk in r.stdout.split("@@")[1:]:
        path, _, body = chunk.partition("\n")
        try: s = json.loads(body)
        except Exception: continue
        ch = s.get("checks", {})
        recs.append(dict(path=f"{h}:{path}", verdict=s.get("verdict"), reasons=s.get("reasons", [])[:12],
                         checks={k: v.get("verdict") for k, v in ch.items()},
                         setup_tt=(ch.get("setup_tt") or ch.get("tt") or {}).get("wns_ps"),
                         hold_ff=(ch.get("hold_ff") or {}).get("wns_ps")))
    fz = json.load(open(kd / "freeze.json"))
    e = old.get(kd.name, dict(view=fz["view"], history=[]))
    seen = {x["path"] for x in e["history"]}
    e["history"] += [x for x in recs if x["path"] not in seen]
    e["host"] = h; e["kit_hash"] = fz["kit_hash"]
    e["verdict"] = ("SIGNED" if e["history"] and e["history"][-1]["verdict"] == "SIGNED" and
                    all(x["verdict"] == "SIGNED" for x in e["history"] if x.get("kit_hash", fz["kit_hash"]) == fz["kit_hash"])
                    else (e["history"][-1]["verdict"] if e["history"] else "NOT RUN"))
    old[kd.name] = e
out.write_text(json.dumps(old, indent=1) + "\n")
import collections
print(collections.Counter(v["verdict"] for v in old.values()))
