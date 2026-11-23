"""Warn about placed plan types above the native flat standard-cell count reference."""

from adv_density import base_type, cells_for, load_cache
from cell_cap import SPLIT_CELLS


def findings(raw, plan_path, tree=None, cells_cache=None, **_kw):
    die = (raw.get("die") or {}).get("name")
    cache, _ = load_cache(cells_cache)
    records = ((cache or {}).get("cells") or {}).get(die) or {}
    by_base = {}
    for name in records:
        by_base.setdefault(base_type(name), []).append(name)

    types = raw.get("partition_types") or {}
    placed = {part.get("type") for part in raw.get("partitions") or [] if isinstance(part, dict)}
    hits = []
    measured = estimated = unknown = 0
    for name, ptype in types.items():
        if ptype.get("hard") or (placed and name not in placed):
            continue
        cells, basis, _, _ = cells_for(name, ptype, records, by_base)
        if cells is None:
            unknown += 1
            continue
        if basis == "kit":
            measured += 1
            basis = "retained kit count"
        else:
            estimated += 1
            basis = f"estimate from {basis}"
        if cells > SPLIT_CELLS:
            hits.append((cells, name, basis))

    out = [
        f"WARN ADV-CELLCAP {name}: {cells:,} standard cells ({basis}) exceeds the {SPLIT_CELLS:,} reference"
        for cells, name, basis in sorted(hits, key=lambda hit: (-hit[0], hit[1]))
    ]
    if measured or estimated or unknown:
        out.append(
            f"WARN ADV-CELLCAP summary: {len(hits)} above reference, {measured} retained kit counts, "
            f"{estimated} estimates, {unknown} unmeasured"
        )
    return out
