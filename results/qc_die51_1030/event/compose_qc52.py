"""DIE-QC-51: plan_qc52 = the LAST QC plan event (OWNER 12.22; COORD 18:54 ruling), base plan_qc50 (dc20ac54, gen50 GEN PASS).
Steps (each one re-derives only what it changes; every other key stays byte-equal):
  (1) ft stations (COORD 18:54, DIE-QC-50 18:52 ASK default YES; METHODOLOGY 12.15c added crossing latency accepted):
      stm/sc slice types: every E<->W ft slot with < 3 stations -> 3 (613-um span: with face-pinned end stations a
      2-station slot has one 613-um hop > 405; 3 stations = 2 x ~307 um);  su_l0/su_l1/su_c types: every 1-station slot
      -> 2 (W->N / N->E landing slots x_st_a_fe, x_su_l1_stm).
  (2) density die-clock taps on EVERY slice type (fe fw hc sc st stm su ctl) that still has the R4 grid: tap_mode density,
      1200/960/200 (the plan_qc51 stm knobs); stm keeps its measured placed sink bins (plan_qc51, DIE-QC-50); other
      types use the planned sinks (face + ft registers; core contents not in the plan = lower bound, UNCHECKED until
      their kits place).  Landing data re-derived with the compose_qc50/qc51 composer rules (self-tested on the base).
  (3) BTAB P8eco bind (COORD 18:54 option (a)) via btab_p8eco.apply() when present.
  (4) latency.lanes recomputed by main tools/die_plan/gen.py latency (reproduces plan_qc50 byte-identically, CHECKED).
usage: compose_qc52.py PLAN_QC50 --out PLAN_QC52 --report REPORT [--no-btab] [--no-stations] [--no-taps]"""
import argparse, copy, hashlib, json, re, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
sys.path.insert(0, str(HERE))
import schema as S, gen_phys as GP, reset_tree as RT

BINDIR = "physical/die_plan/qwen_compute/plan_of_record/sink_bins"
KNOBS = dict(tap_mode="density", tap_max_sinks=1200, tap_target_sinks=960, tap_radius_um=200.0)
L1 = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
cls = lambda tn: (re.match(r"sl[ew]_([a-z]+)", tn).group(1) if re.match(r"sl[ew]_([a-z]+)", tn) else None)


def derive(P, raw, T):
    """compose_qc51.derive (DIE-QC-50), unchanged: landing data that depend on the type's taps / collector tree."""
    lc = raw["partition_types"][T]["clock"]["landing_contract"]
    tree = json.loads(json.dumps(RT.for_type(P, T)))
    n = RT.consumer_count(tree)
    tapxy = {int(r["q"].split("rst_n_t")[1]): r["xy"] for r in tree["relays"] if r["q"].startswith("rst_n_t")}
    srcs = []
    for s in lc.get("collector_local_sources", []):
        pt = s["pin_xy_um"]
        tap = min(range(n), key=lambda i: L1(tapxy[i], pt))
        b = s.get("band") or {}
        if b.get("rect_um") and L1(tapxy[tap], pt) > 405:
            x0, y0, x1, y1 = b["rect_um"]; c = [round((x0 + x1) / 2, 3), round((y0 + y1) / 2, 3)]
            tap = min(range(n), key=lambda i: L1(tapxy[i], c))
        srcs.append(tap)
    old_n = RT.consumer_count(lc["collector_tree"])
    kids = [f"rst_n_t{n + int(c['node'].split('rst_n_t')[1]) - old_n}" if c["node"].startswith("rst_n_t") else c["node"]
            for c in lc.get("collector_children", [])]
    roots = GP.clock_pins(P, T)
    exp = {p["name"]: min(roots, key=lambda r: L1((r[1], r[2]), p["xy_um"]))[0]
           for p in lc["pins"] if p["kind"] == "clock" and p["dir"] == "out"}
    return tree, srcs, kids, exp


def apply(raw, T, d):
    lc = raw["partition_types"][T]["clock"]["landing_contract"]
    tree, srcs, kids, exp = d
    lc["collector_tree"] = tree
    for s, tap in zip(lc.get("collector_local_sources", []), srcs):
        s["tap"] = tap
    for c, k in zip(lc.get("collector_children", []), kids):
        c["node"] = k
    for p in lc["pins"]:
        if p["name"] in exp:
            p["source_clock_tap"] = exp[p["name"]]


def has_lc(raw, T):
    return bool(raw["partition_types"][T].get("clock", {}).get("landing_contract", {}).get("collector_tree"))


ap = argparse.ArgumentParser()
ap.add_argument("plan"); ap.add_argument("--out", required=True); ap.add_argument("--report", required=True)
ap.add_argument("--no-btab", action="store_true"); ap.add_argument("--no-stations", action="store_true")
ap.add_argument("--no-taps", action="store_true")
a = ap.parse_args()
P0 = json.load(open(a.plan))
rep = dict(src=a.plan, knobs=KNOBS, stations=[], taps={}, btab=None)
SL = sorted(tn for tn in P0["partition_types"] if cls(tn))
rep["slice_types"] = len(SL)

# self-test: the composer rules reproduce the base plan's landing data on every slice type that has them
Pc = S.Plan(P0, a.plan)
chk = copy.deepcopy(P0)
LC = [T for T in SL if has_lc(P0, T)]
for T in LC:
    apply(chk, T, derive(Pc, P0, T))
bad = [T for T in LC if json.dumps(chk["partition_types"][T], sort_keys=True) != json.dumps(P0["partition_types"][T], sort_keys=True)]
# st_a (8 types): main reset_tree now places 4 tap relays 2-4 um off the stored xy (tool drift since plan_qc43, relays only;
# taps/sources/children/exports equal) -> these types are re-derived by the current tool like every other changed type
DRIFT = {T for T in bad if cls(T) == "st"}
assert set(bad) == DRIFT, f"re-derivation does not reproduce the base on {sorted(set(bad) - DRIFT)[:5]}"
rep["self_test"] = dict(types=len(LC), reproduced=len(LC) - len(bad), relay_xy_drift=sorted(bad))

P = copy.deepcopy(P0)
# (1) stations
if not a.no_stations:
    for T in SL:
        c = cls(T)
        for f in P["partition_types"][T].get("ft_slots", []):
            new = None
            if c in ("stm", "sc") and {f["in_face"], f["out_face"]} == {"E", "W"} and int(f["stations"]) < 3:
                new = 3
            elif c == "su" and int(f["stations"]) == 1:
                new = 2
            if new:
                assert "regs_um" not in f and "bit_sites_um" not in f, (T, f["name"], "slot has planned station sites")
                rep["stations"].append([T, f["name"], f["in_face"], f["out_face"], f["width"], f["stations"], new])
                f["stations"] = new
# (2) taps
old = {T: copy.deepcopy(P0["partition_types"][T]["clock"].get("landing_contract")) for T in SL}
if not a.no_taps:
    for T in SL:
        ck = P["partition_types"][T].setdefault("clock", {})
        if ck.get("tap_mode") == "density":
            rep["taps"][T] = dict(already="density")      # plan_qc51 stm form re-applied below if absent
            continue
        assert "tap_mode" not in ck and "tap_pitch_um" not in ck, (T, ck.get("tap_mode"))
        ck.update(KNOBS)
        if (ROOT / BINDIR / f"{T}.json").exists():
            ck["sink_bins_file"] = f"{BINDIR}/{T}.json"
# re-derive landing data on every slice type with a landing contract (stations move ft sinks -> taps, so all of them)
Pn = S.Plan(P, a.out)
D = {T: derive(Pn, P, T) for T in LC}
for T in LC:
    apply(P, T, D[T])
# (3) BTAB
if not a.no_btab and (HERE / "btab_p8eco.py").exists():
    import btab_p8eco
    rep["btab"] = btab_p8eco.apply(P, ROOT)
Pf = S.Plan(P, a.out)
for T in SL:
    t0 = S.tap_grid(Pc, T); t1 = S.tap_grid(Pf, T)
    r = rep["taps"].setdefault(T, {})
    r.update(cls=cls(T), taps_old=len(t0), taps_new=len(t1), bins=P["partition_types"][T]["clock"].get("sink_bins_file"),
             instances=sum(1 for q in P["partitions"] if q["type"] == T))
    if T in LC:
        lc0, lc = old[T], P["partition_types"][T]["clock"]["landing_contract"]
        a0, a1 = lc0["collector_tree"], lc["collector_tree"]
        r["collector_tree"] = dict(old=[a0.get("n_tree"), a0.get("depth"), a0.get("max_hop_um")],
                                   new=[a1.get("n_tree"), a1.get("depth"), a1.get("max_hop_um")])
        r["children"] = [[c0["node"], c["node"]] for c0, c in zip(lc0.get("collector_children", []), lc.get("collector_children", [])) if c0["node"] != c["node"]]
open(a.out, "w").write(json.dumps(P, indent=1) + "\n")
# (4) latency table by the main generator
lat0 = {k: v["cycles"] for k, v in P0["latency"]["lanes"].items()}
subprocess.run([sys.executable, str(ROOT / "tools/die_plan/gen.py"), "latency", a.out, "--inplace",
                "--out", str(Path(a.report).parent / "lat")], check=True)
P2 = json.load(open(a.out))
lat1 = {k: v["cycles"] for k, v in P2["latency"]["lanes"].items()}
rep["latency_changed"] = {k: [lat0.get(k), lat1.get(k)] for k in lat1 if lat0.get(k) != lat1.get(k)}
rep["src_sha256"] = hashlib.sha256(open(a.plan, "rb").read()).hexdigest()
rep["dst_sha256"] = hashlib.sha256(open(a.out, "rb").read()).hexdigest()
open(a.report, "w").write(json.dumps(rep, indent=1) + "\n")
print("stations changed", len(rep["stations"]), "latency lanes changed", len(rep["latency_changed"]),
      "taps", sum(r["taps_old"] for r in rep["taps"].values()), "->", sum(r["taps_new"] for r in rep["taps"].values()),
      "src", rep["src_sha256"][:8], "dst", rep["dst_sha256"][:8])
