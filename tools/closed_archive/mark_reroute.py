import json, glob, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import archive
rr = {os.path.basename(p)[:-10]: os.path.basename(p)[:-5] for p in glob.glob(os.path.join(archive.TOOLS, "reroute", "*-arch.json"))}
for mp in glob.glob(os.path.join(archive.ROOT, "*", "*", "manifest.json")):
    m = json.load(open(mp))
    if m.get("status") == "missing" and m["job"] in rr:
        m["status"] = "rerouting"
        m["reroute"] = dict(job=rr[m["job"]], queued_via="/tmp/claude-review-20261003/closure_jobs/", same_commit=m.get("commit"),
                            note="same spec, hosts list and merge_target dropped; the hook archives it when it closes")
        json.dump(m, open(mp, "w"), indent=1)
print(json.dumps({k: v for k, v in archive.build_index().items() if k != "rows"}))
