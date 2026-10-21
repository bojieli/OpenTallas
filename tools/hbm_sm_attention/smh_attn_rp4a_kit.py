#!/usr/bin/env python3
"""HBM-DIEGAP/SMHPARENT 10-21 (H.STA.BLK.14): ref_tile kit SPECS for the smh_attn x16 parent built from the rp4a hardened
halves, as a LANDED cluster (tools/landed_parent/lp.py records results/arch/smh_attn_parent_1021/{main,fb}/).

  MAIN  smh_attn_rp4a_main: lp top ot_hbm_accel_smh_attn_rp4a_lp_main, 34 regions (front launch f, front result fr, one per
        HALF), halves r3a (691.2 wide), an 86.4-um channel between every n and s half for the n->s crossing LANDING
        (ring on the n root at its S face, read on the s root beside u_lands), 86.4-um landing channels between columns.
  FB    smh_attn_rp4a_fb: lp top ot_hbm_accel_smh_attn_rp4a_lp_fb, 18 regions (f, fr, one per TILE = both halves on one
        parent root), halves r3b (734.4 wide) ABUTTED n over s (the crossing is the halves' own direct reg->reg, balanced
        by the region tree against both halves' ETM insertions).
Floorplan (both): columns 0..3 W of the front column, 4..7 E (rows / beat flow outward from the front), p0 tiles on top,
p1 below, the BE row at the bottom, the front result u_fr at the bottom of the front column.  W-side halves are MY
(rows enter the E face); E-side R0.  Every child origin on the 43.2 lattice.

The halves views do not exist yet (r3 gates by SAFE-HBM on ot-gold2); `ref_tile.py gen` needs them.  This script writes the
spec + a STATUS line; re-run it with --gen once physical/ref_tile/smh_rp4ah{n,s}_r3{a,b}/views/* exist (closed, or a
diagnostic stand-in export clearly marked PROVISIONAL) and then gate with pre_route_gate --cts (MAIN + FB in parallel).
    python3 tools/hbm_sm_attention/smh_attn_rp4a_kit.py [--gen]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import smh_attn_rp4a_lp_specs as LS  # noqa: E402
import smh_attn_rp4a_flat_gen as R  # noqa: E402

SPECS = ROOT / "tools/ref_tile/specs_hbm_attention"
HALF = {"main": "r3a", "fb": "r3b"}
HN, HS = LS.HN, LS.HS
NC, NP, NL = R.NC, R.NP, R.NL
LAT = 43.2


def snap(v):
    return round(round(v / LAT) * LAT, 2)


def views(form):
    v = HALF[form]
    return {"n": f"physical/ref_tile/smh_rp4ahn_{v}/views/ot_hbm_smh_rp4ah_n",
            "s": f"physical/ref_tile/smh_rp4ahs_{v}/views/ot_hbm_smh_rp4ah_s"}


def kit(form):
    rec_path = f"results/arch/smh_attn_parent_1021/{form}/ot_hbm_accel_smh_attn_rp4a_lp_{form}_record.json"
    rec = json.loads((ROOT / rec_path).read_text())
    lps = json.loads((ROOT / f"results/arch/smh_attn_parent_1021/lp_spec_{form}.json").read_text())
    g = LS.form_geometry(form)
    w = 691.2 if form == "main" else 734.4
    W, H = snap(g["w"]), snap(g["h"])
    V = views(form)
    kids = []
    for c in range(NC):
        x0 = snap(g["x"][c] - w / 2)
        orient = "MY" if c < NL else "R0"
        for p in range(NP):
            ys = snap(g["y"][f"{p}s"] - HS / 2)
            yn = snap(g["y"][f"{p}n"] - HN / 2)
            kids.append(dict(view=V["n"], count=1, inst=f"u_t{c}{p}_n", at=[x0, yn], orient=orient))
            kids.append(dict(view=V["s"], count=1, inst=f"u_t{c}{p}_s", at=[x0, ys], orient=orient))
    regions = rec["regions"]
    cps = [regions[r]["clock_port"] for r in regions]
    # parent pins: inputs + request / schedule_fault over the front column (N face); results at the bottom of the front
    # column (S face, beside u_fr); per-region clocks on the face nearest the region (p0 / f: N, p1 / fr: S)
    xf0, xf1 = snap(g["xf"] - LS.FW / 2 - 864), snap(g["xf"] + LS.FW / 2 + 864)
    north_in = ["command", "kv_desc", "packet", "xw_en", "xw_addr", "xw_grp", "xw_data", "request", "schedule_fault", "rst_n"]
    south_out = ["rv", "rrow", "rdata", "fault"]
    ck_n = [regions[r]["clock_port"] for r in regions if r == "f" or (r.startswith("t") and r[2] == "0")]
    ck_s = [regions[r]["clock_port"] for r in regions if r not in ("f",) and not (r.startswith("t") and r[2] == "0")]
    pin_ranges = {p: [xf0, xf1] for p in north_in + south_out}
    for r in regions:
        cp = regions[r]["clock_port"]
        if r in ("f", "fr"):
            x = g["xf"]
        else:
            x = g["x"][int(r[1])]
        pin_ranges[cp] = [round(x - 2.16, 2), round(x + 2.16, 2)]
    dom = {"core": dict(ratio=[1, 1], ports=[regions["f"]["clock_port"]],
                        inputs=["command", "kv_desc", "packet", "xw_en", "xw_addr", "xw_grp", "xw_data", "rst_n"],
                        outputs=["request", "schedule_fault"]),
           "fr": dict(ratio=[1, 1], ports=[regions["fr"]["clock_port"]], inputs=[], outputs=south_out)}
    for r in regions:
        if r not in ("f", "fr"):
            dom[r] = dict(ratio=[1, 1], ports=[regions[r]["clock_port"]], inputs=[], outputs=[])
    macro_area = 2 * NC * NP * w * (HN + HS) / 2
    fill = macro_area / (W * H)
    LDIR = f"rtl/hbm_accel/sm/attn/flat/lp_rp4a_{form}"
    bench = f"{LDIR}/ot_hbm_accel_smh_attn_rp4a_lp_{form}_bench.sh"
    benches = [dict(name=f"lp_lockstep_mut{m}", cmd=f"MUTS={m} SIM=verilator bash {bench} {{RUN}}/bench/lp{m}",
                    expect="pass" if m == 0 else "fail",
                    **({"pass_regex": "MUT 0: LP_LOCKSTEP PASS"} if m == 0 else {"fail_regex": f"MUT {m}: LP_LOCKSTEP FAIL"}),
                    threads=16, peak_ram_gb=160, needs=["verilator"]) for m in (0, 1, 2, 3)]
    benches += [dict(name="golden_rp4a_ds640_qkpv",
                     cmd="python3 tools/hbm_sm_attention/sm_elem_bench.py run --shape ds640 --ops qk_sm0,pv_sm0 --rp4a 5,28 "
                         "--lat '{\"out\": 80}' --work {RUN}/bench/golden --out {RUN}/bench/golden.json",
                     expect="pass", pass_regex="PASS HBM_SM_ELEMENT_ATTENTION", threads=16, peak_ram_gb=128, needs=["verilator"])]
    hard = lps["synthesis_hard_instances"]
    checklist = {
        "1_pins": "PASS: every half pin is registered in the halves' RTL (pinrow / pinbeat / straps / u_lands / u_xgi / u_xpi in, "
                  "row_e / beat_e / u_xbo / u_xgo / u_xpo / u_gs out); every cross-region parent net is an lp landing (ring beside "
                  "the source root, read beside the reader); parent inputs land in the front's own pin stages; parent pins over "
                  f"the front column ({xf1 - xf0:.0f} um of N face for ~3,480 input bits: ~1.3 pins/um).",
        "2_reach": "PASS by construction: landed ring -> read hops are E=2 multicycle (<= one column pitch "
                   f"{g['pitch']:.1f} um or one n/s channel); intra-region soft paths sit beside one half face; reset runs hop "
                   f"<= 405 um (lp reach_um default, depth {rec['reset']['depth']}).  Front column -> column 3/4 rows ~0.6 mm = landed.",
        "3_fanout": "lp landing_writer n32 + landing_chunk_bits 24 (kept per-chunk selectors) + regional_reset_copies (<= 32 loads "
                    "per kept reset copy); wide buses sliced <= 720 b per landed net; pre-gate native census decides (front / BE soft "
                    "logic census = the die smh_attn SYNTH census, unchanged RTL).",
        "4_depth": "PASS: landing read = registered slot mux; halves and BE unchanged; no combinational in -> out.",
        "5_storage": "PASS: ring banks are D=4 fixed-latency slots; SRAMs inside the halves (x store, PV merge) and the front "
                     "(pstore / kv_line, as the die smh_attn).",
        "6_floorplan": f"outline {W} x {H} (ENLARGED vs the die slot 1939.68 x 6955.2: 16 rp4a tiles cannot fit it), 32 halves on the "
                       f"43.2 lattice, 86.4 channels between columns{' and between every n/s pair' if form == 'main' else ''}, "
                       f"macro fill {fill:.0%} (+ soft front / BE / landings); aspect {W / H:.2f}.",
        "7_clock": f"{len(regions)} regional roots ({'one per half' if form == 'main' else 'one per tile'} + front launch + front "
                   "result); every region crossing landed (lp audit PASS); hard-child clock references from views/<half>/insertion.json; "
                   + ("the n->s crossing is a landing (no reg->reg between two halves' trees)." if form == "main" else
                      "FALLBACK: the n->s crossing stays a direct reg->reg inside one region; the region root balances both halves' clk pins."),
        "8_schedule": f"static; rp4a vs soft tile: BE lanes +{2 * R.G} (p1 own lanes padded +{R.G}), BE_DELAY 8 -> {8 + 2 * R.G}, HOPD 5; "
                      f"landed results +{rec['compiler']['output_port_offset_edges']['rv']} edges on top (record compiler block), reset release "
                      f"+{rec['compiler']['reset_release_added_edges']}; inputs offset 0.  PRICED -> NOTICE HBM-DIE15.",
    }
    spec = dict(
        name=f"smh_attn_rp4a_{form}", top=f"ot_hbm_accel_smh_attn_rp4a_lp_{form}", kind="cluster",
        sources=[f"{LDIR}/ot_hbm_accel_smh_attn_rp4a_lp_{form}.sv", "rtl/hbm_accel/sm/attn/flat/ot_hbm_accel_smh_attn_rp4a.sv",
                 "rtl/common/landed_parent/ot_pl_land.sv", "rtl/common/landed_parent/ot_pl_land_n32.sv",
                 "rtl/common/landed_parent/ot_pl_land_rst_copy.sv"] + [s for s in lps["child_sources"]],
        defines=lps["defines"], params={},
        clock="multiple_cts_roots", clock_port=regions["f"]["clock_port"], clock_ports=cps,
        clock_data_paths="related_same_frequency",
        clock_relationship=dict(kind="same_pll_fixed_phase", ratio=[1, 1], phase_ps=0),
        clock_entry_domains=dom, landed_record=rec_path, reset_ports=["rst_n"],
        outline=dict(w=W, h=H, exact=True), children=kids, macros=[], inter=[],
        pins={"N": north_in + ck_n, "S": south_out + ck_s}, pin_ranges=pin_ranges,
        route=dict(pd=0.5, threads=32, peak_ram_gb=512, macro_halo_um=5.4, pin_h="M4", pin_v="M3 M5",
                   hold_margin_ns=0.03, io_hold_margin_ns=0.03),
        recipe=4, inhold=False, outhold=False,
        pin_regs=dict(enable=False, reason="every parent input lands in the front's own pin stages (feed / fc_* pin registers) "
                      "and every output leaves u_fr registers; region crossings are lp landings; a kit flop stage would add an "
                      "unpriced edge to the landed record"),
        reset_landing=dict(enable=False, reason=f"the lp RTL lands rst_n in the reset region f (u_lpr root + per-region kept copies, depth "
                           f"{rec['reset']['depth']}, regional_reset_copies <= 32 loads), priced in the landed record"),
        child_clock_ref="boundary", keep_pin_regs=True,
        safe_design_checklist=checklist,
        slot_change_request=(f"HBM-DIE15 sm_SW0-7 / sm_NW0-7 (ot_hbm_accel_smh_attn x16): OUTLINE {W} x {H} um (was 1939.68 x 6955.2); "
                             f"PORT CHANGE: clk -> {len(cps)} region clocks {', '.join(cps[:3])}, ... (die drops one clock per region, "
                             "neighbour-relative; landings need no phase alignment); ports otherwise identical (command 192, kv_desc 64, "
                             "packet 1099, xw_*, request 43, rv/rrow/rdata/fault/schedule_fault); results "
                             f"+{2 * R.G + rec['compiler']['output_port_offset_edges']['rv']} edges vs the soft smh_attn, reset release "
                             f"+{rec['compiler']['reset_release_added_edges']}; ENABLE_INT8 g_int8 glue NOT yet in this parent (die binds "
                             "ENABLE_INT8 1: add the hard smh_int8_t1 tile before u_fl in the next generator rev)."),
        landed=dict(record=rec_path, landings=len(rec["landings"]), landing_flops=rec["flops"]["landing"],
                    reset_depth=rec["reset"]["depth"], lp_spec=f"results/arch/smh_attn_parent_1021/lp_spec_{form}.json"),
        synthesis_hard_instances=hard,
        views_status=f"PENDING: halves views {V['n']} / {V['s']} (r3 gates by SAFE-HBM); front / BE soft",
        job=dict(owner="Claude:HBM-DIEGAP/SMHPARENT", branch="claude/hbm-smhparent-1021", tag=f"smhp_{form}",
                 purpose=f"H.STA.BLK.14 smh_attn x16 parent from the rp4a halves, landed cluster form {form.upper()}",
                 views_to=f"physical/ref_tile/smh_attn_rp4a_{form}/views", record_to=f"results/rtl/ref_tile/smh_attn_rp4a_{form}",
                 extra_paths=["tools/landed_parent", "rtl/common/landed_parent", "rtl/hbm_accel", "rtl/lib", "rtl/gpu", "rtl/hdc",
                              "rtl/proto", "rtl/v41rom", "results/arch/smh_attn_parent_1021", "physical/asap7_memory_macros",
                              "physical/hbm_accel_macros"],
                 benches=benches))
    return spec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", action="store_true", help="also run ref_tile.py gen (needs the halves views)")
    a = ap.parse_args()
    SPECS.mkdir(parents=True, exist_ok=True)
    for form in ("main", "fb"):
        s = kit(form)
        p = SPECS / f"{s['name']}.json"
        p.write_text(json.dumps(s, indent=1) + "\n")
        miss = [v for v in views(form).values() if not (ROOT / v).exists()]
        print(f"wrote {p.relative_to(ROOT)}: outline {s['outline']['w']} x {s['outline']['h']}, {len(s['children'])} halves, "
              f"{len(s['clock_ports'])} clocks; views {'MISSING ' + ', '.join(miss) if miss else 'present'}")
        if a.gen:
            if miss:
                print("  skip gen: halves views missing")
                continue
            subprocess.run([sys.executable, str(ROOT / "tools/ref_tile/ref_tile.py"), "gen", str(p)], check=True)


if __name__ == "__main__":
    main()
