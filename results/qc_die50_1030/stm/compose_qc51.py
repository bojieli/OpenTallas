"""DIE-QC-50/stm: plan_qc51 = plan_qc49 + density clock-tap split on the 11 stm types (COORD 17:50 ruling, QC-KITS-AA ASK).

Measured failure (QC-KITS-AA 17:49, plan_qc49 placed kits, AUTO-GEOM CHECKED): every stm type has the R4 400-um grid,
2 x 4 = 8 taps for 50-64k flops -> clock_tap_sinks 12.5k-15.6k per tap (limit 1500) and clock_reach 320 (limit 220).
Delta (OWNER decision 5 density taps; coll_ftm precedent in this plan): clock.tap_mode "density", tap_max_sinks 1200,
tap_target_sinks 960, tap_radius_um 200, sink_bins_file = the type's MEASURED placed die-clock sinks (10.8-um bins,
sink_bins/<type>.json; 2 types whose kit was still placing use the bins of the same-base placed variant, named in the
file).  Taps are computed by the main tools (schema.tap_grid -> taps.density_taps).
Dependent landing data are re-derived with the composer rules exactly as DIE-QC-49 compose_qc50.py (self-tested on
plan_qc49 first: the re-derivation must reproduce the stored values byte-for-byte):
  * landing_contract.collector_tree = reset_tree.for_type(P, T);
  * collector_local_sources[].tap = nearest tap relay to the ring pin (band centre if > 405 um);
  * collector_children[].node = rst_n_t{consumer_count + k};
  * forwarded-out clock pins source_clock_tap = nearest normal clock tap.
Outline, buses, ft slots, bands, hard cores, ports, lanes and every non-stm type are unchanged.
usage: compose_qc51.py PLAN_QC49 --out PLAN_QC51 --report REPORT"""
import argparse, copy, hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools" / "die_plan"))
import schema as S, gen_phys as GP, reset_tree as RT

STM = ['slw_stm_v3', 'sle_stm_v3', 'slw_stm_v1__cle34a73c3', 'slw_stm_v1__cl05fc43f7__cl2086fa2c',
       'slw_stm_v1__cl05fc43f7__cl389df4e9', 'slw_stm_v2__cl1ca9c415', 'slw_stm_v2__cl9beb65e6',
       'sle_stm_v1__cl27746664', 'sle_stm_v1__clbe630b9c', 'sle_stm_v2__cl7b3062fa', 'sle_stm_v2__cl55be2264']
BINDIR = "physical/die_plan/qwen_compute/plan_of_record/sink_bins"
KNOBS = dict(tap_mode="density", tap_max_sinks=1200, tap_target_sinks=960, tap_radius_um=200.0)
L1 = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])


def derive(P, raw, T):
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


ap = argparse.ArgumentParser()
ap.add_argument("plan"); ap.add_argument("--out", required=True); ap.add_argument("--report", required=True)
a = ap.parse_args()
P0 = json.load(open(a.plan))
rep = dict(types={}, knobs=KNOBS)
# self-test on the source plan (all 11 types, one Plan object)
chk = copy.deepcopy(P0)
Pc = S.Plan(P0, a.plan)
for T in STM:
    apply(chk, T, derive(Pc, P0, T))
assert json.dumps(chk, sort_keys=True) == json.dumps(P0, sort_keys=True), "re-derivation does not reproduce plan_qc49"
rep["self_test"] = "composer-rule re-derivation reproduces plan_qc49 landing data of all 11 stm types byte-identically"
P = copy.deepcopy(P0)
for T in STM:
    ck = P["partition_types"][T]["clock"]
    assert "tap_mode" not in ck and "tap_pitch_um" not in ck, (T, ck.get("tap_mode"))
    ck.update(KNOBS); ck["sink_bins_file"] = f"{BINDIR}/{T}.json"
    # ring bands are NOT clock keep-outs: die_clock/check treat type clock.keepouts_um as hard cores, which put 16
    # die lane stations "inside a hard core" (G0C +16 street_die_leg WARN, measured 18:5x) -> taps may sit on a band
old = {T: copy.deepcopy(P0["partition_types"][T]["clock"]["landing_contract"]) for T in STM}
Pn = S.Plan(P, a.out)
D = {T: derive(Pn, P, T) for T in STM}
for T in STM:
    apply(P, T, D[T])
Pf = S.Plan(P, a.out)
for T in STM:
    lc0, lc = old[T], P["partition_types"][T]["clock"]["landing_contract"]
    t0, t1 = lc0["collector_tree"], lc["collector_tree"]
    taps0 = S.tap_grid(Pc, T); taps1 = S.tap_grid(Pf, T)
    r = dict(taps_old=len(taps0), taps_new=len(taps1), tap_xy=[[n, round(x, 3), round(y, 3)] for n, x, y in taps1],
             collector_tree=dict(old=dict(n_tree=t0.get("n_tree"), depth=t0.get("depth"), max_hop_um=t0.get("max_hop_um")),
                                 new=dict(n_tree=t1.get("n_tree"), depth=t1.get("depth"), max_hop_um=t1.get("max_hop_um"))),
             tap_depth_max=dict(old=max(t0.get("tap_depth", {0: 0}).values()), new=max(t1.get("tap_depth", {0: 0}).values())),
             local_source_taps=[[s0["name"], s0["tap"], s["tap"]] for s0, s in zip(lc0.get("collector_local_sources", []), lc.get("collector_local_sources", []))],
             children=[[c0["part"], c0["node"], c["node"]] for c0, c in zip(lc0.get("collector_children", []), lc.get("collector_children", []))],
             export_taps=[[p0["name"], p0.get("source_clock_tap"), p.get("source_clock_tap")] for p0, p in zip(lc0["pins"], lc["pins"]) if p0.get("source_clock_tap") != p.get("source_clock_tap")],
             instances=[q["name"] for q in P["partitions"] if q["type"] == T])
    rep["types"][T] = r
    print(T, "taps", r["taps_old"], "->", r["taps_new"], "tree", r["collector_tree"], "kids", r["children"], flush=True)
open(a.out, "w").write(json.dumps(P, indent=1) + "\n")
rep["src_sha256"] = hashlib.sha256(open(a.plan, "rb").read()).hexdigest()
rep["dst_sha256"] = hashlib.sha256(open(a.out, "rb").read()).hexdigest()
open(a.report, "w").write(json.dumps(rep, indent=1) + "\n")
print("src", rep["src_sha256"][:8], "dst", rep["dst_sha256"][:8])
