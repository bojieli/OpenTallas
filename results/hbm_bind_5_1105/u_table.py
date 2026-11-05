#!/usr/bin/env python3
"""U table with open inputs (HBM-BIND-5 item 4). usage: u_table.py BIND_DIR GEN_REPORT OUT.json
U 0 means: no unplanned crossing bit AND no open functional top input AND no unproven tie."""
import json, re, sys, collections
g, gr, out = sys.argv[1:4]
B = json.load(open(g + "/bind_report.json")); J = json.load(open(g + "/asbuilt.json"))
top = J["modules"]["hbm_current_native_top"]; R = json.load(open(gr))
up = B.get("lanes", {}).get("unplanned_pairs", {})
vals = up.values() if isinstance(up, dict) else [x.get("bits", x.get("width", 0)) for x in up]
ub = sum(v if isinstance(v, int) else v.get("bits", v.get("width", 0)) for v in vals)
oblig = {o["inst"] + "__" + o["port"]: o for o in R.get("obligations", [])}
def cl(n):
    if re.search(r"__rr_[vd]$", n): return "C2 FUSED lane VM read (SS33-TOK map)"
    m = re.match(r"native_required__(.+)$", n)
    if m and m.group(1) in oblig: return "C4q S half boundary: " + re.sub(r"_N[EW]\d*.*", "", oblig[m.group(1)]["from_"][0])
    if re.search(r"rst_n$|por|refclk", n): return "reset/clock (reset tree, not data)"
    if n.startswith("lk_") or "pma" in n: return "C0 die IO"
    if "host_cp" in n: return "host session"
    return "OTHER"
ins = collections.Counter(); ports = collections.Counter()
for n, p in top["ports"].items():
    if p["direction"] != "input": continue
    c = cl(n); ins[c] += len(p["bits"]); ports[c] += 1
errs = collections.Counter(re.match(r"\w+", e).group(0) for e in B.get("errors", []))
T = dict(unplanned_bits=ub, unplanned_pairs=len(up), open_inputs_bits=dict(ins), open_inputs_ports=dict(ports), candidate_ties_unproven_bits=sum(R.get("candidate_ties", {}).values()), errors=dict(errs))
func = sum(v for k, v in ins.items() if k.startswith(("C2", "C4q", "OTHER")))
T["u_closed"] = ub == 0 and func == 0 and T["candidate_ties_unproven_bits"] == 0
json.dump(T, open(out, "w"), indent=1); print(json.dumps(T, indent=0)[:1800])
