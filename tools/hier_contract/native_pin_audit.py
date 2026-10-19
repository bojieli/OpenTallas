#!/usr/bin/env python3
"""Native pin audit of every CLOSED view on main (el1014-root-recipe2, 2026-10-14).

The tile defect rule (10-13 die clock delivery rule, RESUME_AGENT_HEADER_1013): the die delivers the clock at a tile's
clock pin at phi - R (R = insertion.json <corner>.boundary.mean, the sign-off reference), so per pin, at TT, from the
routed view's exported timing (Liberty ETM):
    launch  = O - R   O = clock -> output arc at the first (lightest) load point        budget <= 220 ps
    capture = S + R   S = setup constraint at the input pin                            budget <= 190 ps
(the same numbers as physical/qwen_native_cbuf/audit_boundary_lib.py and tools/hier_contract/pinreg_audit.py o / s; the
clock-extrema packet max - R / R - min is reported apart, not folded in).  A combinational pin-to-pin arc is a fail of
its own (the pin is not registered).

Views: every directory under physical/ holding <cell>.lef + <cell>_tt.lib (the shape ref_tile export and the closure
loop write), memory / PHY macro abstracts excluded.  CLOSED: the closure-loop job that produced the view (abstract.json
orfs_dir, else the closure-loop commit that last touched the LEF) has status CLOSED in the loop state; a view without
any loop record (promoted / hand-assembled stores) is kept and marked closed_by "store"; a view whose loop job is NOT
CLOSED is dropped.  Design: the die contract that binds the cell, else the cell / path family.
Used in the die: "yes" when the view is the one the die census binds for its cell (current contract, contract mode of
die_real_census.py, plus the recorded die-case censuses), "cell" when the contract has the cell but binds another view
(or none: outline differs), "no" otherwise.

    native_pin_audit.py [--root REPO] [--jobs N] --out DIR
    native_pin_audit.py --view DIR [--cell C] --relative-to (PS | tt=PS,ff=PS | NEIGHBOUR_VIEW_DIR | insertion.json)

RELATIVE MODE (owner 2026-10-17 0dq, memory clock-rule-boundary-match-1017): with --relative-to the reference is the
parent's compensation C (or the neighbour's boundary mean for a landed link) instead of the view's own R: launch O - C,
capture S + C, and the boundary match max |pin-flop arrival - C| <= 80 ps at TT and FF.  Every record also reports the
pin-flop spread at TT and FF; spread > 80 ps at either corner is a FAIL (insertion alone never is).

CASE PINS (QK-FWD 2026-10-18, coordinator 0gs (b)): --case PAT[,PAT...] (fnmatch on the Liberty pin name, e.g.
k0,k1,k2) names input pins the die holds CONSTANT and declares so with set_case_analysis in the die SDC (strap / ID pins
driven from tie outputs).  Die STA has no timing check on a case-constant pin, so these pins leave the launch / capture
metric; they are listed in the record (case_pins, case_pins_raw = their unwaived metric) and never hide a data pin.
--static-pins is an alias of --case (S81-MISC 10-18 receipts used that name; ONE mechanism, record field case_pins), and
--case-evidence / --static-evidence records where the die ties the pins (case_evidence).  A pattern that matches no input
pin of the view is an error (a typo must not silently pass a pin).  DIE OBLIGATION: the die netlist ties these pins and
the die SDC set_case_analysis-es them; tools/fleet_viz/native_sync.py accepts a case-pin receipt PASS over an own FAIL.
"""
from __future__ import annotations

import argparse
import collections
import fnmatch
import json
import multiprocessing as mp
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pinreg_audit as PA  # noqa: E402
import die_real_census as DRC  # noqa: E402

LAUNCH_PS = 220.0
CAPTURE_PS = 190.0
STATE = Path(os.environ.get("CL_STATE", str(Path.home() / ".local/state/closure_loop")))
# current die contracts (10-14 07:10): Qwen = the TP8 ROM die v4 + the KV die (the compute / KV-system split contracts
# are not published yet), S81 v17, HBM r25gq v12; recorded die-case censuses add the case bindings
CONTRACTS = {
    "qwen": ["results/arch/hier_contract_1012/qwen_rom_tp8.json", "results/arch/hier_contract_1011/qwen_kv.json"],
    "s81": ["results/arch/hier_contract_1011/s81.json"],
    "hbm": ["results/arch/hier_contract_1011/r25gq.json"],
}
CENSUS = {
    "qwen": ["results/physical/die_real_census/qwen_rom_tp8_v4.json"],
    "s81": ["results/physical/die_iter_1012/s81/real_view_census_v16_20261013/ds_rom_s81_layer1_v16.json"],
    "hbm": ["results/physical/die_real_census/hbm_r25gqn_v12.json"],
}
ORDER = ("qwen", "s81", "hbm", "other")
JOB_RE = re.compile(r"/closure-loop/([^/]+)/")
COMMIT_JOB_RE = re.compile(r"\bjob ([A-Za-z0-9_.-]+-[0-9a-f]{7,}[A-Za-z0-9_.-]*)")


def family(cell: str, view: str) -> str:
    s = (cell + " " + view).lower()
    if re.search(r"(^|[/_ ])(qfd|qkd|qkh|qkv|qwen|qdq|qkez|qend|qtile|qrom)", s):
        return "qwen"
    if re.search(r"(s81|dsrom|dsfd|ot_ds_|redesign_ds|engc)", s):
        return "s81"
    if re.search(r"(hbm|hfd|hgi|hattn|smh|smpub|hcoll|lkep|b2_|mtp_|ot_h|idxw|ctlw|ha2_)", s):
        return "hbm"
    return "other"


def find_views(root: Path) -> list[tuple[str, str]]:
    out = []
    for dp, dn, fn in os.walk(root / "physical"):
        dn[:] = [d for d in dn if d not in (".git", "__pycache__", "routes", "work")]
        names = set(fn)
        for f in names:
            if not f.endswith(".lef"):
                continue
            c = f[:-4]
            if f"{c}_tt.lib" in names or f"{c}_tt.lib.gz" in names:
                rel = str(Path(dp).relative_to(root))
                if not re.search(DRC.MACRO_RE, rel + "/"):
                    out.append((c, rel))
    return sorted(out, key=lambda x: x[1])


def git(root: Path, *a) -> str:
    return subprocess.run(["git", "-C", str(root), *a], capture_output=True, text=True).stdout


def loop_job(root: Path, view: str, cell: str) -> str | None:
    for n in ("abstract.json", "export.json"):
        f = root / view / n
        if f.exists():
            m = JOB_RE.search(f.read_text(errors="replace")[:20000])
            if m:
                return m.group(1)
    msg = git(root, "log", "-1", "--format=%s", "--", f"{view}/{cell}.lef")
    m = COMMIT_JOB_RE.search(msg) if "closure-loop" in msg else None
    return m.group(1) if m else None


def job_status(name: str | None, cache={}) -> str | None:
    if not name:
        return None
    if name not in cache:
        f = STATE / "jobs" / f"{name}.json"
        try:
            cache[name] = json.loads(f.read_text()).get("status")
        except (OSError, ValueError):
            cache[name] = "UNKNOWN_JOB"
    return cache[name]


def audit_one(arg):
    """arg = (root, cell, view[, comp[, case]]): comp = pinreg_audit.compensation() dict (relative mode), case = fnmatch
    patterns of input pins held constant by die-SDC set_case_analysis (excluded from the launch / capture metric)."""
    root, cell, view = arg[:3]
    comp = arg[3] if len(arg) > 3 else None
    case = tuple(arg[4]) if len(arg) > 4 and arg[4] else ()
    is_case = lambda n: any(fnmatch.fnmatchcase(n, c) or fnmatch.fnmatchcase(n.split('[')[0], c) for c in case)
    root = Path(root)
    lib_path = root / view / f"{cell}_tt.lib"
    if not lib_path.exists():
        lib_path = root / view / f"{cell}_tt.lib.gz"
    ij = root / view / "insertion.json"
    try:
        ins = json.loads(ij.read_text()) if ij.exists() else None
    except ValueError:
        ins = None
    try:
        lib = PA.parse_lib(lib_path)
    except Exception as e:  # noqa: BLE001
        return dict(cell=cell, view=view, error=f"lib: {type(e).__name__}: {e}")
    refs = PA.clock_refs(lib, ins, "tt")
    rec = dict(cell=cell, view=view, lib_cell=lib["cell"], insertion=bool(ins),
               ref_src=sorted({v["src"] for v in refs.values()}) or ["none (ideal clock)"])
    if refs:
        ck = max(refs.values(), key=lambda v: v["bmax"] - v["bmin"])
        rec.update(R_ps=round(ck["rise"], 1), spread_ps=round(ck["bmax"] - ck["bmin"], 1))
    rel = {}
    if comp is not None and refs and comp.get("tt") is not None:
        rel["tt"] = PA.boundary_match(refs, comp["tt"])
        refs = PA.relative_refs(refs, comp["tt"])
        rec.update(relative_to=comp.get("src"), ref_src=sorted({v["src"] for v in refs.values()}))
    wl = wc = None
    nl = nc = nout = nin = 0
    comb = []
    case_raw = {}
    for name, m in PA.pin_metrics(lib, refs).items():
        if case and m["dir"] == "input" and is_case(name):
            case_raw[name] = None if m["inp"] is None else round(m["inp"], 1)
            continue
        if m["comb"] and m["dir"] in ("input", "output"):
            comb.append(name)
        if m["dir"] == "output" and m["out"] is not None:
            nout += 1
            nl += m["out"] > LAUNCH_PS
            if wl is None or m["out"] > wl[1]:
                wl = (name, m["out"])
        elif m["dir"] == "input" and m["inp"] is not None:
            nin += 1
            nc += m["inp"] > CAPTURE_PS
            if wc is None or m["inp"] > wc[1]:
                wc = (name, m["inp"])
    rec.update(outputs=nout, inputs=nin, launch_ps=round(wl[1], 1) if wl else None, launch_pin=wl[0] if wl else None,
               capture_ps=round(wc[1], 1) if wc else None, capture_pin=wc[0] if wc else None, launch_over=nl, capture_over=nc,
               comb_pins=len(comb), comb_first=sorted(comb)[:3])
    if case:
        miss = [c for c in case if not any(fnmatch.fnmatchcase(n, c) or fnmatch.fnmatchcase(n.split('[')[0], c) for n in case_raw)]
        if miss:
            return dict(cell=cell, view=view, error=f"case patterns match no input pin of the view: {miss}")
        rec.update(case_patterns=list(case), case_pins=sorted(case_raw), case_pins_raw_capture_ps=case_raw)
    # DIE HOLD BUDGET inputs (FLOW-HOLD 2026-10-16, results/arch/boundary_hold_budget_1016/RULE.md): at FF, the
    # sender's guaranteed launch (min over outputs of O_min - R) and the receiver's pin hold need (max over inputs of
    # H - R; negative = data may arrive that long before the edge).  Die FF STA reads the same ETM arcs; reported here,
    # never part of the native verdict.
    ff_path = root / view / f"{cell}_ff.lib"
    if not ff_path.exists():
        ff_path = root / view / f"{cell}_ff.lib.gz"
    if ff_path.exists():
        try:
            flib = PA.parse_lib(ff_path)
            frefs = PA.clock_refs(flib, ins, "ff")
            if frefs:
                fck = max(frefs.values(), key=lambda v: v["bmax"] - v["bmin"])
                rec["ff_spread_ps"] = round(fck["bmax"] - fck["bmin"], 1)
            if comp is not None and frefs and comp.get("ff") is not None:
                rel["ff"] = PA.boundary_match(frefs, comp["ff"])
                frefs = PA.relative_refs(frefs, comp["ff"])
            fm = {n: m for n, m in PA.pin_metrics(flib, frefs).items() if not (case and m["dir"] == "input" and is_case(n))}
            lm = [m["lmin"] for m in fm.values() if m["dir"] == "output" and m["lmin"] is not None]
            hn = [m["hold"] for m in fm.values() if m["dir"] == "input" and m["hold"] is not None]
            rec.update(ff_launch_min_ps=round(min(lm), 1) if lm else None, ff_hold_need_ps=round(max(hn), 1) if hn else None)
        except Exception as e:  # noqa: BLE001
            rec["ff_error"] = f"{type(e).__name__}: {e}"
    why = []
    if wl and wl[1] > LAUNCH_PS:
        why.append(f"launch {wl[1]:.9g} > {LAUNCH_PS:.0f} ({nl} pins)")
    if wc and wc[1] > CAPTURE_PS:
        why.append(f"capture {wc[1]:.9g} > {CAPTURE_PS:.0f} ({nc} pins)")
    if comb:
        why.append(f"{len(comb)} combinational pins")
    if "ff_spread_ps" not in rec and isinstance(((ins or {}).get("ff") or {}).get("boundary"), dict):
        b = ins["ff"]["boundary"]           # no FF Liberty: the measured FF pin-flop range of insertion.json
        if b.get("min") is not None and b.get("max") is not None:
            rec["ff_spread_ps"] = round(float(b["max"]) - float(b["min"]), 1)
    for c, k in (("TT", "spread_ps"), ("FF", "ff_spread_ps")):     # owner 10-17 0dq: pin-flop spread at TT AND FF
        if (rec.get(k) or 0) > PA.NEIGHBOUR_SKEW_PS and any("insertion.json" in x for x in rec["ref_src"]):
            why.append(f"{c} pin-flop spread {rec[k]} > {PA.NEIGHBOUR_SKEW_PS:.0f}")
    if comp is not None:
        rec["relative"] = rel
        for c, m in rel.items():
            if m and m["mismatch_ps"] > PA.NEIGHBOUR_SKEW_PS:
                why.append(f"{c.upper()} boundary vs neighbour {m['mismatch_ps']} > {PA.NEIGHBOUR_SKEW_PS:.0f} "
                           f"(pin flops {m['rel_min_ps']}..{m['rel_max_ps']} ps from C {m['comp_ps']:g})")
        if not rel:
            why.append("relative mode: no clock reference to compensate against")
    rec["pass"] = not why
    rec["fail_why"] = "; ".join(why)
    return rec


def die_bindings(root: Path) -> dict:
    """design -> {cell: set(view dirs the die binds)}, and the set of contract cells per design"""
    bound, cells, meta = {}, {}, {}
    for d, cs in CONTRACTS.items():
        bound[d], cells[d] = collections.defaultdict(set), set()
        for c in cs:
            p = root / c
            if not p.exists():
                continue
            res = DRC.census_contract(p, [root])
            meta[c] = dict(version=res.get("contract_version"), die=res.get("contract_die"))
            for m, r in res["masters"].items():
                cells[d].add(m)
                if r.get("view") and r["class"] in ("real", "hard_macro"):
                    bound[d][m].add(r["view"])
        for c in CENSUS.get(d, []):
            p = root / c
            if not p.exists():
                continue
            j = json.loads(p.read_text())
            meta[c] = dict(version=j.get("contract_version"), die=j.get("die"), case=j.get("case"))
            for m, r in j.get("masters", {}).items():
                cells[d].add(m)
                if r.get("view") and r.get("class") in ("real", "etm_only", "lef_only"):
                    bound[d][m].add(r["view"].rstrip("/"))
    return dict(bound=bound, cells=cells, meta=meta)


def receipt_path(p, root):
    """the receipt as a repo-relative path when it lies inside the checkout (closed_stands reads a COMMITTED receipt at
    the job's commit / origin/main; an absolute local path is not committed evidence)."""
    try:
        return str(Path(p).resolve().relative_to(Path(root).resolve()))
    except ValueError:
        return str(p)


def reroute_reason_for(r, source, hints):
    """(ROOT-INF1 2026-10-18, INF.1) the CLOSED-STANDS "reroute_reason" for a routed view that FAILS this audit.
    native_spread when the only miss is the TT / FF pin-flop spread (> 80, owner 0dq), else native_capture (it admits any
    capture / launch / spread FAIL).  Before this the candidates carried kind pin_register, which closed_stands refuses
    without a pair_cost_ps > 683.3 -- so a spread-failed closed tile could not be re-routed from the audit's output."""
    lim = PA.NEIGHBOUR_SKEW_PS
    spread = any((r.get(k) or 0) > lim for k in ("spread_ps", "ff_spread_ps"))
    other = bool(r.get("launch_over") or r.get("capture_over") or r.get("comb_pins"))
    kind = "native_spread" if spread and not other else "native_capture"
    return dict(kind=kind, source=source, cell=r.get("lib_cell") or r["cell"], launch_ps=r.get("launch_ps"),
                capture_ps=r.get("capture_ps"), spread_ps=r.get("spread_ps"), ff_spread_ps=r.get("ff_spread_ps"),
                fix="; ".join(hints) or "re-kit the boundary (pin flops at the pins, balanced boundary clock)")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(HERE.parents[1]))
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--out", help="output dir (full audit of every CLOSED view)")
    ap.add_argument("--view", help="audit this one view dir (relative to --root) and print the record")
    ap.add_argument("--cell", help="cell of --view (default: the only <cell>_tt.lib in it)")
    ap.add_argument("--relative-to", help="parent compensation C: ps, tt=PS,ff=PS, a neighbour view dir or its "
                                          "insertion.json (boundary mean); launch O - C, capture S + C, boundary match")
    ap.add_argument("--case", "--static-pins", dest="case",
                    help="comma list of input pin patterns held constant by die-SDC set_case_analysis "
                         "(strap / ID pins): excluded from the launch / capture metric and listed (alias --static-pins)")
    ap.add_argument("--case-evidence", "--static-evidence", dest="case_evidence",
                    help="--view: where the die ties the case pins (bind table / RTL contract); recorded as case_evidence")
    a = ap.parse_args(argv)
    root = Path(a.root).resolve()
    comp = PA.compensation(a.relative_to) if a.relative_to else None
    if a.view:
        vd = root / a.view
        cell = a.cell or next(p.name[:-7] for p in sorted(vd.glob("*_tt.lib")))
        case = [c.strip() for c in (a.case or "").split(",") if c.strip()]
        r = audit_one((str(root), cell, a.view, comp, case))
        if case and a.case_evidence and not r.get("error"):
            r["case_evidence"] = a.case_evidence
        print(json.dumps(r, indent=1))
        return 0 if r.get("pass") else 1
    if not a.out:
        ap.error("--out or --view is required")
    t0 = time.time()
    views = find_views(root)
    head = git(root, "rev-parse", "HEAD").strip()
    keep, dropped = [], collections.Counter()
    for cell, view in views:
        job = loop_job(root, view, cell)
        st = job_status(job)
        if job and st != "CLOSED" and st != "UNKNOWN_JOB":
            dropped[st] += 1
            continue
        keep.append((cell, view, job, "loop" if st == "CLOSED" else ("loop job not in state" if job else "store")))
    with mp.Pool(a.jobs) as pool:
        recs = pool.map(audit_one, [(str(root), c, v, comp) for c, v, _, _ in keep], chunksize=4)
    db = die_bindings(root)
    rows = []
    for (cell, view, job, how), r in zip(keep, recs):
        r.update(job=job, closed_by=how)
        des = [d for d in CONTRACTS if cell in db["cells"][d]]
        r["design"] = des[0] if des else family(cell, view)
        if any(view in db["bound"][d].get(cell, ()) for d in CONTRACTS):
            r["used"] = "yes"
        elif des:
            r["used"] = "cell"
        else:
            r["used"] = "no"
        rows.append(r)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    summary = {}
    for d in ORDER:
        rs = sorted((r for r in rows if r["design"] == d),
                    key=lambda r: (r.get("pass", True), {"yes": 0, "cell": 1, "no": 2}[r["used"]], -(r.get("launch_ps") or 0)))
        s = collections.Counter()
        for r in rs:
            s["views"] += 1
            s["error"] += "error" in r
            s["pass"] += bool(r.get("pass"))
            s["fail"] += r.get("pass") is False
            s[f"used_{r['used']}"] += 1
            s[f"fail_used_{r['used']}"] += r.get("pass") is False
            s["launch_fail"] += bool(r.get("launch_over"))
            s["capture_fail"] += bool(r.get("capture_over"))
            s["comb_fail"] += bool(r.get("comb_pins"))
            s["no_insertion_json"] += not r.get("insertion", True)
        summary[d] = dict(s)
        (out / f"{d}.json").write_text(json.dumps(dict(schema="opentallas.native_pin_audit.v1", design=d, source=head,
                                                       budget=dict(launch_ps=LAUNCH_PS, capture_ps=CAPTURE_PS, corner="tt"),
                                                       summary=dict(s), views=rs), indent=1) + "\n")
    md = [f"# Native pin audit of CLOSED views (TT launch O-R <= {LAUNCH_PS:.0f} ps, capture S+R <= {CAPTURE_PS:.0f} ps)", "",
          f"Source {head[:12]}; tool tools/hier_contract/native_pin_audit.py; {len(views)} views found, {len(keep)} kept "
          f"(closed or store), dropped (loop job not CLOSED): {dict(dropped)}.", "",
          "Contracts / censuses for 'used': " + "; ".join(f"{k} v{v.get('version')}" for k, v in db["meta"].items()), "",
          "| design | views | pass | fail | used yes (fail) | cell only (fail) | not used (fail) | launch fail | capture fail | comb | no insertion.json |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for d in ORDER:
        s = summary[d]
        md.append(f"| {d} | {s.get('views', 0)} | {s.get('pass', 0)} | {s.get('fail', 0)} | {s.get('used_yes', 0)} ({s.get('fail_used_yes', 0)}) | "
                  f"{s.get('used_cell', 0)} ({s.get('fail_used_cell', 0)}) | {s.get('used_no', 0)} ({s.get('fail_used_no', 0)}) | "
                  f"{s.get('launch_fail', 0)} | {s.get('capture_fail', 0)} | {s.get('comb_fail', 0)} | {s.get('no_insertion_json', 0)} |")
    for d in ORDER:
        rs = json.loads((out / f"{d}.json").read_text())["views"]
        md += ["", f"## {d}", "", "| view | cell | closed by | worst launch ps (pin) | worst capture ps (pin) | comb | R src | pass | used |",
               "|---|---|---|---:|---:|---:|---|---|---|"]
        for r in rs:
            if "error" in r:
                md.append(f"| {r['view']} | {r['cell']} | {r.get('closed_by')} | | | | | ERROR {r['error'][:60]} | {r['used']} |")
                continue
            md.append(f"| {r['view']} | {r['cell']} | {r['closed_by']} | {r['launch_ps']} ({r['launch_pin']}) | "
                      f"{r['capture_ps']} ({r['capture_pin']}) | {r['comb_pins']} | {'ins' if r['insertion'] else 'lib est'} | "
                      f"{'PASS' if r['pass'] else 'FAIL'} | {r['used']} |")
    # re-route candidates: failing views the dies bind, with the closed_stands pin_register reroute_reason ready to paste
    cands = []
    for d in ORDER:
        for r in json.loads((out / f"{d}.json").read_text())["views"]:
            if r["used"] != "yes" or r.get("pass", True):
                continue
            hints = []
            if r.get("launch_over"):
                hints.append(f"{r['launch_over']} outputs over {LAUNCH_PS:.0f} (worst {r['launch_pin']} {r['launch_ps']}): one "
                             "dedicated flop per output pin at the pin, HB2 pad (recipe 2 on main >= 36de4b87f)")
            if r.get("capture_over"):
                rst = r["capture_pin"] and re.match(r"(rst|rs$|reset)", r["capture_pin"])
                hints.append(f"{r['capture_over']} inputs over {CAPTURE_PS:.0f} (worst {r['capture_pin']} {r['capture_ps']})"
                             + (": the reset input needs its own capture flop at the pin (local reset release)" if rst else
                                ": single capture flop at each input pin, HB2 pad"))
            if r.get("comb_pins"):
                hints.append(f"{r['comb_pins']} combinational pins: register them")
            if (r.get("spread_ps") or 0) > 80:
                hints.append(f"boundary clock spread {r['spread_ps']} ps > 80: balance the boundary registers / split the root")
            if (r.get("ff_spread_ps") or 0) > 80:
                hints.append(f"FF pin-flop spread {r['ff_spread_ps']} ps > 80: balance the boundary registers at FF")
            cands.append(dict(design=d, cell=r["cell"], view=r["view"], job=r.get("job"), launch_ps=r.get("launch_ps"),
                              capture_ps=r.get("capture_ps"), spread_ps=r.get("spread_ps"), r_from=r["ref_src"],
                              reroute_reason=reroute_reason_for(r, receipt_path(out / f"{d}.json", root), hints)))
    (out / "reroute_candidates.json").write_text(json.dumps(dict(schema="opentallas.native_pin_audit.candidates.v1",
                                                                  source=head, candidates=cands), indent=1) + "\n")
    md += ["", "## Re-route candidates (fail AND bound by the die)", "",
           "| design | cell | view | launch | capture | spread | fix |", "|---|---|---|---:|---:|---:|---|"]
    md += [f"| {c['design']} | {c['cell']} | {c['view']} | {c['launch_ps']} | {c['capture_ps']} | {c['spread_ps']} | "
           f"{c['reroute_reason']['fix']} |" for c in cands]
    (out / "README.md").write_text("\n".join(md) + "\n")
    print(json.dumps(dict(summary=summary, dropped=dict(dropped), seconds=round(time.time() - t0, 1))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
