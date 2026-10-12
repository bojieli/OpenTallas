import json, subprocess, sys, shlex, concurrent.futures as cf
S = json.load(open("/home/ubuntu/closed_archive/_tools/scope.json"))["scope"]
code = open("/home/ubuntu/closed_archive/_tools/inventory_remote.py").read()
only = sys.argv[1:]  # optional host filter
byh = {}
for s in S:
    if not only or s["host"] in only:
        byh.setdefault(s["host"], []).append(s)
def go(h):
    arg = json.dumps(byh[h])
    cmd = f"OT_INV={shlex.quote(arg)} python3 - <<'INVPY'\n{code}\nINVPY\n"
    if h == "localhost":
        p = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=3000)
    else:
        p = subprocess.run(["ssh", "-o", "ConnectTimeout=10", "-o", "ControlPath=none", "-o", "BatchMode=yes", h, "bash -s"], input=cmd, capture_output=True, text=True, timeout=3000)
    for line in p.stdout.splitlines():
        if line.startswith("INV_JSON"):
            return h, json.loads(line[8:]), ""
    return h, None, p.stderr[-2000:]
res = {}
with cf.ThreadPoolExecutor(8) as ex:
    for h, r, err in ex.map(go, list(byh)):
        print(h, "ok" if r is not None else "FAIL " + err, flush=True)
        if r:
            res.update(r)
old = {}
try:
    old = json.load(open("/home/ubuntu/closed_archive/_tools/inventory.json"))
except Exception:
    pass
old.update(res)
json.dump(old, open("/home/ubuntu/closed_archive/_tools/inventory.json", "w"))
