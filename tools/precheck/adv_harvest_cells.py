#!/usr/bin/env python3
"""harvest_cells.py -- PRECHECK-R2 ADV-DENSITY cache: measured synth std-cell counts per (die, type).

Source: kit-wave result.json of every kit attempt (wave items and private specs).  cells = the kit's
native_cell_count.json stdcells, else the synth_stat.txt 'Number of cells' (top only, block macros excluded),
the same count cell_check.py (PLAN-GEN-RULES-1 rule C) reads.  Per (die, type) it keeps the NEWEST record and the
newest record that PLACED (stage geom/geom_run, or place not FAIL): the placed record is the evidence that a
density was placeable.  Read-only; seconds.
  harvest_cells.py OUT.json [GLOB ...]"""
import glob, json, os, re, sys, time

DEF = ["~/coord/autopilot/kit_wave/*/a*/result.json", "~/coord/autopilot/private_specs/*/*/result.json",
       "/srv/opentallas-scratch2/claude/*/spec_*/result.json", "/srv/opentallas-scratch2/claude/*/*/spec_*/result.json"]
FILL = re.compile(r"\bfill=\w+\(([\d.]+)\)")
PLACED = {"geom", "geom_run"}


def placed(d):
    return d.get("stage") in PLACED or (d.get("stage") == "place" and d.get("verdict") != "FAIL")


def main():
    out = sys.argv[1]
    db, n = {}, 0
    for pat in sys.argv[2:] or DEF:
        for f in glob.glob(os.path.expanduser(pat)):
            try:
                d = json.load(open(f))
            except Exception:
                continue
            cells = d.get("cells")
            if not isinstance(cells, int) or isinstance(cells, bool) or cells <= 0:
                continue
            die, item, plan = d.get("die"), d.get("item"), None
            try:
                s = json.load(open(os.path.join(os.path.dirname(f), "spec.json")))
                if s.get("kind") not in (None, "type"):
                    continue
                die, item, plan = die or s.get("die"), item or s.get("item"), s.get("plan")
            except Exception:
                pass
            if not die or not item:
                continue
            n += 1
            t0 = float(d.get("t0") or os.path.getmtime(f))
            m = FILL.search(d.get("geom") or "")
            cc = d.get("cell_check") or {}
            rec = dict(cells=cells, t0=round(t0), stage=d.get("stage"), verdict=d.get("verdict"), src=f, plan=plan,
                       fill=float(m.group(1)) if m else None, outline_um=cc.get("outline_um"), soft_um2=cc.get("soft_um2"))
            k = db.setdefault(die, {}).setdefault(item, {})
            if "last" not in k or t0 > k["last"]["t0"]:
                k["last"] = rec
            if placed(d) and ("placed" not in k or t0 > k["placed"]["t0"]):
                k["placed"] = rec
    json.dump(dict(schema="precheck-r2.cells_cache.v2", made=time.strftime("%Y-%m-%d %H:%M"), results=n, cells=db),
              open(out, "w"), indent=0, sort_keys=True)
    print(f"HARVEST_CELLS {n} results, " + ", ".join(f"{k} {len(v)}" for k, v in sorted(db.items())))


if __name__ == "__main__":
    main()
