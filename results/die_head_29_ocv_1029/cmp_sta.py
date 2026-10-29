"""DIE-HEAD-29: compare two die_sta_related.json: byte-identity, then per top-level path which subtrees differ;
START rows (count_aligned*/<C>/start_skew) reported separately with their key numbers."""
import json, sys, hashlib
a, b = (open(p, "rb").read() for p in sys.argv[1:3])
print("bytes_identical", a == b, hashlib.sha256(a).hexdigest()[:12], hashlib.sha256(b).hexdigest()[:12])
A, B = json.loads(a), json.loads(b)
diffs = []
def walk(x, y, p, dep):
    if x == y:
        return
    if dep < 4 and isinstance(x, dict) and isinstance(y, dict):
        for k in sorted(set(x) | set(y)):
            walk(x.get(k), y.get(k), p + "/" + k, dep + 1)
    else:
        diffs.append(p)
walk(A, B, "", 0)
print("diff_paths", len(diffs))
for p in diffs[:40]:
    print("  ", p)
for top in ("count_aligned", "count_aligned_info"):
    for c, v in (A.get(top) or {}).items():
        s0, s1 = v.get("start_skew"), (B.get(top) or {}).get(c, {}).get("start_skew")
        if s0 is not None:
            sm = lambda s: {k: (s[k] if not isinstance(s[k], (list, dict)) else (len(s[k]) if isinstance(s[k], list) else {kk: vv for kk, vv in s[k].items() if not isinstance(vv, (list, dict))})) for k in s}
            print(top, c, "start_skew OLD", json.dumps(sm(s0))[:600])
            print(top, c, "start_skew NEW", json.dumps(sm(s1))[:600])
non_start = [p for p in diffs if "/start_skew" not in p]
print("NON_START_DIFFS", len(non_start), non_start[:20])
