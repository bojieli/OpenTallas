#!/usr/bin/env python3
"""ref_tile spec for qfd_c_b16_dv (Q-CLUSTER).  Inputs: results/arch/qwen_cluster_1017/cluster_contract_dv.json and
relay_sites_dv.json (qc_gen.py).  Two modes:

  qc_kit.py diag   -> tools/ref_tile/specs_qcluster/qfd_c_b16_dv_diag.json: children = the A0 STAND-IN abstracts
                      (physical/ref_tile/qfd_c_b16_dv_diag/a0_standin, a0_standin.py): gates only, never submitted/bound
  qc_kit.py real --nk VIEW --nl VIEW -> qfd_c_b16_dv.json: children = the CLOSED native-PASS A0 c1 views

Clock (Q-CLUSTER2 10-17): eight regional CTS roots ck_w0 (core) .. ck_w3 / ck_e0 .. ck_e3 (side x tile row, every
clock port a CTS root, related 1:1, each boundary port in the domain of the region holding its pin register; the region
SDC physical/qcluster/qfd_c_b16_dv_quadrants.sdc is written here).  --engine spine (default: one balanced spine per root,
OT_SPINE_PORTS) or cts (TritonCTS per root, child entry insertion from the A0 TT-lib clock-tree arcs).  Boundary: every data pin is
registered in the S / N strip by the generated RTL (flop-first / flop-last), so pin_regs are off with that reason,
hold_budget "die", no inhold / outhold.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCH = ROOT / "results/arch/qwen_cluster_1017"
STANDIN = "physical/ref_tile/qfd_c_b16_dv_diag/a0_standin"
STN_STANDIN = "physical/ref_tile/qfd_c_b16_dv_diag/stn_standin"
# Q-CLUSTER3: the stations are hard children (blackboxes here); only the 1-bit reset stages (qfd_q3h_stn W=1) stay soft
FABRIC_SRC = ["rtl/physical/qcluster/qfd_q3h_stn.sv", "rtl/physical/qcluster/qfd_c_land.sv",
              "rtl/physical/qcluster/qfd_c_b16_dv_fabric.sv", "rtl/physical/qcluster/qfd_c_b16_dv.sv"]
# Q-CL16-LAND (10-18): die delivery residual between communicating region clocks (die_clock_contract.json obligation 2,
# as rewritten by Q-CL16-EARLY cc6c1f3ae: drops phase-aligned within +/-60 ps at TT and FF), ON TOP of the per-clock
# 60 setup / 25 hold uncertainty: inter-clock uncertainty overrides the per-clock value, so the pair gets 120 / 85.
DIE_RESIDUAL_PS = 60
BASE_UNC_PS = dict(setup=60, hold=25)
DIE_CLOCK = ARCH / "q_cluster16/die_clock_contract.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["diag", "real"])
    ap.add_argument("--nk")
    ap.add_argument("--nl")
    ap.add_argument("--stn", help="real mode: directory holding the CLOSED station views qfd_c_stn516/514, qfd_c_xstn(w)")
    ap.add_argument("--engine", choices=["spine", "cts"], default="spine")
    # Q-CLUSTER5 (coordinator 0ea (4)): fallback (a) of option (b): CENTRE-FED regions.  'centre' moves every regional
    # clock port to an interior area pin at its region centre at PRE_CTS (physical/qcluster/qfd_c_b16_dv_centre_feed.tcl;
    # the die drops the regional clock there) and builds the spine with the symmetric insertion-aware topology
    # (OT_SPINE_SYM=1: nodes at bounding-box centres, each hard child taps the tree as high as its own internal
    # insertion requires, so the pads left are the true imbalance).  Kit names get a 'c' (diagc / diagct).
    ap.add_argument("--feed", choices=["face", "centre"], default="face")
    # Q-CLUSTER16 (owner 0ei 10-18): 16 regions (one per A0 tile); kit names get '16' (diag16c / diag16ct)
    ap.add_argument("--tag", default="", help="kit name infix after 'diag' (e.g. 16)")
    ap.add_argument("--branch", help="job branch (default by tag)")
    a = ap.parse_args()
    C = json.loads((ARCH / "cluster_contract_dv.json").read_text())
    W, H = C["outline_um"]["w"], C["outline_um"]["h"]
    nkm, nlm = C["a0"]["nk"], C["a0"]["nl"]
    if a.mode == "diag":
        nk, nl = f"{STANDIN}/{nkm}", f"{STANDIN}/{nlm}"
        name = "qfd_c_b16_dv_diag" + a.tag + ("c" if a.feed == "centre" else "") + ("" if a.engine == "spine" else "t")
        bb = [f"{STANDIN}/a0_rr_bb.v", f"{STN_STANDIN}/stn_bb.v"]
        stn = STN_STANDIN
    else:
        if not (a.nk and a.nl and a.stn):
            raise SystemExit("real mode needs --nk / --nl CLOSED native-PASS A0 views and --stn station views")
        nk, nl, name, bb = a.nk, a.nl, "qfd_c_b16_dv" + ("_c" if a.feed == "centre" else "") + ("" if a.engine == "spine" else "_t"), []
        stn = a.stn
    tiles = []
    spare = tuple(C["tree"]["nl_slot"])
    for t in C["tiles"]:
        c, r = (int(v) for v in t["inst"][4:].split("_"))
        tiles.append(dict(view=nl if (c, r) == spare else nk, count=1, inst=t["inst"], at=t["at"], orient=t["orient"],
                          at_exact=True))
    for k in C["stations"]["children"]:
        tiles.append(dict(view=f"{stn}/{k['master']}", count=1, inst=k["inst"], at=k["at"], orient=k["orient"],
                          at_exact=True))
    ports = C["ports"]
    faces = {"N": [], "S": [], "E": [], "W": []}
    for p in ports:
        faces[p["face"]].append(p["port"])
    xs = C["region_seams"]["x"]
    xs = xs if isinstance(xs, list) else [xs]
    regions = list(C["clocks"])
    sixteen = len(regions) == 16
    cks = [f"ck_{q}" for q in regions]
    dom = {q: dict(inputs=[], outputs=[]) for q in regions}
    for p in ports:
        n = p["port"]
        if n.startswith("ck_") or n in ("tie_hi", "tie_lo", "cid", "far"):
            continue
        # the pin register's region: S-face registers in tile row 0, N-face in row 3; side from the register lane
        # (qc_gen.quad: the T centre lane x == XT is E)
        x = p.get("lane_x", (p["range_um"][0] + p["range_um"][1]) / 2)
        if p.get("region"):   # Q-CB16RST: regional reset pins name their region (pin register u_fab.u_rpin_<q> on ck_<q>)
            q = p["region"]
        elif sixteen:   # qc_gen.quad: column = #x-seams <= x (on-seam -> higher column); S-face pin registers row 0, N row 3
            q = f"c{sum(x >= v - 1e-6 for v in xs)}r{0 if p['face'] == 'S' else 3}"
        else:
            q = ("w" if x < xs[0] - 1e-6 else "e") + ("0" if p["face"] == "S" else "3")
        dom[q]["outputs" if n.startswith(("bco", "rs_o")) or n == "rs" else "inputs"].append(n)
    # region centres (centre feed): x = middle of the corridor between the region's two A0 tiles, y = tile-row centre
    a0w, a0h = C.get("a0", {}).get("w_um", 457.92), C.get("a0", {}).get("h_um", 1166.4)
    at = {t["inst"][4:]: t["at"] for t in C["tiles"]}
    centres = {}
    if sixteen:
        # one A0 tile per region: the area pin goes in the in-region corridor part (beside the tile; M7 over the A0 is
        # 85% OBS) that holds more of the region's station sinks, at its x centre, at the tile-row centre y
        corr = C["corridors"]
        bands = [0.0] + xs + [W]
        for q in regions:
            c, r = int(q[1]), int(q[3])
            tx0 = at[C["clocks"][q]["tiles"][0]][0]
            ty0 = at[C["clocks"][q]["tiles"][0]][1]
            sides = []
            for lo, hi in corr.values():
                lo2, hi2 = max(lo, bands[c]), min(hi, bands[c + 1])
                if hi2 - lo2 > 1.0 and (abs(hi - tx0) < 1.0 or abs(lo - (tx0 + a0w)) < 1.0):
                    n = sum(1 for k in C["stations"]["children"] if k["region"] == q and lo2 - 1 <= k["at"][0] <= hi2 + 1)
                    sides.append((n, hi2 - lo2, lo2, hi2))
            n, _, lo2, hi2 = max(sides)
            centres[q] = (round((lo2 + hi2) / 2, 3), round(ty0 + a0h / 2, 3))
    for q in ([] if sixteen else regions):
        xs = sorted(at[k][0] for k in C["clocks"][q]["tiles"])
        ys = [at[k][1] for k in C["clocks"][q]["tiles"]]
        centres[q] = (round((xs[0] + a0w + xs[-1]) / 2, 3), round(min(ys) + a0h / 2, 3))
    core = regions[0]
    sdc = [f"# Q-CLUSTER qfd_c_b16_dv: the {len(regions) - 1} non-core regional roots (generated by tools/qwen_cluster/qc_kit.py; DO NOT EDIT).",
           "# Same period / phase as core_clk (related, neighbour-relative die delivery); each boundary port is timed against the",
           "# clock of the region that holds its pin register (0.2 T in / out, as core_clk's ports).",
           "set ot_q_per [get_property [get_clocks core_clk] period]"]
    rest = [q for q in regions if q != core]
    sdc += [f"create_clock -name ck_{q} -period $ot_q_per [get_ports ck_{q}]" for q in rest]
    lst = " ".join(f"ck_{q}" for q in rest)
    sdc += [f"set_clock_uncertainty -setup 60 [get_clocks {{{lst}}}]", f"set_clock_uncertainty -hold 25 [get_clocks {{{lst}}}]"]
    if sixteen:
        # communicating region pairs (both directions) from the die-clock contract; core region = core_clk
        clk = {q: ("core_clk" if q == core else f"ck_{q}") for q in regions}
        pairs = json.loads(DIE_CLOCK.read_text())["communicating_pairs"]
        sdc.append(f"# Q-CL16-LAND: die delivery residual {DIE_RESIDUAL_PS} ps between the {len(pairs)} communicating region "
                   "pairs (both directions), setup and hold, on top of 60 / 25 (die_clock_contract.json obligation 2)")
        for k in sorted(pairs):
            a_, b_ = k.split("-")
            for f_, t_ in ((a_, b_), (b_, a_)):
                for kind in ("setup", "hold"):
                    sdc.append(f"set_clock_uncertainty -{kind} {BASE_UNC_PS[kind] + DIE_RESIDUAL_PS} "
                               f"-from [get_clocks {clk[f_]}] -to [get_clocks {clk[t_]}]")
        # Q-CLUSTER-LANDALL: every multi-bit crossing is landed.  The multicycle is CELL-based (-from the ring's cells -to the
        # read half's cells: exactly the bank / vld -> o paths), so the 1-bit reset hops of the same region pairs stay
        # single-cycle with the inter-region uncertainty above, and the in-region ring / read paths stay single-cycle
        lands = C.get("landings", {}).get("list", [])
        if lands:
            E_, D_ = {L["E"] for L in lands}, {L["D"] for L in lands}
            assert len(E_) == 1 and len(D_) == 1, "one E / D for every landing (qc_gen.py LAND_E / LAND_D)"
            E_, D_ = E_.pop(), D_.pop()
            sdc.append(f"# Q-CLUSTER-LANDALL: {len(lands)} landed crossings (LANDING-CONTRACT L5): ring -> read multicycle "
                       f"-setup {E_} -hold {D_ - 1}, window ({E_} - {D_}) T + t_hold < dL < {E_} T - t_cq - t_setup")
            sdc.append("set ot_qc_lands {" + " ".join(L["name"] for L in lands) + "}")
            sdc.append("set ot_qc_land_miss 0")
            sdc.append("foreach ot_ln $ot_qc_lands {")
            sdc.append("  set ot_lf [get_cells -quiet u_fab.u_land_${ot_ln}_w.*]")
            sdc.append("  set ot_lt [get_cells -quiet u_fab.u_land_${ot_ln}_r.*]")
            sdc.append("  if {[llength $ot_lf] == 0 || [llength $ot_lt] == 0} { incr ot_qc_land_miss; continue }")
            sdc.append(f"  set_multicycle_path -setup {E_} -from $ot_lf -to $ot_lt")
            sdc.append(f"  set_multicycle_path -hold {D_ - 1} -from $ot_lf -to $ot_lt")
            sdc.append("}")
            sdc.append('puts "OT_QC_LAND_SDC [expr {[llength $ot_qc_lands] - $ot_qc_land_miss}] of [llength $ot_qc_lands] landings constrained"')
    bits = {p["port"]: p["bits"] for p in ports}
    pat = lambda n: n if bits.get(n, 2) == 1 else f"{n}[*]"     # Q-CB16RST: scalar ports (rst_<q>) have no [*]
    for q in rest:
        for n in sorted(dom[q]["inputs"]):
            sdc.append(f"set_input_delay [expr {{0.2 * $ot_q_per}}] -clock ck_{q} [get_ports {{{pat(n)}}}]")
        for n in sorted(dom[q]["outputs"]):
            # exact bus name ('rs*' would also catch rs_i / rs_o once rs leaves the core region)
            sdc.append(f"set_output_delay [expr {{0.2 * $ot_q_per}}] -clock ck_{q} [get_ports {{{pat(n)}}}]")
    sdc.append(f"if {{!$::ot_ref_pre_cts}} {{ set_propagated_clock [get_clocks {{{lst}}}] }}")
    # QK-CB16 (10-18): post-CTS, every non-core region's boundary is referenced to ITS OWN propagated tree, exactly as the
    # generic die boundary (signoff.sdc QDM block) references core_clk's ports to the core tree.  The plain 0.2 T above is
    # the pre-CTS (ideal clock) form only: post-CTS it left the region clock's insertion L (1.1-2.1 ns) out of the input
    # min / output max, so diag16at stopped in hold repair at -1,531 ps on u_fab.u_ft_0/d[496] (rs_i -> its pin register,
    # region c1r3: input min 154 ps vs capture L ~1.7 ns) and the bco / rs / rs_o outputs failed setup by ~L.  Reference =
    # the bus's own pin register(s), traversing transparent cells to a fixed point (outputs: the driving register).
    sdc += [
        "if {!$::ot_ref_pre_cts} {",
        "  proc ot_qc_pinreg_cks {bus dir} {",
        "    set out {}; set seen [dict create]",
        "    set pl [get_ports -quiet [format {%s[*]} $bus]]",
        "    if {![llength $pl]} { set pl [get_ports -quiet $bus] }",
        "    foreach port $pl {",
        "      set nets [get_nets -quiet [get_full_name $port]]",
        "      set visited_nets [dict create]",
        "      while {[llength $nets]} {",
        "        set next {}",
        "        foreach n $nets {",
        "          set nn [get_full_name $n]",
        "          if {[dict exists $visited_nets $nn]} { continue }",
        "          dict set visited_nets $nn 1",
        "          foreach pin [get_pins -quiet -of_objects $n] {",
        "            if {[string first / [get_full_name $pin]] < 0} { continue }",
        "            set pd [get_property $pin direction]",
        "            if {($dir eq \"in\" && $pd ne \"input\") || ($dir eq \"out\" && $pd ne \"output\")} { continue }",
        "            set c [get_cells -quiet -of_objects $pin]",
        "            if {![llength $c]} { continue }",
        "            set fn [get_full_name $c]",
        "            set ck [get_pins -quiet \"$fn/ck\"]",
        "            if {![llength $ck]} { set ck [get_pins -quiet \"$fn/CLK\"] }",
        "            if {[llength $ck]} {",
        "              if {![dict exists $seen $fn]} { dict set seen $fn 1; lappend out $ck }",
        "            } elseif {[regexp {^(BUF|HB|INV)} [get_property $c ref_name]]} {",
        "              foreach op [get_pins -quiet -of_objects $c] {",
        "                set od [get_property $op direction]",
        "                if {($dir eq \"in\" && $od eq \"output\") || ($dir eq \"out\" && $od eq \"input\")} { lappend next [get_nets -quiet -of_objects $op] }",
        "              }",
        "            }",
        "          }",
        "        }",
        "        set nets $next",
        "      }",
        "    }",
        "    return $out",
        "  }",
        "  catch {sta::worst_slack_cmd max}",
        "  set ot_qc_ib [expr {[info exists ::env(OT_IO_IN_BUDGET_PS)] ? $::env(OT_IO_IN_BUDGET_PS) : 0.2 * $ot_q_per}]",
        "  set ot_qc_ob [expr {[info exists ::env(OT_IO_OUT_BUDGET_PS)] ? $::env(OT_IO_OUT_BUDGET_PS) : 0.2 * $ot_q_per}]",
        "  set ot_qc_sk [expr {[info exists ::env(OT_IO_SKEW)] ? $::env(OT_IO_SKEW) : 90}]",
        "  set ot_qc_hk [expr {[info exists ::env(OT_IO_HOLD_SKEW)] ? $::env(OT_IO_HOLD_SKEW) : 50}]",
        "  set ot_qc_hki [expr {[info exists ::env(OT_IO_IN_HOLD_SKEW)] ? $::env(OT_IO_IN_HOLD_SKEW) : 0}]",
        "  set ot_qc_die [expr {[info exists ::env(OT_IO_HOLD_BUDGET)] && $::env(OT_IO_HOLD_BUDGET) eq \"die\"}]",
        "  set ot_qc_c [expr {[info exists ::env(OT_BH_LAUNCH_MIN_PS)] ? $::env(OT_BH_LAUNCH_MIN_PS) : 25}]",
        "  set ot_qc_u [expr {[info exists ::env(OT_BH_TILE_HOLD_UNC_PS)] ? $::env(OT_BH_TILE_HOLD_UNC_PS) : 25}]",
        "  set ot_qc_r [expr {[info exists ::env(OT_BH_ROUTE_RELIEF_PS)] ? $::env(OT_BH_ROUTE_RELIEF_PS) : 0}]",
        "  set ot_qc_io_n 0",
        "  foreach {ot_qc_bus ot_qc_dir ot_qc_clk} {" + " ".join(
            f"{n} {d} ck_{q}" for q in rest for d, key in (("in", "inputs"), ("out", "outputs")) for n in sorted(dom[q][key])) + "} {",
        "    set ot_qc_a {}",
        "    foreach p [ot_qc_pinreg_cks $ot_qc_bus $ot_qc_dir] {",
        "      set a0 [get_property $p arrival_min_rise]; set a1 [get_property $p arrival_max_rise]",
        "      if {[string is double -strict $a0] && [string is double -strict $a1]} { lappend ot_qc_a $a0 $a1 }",
        "    }",
        "    if {![llength $ot_qc_a]} { error \"OT_QC_IO: no pin register clock arrival found for $ot_qc_bus ($ot_qc_dir)\" }",
        "    set ot_qc_a [lsort -real $ot_qc_a]; set lmin [lindex $ot_qc_a 0]; set lmax [lindex $ot_qc_a end]",
        "    set pp [get_ports -quiet [format {%s[*]} $ot_qc_bus]]",
        "    if {![llength $pp]} { set pp [get_ports $ot_qc_bus] }",
        "    if {$ot_qc_dir eq \"in\"} {",
        "      set_input_delay [expr {$ot_qc_ib + $lmax + $ot_qc_sk}] -max -clock $ot_qc_clk $pp",
        "      set_input_delay [expr {$ot_qc_die ? $lmin + $ot_qc_c + $ot_qc_u + $ot_qc_r : $lmin - $ot_qc_hki}] -min -clock $ot_qc_clk $pp",
        "    } else {",
        "      set_output_delay [expr {$ot_qc_ob - $lmax + $ot_qc_sk}] -max -clock $ot_qc_clk $pp",
        "      set_output_delay [expr {$ot_qc_die ? $ot_qc_u + $ot_qc_r - $lmin - $ot_qc_c : 0 - $lmin - $ot_qc_hk}] -min -clock $ot_qc_clk $pp",
        "    }",
        "    incr ot_qc_io_n",
        "    puts \"OT_QC_IO $ot_qc_bus $ot_qc_dir $ot_qc_clk L $lmin..$lmax ([expr {[llength $ot_qc_a] / 2}] pin registers) die=$ot_qc_die\"",
        "  }",
        "  puts \"OT_QC_IO_SDC $ot_qc_io_n buses referenced to their region tree\"",
        "}"]
    # Q-CLUSTER4 (coordinator 0de+6 (2)): cid / far are identity straps from the instance's own tie cells (constant per
    # instance; they reach only hard-child pins: A0 tile_id, xstn sidx), so case analysis is the true constraint, not a mask
    sdc += ["set_case_analysis 0 [get_ports {cid[*]}]", "set_case_analysis 0 [get_ports far]"]
    (ROOT / "physical/qcluster/qfd_c_b16_dv_quadrants.sdc").write_text("\n".join(sdc) + "\n")
    if a.feed == "centre" and sixteen:
        # 16 x 'ck_<q>:x:y' overflows an env value the kit generator path-checks (ENAMETOOLONG): one line per pin in a file
        (ROOT / f"physical/qcluster/{name}_ck_centres.txt").write_text(
            "".join(f"ck_{q}:{centres[q][0]}:{centres[q][1]}\n" for q in regions))
    spec = dict(
        name=name, top="qfd_c_b16_dv", kind="cluster",
        diagnostic=a.mode == "diag",
        sources=bb + FABRIC_SRC,
        params={}, clock=a.engine, child_clock_ref="pin" if a.engine == "spine" else None,
        clock_port=cks[0], clock_ports=cks,
        orfs_vars=({"OT_SPINE_PORTS": ",".join(cks), "OT_SPINE_MACRO_LEAF": "1", "OT_SPINE_MACRO_PIN_LEAF": "1"}
                   if a.engine == "spine" else {}) | {
                   "PRE_GLOBAL_PLACE_TCL": "physical/qcluster/fabric_sites_place.tcl",
                   "PRE_DETAIL_PLACE_TCL": "physical/qcluster/fabric_sites_release.tcl",
                   "OT_QC_SITES": "physical/qcluster/qfd_c_b16_dv_sites.tsv",
                   # diag1 (10-17): timing-driven GPL inserted 142,847 buffers on the not-yet-placed station logic
                   # (+279% area) and the step ran out of its 48 GB; the fabric is site-placed, so GPL only spreads the
                   # remaining station / tie logic: no timing- or routability-driven passes
                   "GPL_TIMING_DRIVEN": "0", "GPL_ROUTABILITY_DRIVEN": "0"} | (
                   (({"OT_QC_CK_CENTRES_FILE": f"physical/qcluster/{name}_ck_centres.txt"} if sixteen else
                     {"OT_QC_CK_CENTRES": ",".join(f"ck_{q}:{centres[q][0]}:{centres[q][1]}" for q in regions)})
                    | {"OT_QC_CK_LAYER": "M7"}) | ({"OT_SPINE_SYM": "1"} if a.engine == "spine" else {})
                   if a.feed == "centre" else {}),
        **({"pre_cts_extra": ["physical/qcluster/qfd_c_b16_dv_centre_feed.tcl"]} if a.feed == "centre" else {}),
        io_flop_at_pins=False,
        sdc_extra=["physical/qcluster/qfd_c_b16_dv_quadrants.sdc"],
        reset_ports=[p["port"] for p in ports if p["port"].startswith("rst_")] or ["rst_n"],
        # 4.32: the station tiles sit on the 4.32 lattice (L / R strip stations 4.32 from the A0 faces and the edge cannot
        # be on 43.2); the A0 origins stay multiples of 43.2.  4.32 is track-safe for the station pins (M3 / M4 / M5).
        outline=dict(w=W, h=H, exact=True), child_lattice_um=4.32,
        # the stations need sub-20-um channels by construction (43.2-um L / R strips; corridor lanes 49 um apart): diag
        # kits admit them as a measured probe (abut_plan + job.hold_merge); a production kit needs the coordinator's call
        abut_plan=dict(channel_um=8.6, edge_um=6.4, why="Q-CLUSTER4 channel rule (coordinator 0de+6 (4)): < 20 um only between "
                       "pin-free sides (station E/W sides 8.64 apart, station <-> cluster W/E edge 8.64 = 6.48 from the core edge) or sized to the bits "
                       "crossing (xstn tap face <-> A0 tap face 8.64: 508 straight stubs); every station side facing A0 pins "
                       ">= 21.6, stacked station pin faces >= 21.6"),
        children=tiles, macros=[],
        pins=faces,
        pin_ranges={p["port"]: p["range_um"] for p in ports},
        pin_layers={p["port"]: p["layer"] for p in ports},
        route=dict(pd=0.5, threads=16, peak_ram_gb=192, pin_v="M5", pin_h="M4 M6", macro_halo_um=5.4),
        cluster_level=2, recipe=4, hold_budget="die", inhold=False, outhold=False,
        pin_regs=dict(enable=False, reason="qc_gen.py RTL registers every data pin in the S / N strip (bc / rs_i entry "
                                           "flops, bco / rs / rs_o exit flops, rst_n pin register); cid / far are static "
                                           "straps from the instance's own tie cells"),
        relay_sites="results/arch/qwen_cluster_1017/relay_sites_dv.json",
        structural_change="Q-CLUSTER3 (coordinator 0de+5): the ~78k fabric flops at 282 stage sites are hardened into 167 "
                          "replicated station tiles (qfd_c_stn516 x52, qfd_c_stn514 x83, qfd_c_xstn/xstnw x8+8; own clock "
                          "pin + local tree, flop-first / flop-last); each regional root drives only child clock pins "
                          "(stations + A0 entries) + the 133 soft reset stages: the 8-root gates measured TritonCTS "
                          "1.5-1.9 ns / 400-530 ps and spine 4.1 ns on the loose flops.  Base: Q-CLUSTER qfd_c_b16_dv (SPEC.md): CB cluster with A/T/B corridors 129.6 um (cut 1.79 -> 0.90 "
                          "worst, trunks <= 0.54), eight regional clock roots (side x tile row, <= 13.4k sinks each; "
                          "the four quadrant roots measured 26,984 sinks / spread 3.9 ns), registered pins hold_budget die, DV "
                          "rs_i -> rs_o feedthrough (14 edges) in T.",
        job=dict(owner="Claude:Q-CLUSTER" + a.tag, branch=a.branch or ("claude/qcluster16-1018" if a.tag == "16" else "claude/qcluster-1017"), tag=("dv0" if a.mode == "real" else f"diag{a.tag or (5 if a.feed == 'centre' else 4)}") + ("c" if a.feed == "centre" else "") + ("" if a.engine == "spine" else "t"),
                 purpose="qfd_c_b16_dv cluster (dv2r8f, 48 instances)", submit=a.mode == "real",
                 **({} if a.mode == "real" else {"hold_merge": "Q-CLUSTER3 diagnostic: stand-in A0 + station abstracts"}),
                 **({"extra_paths": ["results/arch/qwen_cluster_1017"]} if a.tag.startswith("16") else {}),
                 benches=[dict(name="qcluster_fabric", cmd="bash tools/qwen_cluster/bench.sh bench_out",
                               expect="pass", pass_regex="BENCH_EXIT 0", threads=8, peak_ram_gb=12)] + (
                     [dict(name="qcluster16_lockstep", cmd="bash tools/qwen_cluster/bench_lockstep.sh lockstep_out",
                           expect="pass", pass_regex="LOCKSTEP_EXIT 0", threads=8, peak_ram_gb=12)] if a.tag.startswith("16") else [])))
    out = ROOT / "tools/ref_tile/specs_qcluster" / f"{name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(spec, indent=1) + "\n")
    print(out)


if __name__ == "__main__":
    main()
