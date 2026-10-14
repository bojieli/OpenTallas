#!/usr/bin/env python3
"""S81 PQ core cluster dsfd_sp_pq: floorplan, hop and cut analysis from the closed tile LEFs (s81-sppq 2026-10-13).

Reads every hard child's routed abstract (exact pin shapes), places the children as PLAN below (origin, orientation),
puts every cluster pin on the face straight in front of the child pin it wires to, and reports
  * per bus: the longest register-to-register hop (Manhattan, driver pin -> farthest sink pin), rule <= 500 um;
  * cuts: nets crossing each vertical / horizontal line against the routing tracks free there (rule <= 0.60);
  * the child clock insertions (views/insertion.json / TT lib) the cluster spine balances.
Writes the ref_tile children[] block, the place_pin file (io_tcl) and the analysis record.

    sp_pq_plan.py [--write] [--json OUT]
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RT = "physical/ref_tile"
VIEWS = {
    "xin": f"{RT}/ot_pqc_t_xin_m5/views/ot_pqc_t_xin",
    "aq": f"{RT}/ot_dsrom_aq12t_m5/views/ot_dsrom_aq12t",
    "ix": f"{RT}/pqc_ix_rt/views/ot_pqc_t_ix",
    "qb": f"{RT}/ot_pqc_t_qb_m5/views/ot_pqc_t_qb",
    "ctl": f"{RT}/ot_pqc_t_ctl16_m5/views/ot_pqc_t_ctl16",
    "ret": f"{RT}/ot_pqc_t_ret_m5/views/ot_pqc_t_ret",
    "bc": f"{RT}/ot_pqc_t_bc_m5/views/ot_pqc_t_bc",
}
BC_PLAN = dict(w=43.2, h=190.08, lo=10.0, hi=180.0, n=1630)      # kit pin plan until the routed view exists
W_CL, H_CL = 1667.52, 449.28                                     # slot 1672.248 x 449.256 on the 8.64 cluster lattice


def lef(path: Path):
    t = path.read_text()
    m = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", t)
    w, h = float(m[1]), float(m[2])
    pins = {}
    for pm in re.finditer(r"^\s*PIN\s+(\S+)\s*\n(.*?)^\s*END\s+\1\s*$", t, re.S | re.M):
        n, b = pm[1], pm[2]
        use = re.search(r"USE\s+(\w+)", b)
        if use and use[1] in ("POWER", "GROUND"):
            continue
        lm = re.search(r"LAYER\s+(\w+)\s*;\s*RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", b)
        x0, y0, x1, y1 = map(float, lm.groups()[1:])
        d = {"W": x0, "E": w - x1, "S": y0, "N": h - y1}
        f = min(d, key=d.get)
        mm = re.match(r"(.*?)\[(\d+)\]$", n)
        base, bit = (mm[1], int(mm[2])) if mm else (n, 0)
        pins[(base, bit)] = (f, lm[1], (x0 + x1) / 2, (y0 + y1) / 2)
    return w, h, pins


def bc_synth():
    p = {}
    for i in range(BC_PLAN["n"]):
        y = BC_PLAN["lo"] + (BC_PLAN["hi"] - BC_PLAN["lo"]) * i / (BC_PLAN["n"] - 1)
        p[("d", i)] = ("W", "M4", 0.042, y)
        p[("q", i)] = ("E", "M4", BC_PLAN["w"] - 0.042, y)
    p[("clk", 0)] = ("W", "M4", 0.042, 3.5)
    p[("rst_n", 0)] = ("W", "M4", 0.042, 5.5)
    return BC_PLAN["w"], BC_PLAN["h"], p


FLIP = {"R0": {}, "MX": {"N": "S", "S": "N"}, "MY": {"E": "W", "W": "E"},
        "R180": {"N": "S", "S": "N", "E": "W", "W": "E"}}


class Inst:
    def __init__(s, name, kind, x, y, orient, lib):
        s.name, s.kind, s.x, s.y, s.o = name, kind, x, y, orient
        s.w, s.h, s.pins = lib[kind]

    def pin(s, base, bit=0):
        f, lay, px, py = s.pins[(base, bit)]
        if s.o in ("MY", "R180"):
            px = s.w - px
        if s.o in ("MX", "R180"):
            py = s.h - py
        return (s.x + px, s.y + py, FLIP[s.o].get(f, f), lay)

    def box(s):
        return (s.x, s.y, s.x + s.w, s.y + s.h)


# ------------------------------------------------------------------------------------------------------------ PLAN
# name: (kind, x, y, orient).  x is relative to GX.  Flow S -> N in the halves, W -> E for the broadcast.
GX = 345.6
PLAN = {}


def plan_default():
    P = {}
    # halves: quantiser over its x_q pin registers (36.7 um shuffle channel); the BF16 x-buffer pair over the quantiser's
    # inner end (x_q reaches it on M7 over the quantiser, 32.4 um landing channel); 60 um corridor above the pairs
    P["u_xin0"] = ("xin", 118.8, 32.4, "MX")
    P["u_xin1"] = ("xin", 712.8, 32.4, "MX")
    P["u_aq0"] = ("aq", 0.0, 86.4, "R180")
    P["u_aq1"] = ("aq", 658.8, 86.4, "MX")
    # (T_IX carries M3 and M5 pins on its N / S faces: no x-mirrored origin keeps both on track, so every T_IX is MX
    #  and takes the controller's signals on its W face)
    P["u_ix0"] = ("ix", 64.8, 291.6, "MX")
    P["u_ix2"] = ("ix", 183.6, 291.6, "MX")
    P["u_ix1"] = ("ix", 658.8, 291.6, "MX")
    P["u_ix3"] = ("ix", 777.6, 291.6, "MX")
    # centre: returns + q buffer at the S edge; first relay stages, controller (signals W, ROM E) and the merge above
    P["u_ret0"] = ("ret", 313.2, 43.2, "R0")
    P["u_qb"] = ("qb", 421.2, 108.0, "R0")
    P["u_ret1"] = ("ret", 540.0, 43.2, "R0")
    P["u_bc0a"] = ("bc", 302.4, 226.8, "R0")
    P["u_bc0b"] = ("bc", 367.2, 226.8, "R0")
    P["u_ctl"] = ("ctl", 432.0, 259.2, "MY")
    P["u_bc1"] = ("bc", 594.0, 226.8, "R0")
    # E of the E half: the shared relay column to the E face
    for k in range(5):
        P[f"u_bt{k + 1}"] = ("bc", 961.2 + 64.8 * k, 226.8, "R0")
    return P


# broadcast bit groups: (name, lsb, n, tile chain).  Every bit passes exactly five relay flops.
def bc_groups():
    w_chain = ["u_bc0a", "u_bc1", "u_bt1", "u_bt2", "u_bt3"]
    c_chain = ["u_bc0b", "u_bc1", "u_bt1", "u_bt2", "u_bt3"]
    e_chain = ["u_bt1", "u_bt2", "u_bt3", "u_bt4", "u_bt5"]
    g = []
    for u in range(4):
        for ix in range(4):
            g.append((f"ix{ix}", 256 * u + 64 * ix, 64, w_chain if ix in (0, 2) else e_chain, ("u_ix%d" % ix, "bt_d", 64 * u)))
    g.append(("ctl_lo", 1024, 46, c_chain, ("u_ctl", "bc_hr_o", 0)))
    g.append(("qb_he1", 1070, 10, c_chain, ("u_qb", "he1", 0)))
    g.append(("qb_hq1", 1080, 256, c_chain, ("u_qb", "hq1", 0)))
    g.append(("qb_he0", 1336, 10, c_chain, ("u_qb", "he0", 0)))
    g.append(("qb_hq0", 1346, 256, c_chain, ("u_qb", "hq0", 0)))
    g.append(("ctl_hi", 1602, 28, c_chain, ("u_ctl", "bc_hr_o", 578)))
    return g


def build(P, lib):
    return {n: Inst(n, k, GX + x, y, o, lib) for n, (k, x, y, o) in P.items()}


def nets(I):
    """[(bus, driver (x, y), [sinks (x, y)], bits)] at bit level; cluster pins are created on the face in front."""
    out, cpins = [], {}

    def cpin(name, bit, face, ref):
        x, y = ref[0], ref[1]
        if face == "S": p = (x, 0.0)
        elif face == "N": p = (x, H_CL)
        elif face == "E": p = (W_CL, y)
        else: p = (0.0, y)
        cpins[(name, bit)] = (face, p)
        return p

    for h in (0, 1):
        xi, aq = I[f"u_xin{h}"], I[f"u_aq{h}"]
        for j in range(1024):
            d = xi.pin("d", j)
            out.append(("x_q", cpin("x_q", 1024 * h + j, "S", d), [d[:2]]))
            out.append((f"xq{h}.aq", xi.pin("q", j)[:2], [aq.pin("x", j)[:2]]))
            out.append((f"xq{h}.ix", xi.pin("q", j)[:2], [I[f"u_ix{h}"].pin("xw", j)[:2], I[f"u_ix{h + 2}"].pin("xw", j)[:2]]))
        for k in range(256):
            out.append((f"aq_q{h}", aq.pin("q", k)[:2], [I["u_qb"].pin("aq_q", 256 * h + k)[:2]]))
        for k in range(10):
            out.append((f"aq_e{h}", aq.pin("e", k)[:2], [I["u_qb"].pin("aq_e", 10 * h + k)[:2]]))
        out.append(("aqf", aq.pin("fault")[:2], [I["u_ctl"].pin("aqf", h)[:2]]))
    c = I["u_ctl"]
    out.append(("aq_vin", c.pin("aq_vin")[:2], [I["u_aq0"].pin("v")[:2], I["u_aq1"].pin("v")[:2]]))
    ixs = [I[f"u_ix{g}"] for g in range(4)]
    out.append(("ba_v", c.pin("ba_v_o")[:2], [t.pin("ba_v")[:2] for t in ixs]))
    for b in range(3):
        out.append(("ba_blk", c.pin("ba_blk_o", b)[:2], [t.pin("ba_blk", b)[:2] for t in ixs]))
    for b in range(36):
        out.append(("h_hi", c.pin("h_hi_o", b)[:2], [t.pin("h_hi", b)[:2] for t in ixs]))
    for b in range(1, 8):
        out.append(("hw7", c.pin("hw_o", b)[:2], [t.pin("hw7", b - 1)[:2] for t in ixs]))
    q = I["u_qb"]
    for b in range(5):
        out.append(("aqi", c.pin("aqi_o", b)[:2], [q.pin("aqi_d", b)[:2]]))
    for b in range(16):
        out.append(("h_b", c.pin("h_b0_o", b)[:2], [q.pin("h_b0", b)[:2]]))
        out.append(("h_b", c.pin("h_b1_o", b)[:2], [q.pin("h_b1", b)[:2]]))
    for b in (12, 13):
        out.append(("hw_sv", c.pin("hw_o", b)[:2], [q.pin("hw_sv", b - 12)[:2]]))
    for b in range(458):
        out.append(("mdr", c.pin("mdr_o", b)[:2], [I["u_ret0"].pin("mdr", b)[:2], I["u_ret1"].pin("mdr", b)[:2]]))
    for g in (0, 1):
        r = I[f"u_ret{g}"]
        out.append(("q2f", r.pin("q2f")[:2], [c.pin("q2f_i", g)[:2]]))
        for b in range(16):
            out.append(("ga", r.pin("ga", b)[:2], [c.pin("ga_i", 16 * g + b)[:2]]))
        for nm, wd, per in (("r_v", 8, 1), ("r_row", 128, 16), ("r_pos", 24, 3), ("r_fp32", 256, 32), ("r_bf16", 128, 16), ("r_e", 8, 1)):
            for b in range(wd):
                d = r.pin(nm, b)
                out.append(("r_in", cpin(nm, wd * g + b, "S", d), [d[:2]]))
        k = 0
        for nm, wd in (("w_we", 8), ("w_addr", 152), ("w_data", 256)):
            for b in range(wd):
                d = r.pin(nm, b)
                # row writes leave on the S face in a strip E of the tile, in pin order along its E face
                px = r.x + r.w + 4.0 + 0.048 * k
                k += 1
                cpins[("o_" + nm, wd * g + b)] = ("S", (px, 0.0))
                out.append(("w_out", d[:2], [(px, 0.0)]))
    # controller scalar pins: N face straight above; ROM ports: N face beside the controller
    for nm, wd in (("go", 1), ("i_ph", 6), ("i_np", 3), ("i_xbase", 19), ("i_xps", 19), ("i_obase", 19), ("i_ops", 19), ("i_fmt", 2),
                   ("x_rv", 1), ("f_fault", 1)):
        for b in range(wd):
            d = c.pin(nm, b)
            out.append(("ctl_in", cpin(nm, b, d[2], d), [d[:2]]))
    for nm, wd in (("o_ready", 1), ("o_idle", 1), ("o_x_re", 1), ("o_x_addr", 19), ("o_fault", 1), ("o_ev", 1)):
        for b in range(wd):
            d = c.pin(nm, b)
            out.append(("ctl_out", d[:2], [cpin(nm, b, d[2], d)]))
    k = 0
    for nm, wd, drv in (("rom_pa0", 7, 1), ("rom_pa1", 7, 1), ("rom_sa", 8, 1), ("rom_pq0", 64, 0), ("rom_pq1", 64, 0), ("rom_sq", 48, 0)):
        for b in range(wd):
            d = c.pin(nm, b)
            px = (c.x - 6.0 - 0.096 * k) if d[2] == "W" else (c.x + c.w + 6.0 + 0.096 * k)
            k += 1
            cpins[(nm, b)] = ("N", (px, H_CL))
            out.append(("rom", d[:2], [(px, H_CL)]) if drv else ("rom", (px, H_CL), [d[:2]]))
    # clock / reset: N face, E of the controller (the spine root is at the port)
    cpins[("clk", 0)] = ("N", (c.x + c.w + 12.0, H_CL))
    cpins[("rst_n", 0)] = ("N", (c.x + c.w + 14.0, H_CL))
    # broadcast
    for name, lsb, n, chain, (src, port, s0) in bc_groups():
        for b in range(n):
            bit = lsb + b
            p = I[src].pin(port, s0 + b)[:2]
            for k, t in enumerate(chain):
                dn = I[t].pin("d", bit)[:2]
                out.append((f"bc.{name}.s{k}" if k == 0 else f"bc.s{k}.{chain[k - 1][2:]}>{t[2:]}", p, [dn]))
                p = I[t].pin("q", bit)[:2]
            out.append(("o_bus", p, [cpin("o_bus", bit, "E", p)]))
    return out, cpins


def hops(N):
    by = {}
    for bus, d, sinks in N:
        m = max(abs(d[0] - s[0]) + abs(d[1] - s[1]) for s in sinks)
        e = by.setdefault(bus, [0, 0.0, 0.0])
        e[0] += 1; e[1] = max(e[1], m); e[2] += m
    return {k: dict(nets=v[0], max_um=round(v[1], 1), mean_um=round(v[2] / v[0], 1)) for k, v in by.items()}



def insertions():
    """TT / FF / SS clock insertion of every child view (views/insertion.json, routed), ps"""
    out = {}
    for k, v in VIEWS.items():
        f = ROOT / v / "insertion.json"
        if not f.exists():
            out[k] = None
            continue
        j = json.loads(f.read_text())
        out[k] = {c: dict(mean=j[c]["all"]["mean"], min=j[c]["all"]["min"], max=j[c]["all"]["max"], sinks=j[c]["all"]["n"])
                  for c in ("tt", "ff", "ss") if c in j}
    return out


# ---------------------------------------------------------------------------------------------------- hop timing
# A hop A -> B of L um closes when  o_A + W_PS_UM * L + s_B <= T - U - SKEW  (die statement, tools/hier_contract/
# pinreg_audit.py): o = clock pin -> output pin minus the child's clock target, s = setup at the input pin plus the target,
# both read from the child's TT ETM; the cluster spine delivers every child's clock pin at  phi - target.  target =
# boundary-mean insertion (insertion.json) + CK_OFFSET_PS[kind].  '<= 500 um' alone is not a rule for these tiles:
# T_CTL launches aq_vin 308 ps after its reference and T_AQ's insertion spans 254..430 ps (gate 10-13).
T_PS, U_PS, SKEW_PS, W_PS_UM, MARGIN_PS = 833.333, 60.0, 50.0, 0.76, 30.0
CK_OFFSET_PS = {"aq": 30.0}        # T_AQ's clock pin 30 ps earlier than its boundary mean: q -> T_QB gains, x / v lose
# bus prefix -> [(driver kind, pin, sink kind, pin)]; None = a cluster pin
PAIR = {"x_q": [(None, None, "xin", "d")], "xq.aq": [("xin", "q", "aq", "x")], "xq.ix": [("xin", "q", "ix", "xw")],
        "aq_q": [("aq", "q", "qb", "aq_q")], "aq_e": [("aq", "e", "qb", "aq_e")], "aqf": [("aq", "fault", "ctl", "aqf")],
        "aq_vin": [("ctl", "aq_vin", "aq", "v")], "ba_v": [("ctl", "ba_v_o", "ix", "ba_v")],
        "ba_blk": [("ctl", "ba_blk_o", "ix", "ba_blk")], "h_hi": [("ctl", "h_hi_o", "ix", "h_hi")],
        "hw7": [("ctl", "hw_o", "ix", "hw7")], "aqi": [("ctl", "aqi_o", "qb", "aqi_d")],
        "h_b": [("ctl", "h_b0_o", "qb", "h_b0"), ("ctl", "h_b1_o", "qb", "h_b1")], "hw_sv": [("ctl", "hw_o", "qb", "hw_sv")],
        "mdr": [("ctl", "mdr_o", "ret", "mdr")], "q2f": [("ret", "q2f", "ctl", "q2f_i")], "ga": [("ret", "ga", "ctl", "ga_i")],
        "r_in": [(None, None, "ret", n) for n in ("r_v", "r_row", "r_pos", "r_fp32", "r_bf16", "r_e")],
        "w_out": [("ret", n, None, None) for n in ("w_we", "w_addr", "w_data")],
        "ctl_in": [(None, None, "ctl", n) for n in ("go", "i_ph", "i_np", "i_xbase", "i_xps", "i_obase", "i_ops", "i_fmt", "x_rv", "f_fault")],
        "ctl_out": [("ctl", n, None, None) for n in ("o_ready", "o_idle", "o_x_re", "o_x_addr", "o_fault", "o_ev")],
        "rom": [("ctl", n, None, None) for n in ("rom_pa0", "rom_pa1", "rom_sa")] + [(None, None, "ctl", n) for n in ("rom_pq0", "rom_pq1", "rom_sq")],
        "bc.ix": [("ix", "bt_d", "bc", "d")], "bc.ctl": [("ctl", "bc_hr_o", "bc", "d")],
        "bc.qb_he": [("qb", "he0", "bc", "d"), ("qb", "he1", "bc", "d")], "bc.qb_hq": [("qb", "hq0", "bc", "d"), ("qb", "hq1", "bc", "d")],
        "bc.s": [("bc", "q", "bc", "d")], "o_bus": [("bc", "q", None, None)]}


def bus_class(bus):
    b = re.sub(r"^(xq|aq_q|aq_e)\d", r"\1", bus)
    if b in PAIR:
        return b
    return max((k for k in PAIR if b.startswith(k)), key=len, default=None)


def etm():
    """per child kind: clock target (ps) and raw ETM numbers per pin base (clock pin -> output, setup at input), TT"""
    sys.path.insert(0, str(ROOT / "tools/hier_contract"))
    import pinreg_audit as PA  # noqa: E402
    out = {}
    for k, v in VIEWS.items():
        lib = PA.parse_lib(ROOT / v / (Path(v).name + "_tt.lib"))
        ins = json.loads((ROOT / v / "insertion.json").read_text())["tt"]
        o, s = {}, {}
        for n, p in lib["pins"].items():
            base = re.sub(r"\[\d+\]$", "", n)
            for typ, _, tb in p["arcs"]:
                if typ == "rising_edge":
                    f = [tb[x][0] for x in ("cell_rise", "cell_fall") if tb.get(x)]
                    if f:
                        o[base] = max(o.get(base, -1e9), max(f))
                elif typ and typ.startswith("setup_"):
                    c = [x for y in ("rise_constraint", "fall_constraint") for x in tb.get(y, [])]
                    if c:
                        s[base] = max(s.get(base, -1e9), max(c))
        out[k] = dict(target=ins["boundary"]["mean"] + CK_OFFSET_PS.get(k, 0.0), boundary=ins["boundary"], o=o, s=s)
    return out


def timing(hp):
    """[(bus, pair, o, s, L, slack)]: slack of every bus against the hop statement (cluster pins: o / s at the pin reported)"""
    E = etm()
    rows = []
    for bus, h in hp.items():
        c = bus_class(bus)
        if c is None:
            rows.append(dict(bus=bus, error="no pin pair for this bus"))
            continue
        for a, ap, z, zp in PAIR[c]:
            o = E[a]["o"][ap] - E[a]["target"] if a else None
            s = E[z]["s"][zp] + E[z]["target"] if z else None
            L = h["max_um"]
            r = dict(bus=bus, pair=f"{a or 'IN'}.{ap or ''} -> {z or 'OUT'}.{zp or ''}", L_um=L)
            if a and z:
                r.update(o_ps=round(o, 1), s_ps=round(s, 1), slack_ps=round(T_PS - U_PS - SKEW_PS - MARGIN_PS - o - s - W_PS_UM * L, 1),
                         reach_um=round((T_PS - U_PS - SKEW_PS - MARGIN_PS - o - s) / W_PS_UM, 1))
            elif a:
                r.update(o_ps=round(o, 1), o_at_cluster_pin_ps=round(o + W_PS_UM * L, 1))
            else:
                r.update(s_ps=round(s, 1), s_at_cluster_pin_ps=round(s + W_PS_UM * L, 1))
            rows.append(r)
    return rows, {k: dict(target_ps=round(v["target"], 1), boundary=v["boundary"]) for k, v in E.items()}


TRK = 0.048


def trk(v):
    """M4 / M5 track (offset 0.012, pitch 0.048)"""
    return round(round((v - 0.012) / TRK) * TRK + 0.012, 4)


def io_tcl(cp):
    """place_pin for every cluster pin: N / S faces on M5, E / W on M4, each on its own track"""
    used, lines = {}, ["# generated by tools/s81/sp_pq_plan.py --write: dsfd_sp_pq cluster pins, each straight in front of the child",
                       "# pin it wires to (S: x_q under the T_XIN d pins, r_* under the T_RET pins, o_w_* in a strip E of each T_RET;",
                       "# N: the controller's scalar pins above T_CTL, the ROM ports beside it, clk / rst_n; E: o_bus at the last",
                       "# relay's q pins).  M5 on N / S, M4 on E, one pin per track."]
    for (name, bit), (face, (x, y)) in sorted(cp.items(), key=lambda kv: (kv[1][0], kv[0][0], kv[0][1])):
        c = trk(x if face in "NS" else y)
        while (face, c) in used:                 # two pins on one track: next free track
            c = round(c + 2 * TRK, 4)
        used[(face, c)] = name
        nm = name if WIDTH[name] == 1 else f"{name}[{bit}]"
        if face in "NS":
            lines.append(f"place_pin -pin_name {{{nm}}} -layer M5 -location {{{c:.3f} {0.0 if face == 'S' else H_CL}}} "
                         "-pin_size {0.024 0.192} -force_to_die_boundary")
        else:
            lines.append(f"place_pin -pin_name {{{nm}}} -layer M4 -location {{{W_CL if face == 'E' else 0.0} {c:.3f}}} "
                         "-pin_size {0.192 0.024} -force_to_die_boundary")
    return "\n".join(lines) + "\n"


WIDTH = dict(clk=1, rst_n=1, go=1, i_ph=6, i_np=3, i_xbase=19, i_xps=19, i_obase=19, i_ops=19, i_fmt=2, f_fault=1, o_ready=1,
             o_idle=1, o_fault=1, o_ev=1, o_x_re=1, o_x_addr=19, x_rv=1, x_q=2048, r_v=16, r_row=256, r_pos=48, r_fp32=512,
             r_bf16=256, r_e=16, o_w_we=16, o_w_addr=304, o_w_data=512, o_bus=1630, rom_pa0=7, rom_pa1=7, rom_pq0=64,
             rom_pq1=64, rom_sa=8, rom_sq=48)

H_TR = (0.036, 0.048, 0.064)      # M2, M4, M6 pitch (horizontal layers);  over a hard child only M6 (not over an M6-PG child)
V_TR = (0.036, 0.048, 0.064)      # M3, M5, M7 (vertical);                 over a hard child only M7
PG6 = {"ix"}                      # children whose own PG is on M6: nothing of the cluster on M6 above them
USE = 0.85                        # tracks left by the cluster's own M6 / M7 power stripes over a child


def cuts(I, N, step=21.6):
    """nets whose bounding box spans the line / tracks free on the line"""
    res = []
    boxes = [(i.kind, *i.box()) for i in I.values()]
    for ax, lim, span, tr in (("x", W_CL, H_CL, H_TR), ("y", H_CL, W_CL, V_TR)):
        c = step
        while c < lim - 1e-6:
            dem = 0
            for _, d, sinks in N:
                v = [d[0 if ax == "x" else 1]] + [s[0 if ax == "x" else 1] for s in sinks]
                if min(v) < c < max(v):
                    dem += 1
            if dem:
                cov = cov6 = 0.0
                for k, x0, y0, x1, y1 in boxes:
                    a0, a1, b0, b1 = (x0, x1, y0, y1) if ax == "x" else (y0, y1, x0, x1)
                    if a0 < c < a1:
                        cov += b1 - b0
                        if k in PG6 and ax == "x":
                            cov6 += b1 - b0
                free = span - cov
                cap = free * sum(1 / p for p in tr) + (cov - cov6) * USE / tr[2]
                res.append(dict(ax=ax, at=round(c, 2), nets=dem, tracks=int(cap), util=round(dem / cap, 3)))
            c += step
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path)
    ap.add_argument("--write", action="store_true", help="write the children[] block and the place_pin file")
    ap.add_argument("--plan-origins", action="store_true", help="ignore the kit's floorplan.json origins")
    a = ap.parse_args()
    lib = {}
    for k, v in VIEWS.items():
        p = ROOT / v / (Path(v).name + ".lef")
        lib[k] = lef(p) if p.exists() else bc_synth()
    P = plan_default()
    I = build(P, lib)
    kit = ROOT / RT / "dsfd_sp_pq_c/floorplan.json"
    if kit.exists() and not a.plan_origins:      # the generator's on-track origins (mirrored children move 0.024 um)
        for b in json.loads(kit.read_text())["blocks"]:
            if b.get("inst") in I:
                I[b["inst"]].x, I[b["inst"]].y = float(b["x"]), float(b["y"])
    # legality (ref_tile floorplan rules): >= 20 um channels between children and to the core edge (core margin 2.16)
    names = list(I)
    bad = []
    for i, n in enumerate(names):
        x0, y0, x1, y1 = I[n].box()
        if x0 < 22.16 - 1e-6 or y0 < 22.16 - 1e-6 or x1 > W_CL - 22.16 + 1e-6 or y1 > H_CL - 22.16 + 1e-6:
            bad.append(f"{n} outside the core window: {I[n].box()}")
        for m in names[i + 1:]:
            u0, v0, u1, v1 = I[m].box()
            if x0 < u1 + 19.99 and u0 < x1 + 19.99 and y0 < v1 + 19.99 and v0 < y1 + 19.99:
                bad.append(f"{n} / {m} closer than 20 um")
    N, cp = nets(I)
    hp = hops(N)
    ct = cuts(I, N)
    worst_cut = max(ct, key=lambda c: c["util"])
    over = {k: v for k, v in hp.items() if v["max_um"] > 500.0}
    print(f"children {len(I)}; cluster pins {len(cp)}; nets {len(N)}")
    for k, v in sorted(hp.items(), key=lambda kv: -kv[1]["max_um"]):
        print(f"  {k:28s} nets {v['nets']:5d}  max {v['max_um']:6.1f}  mean {v['mean_um']:6.1f}")
    print("worst cut", worst_cut, "| cuts > 0.60:", [c for c in ct if c["util"] > 0.60][:8])
    print("LEGALITY", "OK" if not bad else bad[:10])
    print("HOPS", "OK (all <= 500 um)" if not over else f"OVER 500: {over}")
    tm, targets = timing(hp)
    neg = [r for r in tm if r.get("slack_ps", 0) < 0 or r.get("error")]
    worst = {}
    for r in tm:
        if "slack_ps" in r and (r["pair"] not in worst or r["slack_ps"] < worst[r["pair"]]["slack_ps"]):
            worst[r["pair"]] = r
    for r in sorted(worst.values(), key=lambda r: r["slack_ps"])[:14]:
        print(f"  T {r['bus']:20s} {r['pair']:34s} o {r['o_ps']:6.1f} s {r['s_ps']:6.1f} L {r['L_um']:6.1f} reach {r['reach_um']:6.1f} slack {r['slack_ps']:7.1f}")
    io = [r for r in tm if "o_at_cluster_pin_ps" in r or "s_at_cluster_pin_ps" in r]
    print("  cluster pins: worst o", max((r.get("o_at_cluster_pin_ps", 0), r["bus"]) for r in io), "worst s", max((r.get("s_at_cluster_pin_ps", 0), r["bus"]) for r in io))
    print("TIMING", "OK (every hop >= 0 with %g ps margin, skew %g)" % (MARGIN_PS, SKEW_PS) if not neg else f"FAIL: {[(r['bus'], r.get('slack_ps', r.get('error'))) for r in neg][:8]}")
    ins = insertions()
    print("child TT insertion (ps):", {k: (v and v["tt"]["mean"]) for k, v in ins.items()})
    if a.write:
        ch = [dict(view=VIEWS[i.kind], count=1, inst=n, at=[round(GX + P[n][1], 3), P[n][2]], orient=i.o) for n, i in I.items()]
        out = ROOT / "physical/s81_ph_pq"
        out.mkdir(parents=True, exist_ok=True)
        (out / "dsfd_sp_pq_children.json").write_text(json.dumps(ch, indent=1) + "\n")
        (out / "dsfd_sp_pq_pins.tcl").write_text(io_tcl(cp))
        faces = {}
        for (name, _), (f, _) in cp.items():
            faces.setdefault(f, set()).add(name)
        (out / "dsfd_sp_pq_faces.json").write_text(json.dumps({f: sorted(v) for f, v in faces.items()}, indent=1) + "\n")
        print("wrote", out / "dsfd_sp_pq_children.json", out / "dsfd_sp_pq_pins.tcl", len(cp), "pins")
    rec = dict(schema="opentallas.s81.sp_pq_plan.v1", outline=[W_CL, H_CL], gx=GX, child_insertion_ps=ins,
               cluster_pins={f: sum(1 for v in cp.values() if v[0] == f) for f in "NSEW"},
               children={n: dict(kind=i.kind, at=[round(i.x, 3), round(i.y, 3)], orient=i.o, w=i.w, h=i.h) for n, i in I.items()},
               hops=hp, cuts=ct, worst_cut=worst_cut, legality=bad, hop_timing=tm, clock_targets=targets,
               hop_rule=dict(T_ps=T_PS, unc_ps=U_PS, skew_ps=SKEW_PS, margin_ps=MARGIN_PS, wire_ps_um=W_PS_UM, ck_offset_ps=CK_OFFSET_PS))
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps(rec, indent=1) + "\n")
    return 0 if not bad and not over and not neg and worst_cut["util"] <= 0.60 else 1


if __name__ == "__main__":
    sys.exit(main())
