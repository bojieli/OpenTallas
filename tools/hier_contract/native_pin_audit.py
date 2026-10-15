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
"""
from __future__ import annotations

import argparse
import collections
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
    root, cell, view = arg
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
    wl = wc = None
    nl = nc = nout = nin = 0
    comb = []
    for name, m in PA.pin_metrics(lib, refs).items():
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
    why = []
    if wl and wl[1] > LAUNCH_PS:
        why.append(f"launch {wl[1]:.9g} > {LAUNCH_PS:.0f} ({nl} pins)")
    if wc and wc[1] > CAPTURE_PS:
        why.append(f"capture {wc[1]:.9g} > {CAPTURE_PS:.0f} ({nc} pins)")
    if comb:
        why.append(f"{len(comb)} combinational pins")
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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(HERE.parents[1]))
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    root = Path(a.root).resolve()
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
        recs = pool.map(audit_one, [(str(root), c, v) for c, v, _, _ in keep], chunksize=4)
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
            cands.append(dict(design=d, cell=r["cell"], view=r["view"], job=r.get("job"), launch_ps=r.get("launch_ps"),
                              capture_ps=r.get("capture_ps"), spread_ps=r.get("spread_ps"), r_from=r["ref_src"],
                              reroute_reason=dict(kind="pin_register", source=f"{out}/{d}.json", cell=r["lib_cell"] or r["cell"],
                                                  launch_ps=r.get("launch_ps"), capture_ps=r.get("capture_ps"),
                                                  fix="; ".join(hints))))
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
