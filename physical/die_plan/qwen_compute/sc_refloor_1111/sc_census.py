"""SC-REFLOOR-1: census of the sl_sc family in a QC plan: ft slots, buses, cores, die positions, neighbours."""
import json, sys, collections
p = json.load(open(sys.argv[1]))
T = p["partition_types"]
sc = sorted(n for n in T if "_sc_" in n)
parts = p["partitions"]
by_type = collections.defaultdict(list)
for q in parts:
    by_type[q["type"]].append(q)
for n in sc:
    t = T[n]
    W, H = t["outline_um"]
    print(f"\n=== {n} outline {W}x{H} ft_track_frac {t.get('ft_track_frac')} insts {[ (q['name'], q['origin_um'], q.get('orient')) for q in by_type[n]]}")
    for c in t.get("hard_cores") or []:
        print("  core", c.get("inst"), c.get("type") or c.get("module"), c["origin_um"], c["outline_um"], c.get("orient"))
    tot = collections.Counter()
    for s in t["ft_slots"]:
        k = s["in_face"] + ">" + s["out_face"]
        tot[k] += s["width"]
        regs = s.get("regs_um") or []
        print(f"  ft {s['name']:<14} {k} w={s['width']:<5} st={s.get('stations')} lay={s.get('layers')} outwin={s.get('out_window_um')} inwin={s.get('in_window_um')} regs={[tuple(round(v,1) for v in r) for r in regs]}")
    print("  ft totals", dict(tot), "sum", sum(tot.values()))
    bt = collections.Counter()
    for b in t["buses"]:
        bt[b["face"] + ":" + b["dir"]] += b["width"]
    print("  bus totals", dict(bt), "sum", sum(bt.values()))
    for b in t["buses"]:
        if b["width"] >= 100:
            print(f"   bus {b['name']:<16} {b['dir']:<3} {b['face']} w={b['width']} win={b.get('window_um')} lay={b.get('layers')}")
    other = {k: (v if not isinstance(v, (list, dict)) else f"<{type(v).__name__} {len(v)}>") for k, v in t.items() if k not in ("ft_slots", "buses", "hard_cores")}
    print("  other", other)
