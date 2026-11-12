import json, re, sys, collections
a, b = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
def norm(f):
    s = f if isinstance(f, str) else json.dumps(f, sort_keys=True)
    return re.sub(r"-?\d+\.\d+", "#", s)
def items(d, sev):
    out = []
    for f in d["findings"]:
        if isinstance(f, dict) and str(f.get("severity", f.get("level", ""))).upper().startswith(sev):
            out.append(f)
    return out
for sev in ("ERR", "WARN"):
    A = collections.Counter(norm(x) for x in items(a, sev)); B = collections.Counter(norm(x) for x in items(b, sev))
    print(f"== {sev}: base {sum(A.values())} s25 {sum(B.values())}")
    for k in sorted(set(A) | set(B)):
        if A[k] != B[k]:
            print(f"  {A[k]} -> {B[k]}: {k[:400]}")
