"""HBM-HUB-RTL-1 11-12: give glue cells that exist only in the NEW elaboration (a source fix created them, so no old
name maps to them) the partition of the old map cells of the same instance and the same source line.

    python3 -I map_fill.py MAP_IN NEW_ASBUILT MAP_OUT TOP INST_REGEX

A new cell <inst>.<cell> (cell name with its source path stripped, as map keys are written) that is not a map key takes
the partition of the existing keys <inst>.$... whose name carries the same file:line (none: those within +-8 lines of
that file); it must be ONE partition, else it is
reported and left unmapped (the bind then fails closed with UNMAPPED).  List entries [part, local] keep their format: the
local name is the sibling's local prefix + the new cell name.
"""
import collections
import json
import re
import sys

map_in, asb, map_out, top, inst_rx = sys.argv[1:6]
M = json.load(open(map_in))
P = M["parts"]
N = json.load(open(asb))["modules"]
norm = lambda n: "$".join(p.rsplit("/", 1)[1] if "/" in p else p for p in n.split("$"))
line = lambda n: (re.search(r"([\w.]+\.s?v):(\d+)", n) or [None])[0]


def mod_of(path):
    m = top
    for seg in path.split("."):
        c = N[m]["cells"].get(seg)
        if c is None or c["type"] not in N:
            return None
        m = c["type"]
    return m


insts = sorted({k.split(".$", 1)[0] for k in P if ".$" in k and re.fullmatch(inst_rx, k.split(".$", 1)[0])})
added, miss = collections.Counter(), []
for inst in insts:
    mod = mod_of(inst)
    if mod is None:
        miss.append((inst, "no module"))
        continue
    # source line of a cell: its own src attribute in the new elaboration (procdff / procmux names carry no line),
    # else the file:line in its name
    src = {f"{inst}.{norm(n)}": line(re.sub(r"[^|:]*/", "", c.get("attributes", {}).get("src") or "").split("|")[0])
           for n, c in N[mod]["cells"].items() if "$" in n}
    lof = lambda k: src.get(k) or line(k)
    sib = collections.defaultdict(list)
    for k, v in P.items():
        if k.startswith(inst + ".$"):
            sib[lof(k)].append((k, v))
    for n in N[mod]["cells"]:
        if "$" not in n:
            continue
        full = f"{inst}.{norm(n)}"
        if full in P:
            continue
        cand = sib.get(lof(full), [])
        if not cand and lof(full):         # a line the old source had no cell on: the old cells within +-8 lines
            f, l0 = lof(full).rsplit(":", 1)
            cand = [kv for L, kvs in sib.items() if L and L.rsplit(":", 1)[0] == f and abs(int(L.rsplit(":", 1)[1]) - int(l0)) <= 8
                    for kv in kvs]
        parts = {v if isinstance(v, str) else v[0] for _, v in cand}
        if len(parts) != 1 or lof(full) is None:
            miss.append((full, sorted(parts)))
            continue
        k0, v0 = cand[0]
        if isinstance(v0, str):
            P[full] = v0
        else:
            i = v0[1].find(".$")             # local = the sibling's local prefix + the new cell name
            assert i >= 0 or v0[1].startswith("$"), (k0, v0)
            P[full] = [v0[0], v0[1][:i + 1] + norm(n)]
        added[(inst, lof(full))] += 1
M["note"] = M.get("note", "") + f" | HBM-HUB-RTL-1 map_fill: {sum(added.values())} new-source glue cells by instance + source line"
json.dump(M, open(map_out, "w"), indent=1)
print(json.dumps({"added": sum(added.values()), "by": [[list(k), v] for k, v in sorted(added.items())][:24],
                  "miss": len(miss), "miss_first": miss[:8]}))
sys.exit(1 if miss else 0)
