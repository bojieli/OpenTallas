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
V = {"g2": "physical/ref_tile/dsfd_capt_g2_m5/views/dsfd_capt_g2", "x": "physical/ref_tile/dsfd_capt_x8_dual/views/dsfd_capt_x8_dual",
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


def ins(view, port=None):
    d = json.loads((ROOT / view / "insertion.json").read_text())
    if port is not None:
        clocks = d.get("clock_measurements", {})
        d = clocks.get(port) or clocks.get(port + "[0]")
        if not d:
            raise ValueError(f"{view}: measured insertion missing for clock {port}")
    return d["tt"]["boundary"]["mean"] if d["tt"].get("boundary") else d["tt"]["all"]["mean"]


def trk(v):
    return round(round((v - 0.012) / 0.048) * 0.048 + 0.012, 3)


def build(assigned):
    L = {k: lef(v) for k, v in V.items()}
    blocks, kids = [], []

    def add(view, inst, x, y, orient="R0"):
        w, h, _ = lef(view)
        blocks.append((inst, x, y, w, h))
        kids.append({"view": view, "count": 1, "inst": inst, "at": [round(x, 3), round(y, 3)], **({"orient": orient} if orient != "R0" else {})})

    add(V["ctl"], "u_ctl", *CTL, "MX")
    for g in range(8):
        add(V["g2"], f"*g_t?{g}?*u_g", XG[g], Y_G, "MX")
        for half in range(2):
            add(V["x"], f"*g_t?{g}?*u_x{half}", XG[g] - 11.088 + 80.496 * half, Y_X, "MX")
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
    # The die owns all per-bit placement, including clock entries. Never reorder.
    assignment = json.loads(assigned.read_text())
    if assignment["master"] != "dsfd_sp_capture_c" or assignment["outline_um"] != [W_CL, H_CL]:
        raise ValueError("capture assignment master/outline mismatch")
    expected = {"ck_g": 8, "ck_x": 16, "ck_c": 1, "ck_ka": 8, "ck_kb": 8, "ck_sb": 8,
                "ck_sn": 1, "ckv_x": 16, "ckv_d": 1, "ckv_r": 1, "rst": 1, "rsv": 1,
                "f_gather": 6947, "t_vm": 13376, "t_cd": 12}
    if set(assignment["ports"]) != set(expected):
        raise ValueError("capture assigned port set differs from 68-clock RTL")
    pins, tcl = [], [f"# Die assigned capture pins: {assigned}"]
    scalars = {"ck_c", "ck_sn", "ckv_d", "ckv_r"}
    for port, count in expected.items():
        rec = assignment["ports"][port]
        if rec["bits"] != count or len(rec["per_bit"]) != count:
            raise ValueError(f"{port}: assigned bit count differs from RTL")
        for bit, (face, layer, along, depth) in enumerate(rec["per_bit"]):
            if face not in ("N", "S"):
                raise ValueError(f"{port}: unexpected assigned face {face}")
            name = port if count == 1 else f"{port}[{bit}]"
            pins.append((name, face, along))
            tcl.append(f"place_pin -pin_name {{{name}}} -layer {layer} "
                       f"-location {{{along:.3f} {H_CL if face == 'N' else 0.0}}} "
                       f"-pin_size {{0.024 {depth}}} -force_to_die_boundary")
    # ---- clocks
    R = {"ck_g": ins(V["g2"]), "ck_x": ins(V["x"], "ck"), "ckv_x": ins(V["x"], "ckv"), "ck_c": ins(V["ctl"]), "ckv_d": ins(V["cd"]), "ckv_r": ins(RV(15, "SN")),
         "ck_sn": ins(RV(68, "EW"))}
    for (g, nm), (x, view) in rel.items():
        if g < 8:
            port = {"u_ka": "ck_ka", "u_kb": "ck_kb", "u_sb": "ck_sb"}[nm]
            R[f"{port}[{g}]"] = ins(view)
    # One synchronous clock per source port: ETM exports require unambiguous
    # single-port references. All core entries keep the same phase and period,
    # all serial entries keep the same phase and 4:3 period; every path is timed.
    sdc = ["# capture has no logic/tree; each entry supplies phi-R to one child",
           "set ot_cc_p [get_property [get_clocks core_clk] period]"]
    clocks = {}
    for port, count in expected.items():
        if not port.startswith("ck"): continue
        for bit in range(count):
            pin = port if port in scalars else f"{port}[{bit}]"
            name = "core_clk" if port == "ck_c" else f"cap_{port}_{bit}"
            clocks[pin] = name
            period = "[expr {$ot_cc_p * 4.0 / 3.0}]" if port.startswith("ckv") else "$ot_cc_p"
            r = R.get(pin, R.get(port))
            if r is None: raise ValueError(f"clock insertion missing: {pin}")
            sdc += [f"create_clock -name {name} -period {period} [get_ports {{{pin}}}]",
                    f"unset_input_delay [get_ports {{{pin}}}]",
                    f"set_clock_latency -source {-r:.1f} [get_ports {{{pin}}}]"]
    sdc += ["set_clock_uncertainty -setup 60 [all_clocks]", "set_clock_uncertainty -hold 25 [all_clocks]",
            "set_false_path -from [get_ports {rst[*] rsv[*]}]",
            "unset_output_delay [get_ports {t_vm[*] t_cd[*]}]"]
    for half in range(16):
        output = " ".join(f"t_vm[{bit}]" for bit in range(832*half,832*(half+1)))
        sdc.append(f"set_output_delay [expr {{0.2 * $ot_cc_p * 4.0 / 3.0}}] -clock {clocks[f'ckv_x[{half}]']} [get_ports {{{output}}}]")
    tail = " ".join(f"t_vm[{bit}]" for bit in range(13312,13376))
    sdc += [f"set_output_delay [expr {{0.2 * $ot_cc_p * 4.0 / 3.0}}] -clock {clocks['ckv_x[6]']} [get_ports {{{tail}}}]",
            f"set_output_delay [expr {{0.2 * $ot_cc_p * 4.0 / 3.0}}] -clock {clocks['ckv_r']} [get_ports {{t_cd[*]}}]"]
    EX = ["tools/s81_ph", "rtl/v41rom", "rtl/proto", "rtl/gpu", "rtl/hdc", "rtl/common", "rtl/dsrom_sys/rd64_capture",
          "rtl/dsrom_sys/s81_ph", "rtl/dsrom_sys/s81_glue", "physical/s81_ph_views/capture"]
    spec = {"name": "s81sp_capc_cl", "top": "dsfd_sp_capture_c", "kind": "cluster",
            "sources": ["rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_sp_capture_c_cl.sv"], "params": {},
            "signal_max_layer": "M6", "clock_port": "ck_c", "reset_ports": ["rst", "rsv"], "clock": "cts", "child_lattice_um": 0.576,
            "outline": {"w": W_CL, "h": H_CL},
            "sdc_extra": [str(OUT_SDC.relative_to(ROOT))], "io_tcl": str(OUT_PINS.relative_to(ROOT)),
            "children": kids,
            "pins": {"N": ["f_gather", "t_cd", "ck_g", "ck_x", "ck_c", "ck_ka", "ck_kb", "ck_sb", "ck_sn", "ckv_r"], "S": ["t_vm", "ckv_x", "ckv_d", "rst", "rsv"]},
            "refglob": "*", "recipe": 2, "route": {"pd": 0.5, "threads": 16, "peak_ram_gb": 64},
            "slot_change_request": "el1011-s81die.log 2026-10-13 17:58 PT [el1013 capture -> s81-die lead]: per-child clock entry pins (ck_g / ck_x / ck_c / ck_ka / ck_kb / ck_sb / ck_sn on N, ckv_x / ckv_d on S, ckv_r on N) instead of one ck pin, t_cd on N at x ~915, outline 1728.0 x 561.6 on the 8.64-um cluster lattice, cluster layer rule (signals <= M6, PG M7), pin bundles in front of the child pins (physical/s81_ph_views/capture/capc_pins.tcl)",
            "structural_change": "the cluster has no logic and no clock tree: 872 station flops -> closed die relay masters, DONE word -> leaf dsfd_capt_cd + one relay stage, one clock entry pin per child (the single-pin spine of the first cluster measured 1,222 ps insertion / 226 ps spread)",
            "why_floorplan": "1728.0 x 561.6 (contract v16 + 0.024). 8 columns at 172.8 pitch: dsfd_capt_x MX at y 43.2, dsfd_capt_g2 MX at y 336.96 (23.76 over the x row; 8.64 lower than v16 so the N channel is 62.6 um: a 15.12-um relay needs 55.2), control tile in the centre gap; 26 relays in one row at y 519.552 between the control tile's N-face pins and the g2 N-face pins (hops <= ~450 um each side), dsfd_capt_cd under the control tile with its relay beside it. Cluster wires: N channel 62.6 um (k buses 8 x 99 b + status, f_gather drops straight onto the g2 pins), g2 -> x abutting columns (832 b each over 23.8 um), t_vm straight down 43 um. Cut of the N channel W-E at the control tile: 4 x 101 b each way over ~4k M2 / M4 / M6 tracks: 0.10.",
            "job": {"owner": "Codex:s81-capture", "branch": "s81-spwfc-1013", "tag": "v3",
                    "purpose": "S81 capture element dsfd_sp_capture_c as a hardened cluster over the CLOSED M5 leaves (8 x dsfd_capt_g2, 16 x dsfd_capt_x8_dual, dsfd_capt_ctl, dsfd_capt_cd) and 26 closed die relay masters: wires only, one clock entry pin per child (the die delivers each at phi - R), no cluster tree.",
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
    ap.add_argument("--assigned-pins", type=Path, default=ROOT / "physical/s81_die_pins/v18/dsfd_sp_capture_c.json")
    a = ap.parse_args()
    spec, tcl, sdc, plan = build(a.assigned_pins)
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
