#!/usr/bin/env python3
"""type_census.py -- PRECHECK-1119 / COORD 11-19: type-reduction census of one die plan.

  type_census.py --die DIE --plan PLAN.json [--bind-rtl DIR] --out OUT.json

Per family (type name up to the first "__t<N>"): number of types, number of distinct bound RTL
(the bind's rtl/<type>.sv with comments, the type name, position suffixes and parameter default
values stripped), number of distinct logic identities (plan contents modules + params + hard core
modules), and which plan fields differ among types that share one RTL hash:
  pins (buses face/window/width), stations (internal_stations, relay_sites, ft_slots),
  taps (clock.taps), outline, orient (instance orientations), cores (hard core placement).
Estimate = distinct (logic id, outline up to rotation) per family: one canonical pin template,
position-specific relays in the streets, mirrored/rotated views reused.
Read-only; prints a JSON record.
"""
import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path

SUFFIX = re.compile(r"__t\d+(?:__(?:cl|pv)[0-9a-f]{6,})*")


def family(t):
    return re.split(r"__(?:t\d+|cl[0-9a-f]{6,}|pv[0-9a-f]{6,})", t)[0]


CLAND = re.compile(r"cland")


def h(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:12]


_CMT = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)
_PDEF = re.compile(r"(parameter\s+(?:\[[^\]]*\]\s*)?\w+\s*=\s*)[^,;)\n]+")


def rtl_hash(path, tname, rom_inst=False):
    try:
        s = path.read_text(errors="replace")
    except OSError:
        return None
    s = _CMT.sub("", s)
    s = s.replace(tname, "TYPE")
    s = SUFFIX.sub("__tX", s)
    s = re.sub(r"\b(src|cl|pv)_?[0-9a-f]{8,}\b", r"\1_H", s)
    s = _PDEF.sub(r"\1V", s)
    if rom_inst:
        s = re.sub(r'\.(INSTANCE|VIAMAP)\("[^"]*"\)', r".\1(I)", s)
    s = re.sub(r"\s+", " ", s)
    return hashlib.sha256(s.encode()).hexdigest()[:12]


def logic_id(t):
    cont = [(c.get("module"), json.dumps(c.get("params") or {}, sort_keys=True)) for c in (t.get("contents") or [])]
    cores = sorted(c.get("module") or "" for c in (t.get("hard_cores") or []) if not CLAND.search(c.get("module") or ""))
    return h([sorted(cont), cores])


def aspects(t, orients):
    ck = t.get("clock") or {}
    return {
        "pins": h([(b.get("name"), b.get("face"), b.get("window_um"), b.get("width")) for b in (t.get("buses") or [])]),
        "faces": h(sorted((b.get("name"), b.get("face")) for b in (t.get("buses") or []))),
        "stations": h([t.get("internal_stations"), t.get("relay_sites"), t.get("ft_slots")]),
        "taps": h([ck.get("taps"), ck.get("tap_mode"), ck.get("tap_um")]),
        "outline": h(t.get("outline_um")),
        "orient": h(sorted(orients)),
        "cores": h(sorted((c.get("inst"), c.get("origin_um"), c.get("orient")) for c in (t.get("hard_cores") or []))),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--die", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--bind-rtl")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    P = json.loads(Path(a.plan).read_text())
    pt = P["partition_types"]
    parts = P.get("partitions") or []
    inst = collections.Counter()
    orients = collections.defaultdict(set)
    for p in parts if isinstance(parts, list) else parts.values():
        inst[p.get("type")] += 1
        orients[p.get("type")].add(p.get("orient") or "R0")
    rtl = Path(a.bind_rtl) if a.bind_rtl else None
    fam = collections.defaultdict(list)
    for tn, t in pt.items():
        rh = rtl_hash(rtl / f"{tn}.sv", tn) if rtl else None
        rhi = rtl_hash(rtl / f"{tn}.sv", tn, True) if rtl else None
        ol = t.get("outline_um") or [0, 0]
        fam[family(tn)].append({
            "type": tn, "instances": inst.get(tn, 0), "rtl": rh, "rtl_rom": rhi, "logic": logic_id(t),
            "outline_rot": h(sorted(round(x, 2) for x in ol)), "aspects": aspects(t, orients.get(tn, set())),
        })
    out = {"die": a.die, "plan": a.plan, "bind_rtl": a.bind_rtl, "families": {}}
    for f, rows in sorted(fam.items()):
        by_rtl = collections.defaultdict(list)
        for r in rows:
            by_rtl[r["logic"]].append(r)
            r["aspects"]["rtl_bound"] = r["rtl"]
            r["aspects"]["rtl_mod_rom_instance"] = r["rtl_rom"]
        diff = collections.Counter()
        shared_groups = 0
        for g in by_rtl.values():
            if len(g) < 2:
                continue
            shared_groups += 1
            for k in g[0]["aspects"]:
                if len({r["aspects"][k] for r in g}) > 1:
                    diff[k] += len(g)
        est = len({(r["logic"], r["outline_rot"]) for r in rows})
        out["families"][f] = {
            "types": len(rows), "instances": sum(r["instances"] for r in rows),
            "distinct_rtl": len({r["rtl"] for r in rows}) if rtl else None,
            "distinct_rtl_mod_rom_instance": len({r["rtl_rom"] for r in rows}) if rtl else None,
            "rtl_missing": sum(1 for r in rows if rtl and r["rtl"] is None),
            "distinct_logic": len({r["logic"] for r in rows}),
            "distinct_outline_rot": len({r["outline_rot"] for r in rows}),
            "shared_logic_groups": shared_groups,
            "types_in_shared_logic_groups_differing_by": dict(diff),
            "estimate_canonical": est,
        }
    tot = {k: sum((v[k] or 0) for v in out["families"].values()) for k in ("types", "distinct_rtl", "distinct_rtl_mod_rom_instance", "distinct_logic", "estimate_canonical")}
    out["total"] = tot
    Path(a.out).write_text(json.dumps(out, indent=1, sort_keys=True))
    print(json.dumps(tot))


if __name__ == "__main__":
    sys.exit(main())
