#!/usr/bin/env python3
"""C-VIEW-OBS-PIN-ABUT (S81-COL-EOL 11-26, FABLE-RC-S81 row, COORD ruling): a hard-core abstract view whose OBS touches a signal pin shape on its FLANK
(zero gap, shared edge along the pin's long axis, same layer) lets the parent router put its pin landing metal onto the OBS: DRT reports a Short between the route net
and the instance (H10 R2 sstn xb[158]: 8-9 M3 shorts at 0.018 um pin slivers; ot_s81_sstn_base566 has 285 thin M3 strips that abut pin slots).

The strips are not real metal: of 566 thin M3 OBS strips of the legacy view, the signed core GDS has no M3 under 454 and a <= 1.1 percent fragment under the other 112 (klayout
region test, core_ot_s81_sstn_base566.gds).  They are what is left of the M3 blanket between pin stubs.  So the repair removes OBS only inside a CLEAR_UM keep-out beside each
abutting pin flank and keeps every part of it that covers real metal (--real JSON of the real metal inside the strips, exported once from the core GDS); nothing else changes
(pins, SIZE, other layers, other OBS stay byte-identical).  Ends of a pin (OBS continuing past the pin tip, the blanket under a pin) are not flank contact and are untouched.

  lint LEF [--layers M3,M4,...]          exit 1 and one line per OBS rect abutting a pin flank on the same layer (any layer when --layers is omitted)
  fix  LEF_IN LEF_OUT [--layers M3] [--clear-um 0.054] [--real REAL.json]    -> receipt JSON on stdout; LEF_OUT lints clean on the layers
  real-pya (run inside klayout -b -r)    exports REAL.json: real metal of one GDS layer inside the thin OBS strips of a LEF (see the script tail)

CLEAR_UM = half of a minimum M3 landing wire past a 0.018 um pin (0.009) + the M3 min spacing (0.036) + one grid step (0.009) = 0.054.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

CLEAR_UM = 0.054
THIN_UM = 0.05          # a "strip": narrow side <= this and long side < STRIP_MAX_UM (the blanket form is never a strip)
STRIP_MAX_UM = 0.5
_RECT = re.compile(r"^(\s*)RECT(\s+)(?:MASK\s+\d+\s+)?(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s*;")


def _nm(v):
    return int(round(float(v) * 1000))


def _fmt(n):
    s = ("%.3f" % (n / 1000.0)).rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


def parse(text):
    """-> (pins [(name, layer, rect_nm)] SIGNAL only, obs [(line_index, layer, rect_nm)], lines)"""
    lines = text.split("\n")
    pins, obs = [], []
    cur, sig, lay, in_obs = None, False, None, False
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s == "OBS":
            in_obs = True
            continue
        m = re.match(r"PIN\s+(\S+)", s)
        if m:
            cur, sig, in_obs = m.group(1), False, False
            continue
        if s.startswith("USE "):
            sig = s.rstrip(" ;").split()[1] == "SIGNAL"
            continue
        m = re.match(r"LAYER\s+(\w+)", s)
        if m:
            lay = m.group(1)
            continue
        m = _RECT.match(ln)
        if m:
            r = tuple(_nm(v) for v in m.groups()[2:])
            if in_obs:
                obs.append((i, lay, r))
            elif cur and sig:
                pins.append((cur, lay, r))
    return pins, obs, lines


def flank_contact(r, q):
    """True when OBS rect q touches pin rect r on a flank (an edge parallel to the pin's long axis): zero gap, positive shared length"""
    if (r[2] - r[0]) >= (r[3] - r[1]):
        return (q[3] == r[1] or q[1] == r[3]) and min(r[2], q[2]) - max(r[0], q[0]) > 0
    return (q[2] == r[0] or q[0] == r[2]) and min(r[3], q[3]) - max(r[1], q[1]) > 0


def findings(text, layers=None):
    pins, obs, _ = parse(text)
    out = []
    for i, lay, q in obs:
        if layers and lay not in layers:
            continue
        for name, pl, r in pins:
            if pl == lay and flank_contact(r, q):
                out.append(dict(layer=lay, pin=name, pin_rect_nm=list(r), obs_rect_nm=list(q), line=i + 1))
    return out


def _sub(q, z):
    """rect q minus rect z -> up to 4 rects"""
    if not (q[0] < z[2] and q[2] > z[0] and q[1] < z[3] and q[3] > z[1]):
        return [q]
    out = []
    if q[0] < z[0]:
        out.append((q[0], q[1], z[0], q[3]))
    if q[2] > z[2]:
        out.append((z[2], q[1], q[2], q[3]))
    x0, x1 = max(q[0], z[0]), min(q[2], z[2])
    if q[1] < z[1]:
        out.append((x0, q[1], x1, z[1]))
    if q[3] > z[3]:
        out.append((x0, z[3], x1, q[3]))
    return [r for r in out if r[2] > r[0] and r[3] > r[1]]


def fix(text, layers=("M3",), clear_um=CLEAR_UM, real=None):
    """-> (new text, receipt).  real = {layer: [rect_um, ...]} real metal kept as OBS inside the cleared zones (None: nothing kept, receipt says unverified)"""
    pins, obs, lines = parse(text)
    c = _nm(clear_um)
    realr = {L: [tuple(_nm(v) for v in r) for r in rs] for L, rs in (real or {}).items()}
    rep, cleared, kept_real, removed = {}, 0, 0, 0
    for i, lay, q in obs:
        if lay not in layers:
            continue
        pieces = [q]
        hit = False
        for name, pl, r in pins:
            if pl != lay:
                continue
            if not flank_contact(r, q):
                continue
            horiz = (r[2] - r[0]) >= (r[3] - r[1])
            z = (r[0], r[1] - c, r[2], r[3] + c) if horiz else (r[0] - c, r[1], r[2] + c, r[3])
            nxt = []
            for p in pieces:
                nxt += _sub(p, z)
            # real metal inside the zone and inside q stays blocked
            for rr in realr.get(lay, []):
                inter = (max(rr[0], z[0], q[0]), max(rr[1], z[1], q[1]), min(rr[2], z[2], q[2]), min(rr[3], z[3], q[3]))
                if inter[2] > inter[0] and inter[3] > inter[1]:
                    nxt.append(inter)
                    kept_real += 1
            pieces = nxt
            hit = True
        if hit:
            rep[i] = pieces
            cleared += 1
            if not pieces:
                removed += 1
    out = []
    for i, ln in enumerate(lines):
        if i not in rep:
            out.append(ln)
            continue
        m = _RECT.match(ln)
        ind, sp = m.group(1), m.group(2)
        for p in sorted(set(rep[i])):
            out.append("%sRECT%s%s %s %s %s ;" % (ind, sp, _fmt(p[0]), _fmt(p[1]), _fmt(p[2]), _fmt(p[3])))
    new = "\n".join(out)
    rec = dict(schema="opentallas.pin_flank_clear.v1", layers=list(layers), clear_um=clear_um, obs_rects_cleared=cleared, obs_rects_removed=removed,
               real_pieces_kept=kept_real, real_metal="verified against the core GDS" if real is not None else "UNVERIFIED (no --real)",
               before=len(findings(text, layers)), after=len(findings(new, layers)),
               in_sha256=hashlib.sha256(text.encode()).hexdigest(), out_sha256=hashlib.sha256(new.encode()).hexdigest())
    return new, rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    l = sub.add_parser("lint")
    l.add_argument("lef")
    l.add_argument("--layers", default="")
    f = sub.add_parser("fix")
    f.add_argument("lef_in")
    f.add_argument("lef_out")
    f.add_argument("--layers", default="M3")
    f.add_argument("--clear-um", type=float, default=CLEAR_UM)
    f.add_argument("--real")
    a = ap.parse_args(argv)
    if a.cmd == "lint":
        fi = findings(Path(a.lef).read_text(), [x for x in a.layers.split(",") if x] or None)
        for d in fi[:50]:
            print("PIN-FLANK-ABUT %(layer)s pin %(pin)s %(pin_rect_nm)s obs %(obs_rect_nm)s (line %(line)d)" % d)
        print("PIN-FLANK-ABUT %d finding(s)" % len(fi))
        return 1 if fi else 0
    real = json.loads(Path(a.real).read_text())["real_um"] if a.real else None
    new, rec = fix(Path(a.lef_in).read_text(), tuple(x for x in a.layers.split(",") if x), a.clear_um, real)
    Path(a.lef_out).write_text(new)
    print(json.dumps(rec))
    return 0 if rec["after"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
