#!/usr/bin/env python3
"""S81 relay-bay k -> k' plan latency event (DIE-S81-51 ruling 11-03 GO; TOK-VERIFY-1 class fix: the plan is the
latency source of truth, so gen.py latency / lat_pkg / bind carry the relay-bay cycles).

    delta_relay_bay_k_1103.py PLAN EVENT.json [OUT]

For every slot of EVENT (h2_2249/relay_bay_cycle_event_1103.json, relay_bay_300 on slice_station*) with extra cycles:
  * ft_slots[].stations k -> k' (re-derived here from the kit pin centroids, gen_phys.type_pins = the kit io.tcl, and
    asserted equal to the event: relay_bay.py on the built kit then sees k == k' and keeps the plan sites);
  * regs_um = the relay-bay sites (relay_bay.path_points: equal spacing on the in->out Manhattan path, first leg along
    the in-face normal; landed i/k', plain i/(k'-1)), every hop <= 300 um;
  * bit_sites_um / bit_site_cell_um dropped (relay_bay drops them too: per-bit sites of the old k no longer apply).
Then latency.lanes is republished from the plan (gen.latency_table: stations of the crossed slots + R8 group pads).
Writes main's plan format (added_tap_recentre.dumps_like).

Follow-up applied for the 11-03 event (strict bind: slice_station__t12 explicit tap clk_t6 radius 154.2 > 150 after the
re-sited stations): tools/die_plan/added_tap_recentre.py PLAN --out PLAN --types slice_station__t12 --sidecar
h2_2249/landed_sidecar_h2.json --sidecar-out h2_2249/landed_sidecar_h2.json -> one move clk_t6 [65.824, 613.4366] ->
[66.69, 617.76] (5.2 um), 1 of 76 reset relays re-sited, collector tree republished (plan + sidecar)."""
import collections, json, math, sys
from pathlib import Path
TD = Path(__file__).resolve().parents[3] / "tools/die_plan"
sys.path.insert(0, str(TD))
import added_tap_recentre as AT, schema as S, gen_phys as G, gen, relay_bay as RB

src, evp = sys.argv[1], sys.argv[2]
out = sys.argv[3] if len(sys.argv) > 3 else src
S0 = open(src).read(); raw = json.loads(S0); P = S.Plan(raw, src)
ev = json.load(open(evp)); hop = float(ev["max_hop_um"])
old_lat = {k: v["cycles"] for k, v in raw["latency"]["lanes"].items()}
n_slots = 0
for tn, ss in sorted(ev["slots"].items()):
    pins = collections.defaultdict(list)
    for name, _b, _l, x, y, _f in G.type_pins(P, tn):
        pins[name].append((x, y))
    cen = {k: (sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v)) for k, v in pins.items()}
    slots = {s["name"]: s for s in raw["partition_types"][tn]["ft_slots"]}
    for sn, z in sorted(ss.items()):
        s = slots[sn]
        assert int(s.get("stations", 1)) == z["k"], (tn, sn, "plan k differs from the event")
        if not z["extra_cycles"]:
            continue
        A, B = cen[sn + "_i"], cen[sn + "_o"]; L = RB.dist(A, B); nn = math.ceil(L / hop - 1e-9)
        k2 = max(z["k"], nn) if z["landed"] else max(z["k"], nn + 1)
        assert k2 == z["k_new"], (tn, sn, k2, z["k_new"])
        n = k2 if z["landed"] else k2 - 1
        sites = RB.path_points(A, B, s["in_face"], [j / n for j in range(k2)])
        chain = ([A] + sites[1:] + [B]) if z["landed"] else ([A] + sites[1:])
        assert all(RB.dist(p, q) <= hop + 1e-6 for p, q in zip(chain, chain[1:])), (tn, sn, "hop > max")
        s["stations"] = k2
        s["regs_um"] = [[round(x, 4), round(y, 4)] for x, y in sites]
        s.pop("bit_sites_um", None); s.pop("bit_site_cell_um", None)
        n_slots += 1
errs = S.validate(raw)
if errs:
    raise SystemExit("plan invalid after the event:\n  " + "\n  ".join(errs[:20]))
P2 = S.Plan(raw, src)
tab = gen.latency_table(P2)
raw["latency"] = {"lanes": json.loads(json.dumps(tab))}
open(out, "w").write(AT.dumps_like(raw, S0))
d = {k: tab[k]["cycles"] - old_lat.get(k, 0) for k in tab}
print(json.dumps(dict(slots_changed=n_slots, lanes_changed=sum(1 for v in d.values() if v),
                      lanes_by_delta=dict(sorted(collections.Counter(v for v in d.values() if v).items())),
                      cycles_added=sum(d.values()), negative=[k for k, v in d.items() if v < 0][:5])))
