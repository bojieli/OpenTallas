#!/usr/bin/env python3
"""DIE-QC-66/CLK 11-03: QC RE-FORM hold-safe die clock ESTIMATE (pre-build, computed, no build).

Inputs (all read-only): plan_qc52.json (post-RED main), qc_cells_evidence_1102.json, plan sink_bins/*.json,
latch/flop OpenSTA characterisation (ASAP7 RVT NLDM, DFFHQNx1 + DLLx1, max tap slew), optional die_sta_related.json
of a measured die clock run (skew per class). Outputs: regions JSON (machine-readable, for DIE-QC-66/PLAN RF-QC-1),
crossing table JSON + TSV.

Rules applied (OWNER RE-FORM 11-03): <=5k sinks per clock entry; signed cores keep signed latency contracts;
RE-FORM cores publish one uniform estimated contract, parent taps early by (contract - common latency);
every crossing = face register + DLL lockup latch, or a fixed latency (count-aligned) contract;
hold gate FF slack >= 0 with 25 ps hold uncertainty; setup nominal (0 uncertainty), 833 ps.
"""
import argparse, collections, json, math, re
from pathlib import Path

ENTRY_MAX = 5000
STATION_RE = re.compile(r"^(sl[ew]_(stm|fw|fe)_)")          # SAFE-STATION family (relay-register heavy)
SIGNED = {"qfd_dv_s8x_prog", "qfd_dv_s8x_btab", "qfd_dv_s8x_vmr", "qfd_dv_s8_crh_rp1", "qfd_dv_s5_red2_leaf",
          "qfd_dv_s5_su8_rst3"}
REFORM = {"qfd_tile_nk_a0c", "qfd_tile_nl_a0c"} | {f"qfd_qc_su_lane_w_l{i}" for i in range(8)}
# RE-FORM core sinks (estimate): A0 kit a0k3 clock node 12102 sinks (lanes CLK tool note); su_lane ~230k cells
# x logic flop ratio, split 2 blocks/lane (QC-021).
REFORM_SINKS = {"qfd_tile_nk_a0c": 12102, "qfd_tile_nl_a0c": 12102}
SU_LANE_CELLS = 230000
# uniform RE-FORM core contract = l1 MEASURED CTS-only view (plan budget_owner DIE-QC-58S), standard block template
REFORM_CONTRACT = {"tt_ps": 392.5, "ff_ps": 321.0, "tol_ps": 40.0,
                   "basis": "uniform RE-FORM block template = qfd_qc_su_lane_w_l1 MEASURED CTS-only view (DIE-QC-58S), "
                            "<=5k sinks per entry, standard depth; parent tap early 142.5 TT / 118.5 FF"}


def slice_of(name):
    m = re.match(r"^(?:c|sl)_([EW]\d)_", name)
    return m.group(1) if m else "centre"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--cells", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--char", required=True, help="latch/flop characterisation JSON")
    ap.add_argument("--sta", action="append", default=[], help="label=die_sta_related.json (measured skew per class)")
    ap.add_argument("--tree", help="ot_clk kit clock/tree.json: current grid taps per partition")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    plan = json.load(open(a.plan))
    cells = json.load(open(a.cells))["cells_per_type"]
    ch = json.load(open(a.char))
    types = plan["partition_types"]
    win = plan["clock"]["tap_window"]["per_type_ps"]
    win_def = plan["clock"]["tap_window"]["window_ps"]
    seam_ps = plan["clock"]["seam_hold"]["seam_ps"]
    common = plan["clock"]["common_latency_ps"]

    # flop ratio calibration from plan sink_bins (measured placed register inventory) vs cells evidence
    sb = {}
    for t, td in types.items():
        f = (td.get("clock") or {}).get("sink_bins_file")
        if f and (Path(a.repo) / f).exists():
            sb[t] = json.load(open(Path(a.repo) / f))["n"]
    def tcells(t):
        return types[t].get("cells") or (cells.get(t) or {}).get("cells")
    cal = collections.defaultdict(list)
    for t, n in sb.items():
        c = tcells(t)
        if c:
            cal["station" if STATION_RE.match(t) else "logic"].append(n / c)
    ratio = {k: max(v) for k, v in cal.items()}           # max = conservative (more sinks -> more entries)
    ratio.setdefault("logic", ratio.get("station"))

    out_dir = Path(a.out); out_dir.mkdir(parents=True, exist_ok=True)
    parts = []
    core_inst = []
    for p in plan["partitions"]:
        t = p["type"]; td = types[t]
        hcs = td.get("hard_cores") or []
        macros = [h for h in hcs if h["module"].startswith(("ot_sram", "ot_rom", "d2d_sram"))]
        cores = [h for h in hcs if h not in macros]
        if t in sb:
            sinks, basis = sb[t], "sink_bins (placed register inventory)"
        elif tcells(t):
            r = ratio["station"] if STATION_RE.match(t) else ratio["logic"]
            sinks = math.ceil(tcells(t) * r)
            basis = f"cells {tcells(t)} x flop ratio {r:.4f} ({'station' if STATION_RE.match(t) else 'logic'} cal)"
        else:
            sinks, basis = 0, "PHY macro type: PHY-internal clocking, 1 face entry"
        sinks += sum(2 if "2c" in h["module"] else 1 for h in macros)  # macro clock pins
        entries = max(1, math.ceil(sinks / ENTRY_MAX))
        parts.append({"part": p["name"], "type": t, "slice": slice_of(p["name"]), "outline_um": td["outline_um"],
                      "glue_sinks_est": sinks, "basis": basis, "regions": entries, "entries": entries,
                      "sinks_per_entry_max": math.ceil(sinks / entries),
                      "window_ps": win.get(t, win_def), "hard_cores": len(cores), "macros": len(macros)})
        taps = {tp["name"].split(".")[0]: tp for tp in (td.get("clock") or {}).get("taps", []) if tp.get("kind") == "core"}
        for h in cores:
            m = h["module"]; tp = taps.get(h["inst"], {})
            if m in REFORM:
                cs = REFORM_SINKS.get(m) or math.ceil(SU_LANE_CELLS * ratio["logic"])
                blocks = 2 if m.startswith("qfd_qc_su_lane") else 1
                ent = sum(math.ceil(math.ceil(cs / blocks) / ENTRY_MAX) for _ in range(blocks))
                con = dict(REFORM_CONTRACT); state = "RE-FORM (estimated contract)"
            else:
                cs, blocks, ent = None, 1, 1
                con = {"tt_ps": tp.get("insertion_ps", common), "ff_ps": tp.get("insertion_ff_ps"),
                       "tol_ps": tp.get("insertion_tol_ps") or 40.0, "basis": (tp.get("budget_owner") or "")[:160]}
                state = "SIGNED (keeps signed contract)" if m in SIGNED else "face kit / other (plan contract)"
            core_inst.append({"part": p["name"], "type": t, "inst": h["inst"], "module": m, "state": state,
                              "core_sinks_est": cs, "blocks": blocks, "core_entries": ent,
                              "contract": con, "early_tap_tt_ps": round((con["tt_ps"] or common) - common, 2),
                              "parent_window_ps": win.get(t, win_def)})

    if a.tree:
        tt = json.load(open(a.tree))["taps"]
        g = collections.Counter(x["part"] for x in tt if not x["tap"].startswith("clk_c"))
        for p in parts:
            p["current_grid_taps"] = g[p["part"]]
            p["entries_required"] = p["entries"]
            p["entries"] = max(p["entries"], g[p["part"]])
            p["entries_added"] = max(0, p["entries_required"] - g[p["part"]])
            p["sinks_per_entry_max"] = math.ceil(p["glue_sinks_est"] / p["entries"])
            p["regions"] = p["entries"]
    # ---- crossings
    ln = plan["clock"]["landing_network"]["edges"]
    landed_ids = {e["id"][len("cland_clk__"):] for e in ln if e["kind"] == "clock"}
    seam_sync = [x for x in plan["ports"] if x["id"] not in landed_ids]
    landed = [x for x in plan["ports"] if x["id"] in landed_ids]
    ctl_ca = [e for e in ln if e["kind"] == "ctl"]
    intra_reg = sum(p["entries"] - 1 for p in parts)

    # measured skew (arrival minus planned target) per class from die_sta_related runs
    meas = {}
    for s in a.sta:
        lab, f = s.split("=", 1)
        d = json.load(open(f))
        meas[lab] = {c: {k: d["corners"][c]["classes"].get(k, {}).get("skew_diag_max_ps") for k in ("intra", "seam", "landed")}
                     for c in d["corners"]}
        meas[lab]["kit_contract_need_ps"] = d["summary"]["intra"].get("kit_contract_window_needed_ps")
        meas[lab]["die_clock_gate"] = d["summary"]["die_clock_gate"]["verdict"]

    T = 833.0; H = T / 2; UH = 25.0; US = 0.0
    F = ch["flop"]; L = ch["latch_dll"]
    def plain(S):
        return {"tt_setup_ps": round(T - F["TT"]["clkq_max_wire_ps"] - F["TT"]["setup_ps"] - US - S, 2),
                "ff_hold_ps": round(F["FF"]["clkq_min_nowire_ps"] - F["FF"]["hold_ps"] - UH - S, 2)}
    def latch(S):
        return {"tt_setup_ps": round(H - L["TT"]["ckq_max_ps"] - F["TT"]["setup_ps"] - US - S, 2),
                "ff_hold_ps": round(H + L["FF"]["ckq_min_ps"] - F["FF"]["hold_ps"] - UH - S, 2),
                "latch_d_hold_ff_ps": round(F["FF"]["clkq_min_nowire_ps"] - L["FF"]["d_hold_ps"] - UH, 2)}

    wmax = max(p["window_ps"] for p in parts if p["entries"] > 1) if intra_reg else 0
    core_S_signed = max(((c["contract"]["tol_ps"] or 40) + c["parent_window_ps"] for c in core_inst if c["state"].startswith("SIGNED")), default=None)
    rows = []
    def row(cls, count, bits, S, Sbasis, form):
        pl, la = plain(S), latch(S)
        r = {"class": cls, "crossings": count, "bits": bits, "skew_bound_ps": S, "skew_basis": Sbasis,
             "plain_face_reg": pl, "face_reg_plus_lockup": la, "form": form,
             "plain_face_reg_hold_safe": pl["ff_hold_ps"] >= 0}
        r["chosen_tt_setup_ps"] = la["tt_setup_ps"]; r["chosen_ff_hold_ps"] = la["ff_hold_ps"]
        r["hold_safe"] = la["ff_hold_ps"] >= 0 and la["tt_setup_ps"] >= 0 and la["latch_d_hold_ff_ps"] >= 0
        rows.append(r)
    LK = "face register + lockup latch (DLL, launch side, same leaf as launch face reg)"
    row("slot<->slot seam (die clock, abutted faces)", len(seam_sync), sum(x["width"] for x in seam_sync), seam_ps,
        f"plan seam_hold.seam_ps {seam_ps} contract (measured need 91.33+10)", LK)
    row("region<->region inside a slot (new <=5k entries; intra-block unless the region edge is a block face)", intra_reg, None, wmax,
        "max per-type tap window W_t of split types (plan tap_window.per_type_ps)",
        "intra-block: block STA + kit hold repair within W_t (standard flow); if the region edge is a RE-FORM block face -> " + LK)
    row("core<->parent, SIGNED cores", sum(1 for c in core_inst if c["state"].startswith("SIGNED")), None, core_S_signed,
        "signed contract tol 40 + parent type window W_t (worst)", LK)
    row("core<->parent, RE-FORM cores (estimated contract)", sum(1 for c in core_inst if c["state"].startswith("RE-FORM")), None,
        max((c["contract"]["tol_ps"] + c["parent_window_ps"]) for c in core_inst if c["state"].startswith("RE-FORM")),
        "RE-FORM contract tol 40 + parent type window W_t (worst)", LK)
    row("core<->parent, coll face kits / other", sum(1 for c in core_inst if c["state"].startswith("face")), None,
        max(((c["contract"]["tol_ps"] or 40) + c["parent_window_ps"] for c in core_inst if c["state"].startswith("face")), default=0),
        "plan contract tol 40 + parent window", LK)
    row("count-aligned START/ctl edges (registered both ends)", len(ctl_ca), len(ctl_ca), seam_ps, "seam contract", LK)
    rows[:] = [r for r in rows if r["crossings"]]
    rows.append({"class": "landed (source-forwarded clock, ring/edge)", "crossings": len(landed),
                 "bits": sum(x["width"] for x in landed), "skew_bound_ps": None,
                 "skew_basis": "landed arrival spread vs local clock > T/2 (measured skew_diag landed); latch half-cycle insufficient",
                 "form": "fixed latency contract: count-aligned (plan count_aligned_cycles, root_settle 64), face regs both ends",
                 "hold_safe": True, "chosen_tt_setup_ps": None, "chosen_ff_hold_ps": None,
                 "note": "source-synchronous capture on the forwarded clock at the receive face register; forwarded->local by "
                         "count-aligned enable (data stable >= 1 cycle per slot); hold/setup = count-align proof (DIE-QC-57 form), not skew"})

    xcheck = {}
    for lab, m in meas.items():
        xcheck[lab] = {k: {"S_TT": m["TT"][k], "S_FF": m["FF"][k],
                           "plain_ff_hold": plain(m["FF"][k])["ff_hold_ps"] if m["FF"][k] is not None else None,
                           "latch_ff_hold": latch(m["FF"][k])["ff_hold_ps"] if m["FF"][k] is not None else None,
                           "latch_tt_setup": latch(m["TT"][k])["tt_setup_ps"] if m["TT"][k] is not None else None}
                       for k in ("intra", "seam", "landed")}
        xcheck[lab]["die_clock_gate"] = m["die_clock_gate"]
        xcheck[lab]["kit_contract_need_ps"] = m["kit_contract_need_ps"]

    slices = collections.OrderedDict()
    for p in sorted(parts, key=lambda q: (q["slice"], q["part"])):
        s = slices.setdefault(p["slice"], {"partitions": 0, "glue_sinks_est": 0, "entries": 0, "entries_added": 0, "core_entries": 0})
        s["partitions"] += 1; s["glue_sinks_est"] += p["glue_sinks_est"]; s["entries"] += p["entries"]
        s["entries_added"] += p.get("entries_added", 0)
    for c in core_inst:
        slices[slice_of(c["part"])]["core_entries"] += c["core_entries"]
    tot = {"partitions": len(parts), "glue_sinks_est": sum(p["glue_sinks_est"] for p in parts),
           "parent_entries": sum(p["entries"] for p in parts), "core_instances": len(core_inst),
           "core_entries": sum(c["core_entries"] for c in core_inst),
           "partitions_split": sum(1 for p in parts if p["entries"] > 1),
           "types_split": len({p["type"] for p in parts if p["entries"] > 1}),
           "entries_required_5k": sum(p.get("entries_required", p["entries"]) for p in parts),
           "current_grid_taps": sum(p.get("current_grid_taps", 0) for p in parts),
           "entries_added": sum(p.get("entries_added", 0) for p in parts),
           "partitions_needing_added_entries": sum(1 for p in parts if p.get("entries_added")),
           "types_needing_added_entries": sorted({p["type"] for p in parts if p.get("entries_added")})}
    meta = {"schema": "qc_reform_clock_regions.v1", "lane": "DIE-QC-66/CLK", "kind": "ESTIMATE (pre-build, computed)",
            "plan": a.plan, "entry_max_sinks": ENTRY_MAX, "flop_ratio": ratio, "sink_bins_types": len(sb),
            "common_latency_ps": common, "reform_core_contract": REFORM_CONTRACT,
            "timing_basis": {"period_ps": T, "hold_unc_ps": UH, "setup_unc_ps": US, "char": ch},
            "rules": "OWNER RE-FORM 11-03 (<=5k sinks/entry, registered faces, lockup latch or fixed latency on crossings); hold FF>=0 (25 ps unc), setup nominal"}
    json.dump({**meta, "totals": tot, "slices": slices, "partitions": parts, "cores": core_inst},
              open(out_dir / "qc_reform_clock_regions.json", "w"), indent=1)
    json.dump({**meta, "crossings": rows, "measured_xcheck": xcheck}, open(out_dir / "qc_reform_crossing_table.json", "w"), indent=1)
    with open(out_dir / "qc_reform_crossing_table.tsv", "w") as f:
        f.write("class\tcrossings\tbits\tskew_bound_ps\tform\tTT_setup_ps\tFF_hold_ps\tplain_TT_setup\tplain_FF_hold\thold_safe\n")
        for r in rows:
            pl = r.get("plain_face_reg") or {}
            f.write(f"{r['class']}\t{r['crossings']}\t{r['bits']}\t{r['skew_bound_ps']}\t{r['form']}\t{r['chosen_tt_setup_ps']}\t"
                    f"{r['chosen_ff_hold_ps']}\t{pl.get('tt_setup_ps')}\t{pl.get('ff_hold_ps')}\t{r['hold_safe']}\n")
    with open(out_dir / "qc_reform_regions_per_slice.tsv", "w") as f:
        f.write("slice\tpartitions\tglue_sinks_est\tparent_entries\tentries_added\tcore_entries\n")
        for k, s in slices.items():
            f.write(f"{k}\t{s['partitions']}\t{s['glue_sinks_est']}\t{s['entries']}\t{s['entries_added']}\t{s['core_entries']}\n")
    print(json.dumps(tot)); print(json.dumps(ratio))
    for r in rows:
        print(r["class"], r["crossings"], r["bits"], r["skew_bound_ps"], r["chosen_tt_setup_ps"], r["chosen_ff_hold_ps"],
              (r.get("plain_face_reg") or {}).get("ff_hold_ps"), r["hold_safe"])
    print(json.dumps(xcheck))


if __name__ == "__main__":
    main()
