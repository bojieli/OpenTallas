"""CPL-QC-NK-R0: compare the s21 and s22 strict bind dirs modulo out dir / plan name / plan sha.  For every differing
.sv, classify the differing lines: reset relay lines (ot_dp_rrelay*, rst_rl_ wires/assigns, 'depth D @ (x, y)' site
comments) vs anything else.  Also compares the per-type wavefront depth K and per-core release cycle (bind_reset.json /
bind_core_resets.json) and bind_latency / bind_names.  usage: eqdiff.py A B PLAN_A PLAN_B"""
import hashlib, json, re, sys, difflib
from pathlib import Path
A, B = Path(sys.argv[1]), Path(sys.argv[2]); PA, PB = Path(sys.argv[3]), Path(sys.argv[4])
ha, hb = (hashlib.sha256(p.read_bytes()).hexdigest() for p in (PA, PB))
subs = [(str(A), "<OUT>"), (str(B), "<OUT>"), (PA.stem, "<PLAN>"), (PB.stem, "<PLAN>")]
for n in (64, 16, 12):
    subs += [(ha[:n], "<SHA>"), (hb[:n], "<SHA>")]
def norm(t):
    for a, b in subs:
        t = t.replace(a, b)
    return t
RST = re.compile(r"rst_rl_\d+|ot_dp_rrelay|u_rrl_\d+|rst_n_t\d+|depth\s+\d+\s+@|reset relay|wavefront", re.I)
fa = {p.relative_to(A) for p in A.rglob("*") if p.is_file()}
fb = {p.relative_to(B) for p in B.rglob("*") if p.is_file()}
print("only A", sorted(map(str, fa - fb))[:5], "only B", sorted(map(str, fb - fa))[:5], "common", len(fa & fb))
same = 0; real = []; svrep = {}
for r in sorted(fa & fb):
    x, y = (A / r).read_bytes(), (B / r).read_bytes()
    if x == y:
        same += 1; continue
    try:
        xs, ys = norm(x.decode()), norm(y.decode())
    except UnicodeDecodeError:
        real.append(str(r)); continue
    if xs == ys:
        continue
    real.append(str(r))
    if r.suffix in (".sv", ".v"):
        d = [l for l in difflib.unified_diff(xs.splitlines(), ys.splitlines(), lineterm="", n=0)
             if l[:1] in "+-" and not l.startswith(("+++", "---"))]
        rst = [l for l in d if RST.search(l)]
        svrep[str(r)] = dict(lines=len(d), reset_lines=len(rst), other=[l[:160] for l in d if not RST.search(l)][:6])
print("identical", same, "differ after path/plan/sha normalisation", len(real))
for r in real:
    print("DIFF", r, json.dumps(svrep.get(r, {}))[:700])
for f in ("bind_latency.json", "bind_names.json", "bind_latency_consumers.json", "bind_parent_id_straps.json"):
    if (A / f).exists():
        print(f, "equal" if norm((A / f).read_text()) == norm((B / f).read_text()) else "DIFFERS")
def rel(d):
    try:
        j = json.loads((d / "bind_core_resets.json").read_text())
    except Exception as e:
        return str(e)
    return j
ja, jb = rel(A), rel(B)
print("bind_core_resets.json equal" if ja == jb else "bind_core_resets.json differs")
if ja != jb and isinstance(ja, (dict, list)):
    def flat(o, p=""):
        if isinstance(o, dict):
            for k, v in o.items(): yield from flat(v, f"{p}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o): yield from flat(v, f"{p}[{i}]")
        else:
            yield p, o
    fa_, fb_ = dict(flat(ja)), dict(flat(jb))
    keys = sorted(k for k in set(fa_) | set(fb_) if fa_.get(k) != fb_.get(k))
    print(" differing leaves", len(keys))
    for k in keys[:30]:
        print("  ", k, fa_.get(k), "->", fb_.get(k))
