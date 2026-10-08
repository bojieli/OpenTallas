#!/usr/bin/env python3
"""Aggregate the option-B mass re-STA (dispatch_tt.py) into results/closure_loop/tt_restatus_20261007.json + markdown."""
import json, re, sys, os, glob, datetime
T = json.load(open(sys.argv[1])); out_json = sys.argv[2]; out_md = sys.argv[3]
DRC = {}
for l in open("/tmp/setup-triage-tt.log"):
    m = re.match(r"\S+ (\S+) TT_DRC (\S+)", l)
    if m: DRC[m[1]] = int(m[2]) if m[2].isdigit() else None
cls = {}
for l in open("/home/ubuntu/claude-takeover-20261007/setup-triage.md"):
    c = [x.strip() for x in l.split("|")]
    if len(c) > 6 and c[5] in "ABCDEFG" and len(c[5]) == 1:
        for b in re.split(r"[ ;/]+", c[2]): cls[b] = c[5]
def ws(s):
    m = re.search(r"^OT_WS (\S+)", s, re.M)
    try: return round(float(m[1]) * 1e12, 2) if m else None
    except ValueError: return None
def worst(s):
    m = re.search(r"Startpoint: (\S+).*?Endpoint: (\S+)", s, re.S)
    return f"{m[1]} -> {m[2]}" if m else None
recs = []
for t in T:
    d = f"/tmp/setup-triage-local/tt/{t['job']}"
    r = dict(job=t["job"], block=t["block"], loop_status=t["status"], host=t["host"], commit=t["commit"], owner=t.get("owner"),
             orfs_dir=t["orfs"], ss_loop_ps=t["ss"], ff_loop_ps=t["ff"])
    logs = {c: (open(f"{d}/{c}.log").read() if os.path.exists(f"{d}/{c}.log") else "") for c in ("tt", "ttlb", "ss", "ff")}
    for c, s in logs.items():
        r[f"{c}_ws_ps"] = ws(s) if "TRI_RC 0" in s else None
    r["tt_worst_path"] = worst(logs["tt"].split("OT_TNS", 1)[-1]) if logs["tt"] else None
    r["ff_worst_path"] = worst(logs["ff"].split("OT_TNS", 1)[-1]) if logs["ff"] else None
    r["macro_tt_fallback_to_ss"] = "TT_MACRO_SS_FALLBACK" in "".join(logs.values())
    drc = t.get("drc")
    if drc is None: drc = DRC.get(t["job"])
    r["drc"] = drc
    lbl = logs["ttlb"]
    srcsync = bool(re.search(r"no latency for f_|clock (f_a\d+|fi\d)", lbl)) or bool(re.search(r"\(fall edge\)\n.*\n.*v fi\d", logs["tt"]))
    r["link_budget"] = "not_applicable_forwarded_clock" if srcsync else "consistent_split_applied"
    tl, ff = (r["tt_ws_ps"] if srcsync else r["ttlb_ws_ps"]), r["ff_ws_ps"]
    r["setup_verdict_ws_ps"] = tl
    if tl is None or ff is None: v = "NO_DATA"
    elif drc not in (0, None) : v = "DRC_FAIL"
    elif tl >= 0 and ff >= 0: v = "CLOSED_TT" if drc == 0 else "CLOSED_TT_DRC_UNKNOWN"
    elif tl >= 0: v = "HOLD_ONLY"
    else: v = "SETUP_FAIL_TT" + ("_IO_BUDGET_ONLY" if (r["tt_ws_ps"] or -1) >= 0 else "")
    r["verdict"] = v
    r["class"] = cls.get(t["block"])
    recs.append(r)
doc = dict(schema="opentallas.tt_restatus.v1", generated=datetime.datetime.now().isoformat(timespec="seconds"),
           rule="OWNER option B 2026-10-07: closure = setup at TT 833.333 >= 0 under the consistent die-link budget "
                "(physical/common_flow/link_budget_consistent.sdc, S=R=254.7 ps: skew 150, link 114) + hold at FF >= 0 "
                "(job's FF load, sign-off post-SDCs from origin/main, rule H1 where adopted) + DRC 0. SS is sensitivity only.",
           tool="tools/setup_triage/dispatch_tt.py + remote_tt.sh (claude/setup-triage-20261007)", jobs=recs)
os.makedirs(os.path.dirname(out_json), exist_ok=True)
json.dump(doc, open(out_json, "w"), indent=1)
# markdown
from collections import Counter, defaultdict
byblk = defaultdict(list)
for r in recs: byblk[r["block"]].append(r)
rank = {"CLOSED_TT": 0, "CLOSED_TT_DRC_UNKNOWN": 1, "HOLD_ONLY": 2, "SETUP_FAIL_TT_IO_BUDGET_ONLY": 3, "SETUP_FAIL_TT": 4, "DRC_FAIL": 5, "NO_DATA": 6}
best = {b: min(rs, key=lambda r: (rank[r["verdict"]], -(r["setup_verdict_ws_ps"] or -1e9))) for b, rs in byblk.items()}
f = lambda x: "-" if x is None else f"{x:+.1f}"
L = [f"## Option-B mass re-STA (TT setup + FF hold + DRC, consistent link budget), {doc['generated']}",
     f"{len(recs)} final routes, {len(byblk)} blocks. Per block the best route is shown. JSON: results/closure_loop/tt_restatus_20261007.json.",
     "", "Block counts by best verdict: " + ", ".join(f"{k} {v}" for k, v in Counter(r['verdict'] for r in best.values()).most_common()), ""]
def table(title, pred, extra=False):
    rows = [r for r in best.values() if pred(r)]
    L.extend([f"### {title} ({len(rows)})", "| block | job | loop status | TT+LB | TT | FF | SS (sens.) | DRC | class | LB | TT worst path |", "|---|---|---|---|---|---|---|---|---|---|---|"])
    for r in sorted(rows, key=lambda r: (r["setup_verdict_ws_ps"] or -1e9), reverse=True):
        L.append(f"| {r['block']} | {r['job']} | {r['loop_status']} | {f(r['ttlb_ws_ps'])} | {f(r['tt_ws_ps'])} | {f(r['ff_ws_ps'])} | {f(r['ss_ws_ps'])} | {r['drc']} | {r['class'] or ''} | {'n/a fwd-clk' if r['link_budget'].startswith('not') else 'yes'} | {(r['tt_worst_path'] or '')[:90]} |")
    L.append("")
table("NEWLY CLOSED at TT (not CLOSED in the loop)", lambda r: r["verdict"].startswith("CLOSED_TT") and r["loop_status"] != "CLOSED")
table("Closed in the loop AND at TT", lambda r: r["verdict"].startswith("CLOSED_TT") and r["loop_status"] == "CLOSED")
table("Previously CLOSED, NOT closed at TT", lambda r: not r["verdict"].startswith("CLOSED_TT") and r["loop_status"] == "CLOSED")
table("Hold-only failures (TT+LB >= 0, FF < 0)", lambda r: r["verdict"] == "HOLD_ONLY" and r["loop_status"] != "CLOSED")
table("Still failing setup at TT", lambda r: r["verdict"].startswith("SETUP_FAIL") and r["loop_status"] != "CLOSED")
table("DRC / no data", lambda r: r["verdict"] in ("DRC_FAIL", "NO_DATA") and r["loop_status"] != "CLOSED")
open(out_md, "w").write("\n".join(L) + "\n")
print(Counter(r['verdict'] for r in best.values()))
