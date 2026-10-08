#!/usr/bin/env python3
"""TT-BATCH (owner 2026-10-07 option B): inventory every distinct (block, design variant, source commit) in the closure
loop and emit one '<orig>-tt' job per variant family: original source commit, ORFS CORNER=TC route (loop env
OT_ORFS_CORNER + OT_ORFS_CORNER_OVERRIDE), flow-hold mm hold at FF (HM 50), rule H1, setup-triage CTS fix hooks + the
consistent die-link budget (tools/closure_loop/tt_overlay.py, shipped to every host), verdict TT setup / FF hold / DRC.
   make_batch.py JOBS_DIR OVERLAY_VERSION OUT_INVENTORY OUT_SPEC_DIR"""
import glob, json, re, sys, copy
from pathlib import Path

JOBS, VER, INV, OUTD = sys.argv[1:5]
HEX = re.compile(r"^[0-9a-f]{9,10}$")
FLOW = {"mm", "mm2", "mmq", "mmb", "mmcg", "lbc", "lbpin", "cgfix", "tt", "tc", "f", "x", "a", "b", "c", "d", "e",
        "host", "localsmoke", "archive", "e3", "py", "py2", "py3", "bud", "bud2", "ck80", "dpl", "screen"}
REV = re.compile(r"^(r\d+[a-z]?|s\d)$")
FWD = re.compile(r"gath_r25|mcast_r5|mcast_r7|meso_r35|meso_r37|stn_r19|stn_r34|stn_r36|stn_r39|stnh|stnv|fwd_tmr")
SKIP_STATUS = {"INVALID", "REFUSED", "SMOKE_OK"}
TT_SINCE = "2026-10-07T20:20"


def norm(name):
    toks = re.split(r"[-_]", name)
    out, after = [], False
    for t in toks:
        m = re.match(r"^([0-9a-f]{9,10})([a-z]*)$", t)
        if m and re.search(r"\d", m.group(1)):
            after = True
            continue
        if t in FLOW or (after and REV.match(t)):
            continue
        g = re.sub(r"(mmcg|mmq|mm2|mm|tt)$", "", t)
        if g != t and len(g) >= 2:
            t = g
        out.append(t)
    return "_".join(out)


def bench_failed(j):
    return any(re.search(r"expected PASS but rc|expected FAIL but rc=0|bench failed:", e) for e in j.get("events", []))


def is_tt(j):
    s = j["spec"]
    blob = json.dumps(s.get("stages", {}))
    return j.get("created", "") >= TT_SINCE and (
        re.search(r"(^|[-_])(tt|tc)([-_]|$)|tc$", j["name"]) or "CORNER=TC" in blob or "CORNER_OVERRIDE=TC" in blob
        or "OT_SMH_CORNER=TC" in blob or s.get("route_corner"))


jobs = []
for f in sorted(glob.glob(f"{JOBS}/*.json")):
    try:
        jobs.append(json.load(open(f)))
    except Exception:
        pass
fam = {}
for j in jobs:
    fam.setdefault((j["spec"]["block"], norm(j["name"])), []).append(j)

inv, emit = [], []
for (blk, var), js in sorted(fam.items()):
    js.sort(key=lambda j: j.get("created", ""))
    tts = [j for j in js if is_tt(j) and j.get("status") not in ("CANCELLED", "INVALID", "REFUSED")]
    cands = [j for j in js if j.get("status") not in SKIP_STATUS and not bench_failed(j) and not j["name"].endswith("-tt")
             and not is_tt(j) and "signoff833" not in j["name"]]
    rec = dict(block=blk, variant=var, jobs=[dict(name=j["name"], status=j.get("status"), created=j.get("created"),
               commit=j["spec"]["source"].get("commit", "")[:9], bench_failed=bench_failed(j),
               metrics={k: (j.get("metrics") or {}).get(k) for k in ("ss_ps", "ff_ps", "drc", "ss_sensitivity_ps")})
               for j in js])
    if tts:
        rec["decision"] = "skip: TT job already queued/running: " + ", ".join(j["name"] for j in tts)
    elif not cands:
        rec["decision"] = "skip: no eligible job (all invalid / bench-failed / re-signoff-only)"
    else:
        base = cands[-1]
        tname = (base["name"] + "-tt")[:96]
        rec.update(decision="queue", base=base["name"], tt_job=tname, source=base["spec"]["source"],
                   link_budget=not FWD.search(base["name"] + blk))
        inv.append(rec)
        s = copy.deepcopy(base["spec"])
        s["name"] = tname
        s["merge_target"] = None
        s["route_hold_corners"] = "mm"
        s["route_hold_margin_ns"] = 0.05
        s["route_corner"] = "TC"
        s.pop("priority", None)
        if "budget" not in s:
            s["budget"] = {"enabled": False, "reason": "TT-BATCH: re-route of a job created before its budget sheet, kept on "
                           "its original IO SDCs; route-time consistent die-link budget via link_budget_hook (setup-triage)"}
        s["purpose"] = (f"TT-BATCH (owner option B, one large batch): {base['name']} re-routed at ORFS CORNER=TC (setup repair "
                        f"at TT), flow-hold mm FF hold HM 50, rule H1, CTS fix hooks"
                        f"{' + consistent die-link budget' if rec['link_budget'] else ' (forwarded-clock link: own contract, no common-clock budget)'};"
                        f" original source commit kept; verdict TT setup >= 0 / FF hold >= 0 / DRC 0, SS = sensitivity. | was: "
                        + str(s.get("purpose", ""))[:600])
        hooks = "physical/common_flow/cg_pushdown.tcl physical/common_flow/clk_net_protect.tcl" + (
            " physical/common_flow/link_budget_hook.tcl" if rec["link_budget"] else "")
        pre = (f"TTB=$(ls -d /srv/opentallas-scratch/claude/ttbatch/{VER} /home/ubuntu/closure-loop-local/ttbatch/{VER} 2>/dev/null"
               f" | head -1) && export OT_TTB_CORNER_MARK={{CL}}/ttb_corner.txt && python3 $TTB/tools/closure_loop/tt_overlay.py {{SRC}} && ")
        for k in ("calibrate", "route"):
            st = s["stages"].get(k)
            if not isinstance(st, dict) or "cmd" not in st:
                continue
            c = re.sub(r"OT_CTS_FIX_HOOKS='[^']*'", f"OT_CTS_FIX_HOOKS='{hooks}'", st["cmd"])
            c = re.sub(r"export OT_ORFS_CORNER_OVERRIDE=\w+;?", "", c)
            c = re.sub(r"(^|\s)CORNER=\w+ ", r"\1", c)
            extra = f"export OT_CTS_FIX_HOOKS='{hooks}'; " + ("export OT_ORFS_CORNER_OVERRIDE=TC; " if k == "route" else "")
            st["cmd"] = pre + extra + c
        v = s.setdefault("verdict", {})
        v.setdefault("checks", [])
        if not v.get("metrics_cmd"):
            v["checks"].append({"name": "ttb_routed_at_TC",
                                "cmd": "test -s {CL}/ttb_corner.txt && ! grep -qv '^TC ' {CL}/ttb_corner.txt"})
        if rec["link_budget"] and "physical/common_flow/link_budget_consistent.sdc" not in v.get("post_sdc", []):
            pass  # the hook carries the budget into 6_final.sdc; FF post_sdc (mm hold SDCs) stays unchanged
        emit.append(s)
    if rec.get("decision") != "queue":
        inv.append(rec)

Path(OUTD).mkdir(parents=True, exist_ok=True)
for s in emit:
    json.dump(s, open(f"{OUTD}/{s['name']}.json", "w"), indent=1)
json.dump(dict(generated_by="tools/tt_batch/make_batch.py", overlay=VER, families=len(inv),
               queued=sum(r["decision"] == "queue" for r in inv), inventory=inv), open(INV, "w"), indent=1)
print(f"families {len(inv)} queue {len(emit)} skip-tt {sum(r['decision'].startswith('skip: TT') for r in inv)} "
      f"skip-none {sum(r['decision'].startswith('skip: no') for r in inv)}")
