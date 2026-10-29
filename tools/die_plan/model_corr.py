#!/usr/bin/env python3
"""MODEL-CORR-1: fixed spice correlation suite of the ONE shared die clock timing model (METHODOLOGY 12.15b).

Four model errors were found by accident on 10-28 (CA row without OCV, BUF duty distortion, placement-RC trunk
balance, inverter pin-cap range double count).  This suite checks the shared model against ngspice on a FIXED, versioned
reference set every time the model changes, so the next error is found by a test instead of by accident.

Reference set (CASES + one routed path):
  chains   BUFx24 / CKINVDCx16 / inv2 (even inverter taps) on NDR and default (1x) M8/M9 wire, taps at 5 / 20 / 50
           stages (shallow / medium / deep), leg form: 1 mm and 2 mm H-tree legs at the repeater pitch with a fanout-2
           node at every leg end.  Spice and OpenSTA see the same cells and the same RC ladders (clk_inv_cal method).
  routed   one GRT-routed path of a built tree (HEAD hd_tile h16 spine: clk -> h16_n_RD -> h16_n_D1 -> 16 BUFx4 delay
           cells -> h16_t33_drv -> clkbuf_0_h16_t33/A), every net from the design's routed SPEF with all side loads as
           real cells; OpenSTA arrivals of the real design (read_db + SDC + SPEF).
Both analyses (OpenSTA max = late, min = early), both edges (source rise and source fall -> pulse width), TT and FF.

Model value of a tap = OpenSTA arrival -> the shared model's clock calibration (die_sta_related.apply_clock_cal when
present, else the main gate form: --clock-cal spice = scale_clock x spice_cal_factor(corner, clock cell)), for EVERY
mode in die_sta_related.CLOCK_CALS.  ratio = model / spice per (case, corner, tap, edge, late|early).

    model_corr.py gen     --out DIR                 # decks + Verilog/SPEF/OpenSTA tcl of every chain case
    model_corr.py routed  --dump P_TT P_FF --spef S --out DIR/routed   # deck of the routed path (dump_path.tcl output)
    model_corr.py collect DIR --out raw.json         # spice crossings + STA arrivals -> raw rows
    model_corr.py golden  raw.json --out tools/die_plan/model_corr_golden.json [--merge OLD]
    model_corr.py check   [--golden G]               # fast mode: stored spice/STA numbers through the CURRENT model
    model_corr.py report  [--golden G] [--tol 0.02]  # every row whose model/spice is outside 1 +- tol, per mode
    model_corr.py full    --work DIR                 # full mode on a FLEET host: regenerate + rerun spice/STA (docker)

Fast-mode gate (test_model_corr.py, part of the die_plan chunks): FAIL when any model/spice ratio (late or early, rise
or fall, every mode on main) drifts more than 2 % from the stored golden, when model early > model late on any row, when
the golden's raw data hash is broken, or when main grows a clock-cal mode the golden does not hold.
"""
import argparse
import hashlib
import json
import math
import os
import socket
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import clk_inv_cal as CIC          # noqa: E402  (same lib, cells, wire RC, ladder, crossings as CLK-INV-CAL-1/2)

GOLDEN = HERE / "model_corr_golden.json"
DRIFT_TOL = 0.02
REPORT_TOL = 0.02
CORNERS = ("TT", "FF")
PULSE_PS = 2000.0
SINK_FF = 5.0
VDD_RAMP_PS = 50.0      # routed deck: supply ramp from 0 (no DC operating point)
ROUTED_T0_PS = 1000.0   # routed deck: source rise edge (the ramp leaves deep BUFx4 nodes high up to ~0.45 ns)
T_SETTLE_PS = 950.0     # routed deck: crossings before this are the supply ramp
SIDE_UM = 100.0


def _legs(legs_um):
    """H-tree legs at the repeater pitch: each leg of L um = ceil(L/rep) (even for inverters) equal stages; a fanout-2
    node (side branch SIDE_UM to one more cell) at every leg end; taps = the leg-end cell inputs."""
    segs, side, taps = [], {}, []
    for L, n in legs_um:
        segs += [L / n] * n
        side[len(segs)] = SIDE_UM
        taps.append(len(segs))
    return segs, side, taps


CASES = {
    "buf_ndr450_d50": dict(cell="buf", rc="ndr", segs=[450.0] * 50, taps=[5, 20, 50]),
    "inv_ndr250_d50": dict(cell="inv", rc="ndr", segs=[250.0] * 50, taps=[5, 20, 50]),
    "inv_ndr150_d50": dict(cell="inv", rc="ndr", segs=[150.0] * 50, taps=[5, 20, 50]),
    "inv2_ndr200_d50": dict(cell="inv", form="inv2", rc="ndr", segs=[200.0] * 50, taps=[6, 20, 50]),
    "buf_1x450_d20": dict(cell="buf", rc="1x", segs=[450.0] * 20, taps=[5, 20]),
    "inv_1x250_d20": dict(cell="inv", rc="1x", segs=[250.0] * 20, taps=[5, 20]),
    "buf_legs_1_2mm": dict(cell="buf", rc="ndr", legs=[(1000.0, 3), (2000.0, 5), (1000.0, 3), (2000.0, 5)]),
    "inv_legs_1_2mm": dict(cell="inv", rc="ndr", legs=[(1000.0, 4), (2000.0, 8), (1000.0, 4), (2000.0, 8)]),
}


def case_geom(name):
    c = dict(CASES[name])
    if "legs" in c:
        c["segs"], c["side"], c["taps"] = _legs(c["legs"])
    c.setdefault("side", {})
    c.setdefault("form", c["cell"])
    return c


# ------------------------------------------------------------------------------------------------ chain decks
def gen_case(name, d, libdir="/w/lib", osdi="/w/osdi/bsimcmg23.osdi"):
    g = case_geom(name)
    cell = CIC.CELLS[g["cell"]]["cell"]
    inv = CIC.CELLS[g["cell"]]["inverting"]
    w = CIC.WIRE_1X if g["rc"] == "1x" else CIC.WIRE_NDR
    N = len(g["segs"])
    trunk = [f"t{i}" for i in range(N + 1)]
    edges = [(trunk[i], trunk[i + 1], g["segs"][i]) for i in range(N)]
    sides = []
    for k, L in sorted(g["side"].items()):
        sides.append(f"s{k}")
        edges.append((trunk[k], f"s{k}", L))
    cells = trunk + sides
    loads = {trunk[-1]} | set(sides)                  # cells whose output ends in a sink cap
    meas = ["t0"] + [f"t{k}" for k in g["taps"]]
    d.mkdir(parents=True, exist_ok=True)
    for c in CORNERS:
        v = CIC.CORNER[c]["vdd"]
        L = [f"* MODEL-CORR-1 {name} {cell} {c}", ".control", f"pre_osdi {osdi}", "set noaskquit", "run",
             f"wrdata arr_{c}.dat " + " ".join(f"v(i_{s})" for s in meas), "quit", ".endc", ".options klu",
             ".save " + " ".join(f"v(i_{s})" for s in meas), f".temp {CIC.CORNER[c]['temp']}",
             f".include {libdir}/{c}/models.sp", f".include {libdir}/{c}/cells.sp", f"Vdd vdd 0 {v}", "Vss vss 0 0",
             f"Vin src 0 {CIC.pwl_pulse(v, w=PULSE_PS)}", f"Xp1 vss vdd src p1 {cell}", f"Xp2 vss vdd p1 i_t0 {cell}"]
        for b in cells:
            L.append(f"X{b} vss vdd i_{b} o_{b} {cell}")
        for k, (dr, ld, um) in enumerate(edges):
            L += CIC.ladder(f"e{k}", f"o_{dr}", f"i_{ld}", um, w)
        for s in sorted(loads):
            L.append(f"Cl_{s} o_{s} 0 {SINK_FF}f")
        per = 160.0 if g["cell"] == "buf" else 90.0
        tend = 100 + PULSE_PS + sum(max(1.0, u / 250.0) for u in g["segs"]) * per + 1500
        L += [f".tran 1p {tend:.0f}p", ".end"]
        (d / f"deck_{c}.sp").write_text("\n".join(L) + "\n")
    drv = {ld: dr for dr, ld, _ in edges}
    V = ["module chain (src, " + ", ".join(f"q_{s}" for s in sorted(loads)) + ");", "input src;"]
    V += [f"output q_{s};" for s in sorted(loads)]
    V += [f"wire {n};" for n in sorted({"p1", "i_t0"} | {f"o_{b}" for b in cells if b not in loads})]
    V += [f"{cell} xp1 (.A(src), .Y(p1));", f"{cell} xp2 (.A(p1), .Y(i_t0));"]
    for b in cells:
        a = f"o_{drv[b]}" if b in drv else "i_t0"
        V.append(f"{cell} x_{b} (.A({a}), .Y({'q_' + b if b in loads else 'o_' + b}));")
    (d / "chain.v").write_text("\n".join(V + ["endmodule"]) + "\n")
    H = ['*SPEF "IEEE 1481-1998"', '*DESIGN "chain"', '*DATE "-"', '*VENDOR "opentallas"', '*PROGRAM "model_corr"',
         '*VERSION "1"', '*DESIGN_FLOW "PIN_CAP NONE"', '*DIVIDER /', '*DELIMITER :', '*BUS_DELIMITER [ ]',
         '*T_UNIT 1 PS', '*C_UNIT 1 FF', '*R_UNIT 1 OHM', '*L_UNIT 1 HENRY', ""]
    by = {}
    for dr, ld, um in edges:
        by.setdefault(dr, []).append((ld, um))
    for dr, lds in by.items():
        caps, ress, nid, tot = {}, [], 0, 0.0
        for ld, um in lds:
            n = max(1, int(math.ceil(um / CIC.PI_UM - 1e-9)))
            rs, cs = w["r_ohm_um"] * um / n, w["c_ff_um"] * um / n
            prev = f"x_{dr}:Y"
            for j in range(n):
                if j < n - 1:
                    nid += 1
                    nx = f"o_{dr}:{nid}"
                else:
                    nx = f"x_{ld}:A"
                caps[prev] = caps.get(prev, 0.0) + cs / 2
                caps[nx] = caps.get(nx, 0.0) + cs / 2
                ress.append((prev, nx, rs))
                tot += cs
                prev = nx
        H += [f"*D_NET o_{dr} {tot:.5f}", "*CONN", f"*I x_{dr}:Y O"] + [f"*I x_{ld}:A I" for ld, _ in lds] + ["*CAP"]
        H += [f"{i + 1} {k} {v:.5f}" for i, (k, v) in enumerate(caps.items())] + ["*RES"]
        H += [f"{i + 1} {p} {q} {r:.4f}" for i, (p, q, r) in enumerate(ress)] + ["*END", ""]
    (d / "chain.spef").write_text("\n".join(H) + "\n")
    pins = " ".join(f"x_{s}/A" for s in meas)
    for c in CORNERS:
        T = [f"read_liberty lib_{c}.lib", "read_verilog chain.v", "link_design chain", "read_spef chain.spef",
             "create_clock -name vclk -period 10000", "set_input_delay 0 -clock vclk [get_ports src]",
             "set_input_transition 32.00 [get_ports src]", f"set_load {SINK_FF} [all_outputs]",
             "set_output_delay 0 -clock vclk [all_outputs]", "report_checks -group_count 1 -digits 3",
             f"set f [open sta_arr_{c}.txt w]", f"foreach p [list {pins}] {{", "  set pin [get_pins $p]",
             "  puts $f \"$p [get_property $pin arrival_max_rise] [get_property $pin arrival_max_fall] "
             "[get_property $pin arrival_min_rise] [get_property $pin arrival_min_fall]\"", "}", "close $f"]
        (d / f"sta_{c}.tcl").write_text("\n".join(T) + "\n")
    depth = {"t0": 0}
    for dr, ld, _ in edges:
        depth[ld] = depth[dr] + 1
    M = dict(case=name, kind="chain", cell=g["cell"], form=g["form"], master=cell, inverting=inv, rc=g["rc"],
             segs_um=g["segs"], side_um={str(k): v for k, v in g["side"].items()}, root="t0",
             taps=[f"t{k}" for k in g["taps"]], depth={s: depth[s] for s in meas},
             parity={s: (depth[s] % 2 if inv else 0) for s in meas}, sink_ff=SINK_FF, pulse_ps=PULSE_PS,
             wire=w, pi_um=CIC.PI_UM)
    (d / "meas.json").write_text(json.dumps(M, indent=1) + "\n")
    return M


def gen(a):
    out = Path(a.out)
    for n in (a.case or sorted(CASES)):
        gen_case(n, out / n, a.libdir, a.osdi)
        print("gen", n)


# ------------------------------------------------------------------------------------------------ routed path
def parse_dump(path):
    """dump_path.tcl output -> {endpoint: dict(pins=[(pin, master, dir, [8 floats])] endpoint->root, nets=[...])}"""
    P, cur = {}, None
    for ln in Path(path).read_text().splitlines():
        f = ln.split()
        if not f:
            continue
        if f[0] == "PATH":
            cur = P.setdefault(f[1], dict(pins=[], nets=[]))
        elif f[0] == "PIN":
            cur["pins"].append((f[1], f[2], f[3], [float(x) for x in f[4:12]]))
        elif f[0] == "NET":
            cur["nets"].append(dict(name=f[1], pins=[], ports=[]))
        elif f[0] == "NPIN":
            cur["nets"][-1]["pins"].append((f[1], f[2], f[3]))
        elif f[0] == "NPORT":
            cur["nets"][-1]["ports"].append(f[1])
        elif f[0] == "ROOT":
            cur["root_port"] = f[1]
    return P


def spef_nets(spef, names):
    """the *D_NET sections of `names` from a SPEF (R in KOHM -> ohm when *R_UNIT 1 KOHM)."""
    want, out, cur, sec, runit = set(names), {}, None, None, 1.0
    with open(spef) as fh:
        for ln in fh:
            if ln.startswith("*R_UNIT"):
                runit = 1e3 if "KOHM" in ln else 1.0
            if ln.startswith("*D_NET"):
                f = ln.split()
                cur = dict(total_ff=float(f[2]), caps=[], res=[], conn=[]) if f[1] in want else None
                if cur is not None:
                    out[f[1]] = cur
                sec = None
                continue
            if cur is None:
                continue
            s = ln.strip()
            if s.startswith("*CONN"):
                sec = "conn"
            elif s.startswith("*CAP"):
                sec = "cap"
            elif s.startswith("*RES"):
                sec = "res"
            elif s.startswith("*END"):
                cur, sec = None, None
            elif s and sec == "conn" and s[:2] in ("*I", "*P"):
                cur["conn"].append(s.split()[1])
            elif s and sec == "cap":
                f = s.split()
                if len(f) == 3:
                    cur["caps"].append((f[1], float(f[2])))
                else:
                    cur["caps"].append((f[1], float(f[3]), f[2]))    # coupling cap -> grounded (no aggressor)
            elif s and sec == "res":
                f = s.split()
                cur["res"].append((f[1], f[2], float(f[3]) * runit))
    return out


def _node(s):
    return "n_" + s.replace(":", "__").replace("/", "_").replace(".", "_").replace("[", "_").replace("]", "_")


def routed(a):
    """spice deck of ONE routed path: the path's cells and every net between root and endpoint from the SPEF; side
    loads = the real cells (output loaded by its net's total SPEF cap).  Root = the first cell input after the port
    (driven by a PWL ramp of the STA slew there); taps = every path cell input."""
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    dumps = {c: parse_dump(p) for c, p in zip(CORNERS, a.dump)}
    ep = a.endpoint or next(iter(dumps["TT"]))
    path = {c: dumps[c][ep] for c in CORNERS}
    pins = path["TT"]["pins"][::-1]                         # root -> endpoint: [A0, Y0, A1, Y1, ..., A_end]
    ins = [p for p in pins if p[2] == "input"]
    root = ins[0][0]
    netlist = [n for n in path["TT"]["nets"][::-1] if not n["ports"]]   # the port net is replaced by the ramp source
    sp = spef_nets(a.spef, [n["name"] for n in netlist])
    lib = {}
    for c in CORNERS:
        lib[c] = {}
    masters = {}
    for n in netlist:
        for p, m, d in n["pins"]:
            masters[p.split("/")[0]] = m
    path_cells = [p[0].split("/")[0] for p in ins[:-1]]        # cells whose output we follow
    end_inst = ins[-1][0].split("/")[0]
    taps = [p[0] for p in ins]
    for c in CORNERS:
        v = CIC.CORNER[c]["vdd"]
        st = {p[0]: p[3] for p in path[c]["pins"]}
        slew = st[root][4]
        meas = [_node(t.replace("/", ":")) for t in taps]
        L = [f"* MODEL-CORR-1 routed path {ep} {c}", ".control", f"pre_osdi {a.osdi}", "set noaskquit", "run",
             # SPARSE solver + supply ramp + uic: KLU fails the DC operating point on the routed RC + side-cell deck
             # (singular matrix); with a DC op, SPARSE still aborts the BUFx4 transient at t < 0.2 ps (timestep too
             # small, TT and FF).  Ramping VDD from 0 (all nodes start at 0 = a consistent state, no DC op) converges
             # in both corners; crossings before T_SETTLE_PS (the supply ramp) are ignored by collect_case.
             f"wrdata arr_{c}.dat " + " ".join(f"v({m})" for m in meas), "quit", ".endc", ".options",
             ".save " + " ".join(f"v({m})" for m in meas), f".temp {CIC.CORNER[c]['temp']}",
             f".include {a.libdir}/{c}/models.sp", f".include {a.libdir}/{c}/cells.sp",
             f"Vdd vdd 0 PWL(0 0 {VDD_RAMP_PS:.0f}p {v})", "Vss vss 0 0",
             # 10-90 slew s -> 0-100 ramp s/0.8 (the clk_inv_cal convention: 40 ps ramp <-> 32 ps input transition)
             f"Vin {meas[0]} 0 {CIC.pwl_pulse(v, ramp=slew / 0.8, t0=ROUTED_T0_PS, w=PULSE_PS)}"]
        side_n = 0
        for n in netlist:
            net = sp[n["name"]]
            for k, (x, y, r) in enumerate(net["res"]):
                L.append(f"R{_node(n['name'])}_{k} {_node(x)} {_node(y)} {max(r, 1e-3):.6f}")
            for k, cap in enumerate(net["caps"]):
                L.append(f"C{_node(n['name'])}_{k} {_node(cap[0])} 0 {cap[1]:.6f}f")
            for p, m, d in n["pins"]:
                inst = p.split("/")[0]
                if d != "input" or inst == end_inst and p == taps[-1]:
                    continue
                if inst in path_cells:
                    continue
                side_n += 1
                L.append(f"Xside{side_n} vss vdd {_node(p.replace('/', ':'))} side{side_n}_y {m}")
                L.append(f"Cside{side_n} side{side_n}_y 0 {a.side_load_ff:.3f}f")
        for inst in path_cells:
            L.append(f"X{_node(inst)} vss vdd {_node(inst + ':A')} {_node(inst + ':Y')} {masters[inst]}")
        # the endpoint cell: real cell when a spice model exists, its output loaded like a side load
        L.append(f"Xend vss vdd {_node(taps[-1].replace('/', ':'))} end_y {masters[end_inst]}")
        L.append(f"Cend end_y 0 {a.side_load_ff:.3f}f")
        tend = ROUTED_T0_PS + PULSE_PS + 1000
        L += [f".tran 0.5p {tend:.0f}p uic", ".end"]
        (out / f"deck_{c}.sp").write_text("\n".join(L) + "\n")
        # OpenSTA arrivals of the real design (max/min, rise/fall) at every tap; fall columns are source-fall edges
        rows = []
        for t in taps:
            x = st[t]
            rows.append(f"{t} {x[0]} {x[1] - a.period / 2} {x[2]} {x[3] - a.period / 2}")
        (out / f"sta_arr_{c}.txt").write_text("\n".join(rows) + "\n")
    M = dict(case="routed_hd_tile_h16_t33", kind="routed", cell="buf", form="buf_routed", endpoint=ep, root=root,
             taps=taps[1:], depth={t: i for i, t in enumerate(taps)}, parity={t: 0 for t in taps},
             masters={t.split("/")[0]: masters.get(t.split("/")[0]) for t in taps}, side_load_ff=a.side_load_ff,
             pulse_ps=PULSE_PS, period_ps=a.period, t_settle_ps=T_SETTLE_PS, vdd_ramp_ps=VDD_RAMP_PS,
             t0_ps=ROUTED_T0_PS, nets=[n["name"] for n in netlist],
             spef_total_ff={n["name"]: sp[n["name"]]["total_ff"] for n in netlist},
             spef_sha256=_sha_file(a.spef), dump_sha256={c: _sha_file(p) for c, p in zip(CORNERS, a.dump)},
             meas_nodes=[_node(t.replace("/", ":")) for t in taps], tap_names=taps,
             note="non-inverting BUFx24/BUFx4 path; STA columns: max_rise max_fall min_rise min_fall, the fall "
                  "columns minus period/2 (source fall at T/2), so both edges are insertion delays")
    (out / "meas.json").write_text(json.dumps(M, indent=1) + "\n")
    print("routed", ep, len(taps), "taps", len(netlist), "nets")


def _sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------ collect
def collect_case(d, c):
    """rows of one case dir and corner: per tap and source edge the spice arrival and the STA max/min arrival, all
    referred to the root (the root is the clock source of the reference path)."""
    M = json.loads((d / "meas.json").read_text())
    vh = CIC.CORNER[c]["vdd"] / 2
    cr = CIC.crossings_all(d / f"arr_{c}.dat", vh)
    if M.get("t_settle_ps"):                                  # routed deck: drop the supply-ramp crossings
        cr = [[x for x in v if x[0] >= M["t_settle_ps"] * 1e-12] for v in cr]
        if any(v and v[0][1] != 1 for v in cr):
            raise SystemExit(f"{d} {c}: a node was still high at t_settle (supply ramp not settled)")
    names = [M["root"]] + M["taps"]
    sta = {}
    for ln in (d / f"sta_arr_{c}.txt").read_text().splitlines():
        f = ln.split()
        k = f[0].split("/")[0][2:] if M["kind"] == "chain" else f[0]
        sta[k] = [float(x) for x in f[1:5]]                   # max_r max_f min_r min_f
    if any(len(x) != 2 for x in cr):
        raise SystemExit(f"{d} {c}: expected 2 crossings per node, got {[len(x) for x in cr]}")
    root_sp = cr[0]
    r = sta[M["root"]]
    rows = []
    for s, x in zip(names[1:], cr[1:]):
        p = M["parity"][s]
        t = sta[s]
        for e, ed in ((0, "rise"), (1, "fall")):
            sp_ = (x[e][0] - root_sp[e][0]) * 1e12
            tap_edge = "rise" if x[e][1] > 0 else "fall"
            # STA arrival of the tap edge launched by source edge ed: [max, min] at the tap minus the root's same edge
            ti = 0 if tap_edge == "rise" else 1
            ri = 0 if ed == "rise" else 1
            if M["kind"] == "routed":                    # dump columns are already per source edge
                ti = ri
            mx = t[ti] - r[ri]
            mn = t[2 + ti] - r[2 + ri]
            rows.append(dict(case=M["case"], corner=c, cell=M["cell"], form=M["form"], tap=s, depth=M["depth"][s],
                             src_edge=ed, tap_edge=tap_edge, spice_ps=round(sp_, 3), sta_late_ps=round(mx, 3),
                             sta_early_ps=round(mn, 3)))
    return rows


def collect(a):
    rows, decks = [], {}
    for d in sorted(Path(a.dir).iterdir()):
        if not (d / "meas.json").is_file():
            continue
        for c in CORNERS:
            rows += collect_case(d, c)
            decks[f"{d.name}/{c}"] = hashlib.sha256((d / f"deck_{c}.sp").read_bytes()).hexdigest()
    Path(a.out).write_text(json.dumps(dict(rows=rows, deck_sha256=decks), indent=1) + "\n")
    print(len(rows), "rows")


# ------------------------------------------------------------------------------------------------ the shared model
def _dsr():
    import die_sta_related as R
    return R


def model_modes(R=None):
    R = R or _dsr()
    return tuple(getattr(R, "CLOCK_CALS", ("none", "spice")))


def model_arrivals(rows_tap, corner, cell, mode, R=None):
    """{tap: dict(late_ps, early_ps, fall_late_ps, fall_early_ps)} of STA arrivals -> the shared model's calibrated
    arrivals.  Calls the ONE calibration step planner and gate use (apply_clock_cal), or the main gate form."""
    R = R or _dsr()
    meta = dict(cppr_node_range_ps={})
    if hasattr(R, "apply_clock_cal"):
        _, t = R.apply_clock_cal(meta, rows_tap, corner, cell, mode)
        return t
    if mode == "none":
        return rows_tap
    if mode == "spice":
        _, t = R.scale_clock(meta, rows_tap, R.spice_cal_factor(corner, cell))
        return t
    raise SystemExit(f"clock-cal mode {mode} unknown to this die_sta_related")


def ratios(raw_rows, R=None):
    """{mode: {key: dict(late, early, duty_err_ps, spice_ps)}} with key = case|corner|tap|src_edge."""
    R = R or _dsr()
    by = {}
    for r in raw_rows:
        by.setdefault((r["case"], r["corner"], r["cell"]), {}).setdefault(r["tap"], {})[r["src_edge"]] = r
    out = {}
    for mode in model_modes(R):
        res = out.setdefault(mode, {})
        for (case, c, cell), taps in by.items():
            t = {k: dict(late_ps=v["rise"]["sta_late_ps"], early_ps=v["rise"]["sta_early_ps"],
                         fall_late_ps=v["fall"]["sta_late_ps"], fall_early_ps=v["fall"]["sta_early_ps"])
                 for k, v in taps.items()}
            m = model_arrivals(t, c, cell, mode, R)
            for k, v in taps.items():
                for ed, lk, ek in (("rise", "late_ps", "early_ps"), ("fall", "fall_late_ps", "fall_early_ps")):
                    sp = v[ed]["spice_ps"]
                    res[f"{case}|{c}|{k}|{ed}"] = dict(late=round(m[k][lk] / sp, 5), early=round(m[k][ek] / sp, 5),
                                                       late_ps=round(m[k][lk], 3), early_ps=round(m[k][ek], 3),
                                                       spice_ps=sp)
                # pulse width distortion (source-fall arrival - source-rise arrival): model late vs spice
                dm = m[k]["fall_late_ps"] - m[k]["late_ps"]
                ds = v["fall"]["spice_ps"] - v["rise"]["spice_ps"]
                res[f"{case}|{c}|{k}|duty"] = dict(model_ps=round(dm, 3), spice_ps=round(ds, 3),
                                                    err_ps=round(dm - ds, 3), ref_ps=v["rise"]["spice_ps"])
    return out


def raw_hash(raw_rows):
    return hashlib.sha256(json.dumps(raw_rows, sort_keys=True).encode()).hexdigest()


def golden(a):
    raw = json.loads(Path(a.raw).read_text())
    R = _dsr()
    G = json.loads(Path(a.merge).read_text()) if a.merge else {}
    if G and G.get("raw_sha256") != raw_hash(raw["rows"]):
        raise SystemExit("--merge golden holds different raw data")
    G.update(version=1, raw_rows=raw["rows"], raw_sha256=raw_hash(raw["rows"]), deck_sha256=raw["deck_sha256"],
             drift_tol=DRIFT_TOL)
    if a.meta:
        G.setdefault("provenance", {}).update(json.loads(Path(a.meta).read_text()))
    src = hashlib.sha256(Path(R.__file__).read_bytes()).hexdigest()
    for mode, v in ratios(raw["rows"], R).items():
        G.setdefault("modes", {})[mode] = v
        G.setdefault("mode_source", {})[mode] = dict(die_sta_related_sha256=src, path=str(Path(R.__file__)))
    Path(a.out).write_text(json.dumps(G, indent=1, sort_keys=True) + "\n")
    print("golden", a.out, "modes", sorted(G["modes"]))


# ------------------------------------------------------------------------------------------------ fast-mode check
def check_golden(G, R=None, tol=None):
    """-> (failures, notes).  Every model/spice ratio of every mode on this die_sta_related within tol (relative) of
    the golden; model early <= model late; duty error within tol x the tap arrival; raw hash intact."""
    R = R or _dsr()
    tol = G.get("drift_tol", DRIFT_TOL) if tol is None else tol
    fails, notes = [], []
    if raw_hash(G["raw_rows"]) != G["raw_sha256"]:
        fails.append("golden raw rows do not match raw_sha256 (edited golden)")
        return fails, notes
    cur = ratios(G["raw_rows"], R)
    for mode, rows in cur.items():
        g = G["modes"].get(mode)
        if g is None:
            fails.append(f"mode {mode}: on this die_sta_related but not in the golden -> regenerate the golden "
                         "(model_corr.py golden --merge) with a spice-checked review")
            continue
        for k, v in rows.items():
            gv = g.get(k)
            if gv is None:
                fails.append(f"{mode} {k}: row missing in golden")
                continue
            if k.endswith("|duty"):
                if abs(v["err_ps"] - gv["err_ps"]) > tol * abs(v["ref_ps"]):
                    fails.append(f"{mode} {k}: duty error {v['err_ps']:+.2f} ps vs golden {gv['err_ps']:+.2f} "
                                 f"(> {tol:.0%} of {v['ref_ps']:.1f} ps)")
                continue
            for side in ("late", "early"):
                d = v[side] / gv[side] - 1.0
                if abs(d) > tol:
                    fails.append(f"{mode} {k} {side}: model/spice {v[side]:.4f} vs golden {gv[side]:.4f} "
                                 f"({d:+.2%} > {tol:.0%})")
            if v["early_ps"] > v["late_ps"] + 1e-6:
                fails.append(f"{mode} {k}: model early {v['early_ps']:.2f} > late {v['late_ps']:.2f}")
    for mode in G["modes"]:
        if mode not in cur:
            notes.append(f"golden mode {mode} not on this die_sta_related (not checked)")
    return fails, notes


def outside(G, R=None, tol=REPORT_TOL, modes=None):
    """rows of the CURRENT model whose model/spice is outside 1 +- tol (late or early), and duty errors > tol x arrival."""
    cur = ratios(G["raw_rows"], R)
    out = []
    for mode, rows in cur.items():
        if modes and mode not in modes:
            continue
        for k, v in rows.items():
            if k.endswith("|duty"):
                if abs(v["err_ps"]) > tol * abs(v["ref_ps"]):
                    out.append((mode, k, "duty", v["err_ps"], v["model_ps"], v["spice_ps"]))
                continue
            for side in ("late", "early"):
                if abs(v[side] - 1.0) > tol:
                    out.append((mode, k, side, v[side], v[f"{side}_ps"], v["spice_ps"]))
    return out


def check(a):
    G = json.loads(Path(a.golden).read_text())
    f, n = check_golden(G)
    for x in n:
        print("NOTE", x)
    for x in f:
        print("FAIL", x)
    print("MODEL-CORR", "FAIL" if f else "PASS", f"{len(f)} failures,", len(G["raw_rows"]), "raw rows")
    return 1 if f else 0


def report(a):
    G = json.loads(Path(a.golden).read_text())
    rows = outside(G, tol=a.tol, modes=a.mode)
    summ = {}
    for mode, k, side, *_ in rows:
        case = k.split("|")[0]
        summ.setdefault(mode, {}).setdefault(side, {}).setdefault(case, 0)
        summ[mode][side][case] += 1
    for mode, k, side, val, mps, sps in rows:
        if side == "duty":
            print(f"{mode:10s} {k:48s} duty  err {val:+8.2f} ps (model {mps:+.2f} spice {sps:+.2f})")
        else:
            print(f"{mode:10s} {k:48s} {side:5s} {val:.4f} (model {mps:.1f} spice {sps:.1f} ps)")
    print(json.dumps(summ, indent=1))
    if a.json:
        Path(a.json).write_text(json.dumps(dict(tol=a.tol, rows=rows, summary=summ), indent=1) + "\n")


# ------------------------------------------------------------------------------------------------ full mode
FLEET_HOSTS = ("intel1", "intel2", "epyc2", "key-cardinal")


def full(a):
    """re-run spice + OpenSTA for every chain case (docker ot-ngspice:r3 + openroad/orfs:asap7lock) and compare the
    fresh raw rows with the golden's (spice and STA each within tol).  Fleet hosts only."""
    h = socket.gethostname()
    if not a.allow_host and not any(x in h for x in FLEET_HOSTS):
        raise SystemExit(f"full mode re-runs spice: fleet hosts only (this is {h}); --allow-host to override")
    W = Path(a.work).resolve()
    gen(argparse.Namespace(out=str(W), case=None, libdir="/w/lib", osdi="/w/osdi/bsimcmg23.osdi"))
    uid = f"{os.getuid()}:{os.getgid()}"
    jobs = []
    for d in sorted(W.iterdir()):
        if not (d / "meas.json").is_file() or json.loads((d / "meas.json").read_text())["kind"] != "chain":
            continue
        for c in CORNERS:
            jobs.append(["docker", "run", "--rm", "--memory", "2g", "-u", uid, "-v", f"{d}:/d", "-w", "/d",
                         "openroad/orfs:asap7lock", "sh", "-c",
                         f"zcat /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_{c}_nldm_"
                         f"220122.lib.gz > lib_{c}.lib; /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/sta "
                         f"-no_splash -exit sta_{c}.tcl > sta_{c}.log 2>&1"])
            jobs.append(["docker", "run", "--rm", "--memory", "4g", "--cpus", "1", "-u", uid, "-v",
                         f"{Path(a.lib).resolve()}:/w/lib:ro", "-v", f"{Path(a.osdi).resolve()}:/w/osdi:ro", "-v",
                         f"{d}:/d", "-w", "/d", "ot-ngspice:r3", "sh", "-c",
                         f"ngspice -b deck_{c}.sp > deck_{c}.log 2>&1"])
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(a.jobs) as ex:
        rcs = list(ex.map(lambda j: subprocess.run(j).returncode, jobs))
    if any(rcs):
        raise SystemExit(f"{sum(1 for x in rcs if x)} docker jobs failed (see {W}/*/sta_*.log, deck_*.log)")
    rows = []
    for d in sorted(W.iterdir()):
        if (d / "meas.json").is_file():
            for c in CORNERS:
                rows += collect_case(d, c)
    G = json.loads(Path(a.golden).read_text())
    g = {(r["case"], r["corner"], r["tap"], r["src_edge"]): r for r in G["raw_rows"]}
    bad = 0
    for r in rows:
        o = g.get((r["case"], r["corner"], r["tap"], r["src_edge"]))
        if o is None:
            print("NEW", r)
            bad += 1
            continue
        for k in ("spice_ps", "sta_late_ps", "sta_early_ps"):
            if abs(r[k] / o[k] - 1) > a.tol:
                print("DRIFT", r["case"], r["corner"], r["tap"], r["src_edge"], k, o[k], "->", r[k])
                bad += 1
    Path(W / "full_raw.json").write_text(json.dumps(dict(rows=rows), indent=1) + "\n")
    print("MODEL-CORR FULL", "FAIL" if bad else "PASS", bad, "drifts", len(rows), "rows")
    return 1 if bad else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    g = sp.add_parser("gen")
    g.add_argument("--out", required=True)
    g.add_argument("--case", action="append")
    g.add_argument("--libdir", default="/w/lib")
    g.add_argument("--osdi", default="/w/osdi/bsimcmg23.osdi")
    r = sp.add_parser("routed")
    r.add_argument("--dump", nargs=2, required=True, metavar=("TT", "FF"))
    r.add_argument("--spef", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--endpoint")
    r.add_argument("--period", type=float, default=833.0)
    r.add_argument("--side-load-ff", type=float, default=5.0)
    r.add_argument("--libdir", default="/w/lib")
    r.add_argument("--osdi", default="/w/osdi/bsimcmg23.osdi")
    c = sp.add_parser("collect")
    c.add_argument("dir")
    c.add_argument("--out", required=True)
    o = sp.add_parser("golden")
    o.add_argument("raw")
    o.add_argument("--out", default=str(GOLDEN))
    o.add_argument("--merge")
    o.add_argument("--meta")
    k = sp.add_parser("check")
    k.add_argument("--golden", default=str(GOLDEN))
    p = sp.add_parser("report")
    p.add_argument("--golden", default=str(GOLDEN))
    p.add_argument("--tol", type=float, default=REPORT_TOL)
    p.add_argument("--mode", action="append")
    p.add_argument("--json")
    f = sp.add_parser("full")
    f.add_argument("--work", required=True)
    f.add_argument("--golden", default=str(GOLDEN))
    f.add_argument("--lib", required=True, help="spice lib dir (<C>/models.sp + cells.sp)")
    f.add_argument("--osdi", required=True, help="dir holding bsimcmg23.osdi")
    f.add_argument("--tol", type=float, default=DRIFT_TOL)
    f.add_argument("--jobs", type=int, default=8)
    f.add_argument("--allow-host", action="store_true")
    a = ap.parse_args(argv)
    return dict(gen=gen, routed=routed, collect=collect, golden=golden, check=check, report=report, full=full)[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
