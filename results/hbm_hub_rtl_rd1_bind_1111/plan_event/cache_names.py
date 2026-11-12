"""HBM-HUB-RTL-1 11-12 (DIE-HBM-100: the cached Nov-8 elaboration is canonical): give the cells of a fresh elaboration
the names the cached as-built gave the same cells, so the bound RTL (wire / instance names) matches the canonical binds.

    python3 -I cache_names.py CACHED_ASBUILT FRESH_ASBUILT OUT_ASBUILT RECEIPT

Per module present in both (same module name): cells with a '$' name are matched by key = (type, src with paths
stripped, parameters, port widths), by rank of the yosys number inside each key; a key renames only when both sides
have the same count, and only names that are not already used.  Nets named <old cell>_<suffix> follow.  Cells that
exist only in the fresh elaboration (source fixes) keep their names.  Connections are not touched (names only).
"""
import json
import re
import sys

cached, fresh, out, receipt = sys.argv[1:5]
C = json.load(open(cached))["modules"]
B = json.load(open(fresh))
N = B["modules"]
num = lambda n: int(m.group(1)) if (m := re.search(r"\$(\d+)$", n)) else -1


def key(c):
    src = re.sub(r"[^|:]*/", "", c.get("attributes", {}).get("src") or "")
    return (c["type"], src, json.dumps(c.get("parameters", {}), sort_keys=True),
            json.dumps({k: len(v) for k, v in c.get("connections", {}).items()}, sort_keys=True))


rec = {"modules": 0, "renamed": 0, "kept_count_mismatch": 0, "already": 0}
for mn, m in N.items():
    if mn not in C or not m.get("cells"):
        continue
    idx = {}
    for side, mod in (("c", C[mn]), ("n", m)):
        for n, c in mod["cells"].items():
            if "$" in n:
                idx.setdefault(key(c), {"c": [], "n": []})[side].append(n)
    ren = {}
    for k, v in idx.items():
        if len(v["c"]) != len(v["n"]):
            rec["kept_count_mismatch"] += len(v["n"])
            continue
        for o, c in zip(sorted(v["n"], key=num), sorted(v["c"], key=num)):
            if o == c:
                rec["already"] += 1
            else:
                ren[o] = c
    if not ren:
        continue
    used = set(m["cells"]) - set(ren)
    ren = {o: c for o, c in ren.items() if c not in used}
    m["cells"] = {ren.get(n, n): c for n, c in m["cells"].items()}
    nets = {}
    for n, v in m["netnames"].items():
        if "_" in n:
            base, suf = n.rsplit("_", 1)
            if base in ren and suf.isidentifier():
                n = ren[base] + "_" + suf
        nets[n] = v
    if len(nets) == len(m["netnames"]):
        m["netnames"] = nets
    rec["modules"] += 1
    rec["renamed"] += len(ren)
json.dump(B, open(out, "w"))
json.dump(rec, open(receipt, "w"), indent=1)
print(json.dumps(rec))
