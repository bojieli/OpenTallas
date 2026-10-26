"""DIE-PROTO-KV it5 (COORD ruling 2026-10-25 21:16, option a): derive the it5 GRT plan from the main KV plan.
(1) ONE ft share for kits and die: every partition type ft_track_frac = SHARE (die_trial -> layer adjustment 1-SHARE
    on M4-M7; g2.py part probes use the same 0.5 adjustment on M2-M7).
(2) strict core blocking: every planned hard core without a routed LEF gets obs_max = its harden recipe sigmax
    (recipes_kv.json, fnmatch on module, _default otherwise), so die_trial.abstract_lef obstructs M4..sigmax.
usage: it5_plan.py PLAN.json RECIPES.json OUT.json [SHARE]"""
import fnmatch, hashlib, json, sys
from collections import Counter
src, rec, out = sys.argv[1:4]
share = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5
P = json.load(open(src))
R = json.load(open(rec))
pat = {k: v for k, v in R.items() if k != "_default" and isinstance(v, dict)}
dflt = R["_default"]["sigmax"]
def sigmax(mod):
    hits = [(len(k), v["sigmax"]) for k, v in pat.items() if fnmatch.fnmatchcase(mod, k) and "sigmax" in v]
    return max(hits)[1] if hits else dflt
c = Counter()
for tn, t in P["partition_types"].items():
    t["ft_track_frac"] = share
    for h in t.get("hard_cores") or []:
        if h.get("lef"):
            continue
        s = sigmax(h["module"])
        if h.get("obs_max") and int(h["obs_max"][1:]) > int(s[1:]):
            s = h["obs_max"]
        h["obs_max"] = s
        c[(h["module"].rsplit("_e", 1)[0] if "head_eighth" in h["module"] else h["module"], s)] += 1
json.dump(P, open(out, "w"), indent=1)
print("source_sha256", hashlib.sha256(open(src, "rb").read()).hexdigest())
print("it5_sha256", hashlib.sha256(open(out, "rb").read()).hexdigest(), "share", share)
for k, v in sorted(c.items()):
    print(v, *k)
