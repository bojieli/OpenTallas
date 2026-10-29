# DIE-QC-20: real-data identity check, attach_region_dme serial vs DME_WORKERS on a region subset (captured trial13 inputs)
import sys, pickle, copy, json, hashlib, time
sys.path.insert(0, sys.argv[1]); sys.setrecursionlimit(100000)
import die_trial as D
c = pickle.load(open(sys.argv[2], "rb"))
kw = dict(c["kw"]); kw["only"] = set(sys.argv[3].split(","))
D.EVEN_LEGS = True   # trial13 kit runs --clock-cell inv2
out = {}
for w in (1, 6):
    D.DME_WORKERS = w
    n = copy.deepcopy(c["nodes"]); t0 = time.time()
    st = D.attach_region_dme(n, c["site"], c["taps"], c["regions"], **kw)
    out[w] = hashlib.sha256(json.dumps([n, st], sort_keys=True, default=str).encode()).hexdigest()[:16]
    print(w, round(time.time() - t0, 1), out[w], flush=True)
print("IDENTICAL" if out[1] == out[6] else "DIFFERENT")
