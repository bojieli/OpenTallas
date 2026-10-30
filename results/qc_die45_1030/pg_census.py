# DIE-QC-45: read-back of the die PG grid (M8/M9 special wires of VDD/VSS) in Codex complete_pg/provider.odb vs the
# plan die.pg.grid (layer, width, pitch, offset, net order); usage (openroad -python): pg_census.py ODB PLAN OUT
import sys, json, collections
import odb
src, planf, out = sys.argv[1:4]
P = json.load(open(planf)); grid = P["die"]["pg"]["grid"]; W, H = P["die"]["outline_um"]
db = odb.dbDatabase.create(); odb.read_db(db, src); b = db.getChip().getBlock(); u = b.getDbUnitsPerMicron()
rows = collections.defaultdict(list)   # (layer, net) -> [(centre, width, lo, hi, dir)]
other = collections.Counter()
for net in b.getNets():
    if net.getSigType() not in ("POWER", "GROUND"):
        continue
    for sw in net.getSWires():
        for w in sw.getWires():
            if w.isVia():
                continue
            L = w.getTechLayer().getName()
            if L not in ("M8", "M9"):
                other[(L, net.getName())] += 1
                continue
            x0, y0, x1, y1 = w.xMin() / u, w.yMin() / u, w.xMax() / u, w.yMax() / u
            if L == "M8":   # horizontal
                rows[(L, net.getName())].append(((y0 + y1) / 2, y1 - y0, x0, x1))
            else:
                rows[(L, net.getName())].append(((x0 + x1) / 2, x1 - x0, y0, y1))
res = dict(odb=src, plan=planf, die_um=[W, H], layers={}, other_layer_swire_rects={f"{k[0]}:{k[1]}": v for k, v in other.items()})
for g in grid:
    L = g["layer"]; half = g["pitch_um"] / 2; off = g["offset_um"]; span = H if L == "M8" else W; ext = W if L == "M8" else H
    for k, net in enumerate(g["nets"]):
        R = rows.get((L, net), [])
        bad_lat = [r for r in R if abs(((r[0] - off) / half) - round((r[0] - off) / half)) > 1e-3 or round((r[0] - off) / half) % 2 != k]
        bad_w = [r for r in R if abs(r[1] - g["width_um"]) > 1e-3]
        cov = collections.defaultdict(float)
        for c, w_, lo, hi in R:
            cov[round(c, 3)] += hi - lo
        exp = [round(off + half * n, 3) for n in range(int((span - off) / half) + 1) if n % 2 == k and off + half * n <= span]
        missing = [c for c in exp if c not in cov]
        short = sorted(((c, round(cov[c], 2)) for c in exp if c in cov and cov[c] < ext * 0.98), key=lambda t: t[1])
        res["layers"][f"{L}:{net}"] = dict(rects=len(R), stripes=len(cov), expected_lattice=len(exp), off_lattice_or_wrong_net=len(bad_lat),
                                          wrong_width=len(bad_w), widths=sorted({round(r[1], 4) for r in R})[:6], missing_lattice=len(missing),
                                          missing_examples=missing[:5], stripes_cover_lt98pct=len(short), short_examples=short[:8],
                                          total_len_um=round(sum(cov.values()), 1))
json.dump(res, open(out, "w"), indent=1); print(json.dumps(res, indent=1))
