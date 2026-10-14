#!/usr/bin/env python3
"""Qualify the S81 native paired views (routed LEF + TT/FF/SS ETM of one export directory).

Input: results/arch/s81_native_20261013/manifest.json (candidate bundles), the closure-loop job state of the route
each bundle was exported from, the element registry snapshot and the die contract.  A bundle is QUALIFIED only when
every gate below holds; nothing is inferred from a CLOSED label.

  pair      LEF and every corner ETM are listed by ONE abstract.json export, and that export's orfs directory is the
            directory the job's closing verdict was measured on (an ECO pass after the export breaks the pair)
  tt / ff   TT setup >= 0 and FF hold >= 0 in the job's closing verdict, and in the export-side corner STA when present
  export    export-side corner STA agrees with the closing verdict within 1 ps (open, not failed, when it does not:
            the exporter's SDC order differs from the verdict's; main 596cd2b8a fixed only the SPEF order)
  drc       the job closed with DRC 0
  bench     a behavioural bench expected to pass passed AND a mutant expected to fail failed (lint is not a bench)
  lint      tools/hier_contract/child_lint.py PASS on the committed LEF + libs
  clock     the FF ETM has clock pins and every one carries min/max_clock_tree_path
  scalar    contract clock_pin_rules: a master the contract lists as scalar-clock must export scalar clock pins;
            vector-named clocks on other masters are recorded (the die binds [0:0] ports by name)
  thr       registry throughput not a MEASURED failure (over 1.10x); unmeasured units ride the per-layer ROM run (owner 10-13)
  current   the bundle's job is the registry's adopted (best) closure of that master (else: a newer view exists)

It also measures, from the FF ETM, the launch side of the minimum-delay seam budget: the smallest clock->output
delay minus that clock's min insertion (launch) and the largest input hold requirement (capture), so the die can
check  cq_min + wire_min >= hold_req + hold_uncertainty + skew  per real seam instead of the interim cq 32 ps model.

Usage: native_view_qualify.py [--manifest M] [--registry EL.json] [--jobs DIR] [--extra GLOB] [--out OUT.json]
(registry: curl -s 127.0.0.1:8765/api/elements > EL.json)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JOBS = Path.home() / ".local/state/closure_loop/jobs"


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def git_time(rel: str, human: bool = False):
    fmt = "%ad" if human else "%at"
    out = subprocess.run(["git", "-C", str(ROOT), "log", "-1", f"--format={fmt}", "--date=format:%m-%d %H:%M", "--", rel],
                         capture_output=True, text=True).stdout.strip()
    return out if human else int(out or 0)


def job_of(orfs_dir: str) -> str | None:
    m = re.search(r"/closure-loop/([^/]+)/", orfs_dir or "")
    return m.group(1) if m else None


NUM = re.compile(r"-?\d+\.?\d*(?:[eE][-+]?\d+)?")


def lib_scan(path: Path) -> dict:
    """Clock pins, their insertion, min clock->output delay and max input hold from an OpenSTA timing model."""
    txt = path.read_text(errors="replace")
    tu = re.search(r"time_unit\s*:\s*\"?1(ps|ns)", txt)
    k = 1000.0 if (tu and tu.group(1) == "ns") else 1.0
    clocks: dict[str, dict] = {}
    cq: dict[str, float] = {}           # related clock pin -> min clk->out delay
    hold: dict[str, float] = {}         # related clock pin -> max hold requirement
    n_out = n_in = 0
    # walk pin groups by brace depth
    for m in re.finditer(r"\n\s*pin\s*\(\s*\"?([^\")]+)\"?\s*\)\s*\{", txt):
        name = m.group(1)
        i = m.end()
        depth = 1
        while depth and i < len(txt):
            c = txt[i]
            depth += (c == "{") - (c == "}")
            i += 1
        body = txt[m.end():i]
        if re.search(r"clock\s*:\s*true", body):
            d = clocks.setdefault(name, {})
            for key in ("min_clock_tree_path", "max_clock_tree_path"):
                vals = []
                for t in re.finditer(r"timing\s*\(\s*\)\s*\{", body):
                    j = t.end(); dd = 1
                    while dd and j < len(body):
                        dd += (body[j] == "{") - (body[j] == "}"); j += 1
                    tb = body[t.end():j]
                    if re.search(r"timing_type\s*:\s*" + key, tb):
                        for v in re.finditer(r"values\s*\(([^;]*?)\)\s*;", tb, re.S):
                            vals += [float(x) * k for x in NUM.findall(v.group(1))]
                if vals:
                    d[key + "_ps"] = round(min(vals) if key.startswith("min") else max(vals), 2)
            continue
        is_out = bool(re.search(r"direction\s*:\s*output", body))
        for t in re.finditer(r"timing\s*\(\s*\)\s*\{", body):
            j = t.end(); dd = 1
            while dd and j < len(body):
                dd += (body[j] == "{") - (body[j] == "}"); j += 1
            tb = body[t.end():j]
            rp = re.search(r"related_pin\s*:\s*\"([^\"]+)\"", tb)
            tt = re.search(r"timing_type\s*:\s*(\w+)", tb)
            if not rp or not tt:
                continue
            ty = tt.group(1)
            if is_out and ty in ("rising_edge", "falling_edge"):
                vals = []
                for g in re.finditer(r"cell_(?:rise|fall)\s*\([^)]*\)\s*\{(.*?)\}", tb, re.S):
                    v = re.search(r"values\s*\((.*?)\)\s*;", g.group(1), re.S)
                    if v:
                        vals += [float(x) * k for x in NUM.findall(v.group(1))]
                if vals:
                    n_out += 1
                    key = rp.group(1) + ("" if ty == "rising_edge" else "@fall")
                    cq[key] = min(cq.get(key, 1e18), min(vals))
            elif (not is_out) and ty in ("hold_rising", "hold_falling"):
                vals = []
                for v in re.finditer(r"values\s*\((.*?)\)\s*;", tb, re.S):
                    vals += [float(x) * k for x in NUM.findall(v.group(1))]
                if vals:
                    n_in += 1
                    key = rp.group(1) + ("" if ty == "hold_rising" else "@fall")
                    hold[key] = max(hold.get(key, -1e18), max(vals))
    return {"clocks": clocks, "cq_min_ps": {c: round(v, 2) for c, v in cq.items()},
            "hold_max_ps": {c: round(v, 2) for c, v in hold.items()}, "out_arcs": n_out, "hold_arcs": n_in}


def child_lint(lef: Path, libs: Path) -> dict:
    p = subprocess.run([sys.executable, str(ROOT / "tools/hier_contract/child_lint.py"), str(lef), "--libs", str(libs),
                        "--json"], capture_output=True, text=True)
    try:
        j = json.loads(p.stdout)
    except Exception:
        return {"verdict": "ERROR", "fails": [p.stderr.strip()[-300:] or "no json"], "summary": ""}
    return {"verdict": j.get("verdict"), "fails": j.get("fails", []), "summary": j.get("summary", "")}


def qualify(master: str, n_inst: int, files: dict, d: Path, reg: dict, jobs: Path, rules: dict) -> dict:
    row: dict = {"master": master, "instances": n_inst, "export_dir": str(d), "gates": {}, "why": []}
    lef_p = ROOT / files["lef"]["path"]
    g = row["gates"]

    def gate(name: str, ok: bool | None, detail: str):
        g[name] = {"ok": ok, "detail": detail}
        if ok is not True:
            row["why"].append(f"{name}: {detail}")

    cs = json.loads((ROOT / d / "corner_sta.json").read_text()) if (ROOT / d / "corner_sta.json").exists() else {}
    ab = json.loads((ROOT / d / "abstract.json").read_text()) if (ROOT / d / "abstract.json").exists() else {}
    sta_dir, abs_dir = cs.get("orfs_dir"), ab.get("orfs_dir")
    odbs = sorted({(cs.get(k) or {}).get("odb_sha256") for k in ("setup_tt", "setup_ss", "hold_ff")} - {None})
    job = job_of(abs_dir or sta_dir or "")
    row["job"] = job
    row["sta_odb_sha256"] = odbs
    js = {}
    if job and (jobs / f"{job}.json").exists():
        js = json.loads((jobs / f"{job}.json").read_text())
    met = js.get("metrics") or {}
    row["job_status"] = js.get("status")
    row["job_commit"] = js.get("commit_full")
    row["verdict_orfs_dir"] = met.get("orfs_dir")
    listed = set(ab.get("files") or [])
    unlisted = [Path(f["path"]).name for f in files.values() if Path(f["path"]).name not in listed]
    if not ab:
        gate("pair", False, "no abstract.json beside the LEF: the export has no recorded ODB directory")
    elif not js:
        gate("pair", False, f"no job state for {job}: the closing verdict's directory is unknown")
    elif unlisted:
        # a corner ETM the recorded export did not write: compare its last commit with the LEF's
        t_lef = git_time(files["lef"]["path"])
        old = [u for u in unlisted if git_time(str(Path(files["lef"]["path"]).parent / u)) < t_lef]
        if old:
            gate("pair", False, f"{old} committed {git_time(str(Path(files['lef']['path']).parent / old[0]), True)}, BEFORE the "
                                f"LEF + listed ETMs ({git_time(files['lef']['path'], True)}): it is the extraction of an earlier ODB")
        else:
            gate("pair", None, f"{unlisted} written by a separate later extraction, not by the recorded export "
                               f"(abstract.json lists {sorted(listed)}); no ODB hash links it to the LEF")
    elif met.get("orfs_dir") != abs_dir or (cs and sta_dir != abs_dir):
        vd = met.get("orfs_dir") if met.get("orfs_dir") != abs_dir else sta_dir
        if job and f"/{job}/cl/eco" in (vd or "") and f"/{job}/routes/" in (abs_dir or ""):
            # closure_loop.eco_install_cmd copies the ECO 6_final.{odb,spef,v} over the route's and re-exports the view
            # from the route directory, so this CAN be one ODB -- but the export records no ODB hash to prove that the
            # committed view is the post-install export.  Open until the export carries the hash (or the host ODB is
            # hashed against the verdict's).
            gate("pair", None, f"verdict on the ECO pass {vd}; view exported from the route dir {abs_dir}: the loop installs "
                               "the ECO ODB there before re-export, but the export records no ODB hash"
                               + (f" (verdict ODB {odbs[0][:12]})" if len(odbs) == 1 else ""))
        else:
            gate("pair", False, f"view exported from {abs_dir} but the closing verdict / corner STA was measured on {vd}")
    elif cs and len(odbs) != 1:
        gate("pair", False, f"corner STA names {len(odbs)} ODBs")
    else:
        gate("pair", True, "LEF + TT/FF/SS ETM from one export of the verdict's orfs dir"
             + (f", ODB {odbs[0][:12]}" if odbs else " (no ODB hash recorded)"))

    reason = js.get("reason") or ""
    mt = re.search(r"(TT|SS) \+?(-?[\d.]+) / FF \+?(-?[\d.]+) ps DRC (\d+)", reason)
    # legacy TT-era jobs label their TT route corner 'SS' in the reason; metrics.ss_ps carries the same number
    v_tt = float(mt.group(2)) if mt else None
    v_ff = float(mt.group(3)) if mt else met.get("ff_ps")
    drc = int(mt.group(4)) if mt else met.get("drc")
    e_tt = (cs.get("setup_tt") or {}).get("worst_slack_ps")
    e_ff = (cs.get("hold_ff") or {}).get("worst_slack_ps")
    if e_tt is None and e_ff is None and ab.get("ok") and (ab.get("verdict") or {}).get("expect_ps"):
        # the fixed export (main abc334b14) records its OWN corner STA of the verdict replay in abstract.json:
        # corners.<c>.ws = "OT_WS max <setup s> min <hold s>".  That is the export-side record of this view directory
        # (the same files the die binds), used when the job wrote no corner_sta.json beside it.
        def _ws(c, k):
            mm = re.search(r"OT_WS max (\S+) min (\S+)", ((ab.get("corners") or {}).get(c) or {}).get("ws") or "")
            return round(float(mm.group(1 if k == "max" else 2)) * 1e12, 2) if mm else None
        e_tt, e_ff = _ws("tt", "max"), _ws("ff", "min")
        row["export_sta_source"] = "abstract.json corners.<c>.ws (verdict replay of the fixed export)"
    row["verdict_tt_ff_drc"] = [v_tt, v_ff, drc]
    row["export_tt_ff"] = [e_tt, e_ff]
    if v_tt is None:
        gate("tt", False, "no closing-verdict setup number")
    else:
        gate("tt", v_tt >= 0 and (e_tt is None or e_tt >= 0),
             f"verdict TT setup {v_tt:+.2f} ps" + (f", export {e_tt:+.2f}" if e_tt is not None else ", no export-side TT STA"))
    if v_ff is None:
        gate("ff", False, "no closing-verdict hold number")
    else:
        gate("ff", v_ff >= 0 and (e_ff is None or e_ff >= 0),
             f"verdict FF hold {v_ff:+.2f} ps" + (f", export {e_ff:+.2f}" if e_ff is not None else ", no export-side FF STA"))
    dis = [f"{n} {e - v:+.2f}" for n, v, e in (("TT", v_tt, e_tt), ("FF", v_ff, e_ff))
           if v is not None and e is not None and abs(e - v) > 1.0]
    if e_tt is None and e_ff is None:
        gate("export", None, "no export-side corner STA record to compare with the verdict")
    elif dis:
        gate("export", None, "export minus verdict: " + ", ".join(dis) + " ps")
    else:
        gate("export", True, "export-side STA within 1 ps of the verdict"
             + ("" if e_tt is not None else " (FF only; TT not exported-side checked)"))
    gate("drc", js.get("status") == "CLOSED" and drc == 0, f"job {js.get('status')}; DRC {drc}")
    b = js.get("benches") or {}
    pos = [n for n, v in b.items() if v.get("expect") == "pass" and v.get("ok") and "lint" not in n]
    neg = [n for n, v in b.items() if v.get("expect") == "fail" and v.get("ok")]
    gate("bench", bool(pos) and bool(neg),
         f"pass benches {pos or 'NONE'}; failing mutants {neg or 'NONE'}" + ("" if b else " (no bench record)"))

    lef = ROOT / files["lef"]["path"]
    cl = child_lint(lef, lef.parent)
    gate("lint", cl["verdict"] == "PASS", cl["summary"] + ("" if cl["verdict"] == "PASS" else " | " + " | ".join(cl["fails"])[:600]))

    libs = {}
    for c in ("tt", "ff", "ss"):
        if c in files:
            libs[c] = lib_scan(ROOT / files[c]["path"])
    row["etm"] = libs
    cks = sorted((libs.get("ff") or libs.get("tt") or {}).get("clocks", {}))
    vec = [c for c in cks if "[" in c]
    noins = [c for c in cks if "min_clock_tree_path_ps" not in (libs.get("ff") or {}).get("clocks", {}).get(c, {})]
    gate("clock", bool(cks) and not noins,
         f"clock pins {cks or 'NONE'}" + (f"; no FF min/max_clock_tree_path on {noins}" if noins else ""))
    need = master in rules
    if vec and need:
        gate("scalar", False, f"contract clock_pin_rules requires scalar clocks; view has {vec}")
    else:
        gate("scalar", True, f"vector-named clock pins {vec} (no contract scalar rule for this master)" if vec else "scalar")

    r = reg.get(master) or {}
    thr = (r.get("throughput") or {})
    gt = r.get("gate") or ""
    # OWNER 2026-10-13 (ROM throughput): a ROM design's throughput is qualified by a PER-LAYER measured run of the die
    # composition against the priced layer; unit benches only for critical-path units.  So for an S81 ROM master the
    # unit registry state is a view gate only when it is a MEASURED failure (status UNQUALIFIED: over 1.10x and not on
    # the accepted-cost ledger).  UNMEASURED / no bench / no budget row do not block the BINDING of a closed view: the
    # layer run (el1013-rom-layer-tput-s81.log) is the release gate and is recorded as such (thr_basis), never as a
    # unit qualification.
    st = thr.get("status")
    if st in ("QUALIFIED", "QUALIFIED_BY_BOUND", "EXEMPT"):
        row["thr_basis"] = "unit"
        gate("thr", True, f"registry {gt} ({st}, ratio {thr.get('ratio')}, class row {((thr.get('limiting') or {}).get('op'))})")
    elif st == "UNQUALIFIED":
        row["thr_basis"] = "unit"
        gate("thr", False, f"registry gate {gt}: MEASURED over 1.10x (ratio {thr.get('ratio')}), no accepted-cost ledger row")
    else:
        row["thr_basis"] = "rom_layer_run_pending"
        gate("thr", True, "ROM rule (owner 2026-10-13): unit throughput is not a view gate; qualified by the per-layer measured "
                          "die run against the priced layer (RELEASE gate, pending); registry: " + (gt or "no row") + f" / {st}")
    best = (r.get("best") or {}).get("job")
    gate("current", best == job, f"registry adopted job {best}" + ("" if best == job else f" != bundle job {job}"))

    ffl = libs.get("ff") or {}
    md = {}
    for c, v in ffl.get("cq_min_ps", {}).items():
        ins = ffl["clocks"].get(c, {})
        md[c] = {"cq_min_at_pin_ps": v, "min_insertion_ps": ins.get("min_clock_tree_path_ps"),
                 "max_insertion_ps": ins.get("max_clock_tree_path_ps"),
                 "hold_req_max_ps": ffl.get("hold_max_ps", {}).get(c)}
    row["min_delay_ff"] = md
    # Conservative seam budget of this view at FF (ETM arcs include the tile's clock insertion): internal launch
    # L = cq_min(pin) - max insertion, internal hold H = hold_max(pin) - min insertion.  A zero-wire seam S -> R whose
    # clock pins the die balances to their insertion needs L_S - H_R >= HOLD_UNC (50 ps die hold uncertainty) + skew,
    # i.e. cq + paths >= 65 ps against the 15 ps flop hold of the interim model.
    bud = {}
    for c, v in md.items():
        if c.endswith("@fall") or v["max_insertion_ps"] is None:
            continue
        L = round(v["cq_min_at_pin_ps"] - v["max_insertion_ps"], 2)
        H = None if v["hold_req_max_ps"] is None else round(v["hold_req_max_ps"] - v["min_insertion_ps"], 2)
        bud[c] = {"launch_L_ps": L, "hold_H_ps": H, "insertion_spread_ps": round(v["max_insertion_ps"] - v["min_insertion_ps"], 2),
                  "same_master_zero_wire_margin_ps": None if H is None else round(L - H - 50.0, 2)}
    row["min_delay_budget_ff"] = bud
    hard = [k for k, v in g.items() if v["ok"] is False]
    soft = [k for k, v in g.items() if v["ok"] is None]
    row["verdict"] = "QUALIFIED" if not hard and not soft else ("NOT_ESTABLISHED" if not hard else "NOT_QUALIFIED")
    row["failed_gates"] = hard
    row["open_gates"] = soft
    row["file_sha256"] = {c: sha(ROOT / f["path"]) for c, f in files.items()}
    row["hash_matches_manifest"] = all(row["file_sha256"][c] == f.get("sha256") for c, f in files.items())
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="results/arch/s81_native_20261013/manifest.json")
    ap.add_argument("--registry", default=None, help="saved /api/elements JSON")
    ap.add_argument("--jobs", default=str(JOBS))
    ap.add_argument("--contract", default="results/arch/hier_contract_1011/s81.json")
    ap.add_argument("--extra", default=None,
                    help="glob of further view LEFs (e.g. 'physical/ref_tile/s81_rly_*/views/*/*.lef'); instance counts from --census")
    ap.add_argument("--census", default="results/physical/die_iter_1012/s81/real_view_census_20261013/c5_census.json")
    ap.add_argument("--out", default="results/arch/s81_native_20261013/qualification.json")
    a = ap.parse_args()
    man = json.loads((ROOT / a.manifest).read_text())
    reg = {}
    if a.registry:
        reg = {r["element"]: r for r in json.loads(Path(a.registry).read_text())["rows"]}
    con = json.loads((ROOT / a.contract).read_text())
    rules = {m: r for m, r in con.get("clock_pin_rules", {}).items() if isinstance(r, dict) and r.get("ck") == "scalar"}
    hc_n = {}
    halves = man["hc_reference_leaf_instances"]["total_after_flattening_64_half_regions"] // 30
    cth = con["sub_layouts"]["ot_s81_hc_cth"]
    for r in cth["rows"]:      # a row is one full-width strip or len(x_cols) column tiles
        per = 1 if r["w"] > cth["outline"]["w"] / 2 else len(cth["x_cols"])
        hc_n[r["cell"]] = hc_n.get(r["cell"], 0) + per * halves
    rows, unbound = [], []
    for b in man["native_legacy_bindings"]:
        bd = b["binding"]
        if not bd:
            unbound.append({"master": b["master"], "instances": b["reference_instances"],
                            "why": "no complete native bundle: " + "; ".join(
                                f"{r.get('same_export_directory')} missing {r.get('missing')}"
                                for r in b["rejected_or_incomplete_exports"]) or "no export"})
            continue
        rows.append(qualify(b["master"], b["reference_instances"], bd["files"], Path(bd["same_export_directory"]),
                            reg, Path(a.jobs), rules))
    for h in man.get("hc_half_leaf_membership", []):
        if h.get("files") and not h.get("missing"):
            n = hc_n.get(h["master"], 0)
            rows.append(qualify(h["master"], n, h["files"], Path(h["files"]["lef"]["path"]).parent, reg, Path(a.jobs), rules))
            rows[-1]["family"] = "hc_half_leaf"
        else:
            unbound.append({"master": h.get("master"), "instances": hc_n.get(h.get("master"), 0),
                            "why": f"HC leaf without a complete native bundle (missing {h.get('missing')})"})
    if a.extra:
        import glob
        cen = json.loads((ROOT / a.census).read_text())
        cnt = {m["master"]: m["instances"] for m in cen["masters"]}
        for lef in sorted(glob.glob(str(ROOT / a.extra))):
            lef = Path(lef)
            mst = lef.stem
            files = {"lef": {"path": str(lef.relative_to(ROOT))}}
            for c in ("tt", "ff", "ss"):
                lp = lef.parent / f"{mst}_{c}.lib"
                if lp.exists():
                    files[c] = {"path": str(lp.relative_to(ROOT))}
            for f in files.values():
                f["sha256"] = sha(ROOT / f["path"])
            rows.append(qualify(mst, cnt.get(mst, 0), files, lef.parent.relative_to(ROOT), reg, Path(a.jobs), rules))
            rows[-1]["family"] = "extra"
    tot = sum(r["instances"] or 0 for r in rows)
    q = [r for r in rows if r["verdict"] == "QUALIFIED"]
    out = {"schema": "s81-native-view-qualification-v1", "manifest": a.manifest,
           "manifest_sha256": sha(ROOT / a.manifest),
           "gates": ["pair", "tt", "ff", "export", "drc", "bench", "lint", "clock", "scalar", "thr", "current"], "contract_version": con.get("version"),
           "bundles": len(rows), "bundle_instances": tot,
           "qualified_masters": len(q), "qualified_instances": sum(r["instances"] or 0 for r in q),
           "gate_failures": {k: sorted(r["master"] for r in rows if k in r["failed_gates"])
                             for k in ["pair", "tt", "ff", "export", "drc", "bench", "lint", "clock", "scalar", "thr", "current"]},
           "gate_open": {k: sorted(r["master"] for r in rows if k in r["open_gates"]) for k in ["pair", "tt", "ff", "export", "drc", "bench", "lint", "clock", "scalar", "thr", "current"]},
           "rows": rows, "unbound": unbound}
    (ROOT / a.out).write_text(json.dumps(out, indent=1) + "\n")
    for r in rows:
        print(f"{r['verdict']:16s} {r['master']:32s} x{r['instances']:<5} fail={','.join(r['failed_gates']) or '-'}"
              f" open={','.join(r['open_gates']) or '-'}")
    print(f"qualified {len(q)}/{len(rows)} masters, {out['qualified_instances']}/{tot} instances; unbound {len(unbound)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
