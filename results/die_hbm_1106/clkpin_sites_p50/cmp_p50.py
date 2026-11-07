#!/usr/bin/env python3
"""part 50 proof: --clock-pin-entry io.tcl clock pins vs the side's own pin table (release_tree_plan pin_compare) for base
(main) and new (part 50) kits; io.tcl base->new line diff.   cmp_p50.py OUT RTP_DIR"""
import glob, json, re, sys
sys.path.insert(0, sys.argv[2]); import release_tree_plan as T
O = sys.argv[1]
rx = re.compile(r"place_pin -pin_name \{([^}]*)\} -layer (\S+) -location \{(\S+) (\S+)\}")
def io_rows(p):
    out = {}
    for l in open(p):
        m = rx.search(l)
        if m: out[m.group(1)] = (m.group(2), round(float(m.group(3)) * 1000), round(float(m.group(4)) * 1000))
    return out
res = {}
for d in ("base", "new"):
    CE = json.load(open(f"{O}/{d}/clock_entries.json"))
    V = {x["module"]: x for x in json.load(open(f"{O}/views_{d}.json"))["view_list"]}
    for m in ("ot_hbm_idx_qctl_static", "ot_hbm_static_cfg_collar_idx256r", "ot_pdie_serdes_rx_bm3_rest"):
        e = next(e for b in CE.values() if isinstance(b, dict) for e in b.values() if isinstance(e, dict) and e.get("module") == m)
        cp = set(e.get("merged_clock_ports") or []) | ({e["port"]} if e.get("port") else set())
        x = V[m]; io = glob.glob(f"{O}/kits_{d}/{x['view'].replace('@', '_')}/*/io.tcl")[0]
        g = io_rows(io); tab = T.canon_pin_rows(json.load(open(f"{O}/{d}/{x['pins_file']}")))
        c = T.pin_compare({k: g[k] for k in cp}, {k: tab[k] for k in cp})
        res[(d, m)] = (io, g)
        print(d, m, x["view"], "MATCH" if T.pins_equiv(c) else "MISMATCH", {k: v for k, v in c.items() if v},
              {k: (g[k], tab[k]) for k in sorted(cp)})
for m in ("ot_hbm_idx_qctl_static", "ot_hbm_static_cfg_collar_idx256r", "ot_pdie_serdes_rx_bm3_rest"):
    a, b = res[("base", m)][1], res[("new", m)][1]
    print("io.tcl base->new", m, "pins", len(a), len(b), "differ", sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k)))
