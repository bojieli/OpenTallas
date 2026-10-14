#!/usr/bin/env python3
"""Plan of the S81 capture cluster dsfd_sp_capture_c (el1013 capture, 2026-10-13): wires + closed children, one clock
entry pin per child, no cluster tree.

    python3 tools/s81_ph/capc_plan.py [--check]

Writes (from the children's routed LEFs and insertion.json):
  tools/ref_tile/specs_s81sp/s81sp_capc_cl.json        the ref_tile cluster spec (children, placement, benches)
  physical/s81_ph_views/capture/capc_pins.tcl          place_pin for every cluster pin, straight in front of the child
                                                       pin it wires to (N / S faces, M5, one pin a track)
  physical/s81_ph_views/capture/capc_clocks.sdc        the stream clock on every ck_* entry and the serial clock on
                                                       every ckv_* entry, each with source latency -R of its child (the
                                                       die delivers every entry at phi - R, clock delivery rule 10-13)
  physical/s81_ph_views/capture/capc_plan.json         placement, hop lengths, R per entry (for the die lead)
Placement (cluster 1728.0 x 561.6, children MX = inputs N, outputs S): x[g] at (X_g, 43.2), g2[g] at (X_g, 336.96),
ctl at (820.8, 172.8), the station relays R0 in one row at y 519.552 (0.576-um track lattice, 35.136 pitch = 15.12 +
20.016 channel), dsfd_capt_cd under the control tile.  Every block keeps >= 20 um to its neighbours and the core edge.
"""
import argparse, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W_CL, H_CL = 1728.0, 561.6
XG = [129.6 + 172.8 * g for g in range(4)] + [950.4 + 172.8 * g for g in range(4)]
Y_X, Y_G, Y_R = 43.2, 336.96, 519.552
CTL = (820.8, 172.8)
CD = (842.4, 86.4)
RW0, RE0, RP = 435.456, 907.776, 35.136
V = {"g2": "physical/ref_tile/dsfd_capt_g2_m5/views/dsfd_capt_g2", "x": "physical/ref_tile/dsfd_capt_x_m5/views/dsfd_capt_x",
     "ctl": "physical/ref_tile/dsfd_capt_ctl_m5/views/dsfd_capt_ctl", "cd": "physical/ref_tile/dsfd_capt_cd/views/dsfd_capt_cd"}
RV = lambda n, d: f"physical/ref_tile/s81_rly_{n}_{d.lower()}/views/dsfd_rly_{n}_{d}"
OUT_SPEC = ROOT / "tools/ref_tile/specs_s81sp/s81sp_capc_cl.json"
OUT_PINS = ROOT / "physical/s81_ph_views/capture/capc_pins.tcl"
OUT_SDC = ROOT / "physical/s81_ph_views/capture/capc_clocks.sdc"
OUT_PLAN = ROOT / "physical/s81_ph_views/capture/capc_plan.json"


def lef(view):
    p = ROOT / view / (Path(view).name + ".lef")
    t = p.read_text()
    m = re.search(r"SIZE ([\d.]+) BY ([\d.]+)", t)
    pins = {}
    for pm in re.finditer(r"\n\s*PIN (\S+)(.*?)\n\s*END \1", t, re.S):
        r = re.search(r"LAYER (\S+) ;\s+RECT\s+([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+)", pm.group(2))
        if r:
            x0, y0, x1, y1 = map(float, r.groups()[1:])
            pins[pm.group(1)] = ((x0 + x1) / 2, (y0 + y1) / 2, r.group(1))
    return float(m.group(1)), float(m.group(2)), pins


def ins(view):
    d = json.loads((ROOT / view / "insertion.json").read_text())
    return d["tt"]["boundary"]["mean"] if d["tt"].get("boundary") else d["tt"]["all"]["mean"]


def trk(v):
    return round(round((v - 0.012) / 0.048) * 0.048 + 0.012, 3)


def build():
    L = {k: lef(v) for k, v in V.items()}
    blocks, kids = [], []

    def add(view, inst, x, y, orient="R0"):
        w, h, _ = lef(view)
        blocks.append((inst, x, y, w, h))
        kids.append({"view": view, "count": 1, "inst": inst, "at": [round(x, 3), round(y, 3)], **({"orient": orient} if orient != "R0" else {})})

    add(V["ctl"], "u_ctl", *CTL, "MX")
    for g in range(8):
        add(V["g2"], f"*g_t?{g}?*u_g", XG[g], Y_G, "MX")
        add(V["x"], f"*g_t?{g}?*u_x", XG[g], Y_X, "MX")
    add(V["cd"], "u_cd", *CD)
    rel = {}                                             # relay instance -> (x, view)
    k = 0
    for g in range(4):                                   # W half, from the W: g0 (ka kb sb), g1, g2, g3, then sn
        for nm, (n, d) in (("u_ka", (68, "EW")), ("u_kb", (54, "EW")), ("u_sb", (2, "WE"))):
            rel[(g, nm)] = (RW0 + RP * k, RV(n, d)); k += 1
    rel[(8, "u_sn")] = (RW0 + RP * k, RV(68, "EW"))
    rel[(9, "u_cr")] = (RE0, RV(15, "SN"))
    k = 1
    for g in range(4, 8):
        for nm, (n, d) in (("u_ka", (63, "WE")), ("u_kb", (63, "WE")), ("u_sb", (2, "EW"))):
            rel[(g, nm)] = (RE0 + RP * k, RV(n, d)); k += 1
    for (g, nm), (x, view) in rel.items():
        add(view, nm if g >= 8 else f"*g_t?{g}?*{nm}", x, Y_R)
    # ---- geometry: every pair >= 20 um apart in x or y, every block >= 20 um from the core edge
    bad = []
    for i, (na, ax, ay, aw, ah) in enumerate(blocks):
        for f, d in (("W", ax - 2.16), ("E", W_CL - 2.16 - ax - aw), ("S", ay - 2.16), ("N", H_CL - 2.16 - ay - ah)):
            if d < 20 - 1e-6: bad.append(f"{na} {d:.2f} um from the {f} core edge")
        for nb, bx, by, bw, bh in blocks[i + 1:]:
            gap = max(max(bx - ax - aw, ax - bx - bw), max(by - ay - ah, ay - by - bh))
            if gap < 20 - 1e-6: bad.append(f"{na} / {nb} gap {gap:.2f}")
    # ---- pins
    pins, used = [], {"N": set(), "S": set()}

    def pin(name, face, x):
        t = trk(x)
        while t in used[face]: t = round(t + 0.048, 3)
        used[face].add(t)
        pins.append((name, face, t))

    _, _, pg = L["g2"]; _, _, px = L["x"]; _, _, pc = L["ctl"]
    for g in range(8):
        pin(f"ck_g[{g}]", "N", XG[g] + pg["ck[0]" if "ck[0]" in pg else "ck"][0])
    pin("ck_c", "N", CTL[0] + pc["ck[0]" if "ck[0]" in pc else "ck"][0])
    for g in range(8):
        for i in range(848):
            pin(f"f_gather[{848 * g + i}]", "N", XG[g] + pg[f"f_row[{i}]"][0])
    for i in range(163):
        pin(f"f_gather[{6784 + i}]", "N", CTL[0] + pc[f"f_ctl[{i}]"][0])
    for g in range(8):
        pin(f"ck_x[{g}]", "N", XG[g] - 12.0)             # down the channel W of the column to dsfd_capt_x's N-face clock pin
        for nm, port in (("u_ka", "ck_ka"), ("u_kb", "ck_kb"), ("u_sb", "ck_sb")):
            pin(f"{port}[{g}]", "N", rel[(g, nm)][0] + 9.6)
    pin("ck_sn", "N", rel[(8, "u_sn")][0] + 9.6)
    _, _, pr = lef(RV(15, "SN"))
    for i in range(12):
        pin(f"t_cd[{i}]", "N", RE0 + pr[f"o[{i}]"][0])
    pin("ckv_r", "N", RE0 + 15.12 + 3.0)
    for g in range(8):
        pin(f"ckv_x[{g}]", "S", XG[g] + px["ckv[0]" if "ckv[0]" in px else "ckv"][0])
        order = sorted(range(1664), key=lambda i: px[f"t_vm[{i}]"][0])
        for n, i in enumerate(order):
            pin(f"t_vm[{1664 * g + i}]", "S", XG[g] + 19.4 + 0.048 * n)
    order = sorted(range(64), key=lambda i: px[f"t_st[{i}]"][0])
    for n, i in enumerate(order):
        pin(f"t_vm[{13312 + i}]", "S", XG[3] + 100.2 + 0.048 * n)
    pin("ckv_d", "S", CD[0] + 15.12 + 4.0)
    pin("rst", "S", 870.0); pin("rsv", "S", 874.0)
    tcl = ["# generated by tools/s81_ph/capc_plan.py: dsfd_sp_capture_c cluster pins, each straight in front of the child pin",
           "# it wires to.  N: f_gather over the g2 columns / the control tile, t_cd over its relay, the stream clock",
           "# entries; S: t_vm under the x columns, the serial clock entries, resets.  M5, one pin a track."]
    for nm, face, x in pins:
        tcl.append(f"place_pin -pin_name {{{nm}}} -layer M5 -location {{{x:.3f} {0.0 if face == 'S' else H_CL}}} "
                   "-pin_size {0.024 0.192} -force_to_die_boundary")
    # ---- clocks
    R = {"ck_g": ins(V["g2"]), "ck_x": ins(V["x"]), "ck_c": ins(V["ctl"]), "ckv_d": ins(V["cd"]), "ckv_r": ins(RV(15, "SN")),
         "ck_sn": ins(RV(68, "EW"))}
    sdc = ["# generated by tools/s81_ph/capc_plan.py (ref_tile spec sdc_extra): the capture cluster has one clock ENTRY per child.",
           "# The die delivers every entry at phi - R of its child (R = the child's routed TT boundary insertion), so each",
           "# entry carries source latency -R here and the children's flops line up; the cluster adds wires, no tree.",
           "# ckv_x has no measured serial insertion in the dsfd_capt_x view (its insertion.json is the stream clock): 0.",
           "set ot_cc_p [get_property [get_clocks core_clk] period]",
           "create_clock -name core_clk -period $ot_cc_p [get_ports {ck_c ck_g[*] ck_x[*] ck_ka[*] ck_kb[*] ck_sb[*] ck_sn}]",
           "create_clock -name ser_clk -period [expr {$ot_cc_p * 4.0 / 3.0}] [get_ports {ckv_x[*] ckv_d ckv_r}]",
           "set_clock_uncertainty -setup 60 [all_clocks]", "set_clock_uncertainty -hold 25 [all_clocks]",
           "if {![catch {get_property [get_clocks core_clk] is_propagated} ot_cc_pr] && $ot_cc_pr eq \"1\"} { set_propagated_clock [all_clocks] }",
           "catch {unset_input_delay [get_ports {ck_c ck_g[*] ck_x[*] ck_ka[*] ck_kb[*] ck_sb[*] ck_sn ckv_x[*] ckv_d ckv_r}]}",
           "set_false_path -from [get_ports {rst[*] rsv[*]}]"]
    for port, r in (("ck_g[*]", R["ck_g"]), ("ck_x[*]", R["ck_x"]), ("ck_c", R["ck_c"]),
                    ("ckv_d", R["ckv_d"]), ("ckv_r", R["ckv_r"])):
        sdc.append(f"set_clock_latency -source {-r:.1f} [get_ports {{{port}}}]")
    for (g, nm), (x, view) in rel.items():
        if g < 8:
            port = {"u_ka": "ck_ka", "u_kb": "ck_kb", "u_sb": "ck_sb"}[nm]
            sdc.append(f"set_clock_latency -source {-ins(view):.1f} [get_ports {{{port}[{g}]}}]")
    sdc.append(f"set_clock_latency -source {-R['ck_sn']:.1f} [get_ports {{ck_sn}}]")
    sdc += ["# serial-domain outputs: 0.2 T of the serial period against ser_clk (they were set against core_clk above)",
            "set ot_cc_so [get_ports {t_vm[*] t_cd[*]}]", "unset_output_delay $ot_cc_so",
            "set_output_delay [expr {0.2 * $ot_cc_p * 4.0 / 3.0}] -clock ser_clk $ot_cc_so"]
    EX = ["tools/s81_ph", "rtl/v41rom", "rtl/proto", "rtl/gpu", "rtl/hdc", "rtl/common", "rtl/dsrom_sys/rd64_capture",
          "rtl/dsrom_sys/s81_ph", "rtl/dsrom_sys/s81_glue", "physical/s81_ph_views/capture"]
    spec = {"name": "s81sp_capc_cl", "top": "dsfd_sp_capture_c", "kind": "cluster",
            "sources": ["rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_sp_capture_c_cl.sv"], "params": {},
            "clock_port": "ck_c", "reset_ports": ["rst", "rsv"], "clock": "cts", "child_lattice_um": 0.576,
            "outline": {"w": W_CL, "h": H_CL},
            "sdc_extra": [str(OUT_SDC.relative_to(ROOT))], "io_tcl": str(OUT_PINS.relative_to(ROOT)),
            "children": kids,
            "pins": {"N": ["f_gather", "t_cd", "ck_g", "ck_x", "ck_c", "ck_ka", "ck_kb", "ck_sb", "ck_sn", "ckv_r"], "S": ["t_vm", "ckv_x", "ckv_d", "rst", "rsv"]},
            "refglob": "*", "recipe": 2, "route": {"pd": 0.5, "threads": 16, "peak_ram_gb": 64},
            "slot_change_request": "el1011-s81die.log 2026-10-13 17:58 PT [el1013 capture -> s81-die lead]: per-child clock entry pins (ck_g / ck_x / ck_c / ck_ka / ck_kb / ck_sb / ck_sn on N, ckv_x / ckv_d on S, ckv_r on N) instead of one ck pin, t_cd on N at x ~915, outline 1728.0 x 561.6 on the 8.64-um cluster lattice, cluster layer rule (signals <= M6, PG M7), pin bundles in front of the child pins (physical/s81_ph_views/capture/capc_pins.tcl)",
            "structural_change": "the cluster has no logic and no clock tree: 872 station flops -> closed die relay masters, DONE word -> leaf dsfd_capt_cd + one relay stage, one clock entry pin per child (the single-pin spine of the first cluster measured 1,222 ps insertion / 226 ps spread)",
            "why_floorplan": "1728.0 x 561.6 (contract v16 + 0.024). 8 columns at 172.8 pitch: dsfd_capt_x MX at y 43.2, dsfd_capt_g2 MX at y 336.96 (23.76 over the x row; 8.64 lower than v16 so the N channel is 62.6 um: a 15.12-um relay needs 55.2), control tile in the centre gap; 26 relays in one row at y 519.552 between the control tile's N-face pins and the g2 N-face pins (hops <= ~450 um each side), dsfd_capt_cd under the control tile with its relay beside it. Cluster wires: N channel 62.6 um (k buses 8 x 99 b + status, f_gather drops straight onto the g2 pins), g2 -> x abutting columns (832 b each over 23.8 um), t_vm straight down 43 um. Cut of the N channel W-E at the control tile: 4 x 101 b each way over ~4k M2 / M4 / M6 tracks: 0.10.",
            "job": {"owner": "Claude:el1013-s81-capture", "branch": "s81-spwfc-1013", "tag": "v2",
                    "purpose": "S81 capture element dsfd_sp_capture_c as a hardened cluster over the CLOSED M5 leaves (8 x dsfd_capt_g2, 8 x dsfd_capt_x, dsfd_capt_ctl, dsfd_capt_cd) and 26 closed die relay masters: wires only, one clock entry pin per child (the die delivers each at phi - R), no cluster tree.",
                    "benches": [
                        {"name": "capc_lockstep_exact", "cmd": "bash tools/s81_ph/capc_bench.sh {RUN}/bench t1 'mix mix11 mix12 mix13 trace err over range rreq'", "expect": "pass", "pass_regex": "^CAPC_BENCH PASS", "min_count_regex": "CAPC_BENCH PASS cases=([0-9]+)", "threads": 12, "peak_ram_gb": 32, "needs": ["verilator"]},
                        {"name": "capc_mut_kswap", "cmd": "bash tools/s81_ph/capc_bench.sh {RUN}/bench m1 'mix' S81PH_CAPC_MUT_KSWAP", "expect": "fail", "fail_regex": "CAPC_BENCH FAIL", "threads": 8, "peak_ram_gb": 16, "needs": ["verilator"]}],
                    "extra_paths": EX, "views_to": "physical/ref_tile/s81sp_capc_cl/views", "record_to": "results/rtl/ref_tile/s81sp_capc_cl"}}
    plan = {"schema": "opentallas.s81.capture_cluster_plan.v1", "outline": [W_CL, H_CL], "geometry_violations": bad,
            "clock_entries_R_ps": {k: round(v, 1) for k, v in R.items()},
            "blocks": [{"inst": n, "x": round(x, 3), "y": round(y, 3), "w": w, "h": h} for n, x, y, w, h in blocks],
            "pins": {"N": sum(1 for p in pins if p[1] == "N"), "S": sum(1 for p in pins if p[1] == "S")}}
    return spec, "\n".join(tcl) + "\n", "\n".join(sdc) + "\n", plan


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    spec, tcl, sdc, plan = build()
    outs = ((OUT_SPEC, json.dumps(spec, indent=1) + "\n"), (OUT_PINS, tcl), (OUT_SDC, sdc), (OUT_PLAN, json.dumps(plan, indent=1) + "\n"))
    if a.check:
        ok = all(p.exists() and p.read_text() == t for p, t in outs)
        print("capc_plan: " + ("current" if ok else "STALE")); return 0 if ok else 1
    for p, t in outs:
        p.parent.mkdir(parents=True, exist_ok=True); p.write_text(t)
    print(f"capc_plan: {len(plan['blocks'])} blocks, pins N {plan['pins']['N']} S {plan['pins']['S']}, R {plan['clock_entries_R_ps']}")
    for b in plan["geometry_violations"]: print("GEOMETRY", b)
    return 1 if plan["geometry_violations"] else 0


if __name__ == "__main__":
    sys.exit(main())
