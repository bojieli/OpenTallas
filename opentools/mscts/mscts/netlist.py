"""Emit a built region tree (region.segments) as (1) a transistor-level SPICE deck and (2) Verilog + SPEF + OpenSTA Tcl,
so the SAME buffers and the SAME RC ladders are timed by circuit simulation and by STA.

Cells/technology are parameters (default ASAP7 BUFx24 RVT, NDR M8/M9 RC from clkplan.model).  Arrival = 50 % rising
crossing at every sink buffer input pin minus the one at the region root buffer input (both tools measure the same
reference).  Every buffer is non-inverting; the source is an ideal ramp through two pre-driver buffers.
"""
import math

CFG = dict(cell="BUFx24_ASAP7_75t_R", pin_in="A", pin_out="Y", sub_order=("VSS", "VDD", "A", "Y"),
           r_ohm_um=4.45, c_ff_um=0.11, pi_um=45.0, sink_load_ff=5.0, vdd={"TT": 0.70, "FF": 0.77},
           temp={"TT": 25, "FF": 0}, ramp_ps=40.0)


def _ladder(L, cfg):
    n = max(1, int(math.ceil(L / cfg["pi_um"] - 1e-9)))
    return n, cfg["r_ohm_um"] * L / n, cfg["c_ff_um"] * L / n


def spice(bufs, edges, root, sinks, corner, libdir, osdi, cfg=CFG, out_dat="arr.dat"):
    c = cfg
    v = c["vdd"][corner]
    L = [f"* opentools.mscts region tree {corner}", ".control", f"pre_osdi {osdi}", "set noaskquit", "run",
         f"wrdata {out_dat} v(i_{root}) " + " ".join(f"v(i_{s})" for s in sinks), "quit", ".endc", ".options klu",
         ".save v(i_" + root + ") " + " ".join(f"v(i_{s})" for s in sinks), f".temp {c['temp'][corner]}",
         f".include {libdir}/{corner}/models.sp", f".include {libdir}/{corner}/cells.sp",
         f"Vdd vdd 0 {v}", "Vss vss 0 0", f"Vin src 0 PWL(0 0 100p 0 {100 + c['ramp_ps']:.0f}p {v})",
         f"Xp1 vss vdd src p1 {c['cell']}", f"Xp2 vss vdd p1 i_{root} {c['cell']}"]
    for b in bufs:
        L.append(f"X{b} vss vdd i_{b} o_{b} {c['cell']}")
    for k, (d, ld, wl) in enumerate(edges):
        n, r, cc = _ladder(wl, c)
        prev = f"o_{d}"
        for j in range(n):
            nx = f"w{k}_{j}" if j < n - 1 else f"i_{ld}"
            L += [f"Ca{k}_{j} {prev} 0 {cc / 2:.5f}f", f"R{k}_{j} {prev} {nx} {r:.4f}", f"Cb{k}_{j} {nx} 0 {cc / 2:.5f}f"]
            prev = nx
    for s in sinks:
        L.append(f"Cl_{s} o_{s} 0 {c['sink_load_ff']}f")
    return "\n".join(L) + "\n"


def tran_line(t_end_ps):
    return f".tran 1p {t_end_ps:.0f}p\n.end\n"          # solver-chosen step: same 50 % crossings as tmax 1p (qcs_small, 0.00 ps)


def verilog(bufs, edges, root, sinks, cfg=CFG):
    c = cfg
    outs = [f"q_{s}" for s in sinks]
    L = [f"module region_tree (src, {', '.join(outs)});", "input src;"] + [f"output {o};" for o in outs]
    nets = {"p1", f"i_{root}"} | {f"o_{b}" for b in bufs} | {f"i_{b}" for b in bufs}
    L += [f"wire {n};" for n in sorted(nets)]
    L.append(f"{c['cell']} xp1 (.{c['pin_in']}(src), .{c['pin_out']}(p1));")
    L.append(f"{c['cell']} xp2 (.{c['pin_in']}(p1), .{c['pin_out']}(i_{root}));")
    drv_of = {ld: d for d, ld, _ in edges}
    for b in bufs:
        # the input net of a load buffer IS its driver's output net in Verilog; SPEF gives the RC between them
        inn = f"o_{drv_of[b]}" if b in drv_of else f"i_{b}"
        out = f"q_{b}" if b in sinks else f"o_{b}"
        L.append(f"{c['cell']} x_{b} (.{c['pin_in']}({inn}), .{c['pin_out']}({out}));")
    L.append("endmodule")
    return "\n".join(L) + "\n"


def spef(bufs, edges, sinks, cfg=CFG):
    c = cfg
    by = {}
    for k, (d, ld, wl) in enumerate(edges):
        by.setdefault(d, []).append((k, ld, wl))
    H = ['*SPEF "IEEE 1481-1998"', '*DESIGN "region_tree"', '*DATE "-"', '*VENDOR "opentools"', '*PROGRAM "mscts"',
         '*VERSION "1"', '*DESIGN_FLOW "PIN_CAP NONE"', '*DIVIDER /', '*DELIMITER :', '*BUS_DELIMITER [ ]',
         '*T_UNIT 1 PS', '*C_UNIT 1 FF', '*R_UNIT 1 OHM', '*L_UNIT 1 HENRY', ""]
    for d, lst in by.items():
        net = f"o_{d}"
        caps, ress = [], []
        tot = 0.0
        nid = 0
        for k, ld, wl in lst:
            n, r, cc = _ladder(wl, c)
            prev = f"x_{d}:{c['pin_out']}"
            for j in range(n):
                if j < n - 1:
                    nid += 1
                    nx = f"{net}:{nid}"
                else:
                    nx = f"x_{ld}:{c['pin_in']}"
                caps += [(prev, cc / 2), (nx, cc / 2)]
                ress.append((prev, nx, r))
                tot += cc
                prev = nx
        agg = {}
        for nd, v in caps:
            agg[nd] = agg.get(nd, 0.0) + v
        H += [f"*D_NET {net} {tot:.5f}", "*CONN", f"*I x_{d}:{c['pin_out']} O"] + \
             [f"*I x_{ld}:{c['pin_in']} I" for _, ld, _ in lst] + ["*CAP"] + \
             [f"{i + 1} {nd} {v:.5f}" for i, (nd, v) in enumerate(agg.items())] + ["*RES"] + \
             [f"{i + 1} {a} {b} {r:.4f}" for i, (a, b, r) in enumerate(ress)] + ["*END", ""]
    return "\n".join(H) + "\n"


def sta_tcl(lib, sinks, root, cfg=CFG, ramp_ps=None):
    c = cfg
    tr = (ramp_ps or c["ramp_ps"]) * 0.8          # 10-90 % of a linear 0-100 % ramp
    L = [f"read_liberty {lib}", "read_verilog region_tree.v", "link_design region_tree", "read_spef region_tree.spef",
         "create_clock -name vclk -period 10000", "set_input_delay 0 -clock vclk [get_ports src]",
         f"set_input_transition {tr:.2f} [get_ports src]", f"set_load {c['sink_load_ff']} [all_outputs]",
         "set_output_delay 0 -clock vclk [all_outputs]",
         ]
    L.append("report_checks -group_count 1 -digits 3")          # forces a full timing update before pin queries
    L.append("set f [open sta_arr.txt w]")
    L.append(f"foreach p [list x_{root}/A {' '.join(f'x_{s}/A' for s in sinks)}] {{")
    L.append("  set pin [get_pins $p]")
    L.append("  puts $f \"$p [get_property $pin arrival_max_rise]\"")
    L.append("}")
    L.append("close $f")
    return "\n".join(L) + "\n"
