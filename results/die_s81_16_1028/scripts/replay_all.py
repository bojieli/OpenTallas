"""replay_all.py OLD NEW DUMPDIR OUT.jsonl NPROC TMO_OLD_MERGE"""
import glob, json, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
old, new, dd, outp, npr, tmo = sys.argv[1:7]
here = sys.argv[0].rsplit("/", 1)[0]
jobs = []
for p in sorted(glob.glob(dd + "/call_*.pkl")):
    for tool, tag in ((old, "old"), (new, "new")):
        for mode in ("hang", "merge"):
            jobs.append((tag, tool, p, mode, int(tmo) if (tag, mode) == ("old", "merge") else 3600))
def run(j):
    tag, tool, p, mode, t = j
    r = subprocess.run([sys.executable, here + "/replay_one.py", tool, p, mode, str(t)], capture_output=True, text=True)
    line = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else json.dumps(dict(pkl=p, mode=mode, err=r.stderr[-400:]))
    d = json.loads(line); d["tool"] = tag
    return d
with open(outp, "w") as f, ThreadPoolExecutor(int(npr)) as ex:
    for d in ex.map(run, jobs):
        f.write(json.dumps(d) + "\n"); f.flush()
