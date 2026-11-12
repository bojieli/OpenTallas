#!/usr/bin/env python3
"""QC-EVENT-S25 11-11 (DIE-QC-99, COORD "run the combined QC event NOW"): plan_qc99_s25 = plan_qc99_s24_views (133f641fe01b)
+ five items, in this order, each re-validated by the caller's gates:

 (1) ap2 (QC-NK-HOLD claude/qc-nk-hold-ap2-1111@fc999610864d, on main e9dccc215446): clock.core_input_lockup
     {modules: {qfd_tile_nk_a0c | qfd_tile_nk_rp2_romleaf_rr (bound leaf): [n_a, n_b, tap, rst_n]}, all: true, pipe: 1, pipe_except: [rst_n]}.
     +1 DECLARED register on n_a/n_b/tap of every NK (bind writes bind_core_input_pipe.json, bind_verify adds it).
 (2) NK/NL clock pin follows the SIGNED LEF (COORD 19:25 decision): ck M5 (228.972, 578.880) instead of M4 (457.824, 668.076).
     hard_cores[].pins_file -> the existing ck tables cores/a0_nk_pins_ck1109.json / cores/a0_nl_pins_ck1107.json
     (= the base tables with only ck changed; the base tables stay untouched for every other plan that names them);
     clock_entry_access (the DIE-QC-97 11-09 / QC-NL 11-07 COORD-approved access form, child-frame footprints from
     results/physical/qc_n{k,l}_clock_adoption_*/access_*/adoption.json, mapped per orient R0 / MY);
     clock.taps[<inst>.ck] xy = type-frame M7 utility-pin centre (R0: ox+dx+cx, MY: ox+dx+W-cx; y = oy+dy+578.880),
     orient = core orient, insertion = the signed pin-flop means (NK vR7 eco2 733.25/586.0, NL idleuck 774.38/610.59);
     NL params IDLE_UCK NOT set (unlike qc52n): bind/sc_hard_params maps a parameterised hard core to the as-built leaf
     by "u_"+rel == inst and module, but the as-built NL leaf is u_u_t_3_0 / qfd_tile_nl_rp2_romleaf_rr, not the plan
     physical u_t30 / qfd_tile_nl_a0c -> strict bind PARAM_REGEN "binds 0 leaves".  The signed NL view IS the IDLE_UCK=1
     build (core LEC EQUIVALENT, COORD 11-07); the bound RTL stays IDLE_UCK=0 exactly as in s24 (tool finding);
     lef/lib = the counted signed views (qcviews_1111/views/<module>/, same form as s24).
 (3) crh_rp1 / vmr: the 4 die-owned ft pins (ft_ck_i/o, ft_rst_i/o) enter through the ROOT-integrated physical FT
     contract on main (tools/die_plan/core_ft_physical.py, SUPPORTED = exactly these two masters;
     physical/die_plan/qwen_compute/ft_physical_1106/<crh|vmr>/proof.json): hard_cores[].physical_ft
     {proof, proof_sha256, unconsumed_outputs [ft_ck_o, ft_rst_o]} + native_port_adapter {merge {}, cycles 0,
     tie {ft_ck_i: 1'b0, ft_rst_i: 1'b0}}; lef/lib = the captured qualified views in that proof (byte-equal to the
     counted signed views).  pins_file stays the canonical signed core pin table (the proof checks it canon-equal).
 (4) WSTART re-space: tools/die_plan/wstart_respace.py apply (claude/cland-wstart-origin-1111@fe4380943c) -- run by the
     caller between stage A and stage B of this script.
 (5) qreg (CLAND-CLASS-1 claude/cland-qreg-1111@2d5e254595, on main): landing_output_qreg on slw_fw_v3 [x_ctl_i];
     count-aligned => sidecar count_aligned.ports[pid]: sched_lat +1, K +1,
     output_qreg 1; sidecar ports[pid].added_cycles +1; plan clock.landing_network.count_aligned_cycles[pid] +1; lane
     latency rows: the before/after gen.latency_table delta is added to the stored row.
     sle_su_l0 x_st_a_fe_i is left out (CA port with sched_lat 2: main's legacy row check refuses it, see QREG).
     FREG is NOT adopted (landing_ring_wreg.freg is a per-TYPE boolean: see the report).

usage: make_s25.py A  REPO S24.json OUT_A.json              (items 1-3)
       make_s25.py B  REPO IN_4.json SIDECAR.json OUT_DIR    (item 5 -> OUT_DIR/plan_qc99_s25.json, sidecar_pv_s25.json)
"""
import copy, hashlib, json, sys
from pathlib import Path

sha = lambda b: hashlib.sha256(b).hexdigest()
W = 457.92
QC = "physical/die_plan/qwen_compute"
NK, NL, CRH, VMR = "qfd_tile_nk_a0c", "qfd_tile_nl_a0c", "qfd_dv_s8_crh_rp1", "qfd_dv_s8x_vmr"
# child-frame clock entry access (verbatim from the COORD-approved adoption records; x/y in the core R0 frame)
ACCESS = {
    NK: dict(pins_file="cores/a0_nk_pins_ck1109.json", tap_child=(229.024, 578.880), ins=(733.25, 586.0),
             fp={"M5": [228.972, 578.745, 228.996, 578.904], "M6": [228.961, 578.756, 229.051, 578.788],
                 "M7": [229.008, 578.496, 229.040, 579.264]},
             owner="QC-EVENT-S25 11-11 (COORD 19:25: the plan follows the SIGNED NK LEF ck M5 228.972,578.880): signed NK vR7 eco2 "
                   "re-sign pin-flop mean TT 733.25 / FF 586.0 (n 2584) at the real M5 ck pin via clock_entry_access "
                   "(DIE-QC-97 11-09 access form); parent STA unqualified"),
    NL: dict(pins_file="cores/a0_nl_pins_ck1107.json", tap_child=(228.960, 578.880), ins=(774.38, 610.59),
             fp={"M5": [228.972, 578.873, 228.996, 578.927], "M6": [228.933, 578.884, 229.007, 578.916],
                 "M7": [228.944, 578.496, 228.976, 579.264]},
             owner="QC-EVENT-S25 11-11 (COORD 19:25: the plan follows the SIGNED NL LEF ck M5 228.972,578.880): signed NL idleuck "
                   "pin-flop mean TT 774.38 / FF 610.59 (n 1041) at the real M5 ck pin via clock_entry_access "
                   "(QC NL 11-07 access_v4 form); parent STA unqualified"),
}
VIEWS = {m: (f"{QC}/qcviews_1111/views/{m}/{m}.lef", f"{QC}/qcviews_1111/views/{m}/{m}_tt.lib") for m in (NK, NL)}
FT = {CRH: "crh", VMR: "vmr"}
# bind matches core_input_lockup on the BOUND leaf module: in the QC as-built (dq97 taps1111 elab) every NK hard core is
# the leaf qfd_tile_nk_rp2_romleaf_rr (same n_a/n_b/tap/rst_n ports); qfd_tile_nk_a0c alone emits nothing (s25 v3 bind:
# no bind_core_input_pipe.json, 0 u_pc_nk).  Both names are listed (a0c for binds whose leaf is the physical module).
LOCKUP = {"modules": {NK: ["n_a", "n_b", "tap", "rst_n"], "qfd_tile_nk_rp2_romleaf_rr": ["n_a", "n_b", "tap", "rst_n"]},
          "all": True, "pipe": 1, "pipe_except": ["rst_n"],
          "note": "QC-EVENT-S25 11-11: QC-NK-HOLD ap2 fc999610864d (COORD 17:10 APPROVED): +1 DECLARED pipe register then the "
                  "negative-level lockup latch on NK n_a/n_b/tap; rst_n latch only (pipe_except). TOK-VERIFY-1: tap 3/10/17/24 -> "
                  "4/11/18/25, rs_fabric 74 -> 79, 4403.2 -> 4391.6 tok/s (-0.26%, accepted under 12.21)."}
# sle_su_l0__cl086d85ba x_st_a_fe_i (-0.3 ps) is NOT taken: on main, clock_landings.Landings applies the legacy
# "added_cycles must be 3 + qreg" row check to count-aligned ports too, so a CA port with sched_lat != 3 (this one: 2)
# cannot carry QREG (strict bind: "legacy landing added_cycles must be 4").  slw_fw_v3 x_ctl_i has sched_lat 3 -> 4,
# which satisfies both the legacy check and the CA sched_lat convention.  Tool finding for CLAND-CLASS-1.
# The +1 bound cycle on W5 ctl->fw also needs the r8 landing table regenerated (r8.py pads on the s25 bind bus_groups):
# r8_sw2_s25.json, delta = W5 ctl->fw class landed 10 -> 11 only (see latency_event.json).
DEAD_TIE_NOTE = ("DECLARED dead-pin tie (QC-EVENT-S25 11-11, DIE-QC-99, COORD ruling 11-11): core {inst} ({module}) "
                 "pins ft_ck_i, ft_rst_i tied 1'b0; ft_ck_o, ft_rst_o unconsumed (physical_ft.unconsumed_outputs). "
                 "Reason: METHODOLOGY 12.2a1 die-owned pushdown feed-through pins of the signed core, not used by this plan "
                 "(no clock.mesh.core_islands / reset use). Unobservable: proof.json isolation graph, re-proved by "
                 "core_ft_physical.isolation from the signed routed 6_final.v at every kit, = one unary buffer per arc "
                 "(ot_isl_ckft / ot_isl_rstft) to its ft_*_o port, no other core port, state or load; the logical core header "
                 "and the bound RTL are unchanged (the 4 ports exist only in the physical black-box header).")
QREG = {"slw_fw_v3": ["x_ctl_i"]}


def r4(v):
    return round(v + 0.0, 4)


def place(h, x0, y0, x1, y1):
    """child R0 rect -> type frame for R0 / MY (MY mirrors x about the core width)"""
    ox, oy = h["origin_um"]; dx, dy = h.get("track_offset_um") or [0.0, 0.0]
    o = h.get("orient", "R0")
    if o == "R0":
        a, b = ox + dx + x0, ox + dx + x1
    elif o == "MY":
        a, b = ox + dx + W - x1, ox + dx + W - x0
    else:
        raise ValueError(f"{h['inst']}: orient {o} not handled")
    return [r4(a), r4(oy + dy + y0), r4(b), r4(oy + dy + y1)]


def stage_a(repo, src, dst):
    repo = Path(repo); raw = Path(src).read_bytes()
    assert sha(raw).startswith("133f641fe01b"), "base must be plan_qc99_s24_views"
    p = json.loads(raw)
    rep = dict(base="plan_qc99_s24_views.json", base_sha256=sha(raw), items={})
    # (1) ap2
    assert "core_input_lockup" not in p["clock"]
    p["clock"]["core_input_lockup"] = copy.deepcopy(LOCKUP)
    nk_types = sorted(tn for tn, t in p["partition_types"].items() if any(h["module"] == NK for h in t.get("hard_cores") or []))
    rep["items"]["1_ap2"] = dict(key="clock.core_input_lockup", value=LOCKUP, nk_types=nk_types)
    # (2) NK / NL clock pin + access + taps + views
    pf_root = repo / QC / "plan_of_record"
    for m, a in ACCESS.items():
        new = json.loads((pf_root / a["pins_file"]).read_text())["pins"]
        ck = [q for q in new if q["name"] == "ck"]
        assert ck == [{"name": "ck", "layer": "M5", "x": 228.972, "y": 578.88}], ck
    edits = []
    for tn, t in sorted(p["partition_types"].items()):
        taps = {tp["name"]: tp for tp in (t.get("clock") or {}).get("taps") or []}
        for h in t.get("hard_cores") or []:
            m = h["module"]
            if m in ACCESS:
                a = ACCESS[m]
                old_pf = h["pins_file"]
                assert old_pf in ("cores/a0_nk_pins.json", "cores/a0_nl_pins.json"), (tn, h["inst"], old_pf)
                assert "clock_entry_access" not in h and "lef" not in h, (tn, h["inst"])
                h["pins_file"] = a["pins_file"]
                h["clock_entry_access"] = {"pin": "ck", "footprints_um": {L: [place(h, *r)] for L, r in a["fp"].items()}}
                if a.get("params"):
                    assert not h.get("params"), (tn, h["inst"], h.get("params"))
                    h["params"] = dict(a["params"])
                h["lef"], h["lib"] = VIEWS[m]
                tp = taps.get(h["inst"] + ".ck")
                assert tp is not None and tp.get("kind") == "core", (tn, h["inst"])
                was = dict(xy=tp["xy"], orient=tp.get("orient"), insertion_ps=tp.get("insertion_ps"),
                           insertion_ff_ps=tp.get("insertion_ff_ps"))
                cx, cy = a["tap_child"]
                r = place(h, cx, cy, cx, cy)
                tp["xy"] = [r[0], r[1]]
                tp["orient"] = h.get("orient", "R0")
                tp["insertion_ps"], tp["insertion_ff_ps"] = a["ins"]
                tp["budget_owner"] = a["owner"]
                edits.append(dict(type=tn, inst=h["inst"], module=m, orient=h.get("orient", "R0"), origin_um=h["origin_um"],
                                  pins_file=[old_pf, a["pins_file"]], tap_was=was, tap_now=dict(xy=tp["xy"], orient=tp["orient"],
                                  insertion_ps=a["ins"][0], insertion_ff_ps=a["ins"][1]),
                                  access=h["clock_entry_access"], params=h.get("params"), lef=h["lef"], lib=h["lib"]))
            elif m in FT:
                d = repo / QC / "ft_physical_1106" / FT[m]
                proof = d / "proof.json"
                pr = json.loads(proof.read_text())
                assert pr["module"] == m
                assert "physical_ft" not in h and "native_port_adapter" not in h and "lef" not in h, (tn, h["inst"])
                core_pins = d / pr["files"]["core_pins"]["path"]
                assert sha((pf_root / h["pins_file"]).read_bytes()) == sha(core_pins.read_bytes()) == pr["files"]["core_pins"]["sha256"], \
                    (tn, h["inst"], "plan pins_file is not the proof's captured core pin table")
                h["lef"] = f"{QC}/ft_physical_1106/{FT[m]}/{pr['files']['lef']['path']}"
                h["lib"] = f"{QC}/ft_physical_1106/{FT[m]}/{pr['files']['tt']['path']}"
                h["physical_ft"] = {"proof": f"{QC}/ft_physical_1106/{FT[m]}/proof.json", "proof_sha256": sha(proof.read_bytes()),
                                    "unconsumed_outputs": ["ft_ck_o", "ft_rst_o"]}
                h["native_port_adapter"] = {"merge": {}, "cycles": 0, "tie": {"ft_ck_i": "1'b0", "ft_rst_i": "1'b0"},
                                            "note": DEAD_TIE_NOTE.format(inst=h["inst"], module=m)}
                edits.append(dict(type=tn, inst=h["inst"], module=m, lef=h["lef"], lib=h["lib"], physical_ft=h["physical_ft"],
                                  native_port_adapter=h["native_port_adapter"], pins_file=h["pins_file"]))
    rep["items"]["2_3_cores"] = edits
    p["note"] = p["note"] + (" | s25 (QC-EVENT-S25 11-11, DIE-QC-99 combined event): s24_views + (1) NK core_input_lockup pipe 1 "
                             "(ap2) + (2) NK/NL ck pin follows the signed LEF (clock_entry_access, taps, insertion) and "
                             "NK/NL signed views bound + (3) crh_rp1/vmr signed views bound via physical_ft (4 die-owned ft pins, "
                             "inputs tied 0, outputs unconsumed) + (4) WSTART re-space (30 branches, 12 types, same depth) + "
                             "(5) landing_output_qreg slw_fw_v3 x_ctl_i (+1 declared, sidecar)")
    Path(dst).write_text(json.dumps(p, indent=1))
    Path(dst + ".report.json").write_text(json.dumps(rep, indent=1) + "\n")
    print("stage A", sha(Path(dst).read_bytes())[:12], "nk types", len(nk_types), "core edits", len(edits))


def stage_b(repo, src, sidecar, outdir):
    repo = Path(repo).resolve(); out = Path(outdir); out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(repo / "tools/die_plan"))
    import gen as G
    import schema as SC
    P = json.loads(Path(src).read_bytes()); S = json.loads(Path(sidecar).read_bytes())
    sc_sha0 = sha(Path(sidecar).read_bytes())
    tab0 = G.latency_table(SC.Plan(copy.deepcopy(P)))
    parts = {q["name"]: q["type"] for q in P["partitions"]}
    ca = S["count_aligned"]["ports"]; srcports = {x["port"]: x for x in S["ports"]}
    cac = P["clock"]["landing_network"]["count_aligned_cycles"]
    rows = []
    for tn, buses in QREG.items():
        c = P["partition_types"][tn]["clock"]
        assert "landing_output_qreg" not in c and all(b in c["landing_ring_wreg"]["buses"] for b in buses), tn
        c["landing_output_qreg"] = list(buses)
        for pr in P["ports"]:
            if parts.get(pr["dst"]["part"]) != tn or pr["dst"]["bus"] not in buses:
                continue
            pid = pr["id"]; e = ca[pid]
            assert cac[pid] == e["sched_lat"] == srcports[pid]["added_cycles"] and not e.get("output_qreg"), \
                (pid, cac[pid], e, srcports[pid]["added_cycles"])
            was = dict(sched_lat=e["sched_lat"], K=e["K"], added_cycles=srcports[pid]["added_cycles"], cac=cac[pid])
            e["sched_lat"] += 1; e["K"] += 1; e["output_qreg"] = 1
            srcports[pid]["added_cycles"] += 1; cac[pid] += 1
            rows.append(dict(type=tn, bus=pr["dst"]["bus"], port=pid, lane=srcports[pid].get("lane"), was=was,
                             now=dict(sched_lat=e["sched_lat"], K=e["K"], added_cycles=srcports[pid]["added_cycles"],
                                      cac=cac[pid], output_qreg=1)))
    assert len(rows) == 1, rows
    tab1 = G.latency_table(SC.Plan(copy.deepcopy(P)))
    lanes = P["latency"]["lanes"]; lat_rows = []
    for lid in sorted(set(tab0) | set(tab1)):
        a, b = tab0.get(lid), tab1.get(lid)
        if a == b:
            continue
        fields = [f for f in ("cycles", "natural", "clock_landing") if (a or {}).get(f) != (b or {}).get(f)]
        # the stored QC rows are not gen.latency_table's (stored fixed / R8 fold differ), so only the DELTA the qreg
        # adds between the before/after derivations is applied to the stored row
        assert lid in lanes and a is not None and b is not None, (lid, fields)
        st = {f: lanes[lid][f] for f in fields}
        for f in fields:
            lanes[lid][f] = st[f] + (b[f] - a[f])
        lat_rows.append(dict(lane=lid, stored={f: [st[f], lanes[lid][f]] for f in fields},
                             derived={f: [a[f], b[f]] for f in fields}))
    (out / "plan_qc99_s25.json").write_text(json.dumps(P, indent=1))
    raw_sc = json.dumps(S).encode()
    (out / "sidecar_pv_s25.json").write_bytes(raw_sc)
    rep = dict(item="5_qreg", sidecar_base_sha256=sc_sha0, sidecar_s25_sha256=sha(raw_sc), ports=rows, lane_latency=lat_rows,
               plan_s25_sha256=sha((out / "plan_qc99_s25.json").read_bytes()))
    (out / "stage_b_report.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "A":
        stage_a(*sys.argv[2:5])
    elif sys.argv[1] == "B":
        stage_b(*sys.argv[2:6])
    else:
        raise SystemExit(__doc__)
