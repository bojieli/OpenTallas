#!/usr/bin/env python3
"""CORE-S81-SVC 10-23: planned hard core of the S81 svc attention engine + its placement in the svc partition types.

    python3 physical/die_plan/s81/cores/svc/gen_svc_cores.py [--cells N] [--std-um2 A]

Core = ot_s81c_attn_hcore (rtl/hdc/v41x/ot_s81c_attn_hcore.sv): ONE attention head with its own front end
(ot_hdc_v41x_attn_hgrp_s at HG 1 / PCOLP 1), a register on every pin.  64 per svc partition (NT 4 tiles x H 16).
Writes (this directory):
  pins/ot_s81c_attn_hcore.json  pin table, CORE-KS format {module, lef, source, pinhash, pins[{name, layer, x, y}]}
                                (core frame um; M4/M5 centres on 0.012 + k*0.048 = on the kit tracks after the S81
                                core track offset [0.108, 0.012] from an 8.64-lattice origin)
  ot_s81c_attn_hcore.lef        abstract stub (SIZE + pin rects + OBS M1-M5): gen_plan_v4 NONFRAME_HC reads SIZE
  cores_svc.json                {core: module, outline, pins_file, lef, cells, placement per svc partition type}
  renders/hcore_plan.png, renders/svc_placement_<type>.png
Placement (one svc partition 1442.88 x 2453.76, orient R0, origins on the 8.64 lattice, >= 13.8 um facing gaps,
34.56 um edge keep-off as gen_plan_v4 HC_GAP_UM / HC_EDGE_UM): 4 head rows (tiles 0-1) | centre band (8 sx_hrow
216 x 216 cores in 2 rows of 4 + the engine / staging soft region E of them) | 4 head rows (tiles 2-3).
"""
import argparse, hashlib, json, math, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
G = 8.64
GAP, EDGE = 13.8, 4 * 8.64
TOFF = (0.108, 0.012)
MOD = "ot_s81c_attn_hcore"
W, H = 157.68, 218.16           # 73 x 2.16, 101 x 2.16
PX, PY = 172.8, 233.28          # origin pitches (20 / 27 lattice): gaps 15.12 / 15.12
HROW = ("dsdv_svc_sx_hrow", 216.0, 216.0)
SVC_OUT = (1442.88, 2453.76)


def trk(v):  # nearest M4/M5 core-frame track 0.012 + k*0.048
    return round(0.012 + round((v - 0.012) / 0.048) * 0.048, 3)


def bus(n, w):
    return [n] if w == 1 else [f"{n}[{i}]" for i in range(w)]


def spread(names, lo, hi):
    """names evenly over [lo, hi] on distinct tracks"""
    n = len(names)
    step = (hi - lo) / max(n, 1)
    out, last = [], -1
    for i, nm in enumerate(names):
        c = trk(lo + (i + 0.5) * step)
        k = round((c - 0.012) / 0.048)
        if k <= last:
            k = last + 1
        last = k
        out.append((nm, round(0.012 + k * 0.048, 3)))
    assert out[-1][1] <= hi + 0.05, (names[0], out[-1], hi)
    return out


def pins():
    P = []
    m = 4.32
    # W face (M4): load stream (control first = S end, then ld_w, ld_wp)
    wn = bus("ld_v", 1) + bus("ld_mode", 1) + bus("ld_bank", 3) + bus("ld_grp", 8) + bus("ld_w2v", 1) + \
        bus("ld_w", 512) + bus("ld_wp", 64)
    P += [dict(name=n, layer="M4", x=0.0, y=y) for n, y in spread(wn, m, H - m)]
    # N face (M5): operand stream
    nn = bus("iv", 1) + bus("ibank", 3) + bus("ib", 576)
    P += [dict(name=n, layer="M5", x=x, y=H) for n, x in spread(nn, m, W - m)]
    # E face (M4): results (centre third) + static head index
    en = bus("ov", 1) + bus("oy", 32) + bus("oflt", 1)
    P += [dict(name=n, layer="M4", x=W, y=y) for n, y in spread(en, H / 2 - 20, H / 2 + 20)]
    P += [dict(name=n, layer="M4", x=W, y=y) for n, y in spread(bus("gid", 8), 20, 30)]
    # S face (M5): clock + reset at the centre (CTS root under the flop mass)
    P += [dict(name="clk", layer="M5", x=trk(W / 2), y=0.0), dict(name="rst_n", layer="M5", x=trk(W / 2 + 3), y=0.0)]
    return P


def face(p):
    return "W" if p["x"] == 0 else "E" if p["x"] == W else "S" if p["y"] == 0 else "N"


def lef_text(P):
    dirs = {**{n: "INPUT" for n in ("clk", "rst_n", "ld_v", "ld_mode", "ld_w2v", "iv")}}
    L = [f"VERSION 5.8 ;", "BUSBITCHARS \"[]\" ;", "DIVIDERCHAR \"/\" ;",
         f"MACRO {MOD}", "  CLASS BLOCK ;", "  ORIGIN 0 0 ;", f"  FOREIGN {MOD} 0 0 ;", f"  SIZE {W:g} BY {H:g} ;",
         "  SYMMETRY X Y ;"]
    for p in P:
        b = p["name"].split("[")[0]
        d = "OUTPUT" if b in ("ov", "oy", "oflt") else "INPUT"
        use = "CLOCK" if b == "clk" else "SIGNAL"
        f = face(p)
        if f in "EW":
            x0 = 0.0 if f == "W" else W - 0.192
            r = (x0, p["y"] - 0.012, x0 + 0.192, p["y"] + 0.012)
        else:
            y0 = 0.0 if f == "S" else H - 0.192
            r = (p["x"] - 0.012, y0, p["x"] + 0.012, y0 + 0.192)
        L += [f"  PIN {p['name']}", f"    DIRECTION {d} ;", f"    USE {use} ;", "    PORT",
              f"      LAYER {p['layer']} ;", "        RECT %.3f %.3f %.3f %.3f ;" % r, "    END", f"  END {p['name']}"]
    for pg in ("VDD", "VSS"):
        L += [f"  PIN {pg}", "    DIRECTION INOUT ;", f"    USE {'POWER' if pg == 'VDD' else 'GROUND'} ;", "  END " + pg]
    L += ["  OBS"] + [f"    LAYER M{i} ;\n      RECT 0.200 0.200 {W - 0.2:.3f} {H - 0.2:.3f} ;" for i in range(1, 6)] + \
         ["  END", f"END {MOD}", "END LIBRARY", ""]
    return "\n".join(L)


def stats(P):
    out = {}
    for f, span in (("N", W), ("S", W), ("E", H), ("W", H)):
        q = [p for p in P if face(p) == f]
        c = sorted((p["x"] if f in "NS" else p["y"]) for p in q)
        mx = max((sum(1 for v in c if a <= v < a + 10) for a in c), default=0)
        out[f] = dict(pins=len(q), span_um=span, per_um=round(len(q) / span, 2), max_10um=mx,
                      pin_per_track=round(len(q) / (span / 0.048), 3), layers=sorted({p["layer"] for p in q}),
                      extent_um=[round(c[0], 3), round(c[-1], 3)] if c else None)
    return out


def up(v):
    return math.ceil(round(v / G, 6)) * G


def placement():
    """64 heads (8 per row) + 8 hrow cores, R0, lattice origins"""
    w, h = SVC_OUT
    cores = []
    x0 = y0 = up(EDGE)
    rows = []
    y = y0
    for r in range(4):
        rows.append(y); y += PY
    band_y = up(y - PY + H + TOFF[1] + GAP)          # hrow band above head row 3
    hy = [band_y, up(band_y + HROW[2] + GAP)]
    y = up(hy[1] + HROW[2] + GAP)
    for r in range(4):
        rows.append(y); y += PY
    for r, yy in enumerate(rows):
        t = r // 2
        for c in range(8):
            hd = (r % 2) * 8 + c
            cores.append(dict(inst=f"u_rsv.u_att.u_eng.g_t[{t}].g_ts.u_t.u_hc.g_h[{hd}].u_c", module=MOD,
                              plan_core=f"attn_t{t}_h{hd}", origin_um=[round(x0 + c * PX, 3), round(yy, 3)],
                              outline_um=[W, H], orient="R0", track_offset_um=list(TOFF)))
    hpx = up(HROW[1] + GAP)
    for r in range(2):
        for b in range(4):
            k = r * 4 + b
            cores.append(dict(inst="u_rsv.u_sx.g_r[%d].g_h[%d].u_hrow" % (k // 2, k % 2), module=HROW[0],
                              plan_core="sx_hrow_ab", origin_um=[round(x0 + b * hpx, 3), round(hy[r], 3)],
                              outline_um=[HROW[1], HROW[2]], orient="R0", track_offset_um=list(TOFF)))
    # checks: inside the edge keep-off, pairwise gaps
    errs = []
    for c in cores:
        ox, oy = c["origin_um"][0] + TOFF[0], c["origin_um"][1] + TOFF[1]
        cw, ch = c["outline_um"]
        if ox < EDGE - 1e-6 or oy < EDGE - 1e-6 or ox + cw > w - EDGE + 1e-6 or oy + ch > h - EDGE + 1e-6:
            errs.append(("edge", c["inst"]))
        for o in (c["origin_um"][0] / G, c["origin_um"][1] / G):
            if abs(o - round(o)) > 1e-6:
                errs.append(("lattice", c["inst"]))
    for i, a in enumerate(cores):
        ax, ay = a["origin_um"]; aw, ah = a["outline_um"]
        for b in cores[i + 1:]:
            bx, by = b["origin_um"]; bw, bh = b["outline_um"]
            dx = max(bx - (ax + aw), ax - (bx + bw)); dy = max(by - (ay + ah), ay - (by + bh))
            if max(dx, dy) < GAP - 1e-6:
                errs.append(("gap", a["inst"], b["inst"], round(max(dx, dy), 3)))
    soft = [round(x0 + 4 * hpx - GAP + GAP, 3), round(hy[0], 3), round(w - EDGE, 3), round(hy[1] + HROW[2], 3)]
    return cores, errs, soft


def render_core(P, path):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    col = {"M4": "tab:red", "M5": "tab:blue"}
    fig, ax = plt.subplots(figsize=(7, 9))
    ax.add_patch(plt.Rectangle((0, 0), W, H, fill=False, lw=1.5))
    ax.add_patch(plt.Rectangle((4.32, 4.32), W - 8.64, H - 8.64, fill=False, lw=0.5, ls="--", color="gray"))
    grp = {}
    for p in P:
        grp.setdefault(p["name"].split("[")[0], []).append(p)
    for b, q in grp.items():
        for p in q:
            f = face(p)
            if f in "EW":
                ax.plot([p["x"], p["x"] + (3 if f == "W" else -3)], [p["y"], p["y"]], color=col[p["layer"]], lw=0.3)
            else:
                ax.plot([p["x"], p["x"]], [p["y"], p["y"] + (3 if f == "S" else -3)], color=col[p["layer"]], lw=0.3)
        xs = sum(p["x"] for p in q) / len(q); ys = sum(p["y"] for p in q) / len(q)
        f = face(q[0])
        dx = {"W": 8, "E": -8, "N": 0, "S": 0}[f]; dy = {"W": 0, "E": 0, "N": -8, "S": 8}[f]
        ax.text(xs + dx, ys + dy, f"{b} ({len(q)})", fontsize=7, ha="left" if f == "W" else "right" if f == "E" else "center",
                va="center")
    st = stats(P)
    ax.set_title(f"{MOD}  {W} x {H} um  {len(P)} pins (M4 red E/W, M5 blue N/S)\n" +
                 "  ".join(f"{f}:{st[f]['pins']} {st[f]['per_um']}/um" for f in "NSEW"), fontsize=8)
    ax.set_xlim(-25, W + 25); ax.set_ylim(-15, H + 15); ax.set_aspect("equal")
    fig.savefig(path, dpi=130); plt.close(fig)


def render_svc(cores, soft, tn, path):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    w, h = SVC_OUT
    fig, ax = plt.subplots(figsize=(8, 13))
    ax.add_patch(plt.Rectangle((0, 0), w, h, fill=False, lw=1.5))
    ax.add_patch(plt.Rectangle((EDGE, EDGE), w - 2 * EDGE, h - 2 * EDGE, fill=False, lw=0.5, ls="--", color="gray"))
    tc = ["#cfe2f3", "#d9ead3", "#fff2cc", "#f4cccc"]
    for c in cores:
        x, y = c["origin_um"][0] + TOFF[0], c["origin_um"][1] + TOFF[1]
        cw, ch = c["outline_um"]
        if c["module"] == MOD:
            t = int(c["plan_core"].split("_")[1][1:])
            ax.add_patch(plt.Rectangle((x, y), cw, ch, fc=tc[t], ec="k", lw=0.6))
            ax.add_patch(plt.Rectangle((x, y + 4), 3, ch - 8, fc="tab:red", ec="none"))       # W ld pins
            ax.add_patch(plt.Rectangle((x + 4, y + ch - 3), cw - 8, 3, fc="tab:blue", ec="none"))  # N ib pins
            ax.add_patch(plt.Rectangle((x + cw - 3, y + ch / 2 - 20), 3, 40, fc="tab:purple", ec="none"))  # E oy
            ax.text(x + cw / 2, y + ch / 2, c["plan_core"].replace("attn_", ""), fontsize=6, ha="center")
        else:
            ax.add_patch(plt.Rectangle((x, y), cw, ch, fc="#d0d0d0", ec="k", lw=0.6))
            ax.text(x + cw / 2, y + ch / 2, "sx_hrow", fontsize=6, ha="center")
    ax.add_patch(plt.Rectangle((soft[0], soft[1]), soft[2] - soft[0], soft[3] - soft[1], fc="none", ec="tab:green",
                               lw=1.2, ls="--"))
    ax.text((soft[0] + soft[2]) / 2, (soft[1] + soft[3]) / 2, "engine / svc_att staging\n(soft + 8 SRAM)", fontsize=7,
            ha="center", color="tab:green")
    ax.plot([725.76], [1226.88], marker="*", color="orange", ms=12)
    ax.set_title(f"{tn}: 64 x {MOD} ({W}x{H}) + 8 sx_hrow, R0, lattice origins\n"
                 "tiles t0..t3 coloured; red=W ld pins, blue=N ib pins, purple=E results; star = clock tap", fontsize=8)
    ax.set_xlim(-20, w + 20); ax.set_ylim(-20, h + 20); ax.set_aspect("equal")
    fig.savefig(path, dpi=110); plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cells", type=int, default=None, help="synth cell count of the core (else the estimate)")
    ap.add_argument("--std-um2", type=float, default=None, help="synth std-cell area um2")
    ap.add_argument("--cells-src", default=None)
    a = ap.parse_args()
    P = pins()
    names = [p["name"] for p in P]
    assert len(names) == len(set(names))
    for p in P:
        c = p["y"] if p["layer"] == "M4" else p["x"]
        k = (c - 0.012) / 0.048
        assert abs(k - round(k)) < 1e-4, p
    (HERE / "pins").mkdir(exist_ok=True); (HERE / "renders").mkdir(exist_ok=True)
    lef_rel = f"physical/die_plan/s81/cores/svc/{MOD}.lef"
    (HERE / f"{MOD}.lef").write_text(lef_text(P))
    ph = hashlib.sha256(json.dumps(sorted((p["name"], p["layer"], p["x"], p["y"]) for p in P)).encode()).hexdigest()[:12]
    pt = dict(module=MOD, lef=lef_rel, source="CORE-S81-SVC 10-23 gen_svc_cores.py (planned pins, top-down)",
              pinhash=ph, pins=P)
    (HERE / "pins" / f"{MOD}.json").write_text(json.dumps(pt, indent=0) + "\n")
    st = stats(P)
    render_core(P, HERE / "renders" / "hcore_plan.png")
    cores, errs, soft = placement()
    plan = json.load(open(REPO / "physical/die_plan/s81/die_plan.json"))
    types = [tn for tn in plan["partition_types"] if tn.startswith("svc_")]
    est_cells = 183981 + 30272 // 4 * 0 + 21000      # hdp_s + one head's front end (estimate until synth)
    cells = a.cells or est_cells
    std = a.std_um2 or 0.0207e6 * cells / 183981
    core_area = (W - 8.64) * (H - 8.64)
    fits = {}
    for tn in types:
        t = plan["partition_types"][tn]
        others = [c["module"] for c in t["contents"] if c["module"] not in ("dsdv_svc_rs", "dsdv_svc_pvso_entry")]
        fits[tn] = dict(outline_um=t["outline_um"], heads=64, hrow=8, extra_contents=others,
                        fits=(not errs and not others and t["outline_um"] == list(SVC_OUT)),
                        note=("extra contents need area outside the 64+8 core array: " + ", ".join(others)
                              if others else "64 heads + 8 hrow + engine soft region fit"))
    out = dict(schema="opentallas.s81.svc_cores.v1", author="CORE-S81-SVC", date="2026-10-23",
               core=dict(module=MOD, rtl="rtl/hdc/v41x/ot_s81c_attn_hcore.sv", select_define="OT_ATTN_HCORE",
                         outline_um=[W, H], pins_file=f"cores/svc/pins/{MOD}.json", lef=lef_rel, pins=len(P),
                         pinhash=ph, cells=cells, cells_source=a.cells_src or "ESTIMATE hdp_s 183,981 (S81-P5 synth) + "
                         "one head front end ~21k; replace with the kit synth", std_um2=round(std, 1),
                         fill_of_core=round(std / core_area, 3), faces=st, per_svc=64,
                         register_on_every_pin="inputs: R0 r_iv/r_ibank/r_ib, kreg copies of ld_* and ld_wp, hh<=gid; "
                         "outputs: ov/oy/oflt registers (hgrp_s HG1 PCOLP1)"),
               replaces=dict(hdp_s="64 x 183,981", hgrp_s_local="16 x 30,272", why="one head + own front end = "
                             "hgrp_s at HG 1: every pin registered, one master, no G->head fan-out cores"),
               placement=dict(svc_outline_um=list(SVC_OUT), orient="R0", gap_um=GAP, edge_um=EDGE,
                              pitch_um=[PX, PY], track_offset_um=list(TOFF), hard_cores=cores, errors=errs,
                              soft_region_um=soft),
               types=fits)
    (HERE / "cores_svc.json").write_text(json.dumps(out, indent=1) + "\n")
    render_svc(cores, soft, "svc_hi_* / svc_lo_* (outline 1442.88 x 2453.76)", HERE / "renders" / "svc_placement.png")
    print(json.dumps(dict(pins=len(P), faces={f: (v["pins"], v["per_um"]) for f, v in st.items()}, errors=errs[:5],
                          cells=cells, fill=out["core"]["fill_of_core"], soft=soft), indent=None))


if __name__ == "__main__":
    main()
