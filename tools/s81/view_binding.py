#!/usr/bin/env python3
"""S81 die: build the by-name real-view binding table and the placeholder ledger (S81 DIE, 2026-10-13).

Binding rule (no exceptions): a die master is bound to a real view (routed LEF + TT/FF/SS ETM of ONE export) only when
tools/s81/native_view_qualify.py calls it QUALIFIED.  This tool adds two binding-side preconditions and removes none:

  export_fix  the export directory's abstract.json carries the verdict replay of main abc334b14 (view_export replays the
              verdict SDC sequence and compares TT setup / FF hold with the verdict): verdict.check.tt.ok and .ff.ok,
              record ok, and the listed LEF / liberty sha256 equal the files on disk.  An ETM exported before that fix
              is not trustworthy and does not bind.
  placer_fit  (--fit, run automatically when a master passes the two gates above) every instance of the master on the
              recipe's die is R0 and the real LEF SIZE fits the slot the placer reserved from the GENERATED outline.

Steps: (1) re-run the qualification gate (unless --no-requalify) with --extra over the relay kit view directories, so a
view directory that appears under physical/ref_tile/s81_rly_*/views/<master>/ is picked up by master name; (2) write the
table the die generator consumes (tools/dsrom_s81_fulldie.py --view-binding / OT_S81_VIEW_BINDING; tools/s81/die_sta.py
takes the same table for the liberty list); (3) write the ledger: every master of the die census with its instances,
the bound view or PLACEHOLDER, the failing / open gates, the owner and what would qualify it.

  view_binding.py [--registry EL.json | --registry-url URL] [--no-requalify] [--fit-recipe OPTS]
outputs (default): results/arch/s81_native_20261013/{view_binding.json, binding_ledger.json, BINDING.md}
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
D = "results/arch/s81_native_20261013"
SCHEMA = "s81-view-binding-v1"          # tools/dsrom_s81_fulldie.py VIEW_BINDING_SCHEMA
RELAY_GLOB = "physical/ref_tile/s81_rly_*/views/*/*.lef"
GATES = ["pair", "tt", "ff", "export", "drc", "bench", "lint", "clock", "scalar", "thr", "current"]
LEAD = "S81 DIE stream lead (claude/el1011-s81dieit)"

# what closes each gate (native_view_qualify.py gate definitions, in the order a view owner has to work)
REMEDY = {
    "pair": "one view_export run (LEF + TT/FF/SS ETM) from the orfs directory of the job's closing verdict; an ECO pass "
            "or a later single-corner extraction breaks the pair",
    "tt": "closing verdict and export-side STA with TT setup >= 0",
    "ff": "closing verdict and export-side STA with FF hold >= 0",
    "export": "re-export with tools/tt_views/view_export.py (main abc334b14): export-side STA within 1 ps of the verdict",
    "drc": "job closed with DRC 0",
    "bench": "a behavioural bench that passes AND a mutant that fails, recorded on the job",
    "lint": "tools/hier_contract/child_lint.py PASS on the committed LEF + libs (pin access from above, PG, clock pins)",
    "clock": "FF ETM with clock pins that all carry min/max_clock_tree_path",
    "scalar": "scalar clock pins where the contract's clock_pin_rules ask for them",
    "thr": "registry throughput not a MEASURED failure; unmeasured ROM units ride the per-layer die run (owner 2026-10-13, release gate)",
    "current": "the view exported from the registry's adopted (best) closure of the master",
    "export_fix": "re-export after main abc334b14 so abstract.json records verdict.check tt/ff ok for the files on disk",
    "placer_fit": "the generator must place the master at its real outline (see BINDING.md, placer assumptions), or the "
                  "kit outline must fit the generated slot at R0",
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def export_fix(row: dict) -> tuple[bool, str]:
    """binding-side gate: the export replayed the verdict SDC sequence (abc334b14) for the files now on disk"""
    d = ROOT / row["export_dir"]
    ap = d / "abstract.json"
    if not ap.exists():
        return False, "no abstract.json in the export directory"
    ab = json.loads(ap.read_text())
    chk = (ab.get("verdict") or {}).get("check") if isinstance(ab.get("verdict"), dict) else None
    if not chk:
        return False, "abstract.json has no verdict.check: exported before the export-SDC fix (main abc334b14)"
    bad = [c for c in ("tt", "ff") if not (chk.get(c) or {}).get("ok")]
    if bad or not ab.get("ok"):
        return False, f"verdict replay not ok ({bad or 'record ok=false'})"
    m = row["master"]
    for f in [f"{m}.lef"] + [f"{m}_{c}.lib" for c in ("tt", "ff", "ss")]:
        if not (d / f).exists() or (ab.get("files") or {}).get(f) != sha(d / f):
            return False, f"{f} on disk is not the file the verdict-replay export recorded"
    return True, "verdict replay ok (TT %s / FF %s ps) for the files on disk" % (
        chk["tt"].get("export_ps"), chk["ff"].get("export_ps"))


def row_files(row: dict) -> dict | None:
    d, m = ROOT / row["export_dir"], row["master"]
    out = {}
    for k, f in [("lef", f"{m}.lef")] + [(c, f"{m}_{c}.lib") for c in ("tt", "ff", "ss")]:
        if not (d / f).exists():
            return None
        out[k] = {"path": str((d / f).relative_to(ROOT)), "sha256": sha(d / f)}
    return out


def fit_check(recipe: str, cands: dict) -> dict:
    """{master: reason} for candidates the placer cannot bind on the recipe's die (non-R0 instance, real outline larger
    than the generated slot, LEF pins not the die netlist's ports).  Builds the die with nothing bound."""
    sys.path.insert(0, str(ROOT / "tools"))
    import shlex
    import dsrom_s81_fulldie as S
    S.VIEW_BINDING = "none"
    a = S.die_options(argparse.ArgumentParser()).parse_args(shlex.split((ROOT / recipe).read_text()) + ["--view-binding", "none"])
    S.apply_options(a)
    m = S.build()
    pdir = S.finalize_r8(m)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump({"schema": SCHEMA, "bound": cands}, fh)
    S.VIEW_BINDING = fh.name
    views = S.bound_views()
    bad = {}
    for it in m["insts"]:
        v = views.get(it.master)
        if v is None or it.master in bad:
            continue
        if it.orient != "R0":
            bad[it.master] = f"instance {it.name} is {it.orient}; bound views are placed R0 only"
        elif v["w"] > it.w + 1e-6 or v["h"] > it.h + 1e-6:
            bad[it.master] = (f"real outline {v['w']} x {v['h']} um exceeds the generated slot {it.w:.3f} x {it.h:.3f} um "
                              f"(instance {it.name})")
        else:
            faults = S.bound_view_pin_faults(it.master, v, pdir.get(it.master, {}))
            if faults:
                bad[it.master] = "LEF pins are not the die netlist's ports: " + "; ".join(faults[:3])
    Path(fh.name).unlink()
    return bad


def gen_lines() -> dict:
    """line numbers of the generator functions BINDING.md cites (re-read on every build, so they stay current)"""
    out = {}
    for i, ln in enumerate((ROOT / "tools/dsrom_s81_fulldie.py").read_text().split("\n"), 1):
        mm = re.match(r"\s*def (stn_dims|_hop_fix|find|_col_relays|_pick|finalize_r8|apply_view_binding|bound_views|"
                      r"bound_view_pin_faults|masters_r8|_faces_r8|write_lefs|case_real|case_grt|case_irm|_lint_pin_pt)\(", ln)
        if mm:
            out.setdefault(mm.group(1), i)
    return out


def contract_owners(path: str) -> dict:
    """cell -> owner of the hier contract: a slot's owner, else its nearest ancestor's"""
    slots = {s["name"]: s for s in json.loads((ROOT / path).read_text()).get("slots", [])}
    out = {}
    for s in slots.values():
        o, q = None, s
        while q is not None and not o:
            o, q = q.get("owner"), slots.get(q.get("parent") or (q["name"].rsplit("/", 1)[0] if "/" in q["name"] else ""))
        if s.get("cell") and o:
            out.setdefault(s["cell"], o)
    return out


CON_OWNER: dict = {}


def owner_of(master: str, reg: dict, row: dict | None) -> tuple[str, str]:
    if master in reg and reg[master].get("owner"):
        return str(reg[master]["owner"]), "element registry"
    if master in CON_OWNER:
        return CON_OWNER[master], "hier contract slot owner"
    if master.startswith("dsfd_rly_"):
        return LEAD + ", relay kits (tools/s81/rly_kits.py)", "kit generator"
    if row is not None and row.get("family") == "hc_half_leaf" or master.startswith("ot_s81_hc_"):
        return "hc-ctile (claude/el1011-s81hc-ctile)", "hier contract slot owner"
    return LEAD + " -- no hardening kit assigned", "default"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--qualification", default=f"{D}/qualification.json")
    ap.add_argument("--census", default="results/physical/die_iter_1012/s81/real_view_census_20261013/c5_census.json")
    ap.add_argument("--extra", default=RELAY_GLOB, help="view LEF glob handed to the qualification gate (by master name)")
    ap.add_argument("--registry", help="saved /api/elements JSON (else fetched from --registry-url)")
    ap.add_argument("--registry-url", default="http://127.0.0.1:8765/api/elements")
    ap.add_argument("--no-requalify", action="store_true", help="use the committed qualification.json as it is")
    ap.add_argument("--fit-recipe", default="results/physical/die_iter_1012/s81/s81_layer1_v14.opts",
                    help="die recipe of the placer_fit gate (only built when a master passes every other gate)")
    ap.add_argument("--no-fit", action="store_true", help="skip placer_fit (the generator still hard-errors at build)")
    ap.add_argument("--contract", default="results/arch/hier_contract_1011/s81.json", help="slot owners (read only)")
    ap.add_argument("--table", default=f"{D}/view_binding.json")
    ap.add_argument("--ledger", default=f"{D}/binding_ledger.json")
    ap.add_argument("--md", default=f"{D}/BINDING.md")
    a = ap.parse_args()

    CON_OWNER.update(contract_owners(a.contract))
    regp = a.registry
    if not regp:
        try:
            with urllib.request.urlopen(a.registry_url, timeout=60) as r, \
                    tempfile.NamedTemporaryFile("wb", suffix=".json", delete=False) as fh:
                fh.write(r.read())
                regp = fh.name
        except OSError as ex:
            if not a.no_requalify:
                raise SystemExit(f"no element registry ({a.registry_url}: {ex}); pass --registry EL.json or --no-requalify")
    reg = {}
    if regp:
        rj = json.loads(Path(regp).read_text())
        reg = {r["element"]: r for r in (rj["rows"] if isinstance(rj, dict) else rj) if isinstance(r, dict) and r.get("element")}
    if not a.no_requalify:
        cmd = [sys.executable, str(ROOT / "tools/s81/native_view_qualify.py"), "--registry", regp, "--extra", a.extra,
               "--census", a.census, "--contract", a.contract, "--out", a.qualification]
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if p.returncode:
            raise SystemExit("native_view_qualify.py failed: " + p.stderr[-800:])
        print(p.stdout.strip().split("\n")[-1])

    qual = json.loads((ROOT / a.qualification).read_text())
    cen = json.loads((ROOT / a.census).read_text())
    rows = {}
    for r in qual["rows"]:                      # one row a master; a QUALIFIED row wins over an earlier candidate
        if r["master"] not in rows or r["verdict"] == "QUALIFIED":
            rows[r["master"]] = r
    unbound = {u["master"]: u for u in qual.get("unbound", []) if u.get("master")}

    # candidates: QUALIFIED + export_fix
    extra_gate = defaultdict(dict)              # master -> {gate: detail} of the binding-side gates that failed
    cands = {}
    for mst, r in sorted(rows.items()):
        if r["verdict"] != "QUALIFIED":
            continue
        ok, why = export_fix(r)
        files = row_files(r)
        if not ok or files is None:
            extra_gate[mst]["export_fix"] = why if not ok else "view file missing on disk"
            continue
        cands[mst] = {"verdict": "QUALIFIED", "export_dir": r["export_dir"], "job": r.get("job"),
                      "job_commit": r.get("job_commit"), "export_fix": why, "files": files,
                      "instances_census": r.get("instances")}
    on_die = {m_["master"] for m_ in cen["masters"]}
    die_c = {k: v for k, v in cands.items() if k in on_die}
    fit = None
    if die_c and not a.no_fit:
        fit = fit_check(a.fit_recipe, die_c)
        for mst, why in fit.items():
            extra_gate[mst]["placer_fit"] = why
            cands.pop(mst)
    table = {"schema": SCHEMA, "rule": "master bound only when native_view_qualify.py says QUALIFIED, the export replayed "
             "the verdict SDC sequence (abc334b14) and the placer can place the real outline",
             "builder": "tools/s81/view_binding.py", "qualification": a.qualification,
             "qualification_sha256": sha(ROOT / a.qualification), "census": a.census,
             "placer_fit": None if fit is None else {"recipe": a.fit_recipe, "rejected": sorted(fit)},
             "bound": {k: v for k, v in sorted(cands.items()) if k in on_die},
             "qualified_not_on_die": sorted(k for k in cands if k not in on_die)}
    (ROOT / a.table).write_text(json.dumps(table, indent=1) + "\n")

    # by-name view directories of census masters that the qualification never saw (reported, never bound)
    seen_dirs = defaultdict(list)
    for lef in glob.glob(str(ROOT / "physical/**/views/**/*.lef"), recursive=True):
        lp = Path(lef)
        if lp.stem in on_die and lp.parent.name == lp.stem:
            seen_dirs[lp.stem].append(str(lp.parent.relative_to(ROOT)))

    def gates_of(r, mst):
        fg = {g: (r["gates"][g].get("detail") or "")[:240] for g in r.get("failed_gates", [])} if r else {}
        og = {g: (r["gates"][g].get("detail") or "")[:240] for g in r.get("open_gates", [])} if r else {}
        fg.update(extra_gate.get(mst, {}))
        return fg, og

    led, reasons = [], Counter()
    for cm in sorted(cen["masters"], key=lambda x: (-x["instances"], x["master"])):
        mst, n = cm["master"], cm["instances"]
        r = rows.get(mst)
        e = {"master": mst, "instances": n, "c5_physical": cm["physical_binding"], "c5_timing": cm["timing_index_tag"]}
        e["owner"], e["owner_source"] = owner_of(mst, reg, r)
        if mst in table["bound"]:
            b = table["bound"][mst]
            e.update(binding="BOUND", view=b["export_dir"], lef=b["files"]["lef"]["path"], job=b["job"],
                     failing_gates={}, open_gates={}, to_qualify="qualified")
        elif cm["physical_binding"] == "source_abstract":
            e.update(binding="CONSTANT_HARD_MACRO", view=cm.get("placed_lef_file"), failing_gates={}, open_gates={},
                     to_qualify="real LEF bound by a generator constant (Q_LEF / CFG_LEF / PHY_LEF / SERDES_LEF / UCIE_LEF), "
                                "outside the native qualification gate; its liberty binds by cell name (c5 timing tag: "
                                + cm["timing_index_tag"] + ")")
            e["owner"], e["owner_source"] = owner_of(mst, reg, None) if mst in reg else ("hard-macro owner (generator constant)", "default")
        else:
            fg, og = gates_of(r, mst)
            e.update(binding="PLACEHOLDER", view=None, failing_gates=fg, open_gates=og)
            if r:
                e.update(candidate_view=r["export_dir"], job=r.get("job"), qualifier_verdict=r["verdict"])
                e["to_qualify"] = "; ".join(f"{g}: {REMEDY[g]}" for g in list(fg) + [g for g in og if g not in fg])
                for g in fg:
                    reasons["gate " + g + " failed"] += n
                for g in og:
                    reasons["gate " + g + " open"] += n
            elif mst.startswith("dsfd_rly_"):
                w_, ff_ = mst.split("_")[2], mst.split("_")[3].lower()
                kit = f"physical/ref_tile/s81_rly_{w_}_{ff_}"
                has = (ROOT / kit).is_dir()
                e["failing_gates"] = {"no_view": f"kit {kit} " + ("exists; no views/%s/ export yet (not routed)" % mst if has
                                                                 else "does not exist")}
                e["kit"] = kit if has else None
                e["to_qualify"] = ("route the kit to closure, export views/%s/ with view_export.py, then every "
                                   "native_view_qualify gate; the binding picks the directory up by name" % mst)
                reasons["relay kit not routed / no view exported"] += n
            elif mst in unbound:
                e["failing_gates"] = {"no_bundle": unbound[mst].get("why", "")[:300]}
                e["to_qualify"] = "a complete same-export bundle (LEF + TT + FF + SS), then every native_view_qualify gate"
                reasons["no complete native bundle (missing corner / LEF)"] += n
            else:
                e["failing_gates"] = {"no_view": "generated master: no routed view in the qualification manifest"}
                e["to_qualify"] = ("a hardening kit for this master (or its tile inventory + assembled view), a closed route, "
                                   "a paired export, then every native_view_qualify gate")
                reasons["no routed view (no kit / not hardened)"] += n
            if seen_dirs.get(mst) and not r:
                e["view_dirs_by_name_not_in_qualification"] = sorted(seen_dirs[mst])
        led.append(e)
    off_die = [{"master": m_, "prospective_instances": r.get("instances"), "family": r.get("family"),
                "qualifier_verdict": r["verdict"], "failing_gates": gates_of(r, m_)[0], "open_gates": gates_of(r, m_)[1],
                "candidate_view": r["export_dir"], "owner": owner_of(m_, reg, r)[0],
                "why_not_bound": "the die netlist of the census has no instance of this master (its parent slab is one "
                                 "generated master); binding needs the generator to instantiate it"}
               for m_, r in sorted(rows.items()) if m_ not in on_die]
    cnt = Counter()
    for e in led:
        cnt[e["binding"] + "_masters"] += 1
        cnt[e["binding"] + "_instances"] += e["instances"]
    gl = gen_lines()
    G = "tools/dsrom_s81_fulldie.py"
    assumptions = [
        f"{G}: _hop_fix.find (line {gl.get('find')}) and _col_relays (line {gl.get('_col_relays')}, _pick line {gl.get('_pick')}) "
        f"choose every relay site from stn_dims([bits], horiz) (line {gl.get('stn_dims')}): the GENERATED outline "
        "(max(face need, 17.28) - SHAVE = 17.256 um minimum), before the relay's face pair is known.",
        "The relay master name dsfd_rly_<W>_<fi><fo> (hence which real outline applies: 8.64 / 10.8 / 15.12 square; W 266 / "
        "283: 34.56 x 19.44 N/S or 21.6 x 30.24 E/W) is assigned AFTER placement from the neighbours' directions (end of "
        f"_hop_fix, line {gl.get('_hop_fix')}; end of _col_relays), so the placer cannot size the site from the real LEF "
        "without a second placement pass.",
        f"apply_view_binding (line {gl.get('apply_view_binding')}, end of finalize_r8 line {gl.get('finalize_r8')}) therefore does "
        "not re-place: a bound instance keeps its slot ORIGIN (lower-left), takes the real LEF SIZE, must be R0 and must "
        "fit the slot; a larger real outline or a non-R0 instance is a hard error (and view_binding.py placer_fit keeps "
        "such a master a placeholder).  The slot remainder is left unused; occupancy / reach / --nxt-reach decisions were "
        "taken on the generated outline.",
        f"Real pin positions: k = 1 LEF (case_real line {gl.get('case_real')}: bound_views.lef, read before elements.lef) and "
        "tools/s81/die_hop_gate.py use the real pins.  masters_r8 / _faces_r8 (lines "
        f"{gl.get('masters_r8')} / {gl.get('_faces_r8')}) still build a generated-face Master for a bound master at the real "
        f"SIZE: the k > 1 bundled GRT view (case_grt line {gl.get('case_grt')}) and the IR windows (case_irm line "
        f"{gl.get('case_irm')}) use those generated faces, and _lint_pin_pt (line {gl.get('_lint_pin_pt')}, --pin-need) "
        "returns the instance centre for a bound master (it reads real pins only for REAL_FILES hard macros).",
        "The neighbours' generated pin faces (_faces_r8) aim at the bound instance's centre, not at its real pin face.",
        "--gen r7 never calls finalize_r8: nothing binds there.  tools/budgets/extract_die.py (clock plan) was not changed "
        "or checked against bound masters.",
    ]
    ledger = {"schema": "s81-binding-ledger-v1", "table": a.table, "qualification": a.qualification,
              "qualification_sha256": table["qualification_sha256"], "census": a.census, "census_run": cen.get("run"),
              "census_source_sha": cen.get("source_sha"),
              "qualification_summary": {"bundles": qual["bundles"], "qualified_masters": qual["qualified_masters"],
                                        "qualified_instances": qual["qualified_instances"]},
              "summary": dict(sorted(cnt.items())), "placeholder_instances_by_reason": dict(reasons.most_common()),
              "placer_assumptions": assumptions, "masters": led, "qualification_rows_not_on_die": off_die}
    (ROOT / a.ledger).write_text(json.dumps(ledger, indent=1) + "\n")

    tot_m, tot_i = len(led), sum(e["instances"] for e in led)
    L = ["# S81 die: by-name view binding", "",
         f"Built by `tools/s81/view_binding.py` from `{a.qualification}` (sha256 {table['qualification_sha256'][:12]}) and "
         f"the {cen.get('run')} census ({tot_m} masters, {tot_i} instances). Table: `{a.table}`; ledger: `{a.ledger}`.", "",
         "Rule: a master is bound to a real view (routed LEF + TT/FF/SS ETM of one export) only when "
         "`native_view_qualify.py` says QUALIFIED, its export replayed the verdict SDC sequence (main abc334b14: "
         "`abstract.json` verdict.check ok for the files on disk) and the placer can place the real outline. No gate is "
         "weakened; everything else is a generated placeholder.", "",
         "| binding | masters | instances |", "|---|---:|---:|"]
    for b in ("BOUND", "PLACEHOLDER", "CONSTANT_HARD_MACRO"):
        L.append(f"| {b} | {cnt[b + '_masters']} | {cnt[b + '_instances']} |")
    L += ["", f"Qualification gate today: {qual['qualified_masters']} of {qual['bundles']} candidate bundles QUALIFIED "
          f"({qual['qualified_instances']} instances). CONSTANT_HARD_MACRO = real LEF bound by a generator constant "
          "(cfg ROM, PHY, SerDes, UCIe, q element), outside the native gate.", "",
          "Placeholder instances by reason (a master with several failing gates counts under each):", "",
          "| reason | instances |", "|---|---:|"]
    L += [f"| {k} | {v} |" for k, v in reasons.most_common()]
    L += ["", "Placeholder masters with a candidate view (failed / open gates, owner):", "",
          "| master | instances | failed | open | owner |", "|---|---:|---|---|---|"]
    for e in led:
        if e["binding"] == "PLACEHOLDER" and e.get("candidate_view"):
            L.append(f"| {e['master']} | {e['instances']} | {', '.join(e['failing_gates']) or '-'} | "
                     f"{', '.join(e['open_gates']) or '-'} | {e['owner']} |")
    if off_die:
        L += ["", f"{len(off_die)} qualification rows are masters the die netlist does not instantiate "
              f"({', '.join(o['master'] for o in off_die)}): none QUALIFIED; see `qualification_rows_not_on_die`."
              if not any(o["qualifier_verdict"] == "QUALIFIED" for o in off_die) else
              f"{len(off_die)} qualification rows are masters the die netlist does not instantiate; see the ledger."]
    L += ["", "## How it is consumed", "",
          "- `tools/dsrom_s81_fulldie.py --view-binding TABLE` (or `OT_S81_VIEW_BINDING`; default the committed table; `none` "
          "binds nothing): `bound_views` verifies every file's sha256 against the table, `apply_view_binding` (end of "
          "`finalize_r8`) hard-errors when the LEF pins are not the die netlist's ports of that master, when an instance is "
          "not R0 or when the real outline exceeds the slot; `write_lefs` drops the generated macro and `case_real` writes "
          "`bound_views.lef`.",
          "- `tools/s81/die_sta.py kit`: a bound master's corner libs come from the table. A generated-outline master that is "
          "not in the table is timed with the interim lib even when a routed-view ETM of that cell exists in the tree "
          "(`unqualified_views_not_bound` in the kit index); `--legacy-unqualified-libs` restores the tree scan for "
          "re-running an earlier case.",
          "- Refresh: `python3 tools/s81/view_binding.py` (re-runs the qualification gate over the manifest bundles and "
          f"`{a.extra}`, so a relay view directory is picked up by master name when it appears).", "",
          "## Placer assumptions (what still uses the generated outline)", ""]
    L += [f"{i}. {s}" for i, s in enumerate(assumptions, 1)]
    (ROOT / a.md).write_text("\n".join(L) + "\n")
    print(f"bound {cnt['BOUND_masters']} masters / {cnt['BOUND_instances']} instances; placeholder "
          f"{cnt['PLACEHOLDER_masters']} / {cnt['PLACEHOLDER_instances']}; constant hard macro "
          f"{cnt['CONSTANT_HARD_MACRO_masters']} / {cnt['CONSTANT_HARD_MACRO_instances']}")
    for k, v in reasons.most_common(8):
        print(f"  {v:7d}  {k}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
