#!/usr/bin/env python3
"""Static check of partition_types[].internal_stations rows against the kit generator's own row rules (QC-PLAN-R3, COORD
11-20, FABLE-PD-QC-2300 F1/F2).  Bind and LATCHECK read neither the row form nor the bit sites, so a row kit_istations
refuses (or a bit site inside a hard core) first shows up as a failed kit hours after the event is applied.

Per row (conn bus:<name>, width = the type's bus width):
  FORM     kit_istations.exact_banks(row, width) raises (bit_sites_um together with bit_route; a stage without width+1
           payload/epoch sites; ...)
  LEAF     bit_route per_bit without leaf_um and without exact sites (kit_istations: "bit_route per_bit needs leaf_um");
           the leaf is the core end of the row: to_um on an in bus, from_um on an out bus
  INSIDE   a bit_sites_um / face_bit_sites_um site inside a hard_cores[] box grown by its halo_um (nominal regs_um of a
           per_bit row are centroids and are not checked)
Estimator for the compose step, not a gate: prints findings, exit 0 unless --strict and findings (new vs --base) exist.
usage: station_rows_check.py PLAN.json [--base BASE.json] [--types T,..] [--json OUT] [--strict]"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def _boxes(t):
    out = []
    for h in t.get("hard_cores") or []:
        if h.get("origin_um") and h.get("outline_um"):
            (x, y), (w, hh) = h["origin_um"], h["outline_um"]; g = float(h.get("halo_um") or 0.0)
            out.append((h["inst"], [x - g, y - g, x + w + g, y + hh + g]))
    return out


def row_findings(tn, t):
    import kit_istations as KI
    width = {b["name"]: int(b.get("width", 1)) for b in t.get("buses") or [] if isinstance(b, dict) and "name" in b}
    boxes = _boxes(t); out = []
    for i, e in enumerate(t.get("internal_stations") or []):
        c = e.get("conn", "")
        if not c.startswith("bus:"):
            continue
        bus = c[4:]; key = f"{tn} {c} #{i}"
        if bus in width:
            try:
                KI.exact_banks(e, width[bus])
            except (ValueError, KeyError, TypeError, IndexError, AssertionError) as ex:
                out.append(("FORM", key, str(ex)[:200]))
        if e.get("bit_route") == "per_bit" and "leaf_um" not in e and e.get("bit_sites_um") is None:
            out.append(("LEAF", key, "bit_route per_bit without leaf_um"))
        n, worst = {}, {}
        for bank in (e.get("bit_sites_um") or []) + ([e["face_bit_sites_um"]] if e.get("face_bit_sites_um") else []):
            for p in bank:
                for nm, b in boxes:
                    if b[0] < p[0] < b[2] and b[1] < p[1] < b[3]:
                        n[nm] = n.get(nm, 0) + 1
                        worst[nm] = max(worst.get(nm, 0.0), min(p[0] - b[0], b[2] - p[0], p[1] - b[1], b[3] - p[1]))
                        break
        for nm in sorted(n):
            out.append(("INSIDE", key, f"{n[nm]} bit sites inside {nm} (+halo), up to {worst[nm]:.1f} um deep"))
    return out


def check(plan, types=None):
    pt = plan["partition_types"]
    return [f for tn in sorted(types or pt) if tn in pt for f in row_findings(tn, pt[tn])]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan"); ap.add_argument("--base"); ap.add_argument("--types"); ap.add_argument("--json")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args(argv)
    types = a.types.split(",") if a.types else None
    f = check(json.load(open(a.plan)), types)
    old = set((k, key) for k, key, _ in check(json.load(open(a.base)), types)) if a.base else set()
    new = [x for x in f if (x[0], x[1]) not in old]
    summ = {k: sum(1 for x in new if x[0] == k) for k in ("FORM", "LEAF", "INSIDE")}
    for x in new:
        print(*x, sep="  ")
    print("STATION-ROWS", "new" if a.base else "all", json.dumps(summ), "types", len({x[1].split()[0] for x in new}))
    if a.json:
        Path(a.json).write_text(json.dumps(dict(summary=summ, findings=new), indent=1) + "\n")
    return 1 if a.strict and new else 0


if __name__ == "__main__":
    sys.exit(main())
