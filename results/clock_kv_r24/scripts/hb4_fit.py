"""CLOCK-KV-R24 HB4 fit per partition (region): seam (by capture partition) + intra (bound) HB4 cells vs the partition's
free std-cell area after hard cores, die clock islands, landing islands, ft stations, glue cells and a PG allowance.
usage: hb4_fit.py PLAN GATE_JSON CELLS_EVIDENCE OUT_TSV"""
import json, sys, collections
plan, gate, ev, out = sys.argv[1:5]
P = json.load(open(plan)); G = json.load(open(gate)); E = json.load(open(ev))["cells_per_type"]
HB = 0.10206          # HB4xp67 LEF 0.378 x 0.27
GLUE = 0.12           # ASSUMED average glue std-cell area um2 (ASAP7 mix), flat_k from cells_evidence
STA = 0.40            # ASSUMED um2 per ft station bit (DFF 0.29 + buffer)
PG = 0.03             # ASSUMED placement-site loss to PG via stacks / straps
UTIL = 0.70           # max placement utilisation of the free area
seam = G["hb4"]["seam"]["hb4_cells_by_part"]; intra = G["hb4"]["intra"].get("hb4_cells_by_part", {})
T = P["partition_types"]; rows = []
for p in P["partitions"]:
    t = T[p["type"]]; w, h = t["outline_um"]; A = w * h
    cores = sum(c["outline_um"][0] * c["outline_um"][1] for c in t.get("hard_cores", []) or [])
    isl = sum((r[2] - r[0]) * (r[3] - r[1]) for r in t.get("clock", {}).get("die_islands_um", []))
    land = sum((r["rect_um"][2] - r["rect_um"][0]) * (r["rect_um"][3] - r["rect_um"][1]) for r in t.get("landing_islands", []) or [])
    st = sum(int(s.get("width", 1)) * int(s.get("stations", 0)) for s in t.get("ft_slots", []) or []) * STA
    glue = (E.get(p["type"], {}).get("flat_k") or 0) * 1000 * GLUE
    free = (A - cores - isl - land) * (1 - PG)
    hs, hi = seam.get(p["name"], 0) * HB, intra.get(p["name"], 0) * HB
    u0 = (glue + st) / free if free > 0 else 9
    u1 = (glue + st + hs + hi) / free if free > 0 else 9
    rows.append((p["name"], p["type"], round(A), round(cores), round(free), round(glue), round(st), round(hs), round(hi),
                 round(u0, 4), round(u1, 4), "FIT" if u1 <= UTIL else "OVER"))
rows.sort(key=lambda r: -r[10])
with open(out, "w") as f:
    f.write("part\ttype\tarea_um2\tcores_um2\tfree_um2\tglue_um2\tft_um2\thb4_seam_um2\thb4_intra_um2\tutil_before\tutil_after\tverdict\n")
    for r in rows:
        f.write("\t".join(map(str, r)) + "\n")
c = collections.Counter(r[11] for r in rows)
print(dict(c), "worst", rows[0], "\nmedian util_after", sorted(r[10] for r in rows)[len(rows) // 2],
      "\nseam cells", sum(seam.values()), "intra cells", sum(intra.values()),
      "\nassumptions glue %.2f um2/cell, ft %.2f um2/bit-station, PG %.0f%%, util cap %.0f%%" % (GLUE, STA, PG * 100, UTIL * 100))
