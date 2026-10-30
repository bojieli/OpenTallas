# openroad -python read-only probe: which native 3_place instances occupy the admitted H2 tree-cell sites. env PLACE SLICE OUT
import json, os, re
from collections import defaultdict
import odb
U = 1000
db = odb.dbDatabase.create(); odb.read_db(db, os.environ["PLACE"]); b = db.getChip().getBlock()
sl = json.load(open(os.environ["SLICE"])); cp = sl["cell_placements"]
seq = re.compile(r"DFF|DHL|DLL|SDF|ICG|ASYNC", re.I)
rows = defaultdict(list)
for i in b.getInsts():
    m = i.getMaster()
    if not i.isPlaced(): continue
    bb = i.getBBox()
    # index by row span in 270-dbu rows
    for ry in range(bb.yMin() // 270, (bb.yMax() - 1) // 270 + 1):
        rows[ry].append((bb.xMin(), bb.xMax(), i.getName(), m.getName(), m.isBlock(), m.getType()))
res = dict(cells=0, blocked=0, blocked_by_seq=0, blocked_by_macro=0, blocked_by_other_fixed=0, blocked_by_comb=0, examples=[])
for n, c in cp.items():
    w = db.findMaster(c["master"]).getWidth(); h = db.findMaster(c["master"]).getHeight()
    x0 = int(round(c["origin_um"][0] * U)); y0 = int(round(c["origin_um"][1] * U)); x1 = x0 + w; y1 = y0 + h
    res["cells"] += 1
    hits = set()
    for ry in range(y0 // 270, (y1 - 1) // 270 + 1):
        for (a, z, nm, mn, blk, ty) in rows[ry]:
            if a < x1 and z > x0: hits.add((nm, mn, blk, ty))
    if not hits: continue
    res["blocked"] += 1
    kinds = set()
    for nm, mn, blk, ty in hits:
        if blk: kinds.add("macro")
        elif seq.search(mn): kinds.add("seq")
        elif ty in ("CORE_WELLTAP", "CORE_TIEHIGH", "CORE_TIELOW", "ENDCAP", "CORE_ANTENNACELL") or mn.startswith("TAPCELL"): kinds.add("fixed")
        else: kinds.add("comb")
    for k, key in (("seq", "blocked_by_seq"), ("macro", "blocked_by_macro"), ("fixed", "blocked_by_other_fixed"), ("comb", "blocked_by_comb")):
        if k in kinds: res[key] += 1
    if len(res["examples"]) < 15: res["examples"].append([n, sorted(f"{nm}:{mn}" for nm, mn, _, _ in hits)[:4]])
json.dump(res, open(os.environ["OUT"], "w"), indent=1)
print("H2G1_SITE_PROBE", json.dumps({k: v for k, v in res.items() if k != "examples"}))
