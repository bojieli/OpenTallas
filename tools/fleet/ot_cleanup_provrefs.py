#!/usr/bin/env python3
"""CLEAN-ALL-1115 (owner rule: never delete prov_view_sources paths).  Build the list of every /srv path that a published view's
provenance names, plus kit_wave.json prov_view_sources dirs.  usage: ot_cleanup_provrefs.py REPO OUT [kit_wave.json]
Distribute OUT to <scratch2>/claude/clean-all-1115/provrefs.txt on every host; ot_cleanup_refguard.py merges it into refs.tsv and
every delete script must skip a target that contains or is inside one of these paths, even for owner RELEASE lists."""
import json, os, re, subprocess, sys
PAT = r"/srv/opentallas-scratch[23]*/claude/[^\"' ,\\<>)]*"
def canon(p):
    return re.sub(r"opentallas-scratch3", "opentallas-scratch2", p).rstrip("/")
def build(repo, kw=None, ref="origin/main"):
    s = set()
    p = subprocess.run(["git", "-C", repo, "grep", "-ho", "-E", PAT, ref, "--", "physical/**/PROVENANCE.json", "physical/**/provenance.json"],
                       capture_output=True, text=True)
    s.update(canon(x) for x in p.stdout.split())
    if kw and os.path.exists(kw):
        for d in json.load(open(kw)).get("dies", {}).values():
            for lst in (d.get("prov_view_sources") or {}).values():
                for c in lst if isinstance(lst, list) else [lst]:
                    if isinstance(c, dict):
                        for k in ("dir", "base"):
                            if isinstance(c.get(k), str) and c[k].startswith("/srv/"):
                                s.add(canon(c[k]))
    return s
def protected(target, refs):
    t = canon(target)
    return any(r == t or r.startswith(t + "/") or t.startswith(r + "/") for r in refs)
if __name__ == "__main__":
    out = build(sys.argv[1], sys.argv[3] if len(sys.argv) > 3 else None)
    open(sys.argv[2], "w").write("\n".join(sorted(out)) + "\n")
    print(len(out), "provenance-referenced paths")
