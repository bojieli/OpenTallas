#!/usr/bin/env python3
"""Split GRT / DRT views of a porous hard-core abstract (QC-FAIL-22, 2026-11-10).

Why: OpenROAD GRT turns every macro OBS rect into a whole-gcell blockage on its layer (measured with a
saturating-demand probe on QC cbx_q10: a view 98 pct free on M7 reads 57 pct free to GRT, edge capacity is
bimodal full/0).  A detailed (porous) abstract therefore loses most of its porosity in GRT, while DRT needs
the real shapes.  The split form gives each stage its own view of the SAME child:

  GRT  : the abstract with OBS removed on --layers; with --bands, the --band-layers get thin preferred-direction
         OBS bands instead, spaced so GRT zeroes about calib*(blocked share + margin) of the gcell rows.  The view
         only REMOVES capacity (pure OBS), so GRT can never see more than the track supply.
  DRT  : the detailed abstract, swapped in on the GRT result (dbInst swapMaster, guides kept).

  --channels FILE (JSON list of DIE-QC-97 route_channels, core frame) keeps those bands OPEN in the GRT view:
  every OBS shape (band or detail) of a channel layer inside a channel rect is cut out.

  region-tcl is DISABLED (exit 2): set_global_routing_region_adjustment over the children RAISED capacity in the
  full flow (cbx_q10 M6 original 45.1M -> derated 132.1M, -193%; HBM q_su21 M4 -71%), although a 1-core probe
  without the kit hooks reduced it monotonically (0.1/0.5/0.9 -> H cap 3/2/1 of 4).  Do not use it.

  Band calibration (1-core saturating probe, ASAP7 gcell 0.57, M6 H, NK porous67): band share 0.251 -> GRT mean
  free 0.65; 0.18 -> 0.795 (target 0.749), so --calib 0.8.  M7 (V) bands zero ~47 pct of V edges at any share
  (unexplained), so M7 stays removed by default (optimistic by the detail M7 blocked share: NK 12.9, NL 2.2 pct).

Commands (die-agnostic, any single-MACRO LEF):
  python3 -I grt_split_view.py grt-view --lef detail.lef --out grt.lef --layers M6,M7
      -> grt.lef = detail.lef minus OBS on those layers (pins, SIZE, PG and other OBS byte-identical)
  python3 -I grt_split_view.py share --lef detail.lef --layers M6,M7 [--pitch M6=0.064,...]
      -> JSON per layer: preferred-direction track length under OBS (blocked share)
  python3 -I grt_split_view.py region-tcl --lef detail.lef --master NAME --layers M6,M7 --margin 0.05 --out f.tcl
      -> Tcl for PRE_GLOBAL_ROUTE: set_global_routing_region_adjustment over each instance of NAME
  python3 -I grt_split_view.py swap-tcl --out swap.tcl
      -> Tcl (env ODB, MASTER, VARLEF) that reads VARLEF as its own library and swaps every MASTER instance
  python3 -I grt_split_view.py check --lef detail.lef --grt grt.lef --layers M6,M7
      -> exit 0 iff grt.lef equals detail.lef except OBS of those layers
"""
import argparse
import json
import re
import sys

DEF_PITCH = {"M1": 0.036, "M2": 0.039, "M3": 0.036, "M4": 0.048, "M5": 0.048, "M6": 0.064, "M7": 0.064,
             "M8": 0.08, "M9": 0.08}
DEF_DIR = {"M1": "V", "M2": "H", "M3": "V", "M4": "H", "M5": "V", "M6": "H", "M7": "V", "M8": "H", "M9": "V"}


def split_obs(text):
    """-> (head, obs_groups, tail). obs_groups = list of (layer, [lines incl LAYER line]) in order."""
    lines = text.split("\n")
    s = next((i for i, l in enumerate(lines) if l.strip() == "OBS"), None)
    if s is None:
        return lines, [], []
    e = next(j for j in range(s + 1, len(lines)) if lines[j].strip() == "END")
    groups, cur = [], None
    for l in lines[s + 1:e]:
        m = re.match(r"\s*LAYER\s+(\S+)\s*;", l)
        if m:
            cur = (m.group(1), [l])
            groups.append(cur)
        elif cur is not None:
            cur[1].append(l)
    return lines[:s + 1], groups, lines[e:]


def grt_view(text, layers):
    head, groups, tail = split_obs(text)
    keep = [g for g in groups if g[0] not in layers]
    body = [l for g in keep for l in g[1]]
    return "\n".join(head + body + tail)


def band_obs(text, shares, gcell, width=0.032):
    """GRT-view OBS that GRT prices at the given blocked share without zeroing every gcell: one thin band along the
    preferred direction every gcell/share um.  GRT zeroes each gcell row (H) / column (V) a band touches and leaves the
    others whole, so about `share` of the rows/columns lose that layer and the rest keep full capacity."""
    sx, sy = size_of(text)
    out = []
    for lay, sh in shares.items():
        if sh <= 0:
            continue
        period = gcell / min(sh, 1.0)
        h = DEF_DIR[lay] == "H"
        ext = sy if h else sx
        out.append("      LAYER %s ;" % lay)
        c = period / 2.0
        while c + width / 2 <= ext:
            if h:
                out.append("        RECT 0 %.3f %.3f %.3f ;" % (c - width / 2, sx, c + width / 2))
            else:
                out.append("        RECT %.3f 0 %.3f %.3f ;" % (c - width / 2, c + width / 2, sy))
            c += period
    return out


def grt_view_bands(text, shares, gcell):
    head, groups, tail = split_obs(text)
    keep = [g for g in groups if g[0] not in shares]
    body = [l for g in keep for l in g[1]] + band_obs(text, shares, gcell)
    return "\n".join(head + body + tail)


def channel_rects(channels, size):
    """core-frame rects {layer: [(x0,y0,x1,y1)]} of route_channels entries (DIE-QC-97 core_route_channel format:
    {"dir": "EW"|"NS", "span_um": [lo, hi], "layers": [...]}); EW spans the full width, NS the full height."""
    w, h = size
    out = {}
    for ch in channels or []:
        lo, hi = (float(v) for v in ch["span_um"])
        r = (0.0, lo, w, hi) if ch["dir"] == "EW" else (lo, 0.0, hi, h)
        for lay in ch["layers"]:
            out.setdefault(lay, []).append(r)
    return out


def _sub(r, c):
    """r minus c as up to 4 rects."""
    x0, y0, x1, y1 = r
    cx0, cy0, cx1, cy1 = c
    if cx0 >= x1 or cx1 <= x0 or cy0 >= y1 or cy1 <= y0:
        return [r]
    out = []
    if cy0 > y0: out.append((x0, y0, x1, cy0))
    if cy1 < y1: out.append((x0, cy1, x1, y1))
    my0, my1 = max(y0, cy0), min(y1, cy1)
    if cx0 > x0: out.append((x0, my0, cx0, my1))
    if cx1 < x1: out.append((cx1, my0, x1, my1))
    return out


def open_channels(text, channels):
    """remove every OBS shape of a channel layer inside the channel rects (parent owns those tracks)."""
    rects = channel_rects(channels, size_of(text))
    if not rects:
        return text
    head, groups, tail = split_obs(text)
    body = []
    for lay, lines in groups:
        if lay not in rects:
            body += lines
            continue
        body.append(lines[0])
        for l in lines[1:]:
            m = re.match(r"(\s*)RECT\s+(?:MASK\s+\d+\s+)?([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*;", l)
            if not m:
                body.append(l)
                continue
            parts = [tuple(float(v) for v in m.groups()[1:])]
            for c in rects[lay]:
                parts = [q for p in parts for q in _sub(p, c)]
            body += ["%sRECT %.4f %.4f %.4f %.4f ;" % (m.group(1), *q) for q in parts if q[2] > q[0] and q[3] > q[1]]
    return "\n".join(head + body + tail)


def size_of(text):
    m = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", text)
    return float(m.group(1)), float(m.group(2))


def share(text, layers, pitch):
    sx, sy = size_of(text)
    _, groups, _ = split_obs(text)
    out = {}
    for lay in layers:
        rects = []
        for g, ls in groups:
            if g != lay:
                continue
            for l in ls:
                m = re.match(r"\s*RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", l)
                if m:
                    rects.append(tuple(map(float, m.groups())))
        p = pitch.get(lay, DEF_PITCH[lay]); o = p / 4.0
        h = DEF_DIR[lay] == "H"
        ext, span = (sy, sx) if h else (sx, sy)
        n = int((ext - o) / p) + 1
        occ = {}
        for x1, y1, x2, y2 in rects:
            lo, hi, a, b = (y1, y2, x1, x2) if h else (x1, x2, y1, y2)
            for k in range(max(0, int((lo - o) / p + 0.999)), min(n - 1, int((hi - o) / p)) + 1):
                occ.setdefault(k, []).append((a, b))
        used = 0.0
        for iv in occ.values():
            iv.sort(); ca = cb = None
            for a, b in iv:
                if ca is None or a > cb:
                    if ca is not None:
                        used += cb - ca
                    ca, cb = a, b
                else:
                    cb = max(cb, b)
            if ca is not None:
                used += cb - ca
        out[lay] = {"rects": len(rects), "blocked_share": round(used / (n * span), 4)}
    return out


def region_tcl(master, adj):
    lines = ["# GENERATED by grt_split_view.py region-tcl: GRT region adjustment over every instance of " + master,
             "# (porous child: GRT view has these layers open, the region prices the detailed view's blocked share)",
             "set ::gsv_n 0",
             "foreach ::gsv_i [[ord::get_db_block] getInsts] {",
             "  if {[[$::gsv_i getMaster] getName] ne \"%s\"} continue" % master,
             "  set ::gsv_b [$::gsv_i getBBox]",
             "  set ::gsv_u [[ord::get_db_tech] getDbUnitsPerMicron]",
             "  set ::gsv_r [list [expr {[$::gsv_b xMin]/double($::gsv_u)}] [expr {[$::gsv_b yMin]/double($::gsv_u)}]"
             " [expr {[$::gsv_b xMax]/double($::gsv_u)}] [expr {[$::gsv_b yMax]/double($::gsv_u)}]]"]
    for lay, a in adj.items():
        lines.append("  set_global_routing_region_adjustment $::gsv_r -layer %s -adjustment %.3f" % (lay, a))
    lines += ["  incr ::gsv_n", "}",
              "puts \"GRT_SPLIT_VIEW %s instances=$::gsv_n %s\"" % (master, " ".join("%s=%.3f" % kv for kv in adj.items()))]
    return "\n".join(lines) + "\n"


SWAP_TCL = r"""# GENERATED by grt_split_view.py swap-tcl: swap every $::env(MASTER) instance in $::env(ODB) to the master read
# from $::env(VARLEF) (its own library, named after the file).  Pins must match (dbInst swapMaster).
read_db $::env(ODB)
set db [ord::get_db]
set before [llength [$db getLibs]]
read_lef $::env(VARLEF)
set libs [$db getLibs]
if {[llength $libs] != $before + 1} { puts "SWAP-ERR new lib not created"; exit 3 }
set nl [lindex $libs end]
set nm [$nl findMaster $::env(MASTER)]
if {$nm eq "NULL" || $nm eq ""} { puts "SWAP-ERR master missing in new lib"; exit 4 }
set n 0
foreach inst [[[$db getChip] getBlock] getInsts] {
  set m [$inst getMaster]
  if {[$m getName] eq "$::env(MASTER)" && $m ne $nm} {
    if {![$inst swapMaster $nm]} { puts "SWAP-ERR swapMaster failed [$inst getName]"; exit 5 }
    puts "SWAPPED [$inst getName] -> [$nl getName] obs=[llength [$nm getObstructions]]"
    incr n
  }
}
if {$n == 0} { puts "SWAP-ERR no instance"; exit 6 }
puts "SWAP-OK n=$n"
write_db $::env(ODB)
"""


def check(detail, grt, layers):
    want = grt_view(detail, layers)
    return want == grt


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("grt-view"); a.add_argument("--lef", required=True); a.add_argument("--out", required=True); a.add_argument("--layers", default="M6,M7")
    a.add_argument("--bands", action="store_true", help="price the detailed blocked share (+margin) with gcell bands instead of removing the OBS")
    a.add_argument("--gcell", type=float, default=0.57); a.add_argument("--margin", type=float, default=0.05); a.add_argument("--pitch", default="")
    a.add_argument("--band-layers", default="M6"); a.add_argument("--calib", type=float, default=0.8)
    a.add_argument("--channels", default="", help="JSON file: route_channels list (core frame) kept open on their layers")
    b = sp.add_parser("share"); b.add_argument("--lef", required=True); b.add_argument("--layers", default="M6,M7"); b.add_argument("--pitch", default="")
    c = sp.add_parser("region-tcl"); c.add_argument("--lef", required=True); c.add_argument("--master", required=True)
    c.add_argument("--layers", default="M6,M7"); c.add_argument("--margin", type=float, default=0.05); c.add_argument("--pitch", default="")
    c.add_argument("--out", required=True)
    d = sp.add_parser("swap-tcl"); d.add_argument("--out", required=True)
    e = sp.add_parser("check"); e.add_argument("--lef", required=True); e.add_argument("--grt", required=True); e.add_argument("--layers", default="M6,M7")
    ns = ap.parse_args(argv)
    lay = [x for x in getattr(ns, "layers", "").split(",") if x]
    pitch = {k: float(v) for k, v in (kv.split("=") for kv in getattr(ns, "pitch", "").split(",") if kv)}
    if ns.cmd == "grt-view":
        t = open(ns.lef).read()
        if ns.bands:
            bl = [x for x in ns.band_layers.split(",") if x and x in lay]
            sh = share(t, lay, pitch)
            shares = {l: (min(0.95, round(ns.calib * (sh[l]["blocked_share"] + ns.margin), 3)) if l in bl else 0.0) for l in lay}
            g = grt_view_bands(t, shares, ns.gcell)
            chs = json.load(open(ns.channels)) if ns.channels else []
            g = open_channels(g, chs); open(ns.out, "w").write(g)
            print(json.dumps({"lef": ns.lef, "out": ns.out, "mode": "bands", "gcell": ns.gcell, "calib": ns.calib, "detail_share": sh,
                              "band_share": shares, "removed": [l for l in lay if l not in bl], "channels": chs,
                              "ok": grt_view(g, set(lay) | set(channel_rects(chs, size_of(t)))) == grt_view(t, set(lay) | set(channel_rects(chs, size_of(t))))}))
        else:
            chs = json.load(open(ns.channels)) if ns.channels else []
            g0 = grt_view(t, set(lay)); g = open_channels(g0, chs); open(ns.out, "w").write(g)
            print(json.dumps({"lef": ns.lef, "out": ns.out, "layers_removed": lay, "channels": chs, "ok": check(t, g0, set(lay))}))
    elif ns.cmd == "share":
        print(json.dumps(share(open(ns.lef).read(), lay, pitch)))
    elif ns.cmd == "region-tcl":
        print("region-tcl disabled: set_global_routing_region_adjustment raised GRT capacity over the children in the "
              "full flow (cbx_q10 M6 -193 pct, HBM M4 -71 pct); use grt-view --bands", file=sys.stderr)
        return 2
        sh = share(open(ns.lef).read(), lay, pitch)
        adj = {l: min(0.95, round(sh[l]["blocked_share"] + ns.margin, 3)) for l in lay}
        open(ns.out, "w").write(region_tcl(ns.master, adj))
        print(json.dumps({"master": ns.master, "share": sh, "adjustment": adj, "out": ns.out}))
    elif ns.cmd == "swap-tcl":
        open(ns.out, "w").write(SWAP_TCL); print(json.dumps({"out": ns.out}))
    elif ns.cmd == "check":
        ok = check(open(ns.lef).read(), open(ns.grt).read(), set(lay))
        print(json.dumps({"check_ok": ok})); return 0 if ok else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
