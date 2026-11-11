#!/usr/bin/env python3
"""Parent route channels reserved THROUGH a hard core (DIE-QC-97 11-10, COORD ruling on cbx NK u_t21).

A hard core that a parent must cross declares `route_channels` on its plan hard_cores entries (core frame, R0):

    {"dir": "EW", "span_um": [lo, hi], "layers": ["M6"], "reason": "..."}

EW = a band over the full core width at core-frame y lo..hi (parent H traffic crosses W<->E); NS = a band over
the full core height at core-frame x lo..hi.  The listed layers belong to the PARENT inside the band:

  core kit   master_plan writes one `route_channel` keepout per channel into the core's master-plan slice
             (layers only, no placement use), so master_slice.emit_tcl puts a routing obstruction on those layers
             there: the core's own router stays off them and its cells still place under the band.
  abstract   the exported view then carries no OBS on those layers inside the band (`lef_violations` checks a
             view; a view with core metal there does not honour the channel).
  parent GRT a GRT view of the core (split-view bands) must leave the band open on those layers: `open_grt_view`
             removes the OBS of those layers inside the band (what-if form, and the form a band view must take).

One hardened master has ONE abstract, so every hard_cores entry of a module must declare the same channels
(`module_channels` refuses a mismatch, like partition_ft_reserve's one-map rule).  The frame is the core's own
R0 frame: an MY instance keeps the EW band at the same y, an MX instance mirrors it (no transform is needed here:
the core view is drawn once in R0).
"""
import json
import re

DIRS = ("EW", "NS")


def norm(ch):
    """canonical (dir, lo, hi, layers) of one route channel entry; ValueError on a malformed one."""
    d = ch.get("dir")
    if d not in DIRS:
        raise ValueError(f"route_channel dir must be one of {DIRS}, got {d!r}")
    lo, hi = (float(v) for v in ch["span_um"])
    if not hi > lo >= 0:
        raise ValueError(f"route_channel span_um must be 0 <= lo < hi, got {ch['span_um']!r}")
    layers = list(ch.get("layers") or [])
    if not layers or any(not re.fullmatch(r"M[1-9]", L) for L in layers):
        raise ValueError(f"route_channel layers must be M1..M9 names, got {layers!r}")
    return d, round(lo, 3), round(hi, 3), tuple(sorted(set(layers)))


def rect(ch, outline_um):
    """core-frame rect [x0, y0, x1, y1] of a channel over a core of outline [w, h]."""
    d, lo, hi, _ = norm(ch)
    w, h = (float(v) for v in outline_um)
    if d == "EW":
        if hi > h:
            raise ValueError(f"EW route_channel {lo}..{hi} outside the core height {h}")
        return [0.0, lo, round(w, 3), hi]
    if hi > w:
        raise ValueError(f"NS route_channel {lo}..{hi} outside the core width {w}")
    return [lo, 0.0, hi, round(h, 3)]


def module_channels(uses):
    """the one channel list of a hard-core module from its plan uses [(type, hard_core_entry)], [] when none.
    Every use must declare the same channels (one abstract per master)."""
    seen = {}
    for tn, h in uses:
        key = tuple(sorted(norm(c) for c in (h.get("route_channels") or [])))
        seen.setdefault(key, []).append(f"{tn}/{h.get('inst')}")
    if len(seen) > 1:
        rows = "; ".join(f"{list(k) or 'none'} on {v[:3]}{'...' if len(v) > 3 else ''}" for k, v in seen.items())
        raise ValueError(f"hard core {uses[0][1].get('module')}: route_channels differ across uses "
                         f"(one hardened view cannot honour both): {rows}")
    key = next(iter(seen)) if seen else ()
    return [dict(dir=d, span_um=[lo, hi], layers=list(ls)) for d, lo, hi, ls in key]


def slice_keepouts(uses, outline_um):
    """master-plan core slice keepouts of the module's channels (routing obstruction only, no placement use)."""
    return [dict(name=f"route_channel{i}", rect_um=rect(c, outline_um), kind="route_channel", use=[],
                 layers=list(c["layers"]))
            for i, c in enumerate(module_channels(uses))]


# ------------------------------------------------------------------------------------------- abstract (LEF) side
def _obs(text):
    """[(layer, x0, y0, x1, y1, line_index)] of the OBS RECTs of a single-MACRO LEF."""
    out, inobs, L = [], False, None
    for i, line in enumerate(text.splitlines()):
        s = line.split()
        if not s:
            continue
        if s[0] == "OBS":
            inobs = True
        elif inobs and s[0] == "END":
            inobs = False
        elif inobs and s[0] == "LAYER":
            L = s[1]
        elif inobs and s[0] == "RECT":
            out.append((L, *(float(v) for v in s[1:5]), i))
    return out


def _overlap(r, a):
    return r[0] < a[2] and r[2] > a[0] and r[1] < a[3] and r[3] > a[1]


def lef_violations(text, channels, outline_um):
    """OBS rects of a core view that sit inside a declared channel on a channel layer (empty = view honours it)."""
    bad = []
    for c in channels:
        a = rect(c, outline_um)
        ls = set(norm(c)[3])
        for L, x0, y0, x1, y1, _ in _obs(text):
            if L in ls and _overlap((x0, y0, x1, y1), a):
                bad.append(dict(layer=L, rect=[x0, y0, x1, y1], channel=a))
    return bad


def open_grt_view(text, channels, outline_um):
    """a GRT view of the core with the channel layers open inside every channel: OBS RECTs of those layers are cut
    to the parts outside the band (an EW band splits a rect in y, an NS band in x).  Pins, SIZE, other layers and
    other OBS are byte-identical.  Returns (text, receipt)."""
    bands = [(rect(c, outline_um), set(norm(c)[3]), norm(c)[0]) for c in channels]
    lines = text.splitlines(keepends=True)
    out, cut, kept = [], 0, 0
    obs = {i: (L, (x0, y0, x1, y1)) for L, x0, y0, x1, y1, i in _obs(text)}
    for i, line in enumerate(lines):
        if i not in obs:
            out.append(line)
            continue
        L, r = obs[i]
        pieces = [r]
        for a, ls, d in bands:
            if L not in ls:
                continue
            nxt = []
            for p in pieces:
                if not _overlap(p, a):
                    nxt.append(p)
                    continue
                cut += 1
                if d == "EW":
                    nxt += [q for q in ((p[0], p[1], p[2], min(p[3], a[1])), (p[0], max(p[1], a[3]), p[2], p[3]))
                            if q[3] - q[1] > 1e-9]
                else:
                    nxt += [q for q in ((p[0], p[1], min(p[2], a[0]), p[3]), (max(p[0], a[2]), p[1], p[2], p[3]))
                            if q[2] - q[0] > 1e-9]
            pieces = nxt
        if pieces == [r]:
            out.append(line)
            continue
        ind = line[:len(line) - len(line.lstrip())]
        for q in pieces:
            kept += 1
            out.append(ind + "RECT " + " ".join(f"{v:.3f}" for v in q) + " ;\n")
    return "".join(out), dict(schema="opentallas.core_route_channel_grt_view.v1", channels=channels,
                              rects_cut=cut, pieces_kept=kept)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for n in ("check", "grt-view"):
        s = sub.add_parser(n)
        s.add_argument("--lef", required=True)
        s.add_argument("--channels", required=True, help="JSON list of route_channels (core frame)")
        s.add_argument("--outline", required=True, help="W,H of the core (um)")
        if n == "grt-view":
            s.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    ch = json.loads(open(a.channels).read()) if not a.channels.lstrip().startswith("[") else json.loads(a.channels)
    ol = [float(v) for v in a.outline.split(",")]
    text = open(a.lef).read()
    if a.cmd == "check":
        bad = lef_violations(text, ch, ol)
        print(json.dumps(dict(lef=a.lef, violations=len(bad), first=bad[:5])))
        return 1 if bad else 0
    t, rec = open_grt_view(text, ch, ol)
    open(a.out, "w").write(t)
    print(json.dumps(dict(rec, lef=a.lef, out=a.out)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
