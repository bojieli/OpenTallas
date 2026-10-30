"""DIE-QC-49/collft: plan_qc50 = plan_qc49 + coll_ft__cla4a25d77 eight-entry RCLK clock taps (brief goal 5).

Source: Codex packet 515014cc720 results/collft_clock_architecture_0336 (eight_entry_proposal.json.gz,
required_config clock.tap_mode explicit / tap_max_sinks 1500 / tap_radius_um 200; per-port local xy).
FLOW-9 core_forest (8bc5475ee9f, on main f2b1e4505) is the slice-side multi-root contract; this delta is the PLAN side:
the type's R4 grid (6 taps clk..clk_t5 at 196.6/589.7 x 165.6/496.8/828) becomes 8 explicit taps clk..clk_t7 at the
Codex entry points, so each instance (coll_f1, coll_f2 = the only instances of the type; both R0) gets 8 die tap
bindings (2 new) with the 6 existing ones moved.  Partition clock ports are plan-generated (gen_rtl tap_grid): the 2 new
ports need no hand RTL.  The informational 'glue' tap entry is dropped (explicit mode: clock.taps IS the explicit table).

Dependent per-type landing data are re-derived with the composer's own rules (tools/die_plan/clock_landing_plan.py
compose/_finish), restricted to this type, and the re-derivation is self-tested on plan_qc49 (must reproduce the stored
values byte-for-byte before it is applied to the new taps):
  * landing_contract.collector_tree = reset_tree.for_type(P, T) (the type's reset relay tree now follows 8 taps);
  * collector_local_sources[].tap = nearest tap relay to the ring pin (band centre if > 405 um, compose rule);
  * collector_children[].node = rst_n_t{consumer_count + k} (rst_n_t6 -> rst_n_t8; same out pin rst_o_0 / xy);
  * forwarded-out pins source_clock_tap = nearest normal clock tap (_finish rule, forward_source clk) -- equals the
    Codex proposed_export_taps for all 6 data exports (asserted); fclk_out_cland_up (Codex: UNRESOLVED) -> rule result.
Bands, pins, outline, ports, the die reset wavefront and every other type are unchanged (diff_infra.py checks).
9190 cross-family (RCLK x FCLK) sequential pairs stay UNPRICED (Codex README).
"""
import argparse, copy, gzip, hashlib, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools" / "die_plan"))
import schema as S, gen_phys as GP, reset_tree as RT

T = "coll_ft__cla4a25d77"
CODEX_TAPS = [("clk", 365.024, 17.312), ("clk_t1", 119.968, 17.312), ("clk_t2", 119.968, 331.168),
              ("clk_t3", 365.024, 331.168), ("clk_t4", 119.968, 662.368), ("clk_t5", 365.024, 662.368),
              ("clk_t6", 119.968, 976.288), ("clk_t7", 365.024, 976.288)]
# Measured plan conflict (landing_place.tcl on the Codex points): clk_t1 sits 0.352 um inside ring band crec_rx_s2_i
# (x0 119.616) and clk_t7 0.032 um inside crec_tx_s2_i (y1 976.32); the reset relays the wavefront puts on those taps
# get collector group boxes (+-2.16 um) overlapping the FIRM ring groups (3 collector + 7 optional overlaps; plan_qc49:
# 0).  Smallest on-track nudge that clears the boxes (gen_phys._snap_tap fixed points): clk_t1 x -3.840 um,
# clk_t7 y +2.688 um.  Bands stay frozen; the other 6 entries are the Codex points exactly.
NUDGE = {"clk_t1": (116.128, 17.312), "clk_t7": (365.024, 978.976)}
TAPS = [(n,) + NUDGE.get(n, (x, y)) for n, x, y in CODEX_TAPS]
EXPORT = {"fclk_out_crec_rx_s1_o": "clk_t6", "fclk_out_crec_rx_s2_o": "clk_t6", "fclk_out_crec_tx_s1_o": "clk",
          "fclk_out_crec_tx_s2_o": "clk", "fclk_out_fltk_o": "clk_t7", "fclk_out_fltv_o": "clk_t7"}
L1 = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])


def derive(raw, path):
    """the composer-rule landing data of T for this raw plan (no mutation)."""
    P = S.Plan(raw, path)
    lc = raw["partition_types"][T]["clock"]["landing_contract"]
    tree = json.loads(json.dumps(RT.for_type(P, T)))
    n = RT.consumer_count(tree)
    tapxy = {int(r["q"].split("rst_n_t")[1]): r["xy"] for r in tree["relays"] if r["q"].startswith("rst_n_t")}
    srcs = []
    for s in lc["collector_local_sources"]:
        pt = s["pin_xy_um"]
        tap = min(range(n), key=lambda i: L1(tapxy[i], pt))
        b = s.get("band") or {}
        if b.get("rect_um") and L1(tapxy[tap], pt) > 405:
            x0, y0, x1, y1 = b["rect_um"]; c = [round((x0 + x1) / 2, 3), round((y0 + y1) / 2, 3)]
            tap = min(range(n), key=lambda i: L1(tapxy[i], c))
        srcs.append(tap)
    old_n = RT.consumer_count(lc["collector_tree"])
    kids = [f"rst_n_t{n + int(c['node'].split('rst_n_t')[1]) - old_n}" for c in lc["collector_children"]]
    roots = GP.clock_pins(P, T)
    exp = {p["name"]: min(roots, key=lambda r: L1((r[1], r[2]), p["xy_um"]))[0]
           for p in lc["pins"] if p["kind"] == "clock" and p["dir"] == "out"}
    return tree, srcs, kids, exp


def apply(raw, d):
    lc = raw["partition_types"][T]["clock"]["landing_contract"]
    tree, srcs, kids, exp = d
    lc["collector_tree"] = tree
    for s, tap in zip(lc["collector_local_sources"], srcs):
        s["tap"] = tap
    for c, k in zip(lc["collector_children"], kids):
        c["node"] = k
    for p in lc["pins"]:
        if p["name"] in exp:
            p["source_clock_tap"] = exp[p["name"]]


ap = argparse.ArgumentParser()
ap.add_argument("plan"); ap.add_argument("--proposal", help="Codex eight_entry_proposal.json.gz (cross-check)")
ap.add_argument("--out", required=True); ap.add_argument("--report", required=True)
a = ap.parse_args()
P0 = json.load(open(a.plan))
rep = dict(type=T, changes=[], codex_taps=CODEX_TAPS, nudge_um=NUDGE)
if a.proposal:
    pr = json.load(gzip.open(a.proposal))
    assert [(t["name"], *t["xy"]) for t in pr["taps"]] == CODEX_TAPS
    assert pr["proposed_export_taps"] == EXPORT
    rep["proposal_check"] = "taps + export taps == Codex eight_entry_proposal (CHECKED)"
    rep["codex_die_bindings"] = pr["die_bindings"]
insts = [p for p in P0["partitions"] if p["type"] == T]
assert sorted(p["name"] for p in insts) == ["coll_f1", "coll_f2"], insts      # type shared by nobody else
assert all(p.get("orient", "R0") == "R0" for p in insts)
# self-test: the re-derivation reproduces the stored plan_qc49 landing data exactly
chk = copy.deepcopy(P0); apply(chk, derive(P0, a.plan))
assert json.dumps(chk, sort_keys=True) == json.dumps(P0, sort_keys=True), "re-derivation does not reproduce the source plan"
rep["self_test"] = "composer-rule re-derivation reproduces plan_qc49 coll_ft landing data byte-identically (CHECKED)"
P = copy.deepcopy(P0)
ck = P["partition_types"][T]["clock"]
assert [x.get("kind") for x in ck.get("taps", [])] == ["glue"], ck.get("taps")
assert "tap_mode" not in ck
old_taps = ck["taps"]
ck["taps"] = [dict(name=n, xy=[x, y]) for n, x, y in TAPS]   # explicit table (no kind, as test_explicit_control_taps)
ck["tap_mode"] = "explicit"; ck["tap_max_sinks"] = 1500; ck["tap_radius_um"] = 200.0
rep["changes"].append(dict(what="clock.taps", old=old_taps, new=ck["taps"]))
rep["changes"].append(dict(what="clock.tap_mode/tap_max_sinks/tap_radius_um", new=["explicit", 1500, 200.0]))
lc0 = copy.deepcopy(ck["landing_contract"])
d = derive(P, a.out)
assert all(d[3][k] == v for k, v in EXPORT.items()), d[3]
apply(P, d)
lc = ck["landing_contract"]
for s0, s in zip(lc0["collector_local_sources"], lc["collector_local_sources"]):
    if s0["tap"] != s["tap"]:
        rep["changes"].append(dict(what=f"collector_local_sources[{s['name']}].tap", old=s0["tap"], new=s["tap"]))
for c0, c in zip(lc0["collector_children"], lc["collector_children"]):
    rep["changes"].append(dict(what=f"collector_children[{c['part']}].node", old=c0["node"], new=c["node"]))
for p0, p in zip(lc0["pins"], lc["pins"]):
    if p0.get("source_clock_tap") != p.get("source_clock_tap"):
        rep["changes"].append(dict(what=f"pins[{p['name']}].source_clock_tap", old=p0["source_clock_tap"], new=p["source_clock_tap"]))
t0, t1 = lc0["collector_tree"], lc["collector_tree"]
rep["changes"].append(dict(what="collector_tree (= reset_tree.for_type)", old=dict(n_tree=t0["n_tree"], n_pad=t0["n_pad"],
    max_hop_um=t0["max_hop_um"], depth=t0["depth"], taps=t0["taps"]), new=dict(n_tree=t1["n_tree"], n_pad=t1["n_pad"],
    max_hop_um=t1["max_hop_um"], depth=t1["depth"], taps=t1["taps"])))
rep["kept"] = dict(tap_pin_heights_um=ck.get("tap_pin_heights_um"), outline_um=P["partition_types"][T]["outline_um"],
                   bands="unchanged (budgets.cland_avoid_reset_types unset: frozen bands keep geometry)")
for p in insts:
    ox, oy = p["origin_um"]
    rep.setdefault("die_bindings", []).append(dict(part=p["name"], taps=[dict(port=n, die_xy_um=[round(ox + x, 4), round(oy + y, 4)]) for n, x, y in TAPS]))
open(a.out, "w").write(json.dumps(P, indent=1) + "\n")
rep["src_sha256"] = hashlib.sha256(open(a.plan, "rb").read()).hexdigest()
rep["dst_sha256"] = hashlib.sha256(open(a.out, "rb").read()).hexdigest()
rep["unpriced"] = "9190 cross-family RCLK x FCLK sequential pairs UNPRICED (Codex 515014cc720 README)"
open(a.report, "w").write(json.dumps(rep, indent=1) + "\n")
print("src", rep["src_sha256"][:8], "dst", rep["dst_sha256"][:8])
for c in rep["changes"][2:]: print(json.dumps(c)[:300])
