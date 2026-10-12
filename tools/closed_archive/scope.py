"""Build archive scope: adopted best jobs of counted elements (+variant/tile blocks) and latest CLOSED per block (cap 2)."""
import json, glob, os, urllib.request, collections
J = os.path.expanduser("~/.local/state/closure_loop/jobs")
reg = json.load(urllib.request.urlopen("http://127.0.0.1:8765/api/elements"))
ov = json.load(open("/home/ubuntu/claude-takeover-20261007/element_overrides.json"))
jobs = {}
for f in glob.glob(J + "/*.json"):
    try:
        d = json.load(open(f))
    except Exception:
        continue
    jobs[d["name"]] = d
closed_by_block = collections.defaultdict(list)
for d in jobs.values():
    if d.get("status") == "CLOSED":
        closed_by_block[d["spec"].get("block")].append(d)
for v in closed_by_block.values():
    v.sort(key=lambda d: d.get("updated") or "", reverse=True)
scope = {}   # job -> dict(element, why)
def add(job, elem, why):
    if job not in scope:
        scope[job] = dict(job=job, element=elem, why=why)
counted = [r for r in reg["rows"] if not r.get("superseded") and r["category"] != "superseded"]
variants = ov.get("variants", {})
nojob = []
for r in counted:
    e = r["element"]
    b = (r.get("best") or {}).get("job")
    blocks = {e} | set(r.get("variants") or [])
    if b:
        if b in jobs:
            add(b, e, "best")
            blocks.add(jobs[b]["spec"].get("block"))
        else:
            nojob.append((e, b))
    for blk in blocks:
        have = [j for j in scope.values() if j["element"] == e and jobs[j["job"]]["spec"].get("block") == blk]
        for d in closed_by_block.get(blk, [])[:2]:
            if len(have) >= 2:
                break
            if d["name"] not in scope:
                add(d["name"], e, "latest-closed" if blk == e else "block:" + str(blk))
                have.append(scope[d["name"]])
out = []
for s in scope.values():
    d = jobs[s["job"]]
    m = d.get("metrics") or {}
    s.update(block=d["spec"].get("block"), host=d.get("host"), run=d.get("run"), commit=d.get("commit_full"),
             orfs_dir=m.get("orfs_dir"), deep_released=d.get("deep_released"), status=d["status"])
    out.append(s)
json.dump(dict(scope=out, nojob=nojob), open("/home/ubuntu/closed_archive/_tools/scope.json", "w"), indent=1)
print(len(out), "jobs;", len(nojob), "best jobs w/o loop state;", collections.Counter(s["why"].split(":")[0] for s in out), collections.Counter(s["host"] for s in out))
