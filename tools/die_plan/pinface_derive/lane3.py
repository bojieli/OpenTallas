"""SU-LAT-1 (DIE-QC-97 11-11): give back the s16 +1 pin cycle on the su_l0 x_su_c_i lanes.
usage: python3 -I lane3.py SRC PLAN_IN PLAN_OUT REPORT_JSON MEAS_DIR [BUS=x_su_c_i] [N=3]

Since s19 (SU-CH-1), x_su_c_i u_lane3 is a channel chain. The kit spaces its stations evenly along each
bit's path, so the bus needs N=3 stations instead of 4 (worst bit path / (N+1) <= 400 um, the mk_cand knee
target). Every chain of BUS in every su_l0 type gets N stations, positioned with the mk_cand formula
(j + 1) / (N + 1), the kit's station spacing (one bus = one latency). Each lane with an su_l0 BUS end loses
(old - N) fixed cycles at that end.

Fail-closed checks: every chain must fit N stations, computed on the kit's own geometry:
- channel chains: istation_channel path length / (N+1) <= 403 (KIT_LIMIT_UM);
- L chains: the measured kit-knee need n_kit_sim (pinface_derive measure, MEAS_DIR/<type>.json row of the same
  bus, lane and leaf_um) <= N; a chain with no matching row fails;
- no lane may be in a latency group.
The script writes plan_lane_latency before and after for every changed lane, then runs schema validation."""
import copy, hashlib, json, sys

SRC, PIN, POUT, REP, MD = sys.argv[1:6]
BUS = sys.argv[6] if len(sys.argv) > 6 else "x_su_c_i"
N = int(sys.argv[7]) if len(sys.argv) > 7 else 3
sys.path.insert(0, SRC + "/tools/die_plan")
import gen_phys, istation_channel as IC, schema  # noqa: E402

raw = json.load(open(PIN))
P0 = schema.Plan(copy.deepcopy(raw), path=PIN)
rep = dict(plan_in=hashlib.sha256(open(PIN, "rb").read()).hexdigest()[:12], bus=BUS, N=N, chains=[], lanes={})
L1 = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
old_n = {}
for tn, t in raw["partition_types"].items():
    if "_su_l0__" not in tn:
        continue
    pins = {}
    for name, bit, _ln, x, y, _f in gen_phys.type_pins(P0, tn):
        pins.setdefault(name, {})[int(bit)] = (float(x), float(y))
    b = next(x for x in t["buses"] if x["name"] == BUS)
    for e in t["internal_stations"]:
        if e.get("conn") != "bus:" + BUS:
            continue
        old_n.setdefault(tn, set()).add(len(e["regs_um"]))
        a, z = e["from_um"], e["to_um"]
        k0 = 2 if str(e.get("launch", "")).startswith("face") else 1
        # chain-level regs at (j + 1) / (N + 1) of from_um -> to_um: the kit's own per-bit spacing (is_bits /
        # is_chan_site, L * (k + 1) / (n + 1)), so the G0C chain hop check sees the hop the kit builds
        e["regs_um"] = [[round(a[0] + (z[0] - a[0]) * (j + 1) / (N + 1), 3), round(a[1] + (z[1] - a[1]) * (j + 1) / (N + 1), 3)]
                        for j in range(N)]
        st = pins[BUS] if not e.get("start_core") else {i: tuple(p) for i, p in enumerate(e["start_um"])}
        lx, ly = e["leaf_um"]
        if e.get("leg_order") == "channel":
            nb, d = max(st) + 1, ("in" if k0 == 2 else "out")
            worst = max(IC.worst_hop(px, py, lx, ly, b["face"], d, *e["channel_um"], bit, nb, N) for bit, (px, py) in st.items())
            need = None
        else:
            core = "+".join(e["core"]) if isinstance(e["core"], list) else e["core"]
            rows = [r for r in json.load(open(f"{MD}/{tn}.json"))["rows"] if "err" not in r and r["bus"] == BUS
                    and r["lane"] == core and [round(v, 2) for v in r["leaf_um"]] == [round(v, 2) for v in e["leaf_um"]]]
            if len(rows) != 1:
                raise SystemExit(f"{tn} {BUS} {core}: {len(rows)} measure rows match (need 1)")
            worst, need = None, rows[0]["n_kit_sim"]
        rep["chains"].append(dict(type=tn, core=e["core"], leg_order=e.get("leg_order", "normal_first"), worst_hop_um=worst,
                                  kit_knee_need=need))
for c in rep["chains"]:
    if c["worst_hop_um"] is not None and c["worst_hop_um"] > IC.KIT_LIMIT_UM:
        raise SystemExit(f"chain {c} exceeds {IC.KIT_LIMIT_UM} um at N={N}")
    if c["kit_knee_need"] is not None and c["kit_knee_need"] > N:
        raise SystemExit(f"chain {c} needs more than N={N} stations")

groups = {l for g in raw.get("latency_groups", []) for l in g.get("lanes", [])}
P = schema.Plan(copy.deepcopy(raw), path=PIN)
lat0 = {}
for ln in raw["lanes"]:
    a, z = P.ports[ln["ports"][0]], P.ports[ln["ports"][-1]]
    ends = [(P.parts.get(a["src"]["part"], {}).get("type"), a["src"].get("bus")), (P.parts.get(z["dst"]["part"], {}).get("type"), z["dst"].get("bus"))]
    drop = sum(max(old_n[t]) - N for t, bb in ends if t in old_n and bb == BUS)
    if drop:
        if ln["id"] in groups:
            raise SystemExit(f"lane {ln['id']} is in a latency group")
        lat0[ln["id"]] = P0.lane_latency(ln["id"])["cycles"]
        ln["fixed_cycles"] = int(ln["fixed_cycles"]) - drop
        rep["lanes"][ln["id"]] = dict(fixed=[ln["fixed_cycles"] + drop, ln["fixed_cycles"]], ends=ends)
Q = schema.Plan(copy.deepcopy(raw), path=PIN)
for l in rep["lanes"]:
    rep["lanes"][l]["latency_cycles"] = [lat0[l], Q.lane_latency(l)["cycles"]]
json.dump(raw, open(POUT, "w"))
open(POUT, "a").write("\n")
errs = schema.validate(json.load(open(POUT))) or []
rep["validate_errors"] = len(errs)
rep["validate_first"] = errs[:5]
json.dump(rep, open(REP, "w"), indent=1)
print(json.dumps(dict(lanes=len(rep["lanes"]), chains=len(rep["chains"]), validate=len(errs)), indent=None))
for l, v in sorted(rep["lanes"].items()):
    print(l, v["fixed"], v["latency_cycles"])
sys.exit(1 if errs else 0)
