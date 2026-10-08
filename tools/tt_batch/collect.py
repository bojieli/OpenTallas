#!/usr/bin/env python3
"""TT-BATCH live table: reads every '<orig>-tt' loop job and writes tt-batch.md (block, variant, TT setup WNS, FF hold
WNS, DRC, SS sensitivity, verdict; best TT variant per block; faster / fewer-stage variants that now close).
   collect.py JOBS_DIR INVENTORY OUT_MD"""
import glob, json, re, sys, datetime, collections
JOBS, INV, OUT = sys.argv[1:4]
inv = json.load(open(INV))
by = {r.get("tt_job"): r for r in inv["inventory"] if r.get("tt_job")}
SLOW = re.compile(r"half|safe|deep|pipe|retime|slat|_ss\b|-ss-|r4|r5|r6|oreg|pp\b|hr\b")
rows = []
for f in sorted(glob.glob(f"{JOBS}/*-tt.json")):
    j = json.load(open(f))
    if j["name"] not in by:
        continue
    r = by[j["name"]]; m = j.get("metrics") or {}
    tt, ff, drc, ss = m.get("ss_ps"), m.get("ff_ps"), m.get("drc"), m.get("ss_sensitivity_ps")
    st = j["status"]
    if st == "CLOSED":
        v = "CLOSED"
    elif tt is not None or ff is not None:
        bad = [k for k, x in (("TT", tt), ("FF", ff)) if x is None or x < 0] + (["DRC"] if drc not in (0, None) else [])
        bad += [f"chk:{c}" for c in (j.get("failed_checks") or [])]
        v = f"{st} ({'/'.join(bad) or 'line met'})"
    else:
        v = st + (f": {str(j.get('reason') or '')[:90]}" if st in ("NEEDS_HUMAN", "REFUSED", "NEEDS_RTL") else "")
    rows.append(dict(block=r["block"], variant=r["variant"], job=j["name"], tt=tt, ff=ff, drc=drc, ss=ss, v=v,
                     closed=st == "CLOSED" or (tt is not None and ff is not None and tt >= 0 and ff >= 0 and drc == 0
                                               and not j.get("failed_checks"))))
f2 = lambda x: "" if x is None else f"{x:+.1f}"
blocks = collections.defaultdict(list)
for x in rows:
    blocks[x["block"]].append(x)
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M PT")
cnt = collections.Counter(x["v"].split(" ")[0].split(":")[0] for x in rows)
L = [f"# TT batch (owner option B: setup TT >= 0 @ 833.333 ps, hold FF >= 0, DRC 0; SS = sensitivity)", "",
     f"Updated {now}. Jobs: {len(rows)} ({', '.join(f'{k} {v}' for k, v in sorted(cnt.items()))}); "
     f"closed {sum(x['closed'] for x in rows)}. Inventory: claude-takeover-20261007/tt-batch-inventory.json; "
     "specs + tools: branch claude/tt-batch-20261007 (tools/tt_batch, tools/closure_loop/tt_overlay.py).", "",
     "Flow per job: original source commit; loop route env OT_ORFS_CORNER=TC (+ OT_ORFS_CORNER_OVERRIDE=TC), patched into "
     "pre-852d9b461 snapshots by tt_overlay.py (verdict check ttb_routed_at_TC proves the route ran at TC); flow-hold mm "
     "FF hold repair HM 50 + rule H1; CTS fix hooks cg_pushdown + clk_net_protect + link_budget_hook (consistent die-link "
     "budget; not on forwarded-clock stations); TT setup from corner_sta setup_tt or the loop's tt_resta.sh.", "",
     "## Faster / fewer-stage variants that close at TT", ""]
fast = [x for x in rows if x["closed"] and not SLOW.search(x["variant"])]
slowc = {x["block"] for x in rows if x["closed"] and SLOW.search(x["variant"])}
for x in fast:
    tag = " (block also closes with a slower variant: adopted design can move here)" if x["block"] in slowc else ""
    L.append(f"- **{x['block']} / {x['variant']}** TT {f2(x['tt'])} FF {f2(x['ff'])} DRC {x['drc']}{tag}")
if not fast:
    L.append("- none yet")
L += ["", "## Best TT variant per block", "", "| block | best variant | TT setup | FF hold | DRC | SS sens. | closed variants |", "|---|---|---|---|---|---|---|"]
for b, xs in sorted(blocks.items()):
    have = [x for x in xs if x["tt"] is not None]
    if not have:
        continue
    best = max(have, key=lambda x: (x["closed"], min(x["tt"], x["ff"] if x["ff"] is not None else -1e9)))
    L.append(f"| {b} | {best['variant']} | {f2(best['tt'])} | {f2(best['ff'])} | {best['drc']} | {f2(best['ss'])} | "
             f"{', '.join(x['variant'] for x in xs if x['closed']) or '-'} |")
L += ["", "## All TT jobs", "", "| block | variant | job | TT setup WNS | FF hold WNS | DRC | SS sensitivity | verdict |",
      "|---|---|---|---|---|---|---|---|"]
for x in sorted(rows, key=lambda x: (x["block"], x["variant"])):
    L.append(f"| {x['block']} | {x['variant']} | {x['job']} | {f2(x['tt'])} | {f2(x['ff'])} | {'' if x['drc'] is None else x['drc']} | {f2(x['ss'])} | {x['v']} |")
L += ["", "## Awaiting TT views (not queued: a macro view has no _tt.lib at the job commit; fail closed at TC)", ""]
for r in inv["inventory"]:
    if r["decision"].startswith("awaiting"):
        L.append(f"- {r['block']} / {r['variant']} ({r.get('base')})")
L += ["", "## Skipped", ""]
for r in inv["inventory"]:
    if r["decision"].startswith("skip"):
        L.append(f"- {r['block']} / {r['variant']}: {r['decision'][6:]}")
open(OUT, "w").write("\n".join(L) + "\n")
print(f"{len(rows)} rows, closed {sum(x['closed'] for x in rows)}")
