#!/usr/bin/env python3
"""Summarise link-budget re-STA logs (tools/setup_triage/dispatch_lb.py) against each job's closed verdict."""
import json, re, sys, glob, os
T = {t["job"]: t for t in json.load(open(sys.argv[1]))}
rows = []
for job, t in T.items():
    f = f"/tmp/setup-triage-local/lb/{job}/lb.log"
    if not os.path.exists(f): rows.append((job, t, None)); continue
    s = open(f).read()
    if "TRI_RC 0" not in s: rows.append((job, t, "ERR")); continue
    ws = float(re.search(r"^OT_WS (\S+)", s, re.M)[1]) * 1e12
    clocks = re.findall(r"^OT_LINK_BUDGET clock (\S+) T ([\d.]+)", s, re.M)
    nolat = re.findall(r"no latency for (\S+)", s)
    blocks = re.split(r"\n(?=Startpoint: )", s)
    def worst(pred):
        best = None
        for b in blocks:
            if not b.startswith("Startpoint"): continue
            if not pred(b): continue
            m = re.search(r"(-?[\d.]+)\s+slack", b)
            if m: v = float(m[1]); best = v if best is None or v < best else best
        return best
    win = worst(lambda b: "(input port clocked by ot_lb_v" in b)
    wout = worst(lambda b: "(output port clocked by ot_lb_v" in b)
    srcsync = bool(nolat) or any(re.match(r"f_a\d+|fi\d|fclk", c) for c, _ in clocks) or re.search(r"clock \S+ \(fall edge\)\n.*\n.*v f", s) is not None
    rows.append((job, t, dict(ws=ws, win=win, wout=wout, clocks=[c for c, _ in clocks], T=[p for _, p in clocks], srcsync=srcsync)))
print("| job | block | closed SS | link-budget SS (worst) | worst in->reg | worst reg->out | clocks | verdict |")
print("|---|---|---|---|---|---|---|---|")
for job, t, r in sorted(rows, key=lambda x: x[0]):
    if r is None or r == "ERR":
        print(f"| {job} | {t['block']} | {t['ss']} | n/a | | | | re-STA failed |"); continue
    if r["srcsync"]: v = "NOT CHECKED: forwarded-clock / source-synchronous link (common-clock split does not apply)"
    elif r["ws"] >= 15: v = "HOLDS"
    else: v = "REVOKED (setup under consistent split)"
    f = lambda x: "-" if x is None else f"{x:+.1f}"
    print(f"| {job} | {t['block']} | {t['ss']:+.2f} | {r['ws']:+.1f} | {f(r['win'])} | {f(r['wout'])} | {','.join(r['clocks'])} T {','.join(r['T'])} | {v} |")
