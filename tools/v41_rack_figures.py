#!/usr/bin/env python3
"""Figures for the V4.1 ROM rack design (inline SVG in the technical report's style).

Reads results/arch/v41_rack.json (tools/v41_rack_design.py) and writes standalone snippets
results/arch/figures/v41_rack_{logical,elevation,links,compare}.html -- each a <figure class="fig"> the report can
drop in verbatim -- plus v41_rack_preview.html, which wraps them in the report's CSS tokens (light and dark).
Colours are the report's tokens only (--rom, --rom-soft, --hbm, --hbm-soft, --ink, --muted, --faint, --rule,
--grid, --panel, --code, --ok, --warn, --bad).
"""
from __future__ import annotations

import html
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "results/arch/v41_rack.json"
FIG = ROOT / "results/arch/figures"

SANS = "IBM Plex Sans, system-ui, sans-serif"
MONO = "IBM Plex Mono, ui-monospace, monospace"


def esc(s):
    return html.escape(str(s), quote=True)


def T(x, y, s, size=11, fill="var(--ink)", anchor="start", weight=400, mono=False, extra=""):
    fam = MONO if mono else SANS
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" style="fill:{fill}" {extra}>{esc(s)}</text>')


def R(x, y, w, h, fill="var(--panel)", stroke="var(--rule)", sw=1, rx=2, dash=None, extra=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" '
            f'style="fill:{fill};stroke:{stroke};stroke-width:{sw}"{d} {extra}/>')


def L(x1, y1, x2, y2, stroke="var(--muted)", sw=1.2, dash=None, arrow=False, mid="a"):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    m = f' marker-end="url(#{mid})"' if arrow else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'style="stroke:{stroke};stroke-width:{sw}"{d}{m}/>')


def P(d, stroke="var(--muted)", sw=1.2, dash=None, arrow=False, fill="none", mid="a"):
    ds = f' stroke-dasharray="{dash}"' if dash else ""
    m = f' marker-end="url(#{mid})"' if arrow else ""
    return f'<path d="{d}" style="fill:{fill};stroke:{stroke};stroke-width:{sw}"{ds}{m}/>'


def markers(prefix):
    out = ["<defs>"]
    for name, col in (("a", "var(--muted)"), ("r", "var(--rom)"), ("h", "var(--hbm)"), ("k", "var(--ink)")):
        out.append(f'<marker id="{prefix}{name}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" '
                   f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" style="fill:{col}"/></marker>')
    out.append("</defs>")
    return "".join(out)


def figure(fid, vb, body, aria, caption):
    return (f'<figure class="fig" id="fig-{fid}">\n  <div class="svgbox"><svg viewBox="{vb}" role="img" '
            f'aria-label="{esc(aria)}" xmlns="http://www.w3.org/2000/svg">{body}</svg></div>\n'
            f'  <figcaption>{caption}</figcaption>\n</figure>\n')


def kfmt(b):
    for u, f in (("GB", 1e9), ("MB", 1e6), ("KB", 1e3)):
        if b >= f:
            return f"{b / f:.1f} {u}"
    return f"{b:.0f} B"


# ---------------------------------------------------------------------------------------------------------
def fig_logical(rec):
    pl = rec["logical"]
    tr = rec["traffic"]
    groups = {g["stage"]: g for g in pl["groups"]}
    kv = set(pl["kv_owner_stages"])
    idx = set(pl["index_stages"])
    eng = {v: k for k, v in pl["engram_consumers"].items()}
    out = [markers("lg")]
    W, H, gap, x0 = 58, 74, 7, 78
    y1, y2 = 58, 188

    def mod_xy(s):
        if s < 14:
            return x0 + s * (W + gap), y1
        return x0 + (27 - s) * (W + gap), y2

    out.append(T(x0, 30, "Token ring: 29 stage modules (tensor group 4 = one package pair each)", 12, weight=600))
    hh = pl["counts"].get("head_hbm_stacks_per_die", 0)
    out.append(T(x0, 45, "layer stage S0-S27 on 112 dies with 4 HBM3E stacks each; H = head + embedding + DSpark "
                          "(4 dies, %s)" % ("%d HBM3E each" % hh if hh else "no HBM"), 10.5, "var(--muted)"))

    def module(x, y, label, sub, head=False):
        s = []
        s.append(R(x, y, W, H, "var(--rom-soft)" if not head else "var(--hbm-soft)",
                   "var(--rom)" if not head else "var(--hbm)", 1.2, 3))
        s.append(T(x + W / 2, y + 12, label, 10.5, anchor="middle", weight=600, mono=True))
        # two packages side by side, two dies each
        for p in range(2):
            px = x + 5 + p * 25
            s.append(R(px, y + 17, 23, 30, "var(--panel)", "var(--muted)", 0.8, 2))
            for d in range(2):
                s.append(R(px + 3, y + 20 + d * 13, 17, 11,
                           "var(--rom)" if not head else "var(--hbm)", "none", 0, 1, extra='opacity="0.85"'))
        s.append(L(x + 28, y + 32, x + 30, y + 32, "var(--ink)", 2))
        s.append(T(x + W / 2, y + 60, sub, 8.5, "var(--muted)", "middle", mono=True))
        return "".join(s)

    for s in range(28):
        g = groups[s]
        x, y = mod_xy(s)
        lay = [l["layer"] for l in g["layers"]]
        sub = f"L{lay[0]}-{lay[-1]}" if len(lay) > 1 else f"L{lay[0]}"
        out.append(module(x, y, f"S{s}", sub))
        badges = []
        if s in kv:
            badges.append(("KV", "var(--hbm)"))
        elif s in idx:
            badges.append(("IX", "var(--hbm)"))
        if s in eng:
            badges.append((f"E{eng[s]}", "var(--ok)"))
        for i, (b, c) in enumerate(badges):
            bx = x + 3 + i * 27
            out.append(R(bx, y + H - 11, 24, 9, c, "none", 0, 2))
            out.append(T(bx + 12, y + H - 4, b, 7.5, "var(--panel)", "middle", 600, True))
        # ring arrows
        if s < 13:
            out.append(L(x + W, y + H / 2, x + W + gap - 1, y + H / 2, "var(--ink)", 1.3, arrow=True, mid="lgk"))
        elif s == 13:
            xa, ya = mod_xy(14)
            out.append(P(f"M{x + W},{y + H / 2} h8 V{ya + H / 2} h-8", "var(--ink)", 1.3, arrow=True, mid="lgk"))
        elif s < 27:
            xn, _ = mod_xy(s + 1)
            out.append(L(x, y + H / 2, xn + W + 1, y + H / 2, "var(--ink)", 1.3, arrow=True, mid="lgk"))
    # head module between rows at the left
    hx, hy = 8, (y1 + y2) / 2
    out.append(module(hx, hy, "H", "S28", head=True))
    x27, y27 = mod_xy(27)
    x0_, y0_ = mod_xy(0)
    out.append(P(f"M{x27},{y27 + H / 2} H{hx + W / 2} V{hy + H + 1}", "var(--ink)", 1.3, arrow=True, mid="lgk"))
    out.append(P(f"M{hx + W / 2},{hy} V{y0_ + H / 2} H{x0_ - 1}", "var(--rom)", 2, arrow=True, mid="lgr"))
    out.append(T(hx + W / 2 + 4, y0_ - 4, "token return", 8.5, "var(--rom)", "start", 600))
    # MTP draft loop

    # --- lower half: tables, switch, host --------------------------------------------------------------
    yb = 310
    out.append(L(10, yb - 18, 990, yb - 18, "var(--rule)", 1))
    out.append(T(10, yb, "Off the stage path: 72 table dies (36 packages, no HBM) behind one switch", 12, weight=600))
    e1 = set(pl["engram_packages"].get("Engram layer L1", []))
    e14 = set(pl["engram_packages"].get("Engram layer L14", []))
    tx, ty = 10, yb + 16
    for i, pk in enumerate(range(58, 94)):
        cx = tx + (i % 18) * 27
        cy = ty + (i // 18) * 34
        both = pk in e1 and pk in e14
        dcol = ["var(--rom)" if pk in e1 else "var(--hbm)", "var(--hbm)" if pk in e14 else "var(--rom)"]
        out.append(R(cx, cy, 24, 28, "var(--panel)", "var(--muted)", 0.8, 2))
        for d in range(2):
            out.append(R(cx + 4, cy + 4 + d * 11, 16, 9, dcol[d] if both else dcol[0], "none", 0, 1,
                         extra='opacity="0.75"'))
    out.append(T(tx, ty + 82, "Engram L1 rows (101.4 GB)", 9.5, "var(--rom)", weight=600))
    out.append(T(tx + 170, ty + 82, "Engram L14 rows (101.4 GB)", 9.5, "var(--hbm)", weight=600))
    out.append(T(tx + 350, ty + 82, "embedding on H dies 112-115", 9.5, "var(--warn)", weight=600))
    # switch
    sx, sy, sw_, sh = 520, yb + 22, 150, 44
    out.append(R(sx, sy, sw_, sh, "var(--hbm-soft)", "var(--hbm)", 1.4, 4))
    out.append(T(sx + sw_ / 2, sy + 18, "51.2T switch", 11, anchor="middle", weight=600))
    out.append(T(sx + sw_ / 2, sy + 33, "250 ns, Ethernet + KP4", 9, "var(--muted)", "middle", mono=True))
    out.append(L(tx + 18 * 27, sy + sh / 2, sx - 2, sy + sh / 2, "var(--hbm)", 1.4, arrow=True, mid="lgh"))
    out.append(L(sx - 2, sy + sh / 2 + 8, tx + 18 * 27, sy + sh / 2 + 8, "var(--hbm)", 1.4, arrow=True, mid="lgh"))
    # host
    hx2, hy2 = 720, yb + 22
    out.append(R(hx2, hy2, 120, 44, "var(--code)", "var(--muted)", 1, 4))
    out.append(T(hx2 + 60, hy2 + 18, "host + 2 x 400G", 10.5, anchor="middle", weight=600))
    out.append(T(hx2 + 60, hy2 + 33, "prefill KV ingest", 9, "var(--muted)", "middle"))
    out.append(L(hx2, hy2 + 22, sx + sw_ + 2, sy + 22, "var(--hbm)", 1.4, arrow=True, mid="lgh"))
    out.append(T(860, yb + 30, "GPU prefill pod", 9.5, "var(--muted)"))
    out.append(L(858, yb + 44, hx2 + 122, hy2 + 22, "var(--hbm)", 1.2, "4 3", arrow=True, mid="lgh"))
    # switch fan-out description
    ly = sy + sh + 22
    lines = [
        ("token id", f"H -> 72 table dies (multicast); 48 rows x 264 B -> S{pl['engram_consumers']['1']} (E1), "
                     f"S{pl['engram_consumers']['14']} (E14)"),
        ("", f"layer 1 gather done {rec['paths']['engram_l1_s'] * 1e6:.2f} us after the argmax; slack 3.57 us"),
        ("KV ingest", f"host -> KV-owning stages {', '.join('S%d' % s for s in pl['kv_owner_stages'])}"),
        ("", f"{rec['traffic']['rows']['T4_kv_ingest']['bytes_per_user_1m'] / 1e9:.2f} GB per 1M-token user, "
             f"{rec['traffic']['rows']['T4_kv_ingest']['seconds_per_1m_user'] * 1e3:.1f} ms at 2 x 400G"),
    ]
    for i, (k, v) in enumerate(lines):
        out.append(T(sx, ly + i * 15, k, 9.5, "var(--hbm)", weight=600))
        out.append(T(sx + 62, ly + i * 15, v, 9.5, "var(--muted)"))
    # per-token bytes table
    rows = tr["rows"]
    ty2 = 480
    out.append(T(10, ty2, "Per token, batch 1, 1M context (bytes; messages)", 11, weight=600))
    items = [("T0 UCIe in package (TP)", rows["T0_ucie"]), ("T1 on-module trace (TP)", rows["T1_tp_trace"]),
             ("T2 stage hops (28 x 40 KB)", rows["T2_stage_hop"]), ("T2 token return", rows["T2_token_return"]),
             ("T3 Engram via switch", rows["T3_engram"]), ("HBM: KV + index keys", rows["hbm_kv_index"])]
    for i, (k, r) in enumerate(items):
        cx = 10 + (i % 3) * 330
        cy = ty2 + 20 + (i // 3) * 36
        out.append(R(cx, cy - 12, 318, 30, "var(--panel)", "var(--rule)", 1, 3))
        out.append(T(cx + 8, cy + 2, k, 9.5, "var(--muted)"))
        m = r.get("messages_per_token")
        out.append(T(cx + 310, cy + 2, kfmt(r["bytes_per_token"]) + (f"; {m}" if m else ""), 10.5, anchor="end",
                     weight=600, mono=True))
        if "utilisation_fill_mtp" in r:
            out.append(T(cx + 8, cy + 14, "link busy at 28-user fill + MTP: %.1f%%" % (100 * r["utilisation_fill_mtp"]),
                         8.5, "var(--faint)"))
    # legend
    lx, ly2 = 10, 574
    for i, (c, t) in enumerate((("var(--rom)", "layer die (4 HBM3E)"), ("var(--hbm)", "H: head + embedding + draft"),
                                ("var(--hbm)", "KV = KV-owning stage, IX = index-scan stage"),
                                ("var(--ok)", "E1/E14 = Engram consumer"))):
        out.append(R(lx + i * 240, ly2, 12, 10, c, "none", 0, 2))
        out.append(T(lx + i * 240 + 18, ly2 + 9, t, 9.5, "var(--muted)"))
    cap = ("<b>Figure R-1. Logical map of the 188 dies.</b> The token circulates a ring of 29 stage modules: 28 "
           "layer stages (S0-S27, one tensor group of 4 dies = one package pair each, 40 layers cut at equal bytes) "
           "and the head + embedding + DSpark group H, whose argmax winner reads the next embedding row locally "
           "and returns it to S0 over one ring hop. Tensor collectives stay "
           "inside a module (UCIe between the dies of a package, a ~120 mm board trace between the two packages); "
           "only the 40 KB residual crosses a cable. The 72 table dies hold the two Engram tables "
           "and sit off the stage path behind one switch: their gather is prefetched from the token id and lands "
           f"within layer 1's slack. Die roles: <code>results/arch/v41_die_placement.json</code>; traffic: "
           f"<code>results/arch/v41_rack.json</code>.")
    return figure("rack-logical", "0 0 1000 592", "".join(out), "Logical map of the V4.1 ROM array", cap)


# ---------------------------------------------------------------------------------------------------------
def fig_elevation(rec):
    el = rec["elevation"]
    pw = rec["power"]
    out = [markers("el")]
    OU = el["usable_ou"]
    h = 13.2
    rx, ry, rw = 70, 44, 250
    top = ry + OU * h
    out.append(T(rx, 24, "Front elevation, ORv3 (21 in, 48 mm OU), 44 OU", 12, weight=600))
    out.append(R(rx - 8, ry - 6, rw + 16, OU * h + 12, "var(--code)", "var(--ink)", 1.5, 3))
    colors = dict(stage=("var(--rom)", "var(--panel)"), table=("var(--rom-soft)", "var(--ink)"),
                  switch=("var(--hbm)", "var(--panel)"), host=("var(--hbm-soft)", "var(--ink)"),
                  power=("var(--muted)", "var(--panel)"), mgmt=("var(--grid)", "var(--ink)"))
    used = set()
    ou_y = {}
    for r in el["rows"]:
        y = top - (r["ou"] - 1 + r["height"]) * h
        fill, ink = colors[r["kind"]]
        out.append(R(rx, y + 0.6, rw, r["height"] * h - 1.2, fill, "var(--rule)", 0.6, 1))
        lab = r["label"]
        if r["kind"] == "stage":
            lab = "stage tray %s: %s" % (r["tray"], " + ".join(r["modules"]))
            for m in r["modules"]:
                ou_y[m] = y + h / 2
        elif r["kind"] == "table":
            lab = lab.replace("table tray ", "")
        elif r["kind"] == "power":
            lab = lab.split("(")[0].strip() + (" 33 kW" if "A" in lab else " 33 kW (2N)")
        out.append(T(rx + 6, y + r["height"] * h / 2 + 3.6, lab, 8.6, ink, mono=r["kind"] in ("stage",)))
        for k in range(r["height"]):
            used.add(r["ou"] + k)
    for u in range(1, OU + 1):
        y = top - u * h
        if u not in used:
            out.append(R(rx, y + 0.6, rw, h - 1.2, "none", "var(--rule)", 0.6, 1, dash="2 3"))
        if u % 2 == 1 or u == OU:
            out.append(T(rx - 12, y + h / 2 + 3.4, u, 8, "var(--faint)", "end", mono=True))
    out.append(T(rx + rw / 2, top - 44 * h + 10 + (OU - el["used_ou"]) * h / 2, "%d OU free" % (OU - el["used_ou"]),
                 10, "var(--faint)", "middle"))
    # rear cable channel: folded ring
    cx = rx + rw + 18
    st_top = max(r["ou"] for r in el["rows"] if r["kind"] == "stage")
    out.append(T(cx - 6, top - st_top * h - 6, "ring cables", 9, "var(--muted)"))
    ring = rec["ring"]
    trays = {}
    for r in el["rows"]:
        if r["kind"] == "stage":
            for i, m in enumerate(r["modules"]):
                trays[m] = (r["ou"], i)
    for i in range(len(ring)):
        a, b = ring[i], ring[(i + 1) % len(ring)]
        (oa, sa), (ob, sb) = trays[a], trays[b]
        ya, yb = top - (oa - 0.5) * h, top - (ob - 0.5) * h
        xa = cx + (0 if sa == 0 else 12)
        xb = cx + (0 if sb == 0 else 12)
        col = "var(--rom)" if not (a == "H" or b == "H") else "var(--hbm)"
        if oa == ob:
            out.append(P(f"M{xa},{ya} H{xa + 20 if xa == xb else xb}" if xa != xb else f"M{xa},{ya} h20", col, 1.4))
            out.append(P(f"M{max(xa, xb)},{ya} v-0.1", col, 1.4))
        else:
            out.append(P(f"M{xa},{ya} H{xb} V{yb + (2.5 if yb > ya else -2.5)}", col, 1.4, arrow=True,
                         mid="el" + ("r" if col == "var(--rom)" else "h")))
    out.append(T(cx + 20, top - 0.5 * h + 3 - 14 * h, "", 8))
    sw = next(r for r in el["rows"] if r["kind"] == "switch")
    ysw = top - (sw["ou"] - 0.5) * h
    out.append(P(f"M{rx + rw},{ysw} h40", "var(--hbm)", 1.2, "3 2"))
    out.append(T(cx + 44, ysw + 3, "DAC to every package", 8.5, "var(--hbm)"))
    # --- tray top view -------------------------------------------------------------------------------
    tx, ty, tw, td = 470, 44, 500, 300
    sc = tw / 533.0
    out.append(T(tx, 24, "Stage tray, top view (1 OU, 533 x ~800 mm), two stage modules", 12, weight=600))
    out.append(R(tx, ty, tw, td, "var(--panel)", "var(--ink)", 1.3, 3))
    out.append(T(tx + 6, ty + td - 6, "front", 9, "var(--faint)"))
    out.append(T(tx + tw - 6, ty + 12, "rear: busbar, manifold, cable bulkhead", 9, "var(--faint)", "end"))
    out.append(R(tx, ty + 18, tw, 10, "var(--code)", "var(--rule)", 0.6, 0))
    pkg = 85 * sc
    for mdx in range(2):
        mx = tx + 14 + mdx * (tw / 2)
        mw = tw / 2 - 28
        my, mh = ty + 60, 190
        out.append(R(mx, my, mw, mh, "var(--rom-soft)", "var(--rom)", 1, 4))
        out.append(T(mx + 6, my + 14, "stage module %s (package pair)" % ("A" if mdx == 0 else "B"), 9.5, "var(--rom)",
                     weight=600))
        for p in range(2):
            px = mx + 18 + p * (pkg + 38)
            py = my + 40
            out.append(R(px, py, pkg, pkg, "var(--panel)", "var(--ink)", 1, 3))
            dw, dh = 25.6 * sc, 31.8 * sc
            for d in range(2):
                dx = px + pkg / 2 - dw + d * dw
                out.append(R(dx, py + pkg / 2 - dh / 2, dw - 1, dh, "var(--rom)", "none", 0, 1))
                for k in range(2):
                    hx = dx + 2 + k * (dw / 2)
                    for yy in (py + pkg / 2 - dh / 2 - 12 * sc - 1, py + pkg / 2 + dh / 2 + 1):
                        out.append(R(hx, yy, 11 * sc, 11 * sc, "var(--hbm)", "none", 0, 1))
            out.append(T(px + pkg / 2, py + pkg + 12, "pkg: 2 dies + 8 HBM3E", 8, "var(--muted)", "middle"))
        # TP trace
        x1 = mx + 18 + pkg
        out.append(L(x1, my + 40 + pkg / 2, x1 + 38, my + 40 + pkg / 2, "var(--ink)", 2.2))
        out.append(T(x1 + 19, my + 40 + pkg / 2 - 5, "TP", 8, "var(--ink)", "middle", 600))
        out.append(T(x1 + 19, my + 40 + pkg / 2 + 12, "~120 mm", 7.5, "var(--muted)", "middle"))
        # flyover to rear
        for p in range(2):
            px = mx + 18 + p * (pkg + 38) + pkg / 2
            out.append(P(f"M{px},{my + 40} V{ty + 30}", "var(--rom)", 1.6, "4 2"))
        # cold plate loop
        out.append(P(f"M{mx + mw - 10},{ty + 28} V{my + mh - 14} H{mx + 10}", "var(--hbm)", 1.1, "1 3"))
    lp = rec["lanes"]["per_package"]
    out.append(T(tx + 8, ty + td - 22, "rom dashed = %d-lane flyover to the rear bulkhead (stage in/out);  "
                                       "blue dotted = cold-plate loop" % (lp["stage_out"] + lp["stage_in"]),
                 8.5, "var(--muted)"))
    # --- key numbers ------------------------------------------------------------------------------------
    kx, ky = 470, 372
    sc_ = pw["scenarios"]
    items = [
        ("rack input, provisioned", "%.1f kW" % (pw["provisioned_rack_input_w"] / 1e3)),
        ("batch 1 / 28-user fill / fill + MTP", "%.1f / %.1f / %.1f kW" % (sc_["b1"]["rack_input_w"] / 1e3,
                                                                           sc_["fill"]["rack_input_w"] / 1e3,
                                                                           sc_["fill_mtp"]["rack_input_w"] / 1e3)),
        ("stage tray (4 packages, 1 OU)", "%.2f kW, cold plates" % (pw["per_tray"]["stage_w"] / 1e3)),
        ("table tray (4 packages, 1 OU)", "%.2f kW, air" % (pw["per_tray"]["table_w"] / 1e3)),
        ("layer package, worst case", "%.0f W (2 dies, 8 HBM3E, SerDes)" % pw["per_package"]["layer_worst_w"]),
        ("power shelves", "%d x 33 kW ORv3 HPR (2N), %.0f A at 50 V" % (pw["shelves"]["count"], pw["busbar_a"])),
        ("height used", "%d of 44 OU (air-cooled variant: %d OU)" % (el["used_ou"], rec["elevation_air"]["used_ou"])),
        ("longest ring cable / switch cable", "%.2f m / %.2f m passive copper" % (
            max(l["length_m"] for l in rec["links"]["stage_links"]), max(rec["links"]["switch_cable_m"]))),
        ("weight (estimate)", "~%d kg" % rec["weight"]["kg"]),
    ]
    out.append(T(kx, ky, "Rack budget", 12, weight=600))
    for i, (k, v) in enumerate(items):
        yy = ky + 20 + i * 22
        out.append(L(kx, yy + 6, kx + 500, yy + 6, "var(--grid)", 1))
        out.append(T(kx, yy, k, 10, "var(--muted)"))
        out.append(T(kx + 500, yy, v, 10.5, anchor="end", weight=600, mono=True))
    cap = ("<b>Figure R-2. One model replica per rack.</b> Left: the ORv3 front elevation. The 15 stage trays fold the "
           "token ring (tray t holds ring positions t and 28-t), so every ring neighbour is on the same or the adjacent "
           "tray and every stage hop is one passive copper cable of at most %.2f m, with no retimer. Right: a stage "
           "tray carries two stage modules; each module board carries one tensor group (a package pair) with the TP "
           "link as a ~120 mm trace. Power uses validated static values (logic leakage 0.10 W/mm2, HBM idle, SerDes at "
           "6.5 pJ/b) and the spec's dynamic model with validated MAC energies, through 87%% voltage regulation, 96%% "
           "PSUs and 3%% fans, provisioned at 1.2x the worst case; weight is an estimate. Sources in <code>results/arch/v41_rack.json</code> "
           "<code>physical_constants</code>." % max(l["length_m"] for l in rec["links"]["stage_links"]))
    return figure("rack-elevation", "0 0 1000 640", "".join(out), "Rack elevation and stage tray", cap)


# ---------------------------------------------------------------------------------------------------------
def fig_links(rec):
    tiers = rec["links"]["tiers"]
    tr = rec["traffic"]["rows"]
    out = [markers("lk")]
    ax0, ax1 = 250, 620
    lo, hi = -3, 3                     # 1 mm .. 1 km

    def X(m):
        return ax0 + (math.log10(m) - lo) / (hi - lo) * (ax1 - ax0)
    top = 64
    out.append(T(10, 22, "Link tiers: physical length (dot) against reach limit (bar end)", 12, weight=600))
    for e in range(lo, hi + 1):
        x = X(10 ** e)
        out.append(L(x, top - 8, x, top + 5 * 62 - 10, "var(--grid)", 1))
        lab = {-3: "1 mm", -2: "1 cm", -1: "10 cm", 0: "1 m", 1: "10 m", 2: "100 m", 3: "1 km"}[e]
        out.append(T(x, top - 14, lab, 9, "var(--faint)", "middle", mono=True))
    heads = [(650, "latency / hop"), (760, "per link, per dir"), (880, "per token, b1")]
    for x, t in heads:
        out.append(T(x, top - 14, t, 9, "var(--faint)", "start", mono=True))
    spec = [
        (2e-3, 1e-3, None, "T0_ucie", "UCIe advanced, <= 2 mm"),
        (0.5, 0.12, None, "T1_tp_trace", "VSR/MR trace, 100-500 mm"),
        (2.0, max(l["length_m"] for l in rec["links"]["stage_links"]), 7.0, "T2_stage_hop", "passive DAC <= 2 m (AEC 7 m)"),
        (2.0, max(rec["links"]["switch_cable_m"]), None, "T3_engram", "passive DAC to switch"),
        (2000.0, 100.0, None, "T4_kv_ingest", "optics, 100 m - 2 km"),
    ]
    for i, (t, (reach, length, alt, key, rl)) in enumerate(zip(tiers, spec)):
        y = top + i * 62
        out.append(T(10, y + 8, t["tier"].split(" ", 1)[0], 11, "var(--rom)", weight=600, mono=True))
        out.append(T(40, y + 8, t["tier"].split(" ", 1)[1].split(" (")[0], 10.5, weight=600))
        out.append(T(10, y + 24, t["per_package"], 9, "var(--muted)"))
        out.append(T(10, y + 37, "length " + t["length"], 9, "var(--faint)"))
        out.append(R(X(1e-3), y, X(reach) - X(1e-3), 12, "var(--rom-soft)", "var(--rom)", 0.8, 2))
        if alt:
            out.append(R(X(reach), y, X(alt) - X(reach), 12, "none", "var(--rom)", 0.8, 2, dash="3 2"))
            out.append(T(X(alt) + 4, y + 10, "AEC", 8.5, "var(--muted)"))
        out.append(T(X(1e-3) + 4, y + 26, rl, 8.5, "var(--muted)"))
        out.append(f'<circle cx="{X(length):.1f}" cy="{y + 6}" r="4.5" style="fill:var(--ink)"/>')
        lat = t["latency_s"]
        out.append(T(650, y + 10, ("%.0f ns" % (lat * 1e9)) if lat else "ms-scale bulk", 11, weight=600, mono=True))
        if key == "T3_engram":
            out.append(T(650, y + 24, "2 ports + switch", 8.5, "var(--muted)"))
        elif key == "T1_tp_trace":
            out.append(T(650, y + 24, "130 ns light FEC + trace", 8.5, "var(--muted)"))
        elif key == "T2_stage_hop":
            out.append(T(650, y + 24, "209 ns full KP4 + flight", 8.5, "var(--muted)"))
        out.append(T(760, y + 10, "%.0f GB/s" % (t["Bps"] / 1e9) if t["Bps"] < 1e12 else "%.1f TB/s" % (t["Bps"] / 1e12),
                     11, weight=600, mono=True))
        r = tr[key]
        if key == "T4_kv_ingest":
            v, sub = kfmt(r["bytes_per_user_1m"]) + "/user", "%.1f ms per 1M user" % (r["seconds_per_1m_user"] * 1e3)
        else:
            v = kfmt(r["bytes_per_token"])
            sub = ("%.1f%% busy, fill+MTP" % (100 * r["utilisation_fill_mtp"])) if "utilisation_fill_mtp" in r else ""
        out.append(T(880, y + 10, v, 11, weight=600, mono=True))
        out.append(T(880, y + 24, sub, 8.5, "var(--muted)"))
    y = top + 5 * 62 + 8
    out.append(T(10, y, "Every stage hop, TP link and switch cable is within passive-copper reach: no retimer or "
                        "AEC. The ring's worst hop is %.1f ns on full KP4 (validated 209 ns, band 160-300)."
                 % (max(l["latency_s"] for l in rec["links"]["stage_links"]) * 1e9), 10, "var(--ink)"))
    cap = ("<b>Figure R-3. Five link tiers.</b> Latency is the hardware floor per hop, on values validated against "
           "normative specs and production datasheets. The on-module trace (T1) keeps the 130 ns light-FEC link "
           "(an OIF CEI-112G-MR channel), re-based to its ~120 mm of trace at 6.7 ns/m. The ring cables (T2) run full "
           "RS(544,514) KP4, 209 ns, because a light FEC is not qualified on CR-class copper; their flight (4.6 ns/m) "
           "is added on top. The switched tier pays two full-KP4 Ethernet ports and 250 ns of switch. Bandwidth is per "
           "link and direction on the lane allocation TP %d / stage %d + %d / switch %d / spare %d of the package's 90 "
           "lanes (%s). Reach classes: UCIe (Hot Chips 2023 tutorial), OIF CEI-112G, IEEE 802.3ck, Credo AEC."
           % (rec["lanes"]["per_package"]["tp"], rec["lanes"]["per_package"]["stage_out"],
              rec["lanes"]["per_package"]["stage_in"], rec["lanes"]["per_package"]["switch"],
              rec["lanes"]["per_package"]["spare"], rec["lanes"]["source"]))
    return figure("rack-links", "0 0 1000 400", "".join(out), "Link tiers: reach, latency, bandwidth", cap)


# ---------------------------------------------------------------------------------------------------------
def fig_compare(rec):
    cmp_ = rec["comparison"]
    ours, nvl, cm = cmp_
    cols = [("var(--rom)", ours), ("var(--hbm)", nvl), ("var(--faint)", cm)]
    out = [markers("cp")]
    metrics = [
        ("racks", [1, 1, 16], "{:.0f}"),
        ("rack power, kW", [ours["rack_kw"], nvl["rack_kw"], cm["rack_kw"]], "{:.0f}"),
        ("accelerator packages", [ours["accelerators"], nvl["accelerators"], cm["accelerators"]], "{:.0f}"),
        ("scale-up bandwidth per package, TB/s per direction",
         [ours["per_accel_scaleup_TBps_per_dir"], nvl["per_accel_scaleup_TBps_per_dir"],
          cm["per_accel_scaleup_TBps_per_dir"]], "{:.2f}"),
    ]
    names = ["OpenTallas V4.1 ROM rack", "GB200 NVL72", "CloudMatrix384"]
    out.append(T(10, 22, "One model replica, three systems (published figures; ours from the rack model)", 12, weight=600))
    for i, (c, nm) in enumerate(zip([c for c, _ in cols], names)):
        out.append(R(10 + i * 230, 34, 12, 10, c, "none", 0, 2))
        out.append(T(28 + i * 230, 43, nm, 10, "var(--ink)", weight=600))
    pw, x0, y0 = 235, 10, 72
    for j, (lab, vals, f) in enumerate(metrics):
        px = x0 + j * (pw + 12)
        out.append(T(px, y0, lab, 10, "var(--muted)", weight=600))
        m = max(vals)
        for i, v in enumerate(vals):
            y = y0 + 12 + i * 30
            w = (pw - 60) * (v / m) if m else 0
            out.append(R(px, y, max(w, 1.5), 20, cols[i][0], "none", 0, 2))
            out.append(T(px + max(w, 1.5) + 4, y + 14, f.format(v), 10.5, weight=600, mono=True))
    y = y0 + 12 + 3 * 30 + 26
    out.append(L(10, y - 14, 990, y - 14, "var(--rule)", 1))
    rows = [("fabric", "fabric"), ("built for", "built_for"), ("cooling", "cooling")]
    for i, (c, s) in enumerate(cols):
        cx = 10 + i * 330
        out.append(T(cx, y, names[i], 10.5, c if i < 2 else "var(--ink)", weight=600))
        yy = y + 16
        for lab, k in rows:
            txt = str(s.get(k, ""))
            words, line = txt.split(), ""
            out.append(T(cx, yy, lab, 8.5, "var(--faint)", mono=True))
            yy += 12
            for w in words:
                if len(line) + len(w) > 52:
                    out.append(T(cx, yy, line, 9, "var(--muted)"))
                    yy += 12
                    line = w
                else:
                    line = (line + " " + w).strip()
            if line:
                out.append(T(cx, yy, line, 9, "var(--muted)"))
                yy += 15
    cap = ("<b>Figure R-4. What each rack is built for.</b> NVL72 and CloudMatrix384 build an all-to-all scale-up "
           "fabric (NVLink switch trays; a two-tier Unified Bus across 16 racks) "
           "because any model, and expert parallelism in particular, needs every accelerator to reach every other. "
           "The ROM rack serves one fixed model whose weights never move: its only on-path traffic is a 40 KB "
           "residual per stage hop and 20 KB collectives inside a package pair, so it needs point-to-point copper "
           "and no scale-up switch, at about a fifth of an NVL72's power; its per-package lanes (90 x 112G) are "
           "spent on %d point-to-point 8-lane ring cables and on-board traces, not on a switch. Sources: "
           "NVIDIA GB200 NVL72 product page and DGX GB200 user guide (120 kW, 1.36 t, 5,000 copper cables); "
           "arXiv:2506.12708 and SemiAnalysis (CloudMatrix384; 559 kW is SemiAnalysis's figure)."
           % rec["lanes"]["ring_cables"])
    return figure("rack-compare", "0 0 1000 330", "".join(out), "Comparison with NVL72 and CloudMatrix384", cap)


def fig_headsram(rec):
    """Head-die draft-KV memory floorplan (gate C10), to scale."""
    fp = rec["head_draft_floorplan"]
    o, a, mc = fp["organisation"], fp["area"], fp["macro"]
    out = [markers("hs")]
    sc = 380 / max(a["block_w_mm"], a["block_h_mm"]) / 1000       # px per um
    x0, y0 = 30, 50
    out.append(T(x0, 26, "Head die: draft-KV memory, %d x %s (to scale)" % (o["macros"], mc["name"]), 12, weight=600))
    bw, bh = a["block_w_mm"] * 1000 * sc, a["block_h_mm"] * 1000 * sc
    out.append(R(x0, y0, bw, bh, "var(--code)", "var(--ink)", 1.2, 2))
    mw, mh = mc["width_um"] * sc, mc["height_um"] * sc
    halo = 5 * sc
    chan = a.get("bus_channel_um", 60.0)
    per_col = o["macros"] // 8                     # four-macro rows per column
    rows_per_bank = per_col // 2
    for col in range(2):
        cx = x0 + col * (4 * (mw + halo) + chan * sc)
        for r in range(per_col):
            cy = y0 + r * (mh + halo) + halo / 2
            for j in range(4):
                out.append(R(cx + j * (mw + halo) + halo / 2, cy, mw, mh, "var(--hbm-soft)", "var(--hbm)", 0.6, 1))
            if r % rows_per_bank == 0:
                out.append(T(cx + 4 * (mw + halo) + 3 if col == 1 else cx - 3, cy + mh / 2 + 3,
                             "bank %d" % (2 * col + r // rows_per_bank), 7, "var(--muted)",
                             "start" if col == 1 else "end", mono=True))
    chx = x0 + 4 * (mw + halo)
    out.append(R(chx, y0, chan * sc, bh, "var(--rom-soft)", "var(--rom)", 0.6, 0))
    out.append(T(chx + chan * sc / 2, y0 + bh + 14, "bus channel", 8.5, "var(--rom)", "middle"))
    ex = x0 + bw + 95
    out.append(R(ex, y0 + bh / 2 - 40, 130, 80, "var(--rom-soft)", "var(--rom)", 1.2, 3))
    out.append(T(ex + 65, y0 + bh / 2 - 8, "drafter BF16", 10, anchor="middle", weight=600))
    out.append(T(ex + 65, y0 + bh / 2 + 8, "attention engine", 10, anchor="middle", weight=600))
    out.append(L(x0 + bw + 30, y0 + bh / 2 - 10, ex - 2, y0 + bh / 2 - 10, "var(--rom)", 2, arrow=True, mid="hsr"))
    out.append(T(x0 + bw + 70, y0 + bh / 2 - 15, "rd %s b" % f"{o['read_port_bits']:,}", 8, "var(--rom)", "middle"))
    out.append(L(ex - 2, y0 + bh / 2 + 12, x0 + bw + 30, y0 + bh / 2 + 12, "var(--hbm)", 2, arrow=True, mid="hsh"))
    out.append(T(x0 + bw + 70, y0 + bh / 2 + 26, "wr %s b" % f"{o['write_port_bits']:,}", 8, "var(--hbm)", "middle"))
    out.append(R(ex, y0 + bh - 30, 130, 30, "var(--hbm-soft)", "var(--hbm)", 1, 3))
    out.append(T(ex + 65, y0 + bh - 11, "paging to 4 HBM3E", 9, anchor="middle"))
    out.append(L(x0 + 10, y0 + bh + 26, x0 + 10 + 1000 * sc, y0 + bh + 26, "var(--ink)", 1.2))
    out.append(T(x0 + 10, y0 + bh + 40, "1 mm", 8.5, "var(--muted)"))
    kx, ky = 720, 60
    t = fp["timing"]
    rows = [("macros", "%d (%d banks x %d; 28 slots)" % (o["macros"], o["banks"], o["macros_per_bank"])),
            ("capacity", "%.2f MB (need %.2f)" % (o["bytes"] / 1e6, o["needed_per_slot_bytes"] * o["slots"] / 1e6)),
            ("block", "%.2f x %.2f mm = %.2f mm2" % (a["block_w_mm"], a["block_h_mm"], a["block_mm2"])),
            ("location", "%.0f mm2 released engine area" % a["head_released_engine_mm2"]),
            ("ports", "1R1W, %s b read + %s b write" % (f"{o['read_port_bits']:,}", f"{o['write_port_bits']:,}")),
            ("macro fmax (ss)", "%.0f MHz vs %.0f MHz" % (t["fmax_ss_mhz"], t["clock_hz"] / 1e6)),
            ("read latency", "%d cycles (registered at macro)" % t["read_latency_cycles"]),
            ("block read", "%.0f cycles, %.2f nJ" % (fp["power"]["block_read_cycles"], fp["power"]["block_read_nj"])),
            ("leakage", "%.1f mW" % fp["power"]["leakage_mw"])]
    out.append(T(kx, ky - 16, "Budget", 11.5, weight=600))
    for i, (k2, v) in enumerate(rows):
        yy = ky + 8 + i * 21
        out.append(L(kx, yy + 6, kx + 275, yy + 6, "var(--grid)", 1))
        out.append(T(kx, yy, k2, 9.5, "var(--muted)"))
        out.append(T(kx + 275, yy, v, 9.5, anchor="end", weight=600, mono=True))
    cap = ("<b>Figure R-5. Head-die draft-KV memory (gate C10).</b> Each head die holds the 28-user fill's draft "
           "windows (3 blocks x 128 rows x 528 B per user, a quarter per die, double-buffered) in %d macros from "
           "this repository's ASAP7 SRAM compiler (%s: 32 KB, 1R1W, 2 spare rows and columns), placed in the "
           "right-sized head die's released engine area, so no ROM is displaced. Four banks of %d macros; a user "
           "slot is interleaved across one bank, giving the drafter's attention a %s-bit read port (a stage's "
           "window in %.0f cycles) and an independent write port, and four users can read at once. Users beyond "
           "the fill page to the head die's 4 HBM3E stacks. Macro geometry and timing come from the compiler's "
           "datasheet; the halo, the bus channel and the wire delay are estimates, and nothing here is routed."
           % (o["macros"], mc["name"], o["macros_per_bank"], f"{o['read_port_bits']:,}",
              fp["power"]["block_read_cycles"] + fp["timing"]["read_latency_cycles"]))
    return figure("rack-headsram", "0 0 1000 %d" % int(y0 + bh + 60), "".join(out), "Head-die draft-KV memory floorplan", cap)


PREVIEW_CSS = """
:root{--ground:#F4F5F2;--panel:#FFFFFF;--ink:#18212C;--muted:#56626E;--faint:#8C959E;--rule:#D6DAD3;--grid:#E7EAE4;
--code:#EEF0EB;--rom:#B05B24;--rom-soft:#F4E2D4;--hbm:#33659A;--hbm-soft:#DBE6F1;--ok:#2E7B53;--warn:#9E7318;--bad:#A03A3A;
color-scheme:light}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--ground:#10151B;--panel:#17202A;--ink:#E3E7EB;
--muted:#A1ACB7;--faint:#7B8692;--rule:#2B3642;--grid:#212B36;--code:#1D2732;--rom:#E48B51;--rom-soft:#382920;
--hbm:#7AA7DB;--hbm-soft:#1D2D3F;--ok:#5DBB8A;--warn:#D8A94A;--bad:#E27C7C;color-scheme:dark}}
:root[data-theme="dark"]{--ground:#10151B;--panel:#17202A;--ink:#E3E7EB;--muted:#A1ACB7;--faint:#7B8692;--rule:#2B3642;
--grid:#212B36;--code:#1D2732;--rom:#E48B51;--rom-soft:#382920;--hbm:#7AA7DB;--hbm-soft:#1D2D3F;--ok:#5DBB8A;
--warn:#D8A94A;--bad:#E27C7C;color-scheme:dark}
body{background:var(--ground);color:var(--ink);font-family:"IBM Plex Sans",system-ui,sans-serif;font-size:15px;
line-height:1.6;margin:0;padding:24px 16px}
main{max-width:1100px;margin:0 auto;display:grid;gap:24px}
.fig{background:var(--panel);border:1px solid var(--rule);border-radius:5px;padding:16px;display:grid;gap:10px;min-width:0;margin:0}
.svgbox{overflow-x:auto}.fig svg{display:block;width:100%;height:auto;min-width:560px}
figcaption{font-size:13px;color:var(--muted)}figcaption b{color:var(--ink)}
code{font-family:"IBM Plex Mono",monospace;font-size:.88em;background:var(--code);padding:1px 5px;border-radius:3px}
"""


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--splice-atlas", action="store_true",
                    help="rewrite the atlas section between the V41_RACK_FIGURES markers from this tool's template "
                         "(off by default: the atlas section is curated; replace only the <svg> bodies by hand)")
    a = ap.parse_args()
    rec = json.loads(REC.read_text())
    sens = rec["reprice_sensitivity"]
    FIG.mkdir(parents=True, exist_ok=True)
    figs = dict(logical=fig_logical(rec), elevation=fig_elevation(rec), links=fig_links(rec), compare=fig_compare(rec))
    extra = dict(headsram=fig_headsram(rec)) if "head_draft_floorplan" in rec else {}
    for k, v in {**figs, **extra}.items():
        (FIG / f"v41_rack_{k}.html").write_text(v)
    prev = ("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" "
            "content=\"width=device-width, initial-scale=1\"><title>V4.1 Rack Figures</title>\n"
            "<link rel=\"stylesheet\" href=\"https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600"
            "&family=IBM+Plex+Sans:wght@400;600&display=swap\">\n<style>" + PREVIEW_CSS + "</style></head>\n<body><main>\n"
            + "".join(figs.values()) + "".join(extra.values()) + "</main></body></html>\n")
    (FIG / "v41_rack_preview.html").write_text(prev)
    atlas = ROOT / "docs/ARCHITECTURE_ATLAS.html"
    if a.splice_atlas and atlas.exists():
        start = "<!-- V41_RACK_FIGURES_BEGIN -->"
        end = "<!-- V41_RACK_FIGURES_END -->"
        base_lane = "R-L9" in sens["baseline"].get("basis", "")
        reprice = ("<h4>Rack-bound sensitivity at 1M, batch 1</h4>\n"
                   "<p>The starting point is the design point "
                   + ("priced on this rack's lanes (R-L9: TP 52 / stage 14 + 14 / switch 4 / spare 6, large "
                      "all-reduces as a fixed-order two-step), so its collective bytes already sit on their peer "
                      "links and its hops on the stage lanes; with overlap simply assumed it was "
                      f"{sens['baseline']['overlap_assumed_rate_tokens_s']:,.0f}. " if base_lane else "")
                   + "It includes the one-hop ring return, so moving embedding rows onto the head dies earns no "
                   "second speed credit, and it assumes a 1.087 GHz system clock that the whole core has not closed. "
                   "The cable geometry adds the worst stage flight to all 29 ring hops. The last row is a "
                   "deliberately pessimistic stress case in which none of the 209 collective peer payloads overlaps "
                   "its producer. It is not an RTL result.</p>\n"
                   "<div class=\"tablewrap\"><table><caption>Table R-1. Conditional rack repricing from "
                   "results/arch/v41_rack.json, reprice_sensitivity</caption>"
                   "<thead><tr><th>Case</th><th>Per-user tokens/s</th><th>ROM chip energy/token, "
                   "with SerDes static</th></tr></thead><tbody>"
                   f"<tr><td>{'Design point on the rack lanes' if base_lane else 'Adopted ladder'}, before rack "
                   f"geometry</td><td>{sens['baseline']['rate_tokens_s']:,.0f}</td>"
                   f"<td>{sens['baseline']['dynamic_j_per_token'] + sens['baseline']['static_w'] / sens['baseline']['rate_tokens_s']:.3f} J "
                   "(SerDes excluded)</td></tr>"
                   f"<tr><td>Folded-ring cable geometry</td><td>{sens['geometry']['rate_tokens_s']:,.0f}</td>"
                   f"<td>{sens['serdes_static']['geometry_j_per_token']:.3f} J</td></tr>"
                   f"<tr><td>No collective overlap (stress case)</td>"
                   f"<td>{sens['no_collective_overlap_stress']['rate_tokens_s']:,.0f}</td>"
                   f"<td>{sens['serdes_static']['no_overlap_j_per_token']:.3f} J</td></tr>"
                   "</tbody></table></div><p>The added SerDes provision is "
                   f"{sens['serdes_static']['additional_w']/1000:.2f} kW for the ROM rack. This table does not "
                   "carry the HBM comparator's rack infrastructure, so no corrected "
                   "ROM:HBM energy ratio is published here.</p>\n")
        section = (start + "\n<h4>Proposed one-rack physical layout</h4>\n"
                   "<p>The 188 dies occupy 94 two-die packages in this analytical layout. "
                   "The rack dimensions, cables, power and switch are estimates and design inputs, "
                   "not a routed rack or a measured throughput result. The folded ring and local embedding "
                   "placement now bind the adopted model, and SerDes power and the two-die link lanes are priced "
                   "(items C4 and C8). The collective overlap and the whole-system clock (C7) and the head-die "
                   "draft-KV SRAM floorplan (C10) still need demonstration "
                   "before the headline rates can use this layout "
                   "(<code>results/arch/v41_rack.json</code>, <code>demonstration_plan</code>).</p>\n"
                   + "\n".join(figs[k] for k in ("logical", "elevation", "links", "compare"))
                   + "\n" + reprice + end)
        page = atlas.read_text()
        if start in page and end in page:
            page = page[:page.index(start)] + section + page[page.index(end) + len(end):]
        else:
            anchor = '  <h3 id="s6-10">6.10 HBM comparator variant</h3>'
            if anchor not in page:
                raise ValueError("Cannot find rack figure insertion point in the technical report")
            page = page.replace(anchor, section + "\n" + anchor, 1)
        atlas.write_text(page)
    print("wrote", ", ".join(str((FIG / f"v41_rack_{k}.html").relative_to(ROOT)) for k in figs),
          "and", (FIG / "v41_rack_preview.html").relative_to(ROOT))


if __name__ == "__main__":
    main()
