#!/usr/bin/env python3
"""Die real-view census (owner 2026-10-13: the first release needs die timing on a die assembled from REAL views).

Counts, per master, the die instances bound to a real closed view against placeholders / generated views.  Die leads run
it on every die case and every contract version.

  die case          die_real_census.py --die NAME --case ID (--def PLACED.def | --netlist die.v) --lef CASE.lef ...
                        --lib CASE_tt.lib ... [--lib-list libs_tt.txt] --repo SRC_ROOT [--repo ...] [--out DIR]
  contract version  die_real_census.py --die NAME --contract results/arch/hier_contract_*/DIE.json --repo SRC_ROOT

REAL = LEF + ETM BY NAME: a view directory under a --repo root holds <master>.lef and <master>_tt.lib (the shape
tools/ref_tile export and the closure loop write), AND
  * the case's LEF MACRO <master> is that file's macro (whitespace-normalised text), and
  * the case's Liberty cell <master> is that view's cell (the same file, or the same whitespace-normalised cell text).
An ETM of another cell bound "by role / by pin direction", a budget view, an interim lib and a generated outline are
therefore not real.  Classes per master:
  real          exact LEF and exact ETM of a view found by name
  lef_only      exact LEF of a named view, timing from something else
  etm_only      exact ETM of a named view, geometry generated (the S81 "closed-tag ETM on a generated LEF" case)
  hard_macro    exact LEF/ETM of a memory / PHY macro abstract (view path matches --macro-re): reported apart, it is
                neither a routed element nor a placeholder
  placeholder   everything else (generated outline / pins, assumed or budget timing); "view_exists" tells whether a
                named view exists that the die did not bind (a replacement candidate), "lef_near" whether the generated
                macro at least has the view's outline and pin names
Contract mode has no case files: a slot is "real" when a named view exists whose LEF outline equals the slot outline
(the die CAN bind it), else placeholder; the JSON says mode "contract" and the README row is labelled so.  A bindable
view is then held against its slot (child_lint check (e): pin names, faces, layers, PG layer): "slot_check" lists the
differences ("slot_pins": exact / differ) and summary "real_slot_exact" counts the instances whose view matches the slot
as the contract states it; a view that differs is real only once the contract adopts its pins (slot change request).
"exported_before_export_sdc_fix" marks a view committed before main abc334b14 (its ETM is PROVISIONAL).
Output: <out>/<die>_<case>.json (per master: instances, class, view, sha256 of the compared texts) and one row per
(die, case) in <out>/README.md.  Exit 0 always (a census, not a gate); --min-real-frac F exits 1 below F.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import child_lint  # noqa: E402

SCHEMA = "opentallas.die_real_census.v1"
EXPORT_FIX = "abc334b14"          # view_export verdict replay (el1013-export-sdc.log); pinreg_audit.py uses the same mark
CLASSES = ("real", "lef_only", "etm_only", "hard_macro", "placeholder")
MACRO_RE = r"(asap7_memory_macros|_macros_v\d|pdie_macros|/hard_ip/|/phy/)"
VIEW_ROOTS = ("physical",)
KEYWORDS = {"module", "endmodule", "input", "output", "inout", "wire", "assign", "reg", "logic", "supply0", "supply1",
            "tri", "parameter", "localparam", "always", "initial", "generate", "endgenerate", "function", "if", "else",
            "begin", "end", "for", "genvar", "defparam", "specify", "primitive"}
HEAD = ("| die | case | mode | source | instances | real | lef only | etm only | hard macro | placeholder | real % | "
        "masters real / all | when |")
SEP = "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"


def norm_hash(text: str) -> str:
    return hashlib.sha256(" ".join(text.split()).encode()).hexdigest()


# ------------------------------------------------------------------------------------------------------- parsers
def def_instances(path: Path) -> Counter:
    """master -> instance count from a DEF COMPONENTS section (streamed)"""
    c, on = Counter(), False
    with open(path, errors="replace") as fh:
        for ln in fh:
            if not on:
                on = ln.startswith("COMPONENTS ")
                continue
            if ln.startswith("END COMPONENTS"):
                break
            m = re.match(r"\s*-\s+\S+\s+(\S+)", ln)
            if m:
                c[m.group(1)] += 1
    return c


def netlist_instances(path: Path) -> Counter:
    """master -> instance count from a FLAT structural netlist (instances of the top module)"""
    c = Counter()
    rx = re.compile(r"^\s*([A-Za-z_]\w*)\s+(?:#\s*\(.*?\)\s*)?(\\\S+\s|[A-Za-z_][\w$]*(?:\[\d+\])?)\s*\(")
    with open(path, errors="replace") as fh:
        for ln in fh:
            m = rx.match(ln)
            if m and m.group(1) not in KEYWORDS:
                c[m.group(1)] += 1
    return c


def lef_macros(path: Path, want: set | None = None) -> dict:
    """{macro: {"hash", "size", "pins"}} of a LEF file (streamed; want limits the macros kept)"""
    out, name, buf = {}, None, []
    with open(path, errors="replace") as fh:
        for ln in fh:
            if name is None:
                m = re.match(r"\s*MACRO\s+(\S+)\s*$", ln)     # not PROPERTYDEFINITIONS' "MACRO width INTEGER ;"
                if m:
                    name, buf = m.group(1), [ln]
                continue
            buf.append(ln)
            if re.match(rf"\s*END\s+{re.escape(name)}\s*$", ln):
                if want is None or name in want:
                    t = "".join(buf)
                    sz = re.search(r"\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)", t)
                    out[name] = {"hash": norm_hash(t), "size": [float(sz.group(1)), float(sz.group(2))] if sz else None,
                                 "pins": sorted(set(re.findall(r"^\s*PIN\s+(\S+)", t, re.M)))}
                name = None
    return out


def lib_cells(path: Path, want: set | None = None) -> dict:
    """{cell: hash} of a Liberty file: the text from 'cell (X) {' to the next cell (the library's closing brace is
    dropped from the last one), whitespace-normalised"""
    text = Path(path).read_text(errors="replace")
    ms = list(re.finditer(r'^[ \t]*cell\s*\(\s*"?([^")\s]+)"?\s*\)\s*\{', text, re.M))
    out = {}
    for i, m in enumerate(ms):
        if want is not None and m.group(1) not in want:
            continue
        if i + 1 < len(ms):
            body = text[m.start():ms[i + 1].start()]
        else:
            body = text[m.start():].rstrip()
            body = body[:-1] if body.endswith("}") else body
        out[m.group(1)] = norm_hash(body)
    return out


# ---------------------------------------------------------------------------------------------------- view index
def view_index(roots: list[Path], masters: set, sub=VIEW_ROOTS, corner="tt") -> dict:
    """{master: [view dir, ...]}: directories under the roots holding <master>.lef and <master>_<corner>.lib"""
    want = {f"{m}.lef": m for m in masters}
    out: dict[str, list] = {}
    for root in roots:
        for s in sub:
            for dp, dn, fn in os.walk(root / s):
                dn[:] = [d for d in dn if d not in (".git", "__pycache__")]
                names = set(fn)
                for f in names & want.keys():
                    m = want[f]
                    if f"{m}_{corner}.lib" in names:
                        out.setdefault(m, []).append(Path(dp))
    return out


def classify(m: str, case_lef: dict | None, case_lib: dict, lib_files: dict, views: list[Path], macro_re: str,
             corner="tt") -> dict:
    """one master against its named views; case_lib = {cell: {hashes}}, lib_files = {realpath: sha} of whole case lib
    files (a view lib read by its own path counts as the exact ETM)"""
    best = {"class": "placeholder", "view": None, "view_exists": bool(views), "lef": "none", "etm": "none"}
    rank = {"real": 4, "hard_macro": 4, "lef_only": 3, "etm_only": 2, "placeholder": 0}
    for vd in views:
        vl = lef_macros(vd / f"{m}.lef", {m}).get(m)
        lef = "none"
        if vl and case_lef:
            if vl["hash"] == case_lef["hash"]:
                lef = "exact"
            elif vl["size"] == case_lef["size"] and vl["pins"] == case_lef["pins"]:
                lef = "outline+pins"
            elif vl["size"] == case_lef["size"]:
                lef = "outline"
        tt = vd / f"{m}_{corner}.lib"
        etm = "none"
        if str(tt.resolve()) in lib_files:
            etm = "exact"
        else:
            vh = lib_cells(tt, {m}).get(m)
            if vh and vh in case_lib.get(m, ()):
                etm = "exact"
        cls = ("real" if lef == "exact" and etm == "exact" else "lef_only" if lef == "exact" else
               "etm_only" if etm == "exact" else "placeholder")
        if cls != "placeholder" and re.search(macro_re, str(vd)):
            cls = "hard_macro"
        cand = {"class": cls, "view": str(vd), "view_exists": True, "lef": lef, "etm": etm}
        key = (rank[cls], lef != "none", etm != "none")
        if key > (rank[best["class"]], best["lef"] != "none", best["etm"] != "none") or best["view"] is None:
            best = cand
    return best


# ---------------------------------------------------------------------------------------------------------- runs
def census_case(inst: Counter, lefs: list[Path], libs: list[Path], roots: list[Path], macro_re=MACRO_RE,
                corner="tt") -> dict:
    case_lef: dict[str, dict] = {}
    for p in lefs:
        case_lef.update(lef_macros(p, set(inst)))
    masters = set(case_lef)                       # die-placed macros; everything else is a std cell / undefined
    case_lib: dict[str, set] = {}
    lib_files = {}
    for p in libs:
        lib_files[str(Path(p).resolve())] = True
        for c, h in lib_cells(p, masters).items():
            case_lib.setdefault(c, set()).add(h)
    idx = view_index(roots, masters, corner=corner)
    per = {}
    for m in sorted(masters):
        r = classify(m, case_lef[m], case_lib, lib_files, idx.get(m, []), macro_re, corner)
        if r["view"]:
            for root in roots:
                try:
                    r["view"] = str(Path(r["view"]).relative_to(root))
                    break
                except ValueError:
                    pass
        per[m] = dict(r, instances=inst[m], size=case_lef[m]["size"], case_lef_sha256=case_lef[m]["hash"],
                      case_has_lib=m in case_lib or r["etm"] == "exact",
                      lef_near=r["lef"] in ("outline+pins", "outline"))
    other = {m: n for m, n in inst.items() if m not in masters}
    return {"masters": per, "other_instances": sum(other.values()), "other_masters": len(other)}


def slot_check(lef: Path, cell: str, slot: dict) -> list[str]:
    """differences between a view's LEF and the slot as the contract states it (child_lint check (e))"""
    try:
        m = child_lint.parse_lef(lef.read_text(errors="replace"), cell)
        ce = slot.get("clock_entry") or {}
        if ce.get("pin") and all(child_lint.expand_bus(p["name"]) != [ce["pin"]] for p in slot.get("pins", [])):
            slot = dict(slot, pins=list(slot.get("pins", [])) + [{k: ce[k] for k in ("face", "layer") if ce.get(k)}
                                                                 | {"name": ce["pin"]}])
        return child_lint.check_contract(m, slot, child_lint.check_pg(m).get("top_layer"))
    except Exception as e:  # noqa: BLE001  (a census, not a gate: an unreadable view is a difference, never a crash)
        return [f"slot check failed: {type(e).__name__}: {e}"]


def before_export_fix(root: Path, rel: str) -> bool | None:
    """the view's LEF was last committed before the export-SDC fix (None: not a git tree / the fix is unknown there)"""
    import subprocess

    def ct(*a):
        r = subprocess.run(["git", "-C", str(root), "log", "-1", "--format=%ct", *a], capture_output=True, text=True)
        return int(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else None
    fix, view = ct(EXPORT_FIX), ct("--", rel)
    return None if fix is None or view is None else view < fix


def census_contract(contract: Path, roots: list[Path], macro_re=MACRO_RE) -> dict:
    d = json.loads(contract.read_text())
    slots = [s for s in d.get("slots", []) if isinstance(s, dict) and s.get("kind") != "die" and s.get("cell")]
    inst = Counter(s["cell"] for s in slots)
    outline, first = {}, {}
    for s in slots:
        first.setdefault(s["cell"], s)
        outline.setdefault(s["cell"], set()).add((round(float(s["outline"]["w"]), 3), round(float(s["outline"]["h"]), 3)))
    idx = view_index(roots, set(inst))
    per = {}
    for m in sorted(inst):
        r = {"class": "placeholder", "view": None, "view_exists": bool(idx.get(m)), "lef": "none", "etm": "none"}
        for vd in idx.get(m, []):
            vl = lef_macros(vd / f"{m}.lef", {m}).get(m)
            # a LEF SIZE carries 6 significant digits (1036.776 is written 1036.78): compare within 0.006 um
            fit = bool(vl and vl["size"] and any(abs(vl["size"][0] - w) <= 0.006 and abs(vl["size"][1] - h) <= 0.006
                                                 for w, h in outline[m]))
            if fit or r["view"] is None:
                view = str(vd)
                for root in roots:
                    try:
                        view = str(vd.relative_to(root))
                        break
                    except ValueError:
                        pass
                r = {"class": ("hard_macro" if re.search(macro_re, str(vd)) else "real") if fit else "placeholder",
                     "view": view, "view_exists": True, "lef": "outline" if fit else "none", "etm": "by name" if fit else "none"}
            if fit:
                if r["class"] == "real":
                    bad = slot_check(vd / f"{m}.lef", m, first[m])
                    r.update(slot=first[m].get("name"), slot_pins="differ" if bad else "exact", slot_check=bad)
                    for root in roots:
                        if vd.is_relative_to(root):
                            r["exported_before_export_sdc_fix"] = before_export_fix(root, str((vd / f"{m}.lef").relative_to(root)))
                            break
                break
        per[m] = dict(r, instances=inst[m], size=sorted(outline[m])[0], lef_near=False)
    return {"masters": per, "other_instances": 0, "other_masters": 0, "contract_version": d.get("version"),
            "contract_die": d.get("die")}


def summarise(res: dict) -> dict:
    tot = Counter()
    mc = Counter()
    for m, r in res["masters"].items():
        tot[r["class"]] += r["instances"]
        mc[r["class"]] += 1
    n = sum(tot.values())
    return {"instances": n, **{c: tot[c] for c in CLASSES}, "real_frac": round(tot["real"] / n, 6) if n else 0.0,
            "masters": len(res["masters"]), "masters_by_class": {c: mc[c] for c in CLASSES},
            "real_slot_exact": sum(r["instances"] for r in res["masters"].values()
                                   if r["class"] == "real" and r.get("slot_pins", "exact") == "exact"),
            "real_provisional_etm": sum(r["instances"] for r in res["masters"].values()
                                        if r["class"] == "real" and r.get("exported_before_export_sdc_fix")),
            "placeholder_with_view": sum(r["instances"] for r in res["masters"].values()
                                         if r["class"] == "placeholder" and r["view_exists"]),
            "top_placeholders": [[m, r["instances"]] for m, r in sorted(
                res["masters"].items(), key=lambda kv: -kv[1]["instances"]) if r["class"] == "placeholder"][:12]}


def readme_row(out: Path, rec: dict) -> None:
    s = rec["summary"]
    row = (f"| {rec['die']} | {rec['case']} | {rec['mode']} | {rec['source']} | {s['instances']} | {s['real']} | "
           f"{s['lef_only']} | {s['etm_only']} | {s['hard_macro']} | {s['placeholder']} | {100 * s['real_frac']:.2f} | "
           f"{s['masters_by_class']['real']} / {s['masters']} | {rec['when']} |")
    p = out / "README.md"
    lines = p.read_text().splitlines() if p.exists() else [
        "# Die real-view census", "",
        "One row per (die, case): instances bound to a real closed view (exact LEF + exact ETM of a view found by the "
        "master's name) against placeholders / generated views.  Generated by tools/hier_contract/die_real_census.py; "
        "per-master detail in <die>_<case>.json.  A contract-mode row counts slots whose cell HAS a closed view of the "
        "slot outline (bindable), not what a die case bound.", "", HEAD, SEP]
    key = f"| {rec['die']} | {rec['case']} | {rec['mode']} |"
    lines = [ln for ln in lines if not ln.startswith(key)] + [row]
    p.write_text("\n".join(lines) + "\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--die", required=True)
    ap.add_argument("--case", help="case id (default: the contract version)")
    ap.add_argument("--def", dest="def_", help="placed DEF (COMPONENTS)")
    ap.add_argument("--netlist", help="flat structural die netlist")
    ap.add_argument("--lef", action="append", default=[], help="LEF the die case placed (repeatable)")
    ap.add_argument("--lib", action="append", default=[], help="TT Liberty the die STA reads (repeatable)")
    ap.add_argument("--lib-list", help="file of Liberty paths, one per line")
    ap.add_argument("--lib-map", action="append", default=[], help="FROM=TO path prefix rewrite for --lib-list entries")
    ap.add_argument("--contract", help="hier contract JSON (contract mode)")
    ap.add_argument("--repo", action="append", default=[], help="source root to find named views in (repeatable)")
    ap.add_argument("--macro-re", default=MACRO_RE)
    ap.add_argument("--corner", default="tt", choices=("tt", "ff", "ss"),
                    help="Liberty corner compared (<master>_<corner>.lib; a die STA that reads no TT libs: ff)")
    ap.add_argument("--source", default="", help="source commit / note recorded in the row")
    ap.add_argument("--out", default=None, help="output directory (default results/physical/die_real_census in the first --repo)")
    ap.add_argument("--min-real-frac", type=float)
    a = ap.parse_args(argv)
    roots = [Path(r).resolve() for r in (a.repo or [str(Path(__file__).resolve().parents[2])])]
    if a.contract:
        res = census_contract(Path(a.contract), roots, a.macro_re)
        mode, case = "contract", a.case or f"v{res['contract_version']}"
        inputs = {"contract": a.contract}
    else:
        if not (a.def_ or a.netlist) or not a.lef:
            ap.error("a die case needs --def or --netlist, and --lef")
        libs = list(a.lib)
        if a.lib_list:
            for ln in Path(a.lib_list).read_text().split():
                for mp in a.lib_map:
                    fr, to = mp.split("=", 1)
                    ln = to + ln[len(fr):] if ln.startswith(fr) else ln
                libs.append(ln)
        libs = [Path(x) for x in libs if Path(x).exists() and re.search(a.corner, Path(x).name, re.I)]
        inst = def_instances(Path(a.def_)) if a.def_ else netlist_instances(Path(a.netlist))
        res = census_case(inst, [Path(x) for x in a.lef], libs, roots, a.macro_re, a.corner)
        mode, case = "case", a.case or "case"
        inputs = {"instances_from": a.def_ or a.netlist, "lef": a.lef, "libs": [str(x) for x in libs], "corner": a.corner}
    rec = {"schema": SCHEMA, "die": a.die, "case": case, "mode": mode, "source": a.source,
           "when": time.strftime("%Y-%m-%d %H:%M %Z"), "roots": [str(r) for r in roots], "inputs": inputs,
           "rule": "real = exact LEF macro + exact Liberty cell of a view directory holding <master>.lef and <master>_<corner>.lib",
           "summary": summarise(res), **res}
    out = Path(a.out) if a.out else roots[0] / "results/physical/die_real_census"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{a.die}_{case}.json").write_text(json.dumps(rec, indent=1) + "\n")
    readme_row(out, rec)
    s = rec["summary"]
    print(f"DIE_REAL_CENSUS {a.die} {case} ({mode}): {s['real']} real / {s['placeholder']} placeholder / {s['lef_only']} "
          f"lef-only / {s['etm_only']} etm-only / {s['hard_macro']} hard-macro of {s['instances']} instances "
          f"({100 * s['real_frac']:.2f}% real; masters {s['masters_by_class']['real']}/{s['masters']}); "
          f"{res['other_instances']} std/undefined"
          + (f"; real with the slot's pins exactly {s['real_slot_exact']}, real on a pre export-SDC-fix ETM "
             f"{s['real_provisional_etm']}" if mode == "contract" else ""))
    return 1 if a.min_real_frac is not None and s["real_frac"] < a.min_real_frac else 0


if __name__ == "__main__":
    sys.exit(main())
