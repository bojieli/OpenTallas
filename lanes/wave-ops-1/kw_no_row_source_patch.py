import sys
p = sys.argv[1]
s = open(p).read()
old = '''def select(rows, cfg, die, state, plan_types=None):
    """-> (picked rows in launch order, {reason: [items]})"""
'''
new = '''NO_ROW_SOURCE = "NO-ROW-SOURCE: only_items item with no OWNERS row and no plan_core_items/allowlist row (never launches)"


def no_row_source(rows, d, die, plan_types):
    """WAVE-OPS-1 11-10 (OWNER item A): only_items names the wave can never pick because nothing makes a row for them.
    A row comes from OWNERS.tsv (the item, its class parent '<k>__...', or its core module for '<m>__v<sha12>'), from
    plan_items_from_allowlist (a type in the plan of record) or from plan_core_items (a core in the plan of record).
    18 HBM cores were allowed in only_items but had no OWNERS row and no plan_core_items entry, so they silently never
    launched.  -> sorted list of those items; [] when the plan is unknown (no probe) or there is no allowlist."""
    if plan_types is None or d.get("only_items") is None:
        return []
    known = {r["item"] for r in rows if r["die"] == die}
    cores = set(d.get("plan_core_items") or [])
    out = []
    for item in d.get("only_items") or []:
        if item in known or core_module(item) in known or any(item.startswith(k + "__") for k in known):
            continue
        if item in plan_types and (d.get("plan_items_from_allowlist") or item in cores):
            continue
        out.append(item)
    return sorted(set(out))


def select(rows, cfg, die, state, plan_types=None):
    """-> (picked rows in launch order, {reason: [items]})"""
'''
assert s.count(old) == 1; s = s.replace(old, new)
old2 = '''    skip = {}
    picked = []
    if (d.get("plan_items_from_allowlist") or d.get("plan_core_items")) and plan_types is not None:'''
new2 = '''    skip = {}
    picked = []
    orphans = no_row_source(rows, d, die, plan_types)
    if orphans:
        skip[NO_ROW_SOURCE] = orphans                   # plan_dies() logs it loudly every tick
    if (d.get("plan_items_from_allowlist") or d.get("plan_core_items")) and plan_types is not None:'''
assert s.count(old2) == 1; s = s.replace(old2, new2)
old3 = '''                picks, skip = select(owners, cfg, die, st, names)
                n = capacity(cfg, die, st, status, hub)      # per-die share; the global caps apply below'''
new3 = '''                picks, skip = select(owners, cfg, die, st, names)
                if skip.get(NO_ROW_SOURCE):                  # WAVE-OPS-1 11-10: never silent (18 HBM cores had no row)
                    its = skip[NO_ROW_SOURCE]
                    (AP.log if AP else log)(f"KIT-WAVE NO-ROW-SOURCE {die}: {len(its)} only_items item(s) have no row "
                                            f"source (no OWNERS row, not in plan_core_items / allowlisted plan types) "
                                            f"and can never launch: " + " ".join(its[:40]) + (" ..." if len(its) > 40 else ""))
                n = capacity(cfg, die, st, status, hub)      # per-die share; the global caps apply below'''
assert s.count(old3) == 1; s = s.replace(old3, new3)
open(p, "w").write(s)
print("patched", p)
