"""replay one dumped dme_region_tree call: replay_one.py TOOL PKL MODE TIMEOUT -> one JSON line"""
import hashlib, json, pickle, signal, sys, time
tool, pkl, mode, tmo = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
sys.path.insert(0, tool); sys.setrecursionlimit(100000)
import die_trial as D
d = pickle.load(open(pkl, "rb"))
kw = dict(d["kw"]); kw.pop("early_mode", None)
if mode != "hang":
    kw["early_mode"] = mode
calls = [0]
orig = D.merge_point_delay
def cnt(*a, **k):
    calls[0] += 1
    return orig(*a, **k)
D.merge_point_delay = cnt
def alarm(*_):
    raise TimeoutError
signal.signal(signal.SIGALRM, alarm); signal.alarm(tmo)
t0 = time.time()
try:
    out, root, st = D.dme_region_tree(d["site"], d["taps"], **kw)
except TimeoutError:
    print(json.dumps(dict(pkl=pkl, mode=mode, timeout=True, s=round(time.time() - t0, 1), merges=calls[0]))); sys.exit(0)
h_full = hashlib.sha256(json.dumps([out, root, st], sort_keys=True, default=str).encode()).hexdigest()[:16]
st2 = {k: v for k, v in st.items() if k != "early_taps"}
print(json.dumps(dict(pkl=pkl, mode=mode, s=round(time.time() - t0, 2), merges=calls[0], ntaps=len(d["taps"]),
                      nout=len(out), h=h_full, st=st2)))
