#!/usr/bin/env python3
"""KIT-PREFLIGHT (KITPACK-CLOSE-1115, COORD r221 / FABLE-FLOWCLASS-KITPACK-2030 F3): at plan adoption, resolve EVERY input the
kit of a die needs on EVERY gen host and refuse with the complete named list, never the first miss.

Why: 948 of 2,172 wave failures in 24 h were missing kit inputs, each found one file at a time on a gen host after ot-run
admission (SRC-TREE-1115: one named ROM file hid 398 missing inputs).  This is the same check, run once per event:

  * src_input      every file kit_wave.src_inputs names (plan, src tools, asbuilt / script, bind_report.json, bind HDL)
  * view           every child view the plan names (partition_types ... *.lef): the view dir must resolve, carry a real
                   provenance.json (export.signoff set: not a stub), a signoff.json copy, and for a hard landing child
                   landing_evidence/manifest.json (a CLOSED view, export_view.close_view), on every gen host
  * retired_host   a prov_view_sources candidate on a terminated host (epyc4/5/6)

    kit_preflight.py DIE [--config kit_wave.json]       exit 1 + the full list when anything is missing
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
RETIRED_HOSTS = ("epyc4", "epyc5", "epyc6")
LANDING_RE = re.compile(r"cland|landing")


def plan_lefs(plan_path):
    """every *.lef string the plan's partition_types name"""
    try:
        doc = json.loads(Path(plan_path).read_text())
    except (OSError, ValueError):
        return []
    out, todo = set(), [doc.get("partition_types") or {}]
    while todo:
        v = todo.pop()
        if isinstance(v, dict):
            todo += list(v.values())
        elif isinstance(v, list):
            todo += v
        elif isinstance(v, str) and v.endswith(".lef"):
            out.add(v)
    return sorted(out)


def view_requirements(plan_path, roots):
    """-> (entries, files): entries = problems seen on the reading host (view dir unresolved, stub provenance);
    files = [(path, by)] the closed view must hold on every gen host"""
    entries, files = [], []
    for lef in plan_lefs(plan_path):
        cands = [lef] if os.path.isabs(lef) else [os.path.join(r, lef) for r in list(roots) + [os.path.dirname(plan_path)]]
        hit = next((c for c in cands if os.path.isfile(c)), None)
        if not hit:
            entries.append(dict(kind="view", path=lef, why="view LEF resolves nowhere on the reading host"))
            continue
        vd = os.path.dirname(hit)
        pv = os.path.join(vd, "provenance.json")
        files += [(hit, lef), (pv, lef), (os.path.join(vd, "signoff.json"), lef)]
        try:
            prov = json.loads(Path(pv).read_text())
        except (OSError, ValueError):
            entries.append(dict(kind="view", path=pv, why="provenance.json unreadable"))
            continue
        if not (prov.get("export") or {}).get("signoff"):
            entries.append(dict(kind="view", path=pv, why="stub provenance (no export.signoff): not exported from a signed build"))
        if LANDING_RE.search(lef) or os.path.isdir(os.path.join(vd, "landing_evidence")):
            files.append((os.path.join(vd, "landing_evidence", "manifest.json"), lef))
    return entries, files


def retired_candidates(cfg, die):
    out = []
    srcs = ((cfg.get("dies") or {}).get(die) or {}).get("prov_view_sources") or {}
    for mod, cands in sorted(srcs.items()):
        for c in cands if isinstance(cands, list) else [cands]:
            if isinstance(c, dict) and c.get("host") in RETIRED_HOSTS:
                out.append(dict(kind="retired_host", path=f"{c['host']}:{c.get('dir')}", why=f"candidate for {mod} names terminated host {c['host']}"))
    return out


def preflight(cfg, die, hosts, run=None, src_files=None):
    """-> [entry]: the COMPLETE list of unresolved inputs, each {kind, path, hosts|why}; [] = every input resolves everywhere"""
    import adopt_guard as AG
    run = run or AG.sh
    d = cfg["dies"][die]
    out = []
    plan = str(d.get("plan") or "")
    entries, files = view_requirements(plan, [str(d.get("src") or "")]) if plan else ([], [])
    out += entries
    allf = sorted(set(list(src_files or []) + [p for p, _ in files]))
    by = {}
    for p, b in files:
        by.setdefault(p, b)
    if allf and hosts:
        gaps = {}
        for h, miss in AG.missing_by_host(allf, hosts, run).items():
            for f in miss:
                gaps.setdefault(f, []).append(h)
        for f, hs in sorted(gaps.items()):
            kind = "view" if f in by else "src_input"
            out.append(dict(kind=kind, path=f, hosts=sorted(hs), **({"by": by[f]} if f in by else {})))
    out += retired_candidates(cfg, die)
    return out


def refusal(die, entries):
    """the one named list: every miss grouped by kind"""
    lines = [f"KIT-PREFLIGHT {die}: REFUSED, {len(entries)} unresolved kit inputs"]
    for kind in ("src_input", "view", "retired_host"):
        rows = [e for e in entries if e["kind"] == kind]
        if rows:
            lines.append(f"  [{kind}] {len(rows)}")
            for e in rows:
                lines.append("    " + e["path"] + (f"  missing on {','.join(e['hosts'])}" if e.get("hosts") else "")
                             + (f"  ({e['why']})" if e.get("why") else "") + (f"  by {e['by']}" if e.get("by") else ""))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("die")
    ap.add_argument("--config", default=os.path.expanduser("~/coord/autopilot/kit_wave.json"))
    a = ap.parse_args(argv)
    import kit_wave as K
    cfg = json.load(open(a.config))
    d = cfg["dies"][a.die]
    hosts = list(d.get("gen_hosts") or cfg.get("gen_hosts") or d.get("hosts") or cfg.get("hosts") or [])
    _t, files = K.src_inputs(cfg, a.die)
    ents = preflight(cfg, a.die, hosts, src_files=sorted(set(files)))
    print(refusal(a.die, ents) if ents else f"KIT-PREFLIGHT {a.die}: OK")
    return 1 if ents else 0


if __name__ == "__main__":
    sys.exit(main())
