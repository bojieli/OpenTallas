#!/usr/bin/env python3
"""Condense setup-triage path dumps into per-job evidence + a first-cut class (reviewed by hand before publishing)."""
import json, sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse import parse, families

PER = 833.33

def auto_class(p):
    if p is None: return "?"
    sl = p["slack"]
    if p["macro_delay"] >= 600: return "C"
    sk = p["skew"]
    if sk is not None and p["input_ext"] is None and sk > 120 and sl + sk - 40 >= 15: return "A"
    if p["max_fanout"][0] >= 64 or (p["data_delay"] and p["fobuf_ps"] > 0.3 * p["data_delay"]): return "D"
    if (p["se_um"] or 0) > 504 or (p["path_len_um"] or 0) > 700 or (p["data_delay"] and p["wirebuf_ps"] > 0.3 * p["data_delay"]): return "F"
    if p["input_ext"] is not None or p["output_ext"] is not None: return "B?io"
    return "E"

def short(n, k=60):
    return n if len(n) <= k else "…" + n[-k:]

def row(p):
    return (f"{short(p['start'],48)} -> {short(p['end'],48)} {p['slack']:+.1f} | L/C {p['launch_clk']}/{p['capture_clk']} sk {p['skew']} T {p['period']} | "
            f"d {p['data_delay']} mac {p['macro_delay']} wire {p['wirebuf_n']}/{p['wirebuf_ps']} fob {p['fobuf_n']}/{p['fobuf_ps']} | lg {p['logic_stages']} {[c for c,_ in p['logic_cells'][:5]]} "
            f"| fo {p['max_fanout'][0]} | se {p['se_um']} len {p['path_len_um']}" + (f" | in {p['input_ext']}" if p['input_ext'] is not None else "") + (f" | out {p['output_ext']}" if p['output_ext'] is not None else "") + (" | MAXDLY" if p['max_delay'] else ""))

def row_long(p):
    return (f"{short(p['start'])} -> {short(p['end'])} {p['slack']:+.1f} | L {p['launch_clk']} C {p['capture_clk']} skew {p['skew']} "
            f"| T {p['period']} | data {p['data_delay']} (macro {p['macro_delay']} {p['macro_cell']}; wirebuf {p['wirebuf_n']}/{p['wirebuf_ps']}) "
            f"| logic {p['logic_stages']} {p['logic_cells'][:4]} | maxstage {p['max_stage']} | fo {p['max_fanout']} | se {p['se_um']}um len {p['path_len_um']} hop {p['max_hop_um']}"
            f" | in_ext {p['input_ext']} out_ext {p['output_ext']} maxdelay {p['max_delay']}")

if __name__ == "__main__":
    T = json.load(open(sys.argv[1]))
    out = []
    for t in T:
        f = f"/tmp/setup-triage-local/{t['job']}/paths.log"
        rec = dict(t)
        if not os.path.exists(f):
            rec["state"] = "missing"; out.append(rec); continue
        txt = open(f).read()
        if "TRI_ERR" in txt or "TRI_END" not in txt:
            rec["state"] = (re.search(r"TRI_ERR.*", txt) or re.search(r"TRI_RC.*", txt) or [""])[0]; out.append(rec); continue
        r = parse(txt)
        rec["state"] = "ok"; rec["paths"] = r["paths"][:8]; rec["families"] = families(r["summary"], 8); rec["n_viol"] = sum(1 for s in r["summary"] if s["slack"] < 15)
        rec["die"] = r["die"]
        rec["auto"] = [auto_class(p) for p in r["paths"][:5]]
        out.append(rec)
    json.dump(out, open(sys.argv[2], "w"), indent=1, default=str)
    for rec in out:
        print(f"### {rec['block']} | {rec['job']} | SS {rec['ss']} FF {rec['ff']} | {rec['host']} | {rec['state']} | auto {rec.get('auto')} | die {rec.get('die')} | nviol(<=300) {rec.get('n_viol')}")
        for p in rec.get("paths", [])[:5]: print("  ", row(p))
        for fam in rec.get("families", [])[:6]: print("   fam", fam)
