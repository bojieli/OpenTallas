"""ADV-C2-REACH (FP-CONVERGE-QC 11-25; WARN only, never a gate): single-cycle reach of the three long hops that
stopped the QC C2 GRT kits (SETUP_TRIAGE, 11-24): rstart (landing_reader_start origin -> u_cland_rstart_tx_p*/q relays ->
pin cland_rstart_out; measured 1128 um, TT -170..-178), flt_o (internal_stations bus:flt_o from -> regs -> to; 1623 um, TT -174)
and btab (g_btb[*].u_m macros -> nearest planned g_read relay site; none planned -> 8 repeaters, TT -153).  FAIL-tier when a
hop > 800 um (calibrated on those 4 paths) or btab has no g_read site; ADVISORY-tier when a hop > the CBC 405 um."""
import re

KIT_LIMIT_UM = 403.0
CBC_HOP_UM = 405.0
REACH_UM = 800.0


def md(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _col(lo, hi, bit, nbits):
    return lo + (hi - lo) * (bit + 0.5) / max(1, nbits)


def chan_path(px, py, lx, ly, face, direction, col):
    """istation_channel.path verbatim: polyline from the chain start (pin for in, leaf for out)"""
    pts = [(px, py), (col, py), (col, ly), (lx, ly)] if face in ("E", "W") else [(px, py), (px, col), (lx, col), (lx, ly)]
    return pts if direction == "in" else pts[::-1]


def plen(pts):
    return sum(md(a, c) for a, c in zip(pts, pts[1:]))


def point_at(pts, t):
    for a, c in zip(pts, pts[1:]):
        d = md(a, c)
        if t <= d:
            f = 0.0 if d == 0 else t / d
            return (a[0] + f * (c[0] - a[0]), a[1] + f * (c[1] - a[1]))
        t -= d
    return pts[-1]


def chan_sites(e, face, direction, W):
    """mid-bit station sites of a leg_order channel entry, kit model (istation_channel.sites)"""
    lo, hi = e["channel_um"]
    pin = e["to_um"] if direction == "out" else e["from_um"]
    lx, ly = e["leaf_um"]
    n = len(e["regs_um"])
    pts = chan_path(pin[0], pin[1], lx, ly, face, direction, _col(lo, hi, W // 2, W + 1))
    L = plen(pts)
    return [point_at(pts, L * (k + 1) / (n + 1)) for k in range(n)], L / (n + 1)


def _find_named(o, name):
    if isinstance(o, dict):
        if o.get("name") == name and isinstance(o.get("xy_um"), list):
            return o["xy_um"]
        for v in o.values():
            r = _find_named(v, name)
            if r:
                return r
    elif isinstance(o, list):
        for v in o:
            r = _find_named(v, name)
            if r:
                return r
    return None


def _hops(tn, what, chain, out):
    hs = [md(a, b) for a, b in zip(chain, chain[1:])]
    if not hs:
        return
    w = max(hs)
    tag = "FINDING" if w > REACH_UM else ("ADVISORY" if w > CBC_HOP_UM else None)
    if tag:
        out.append(f"{tag} C2-REACH {tn} {what}: hops {[round(h) for h in hs]} um, worst {w:.0f} > "
                   f"{REACH_UM if tag == 'FINDING' else CBC_HOP_UM:.0f}")


def check_c2(P, types=None):
    out = []
    for tn, t in sorted(P["partition_types"].items()):
        if types and tn not in types:
            continue
        rs = t.get("relay_sites") or {}
        # rstart: origin -> rstart_tx_p* -> cland_rstart_out
        o = ((t.get("clock") or {}).get("landing_reader_start") or {}).get("origin_rect_um")
        pin = _find_named(t, "cland_rstart_out")
        if o and pin:
            ps = sorted((int(m.group(1)), v) for k, v in rs.items()
                        for m in [re.match(r"u_cland_rstart_tx_p(\d+)/q$", k)] if m)
            _hops(tn, "rstart origin->rstart_tx->cland_rstart_out", [[(o[0] + o[2]) / 2, (o[1] + o[3]) / 2]] +
                  [v for _, v in ps] + [pin], out)
        # flt_o
        for e in t.get("internal_stations", []) or []:
            if e.get("conn") == "bus:flt_o" and e.get("from_um") and e.get("to_um"):
                _hops(tn, "flt_o from->stations->to", [e["from_um"]] + (e.get("regs_um") or []) + [e["to_um"]], out)
        # btab read registers next to the macros
        mac = [h for h in t.get("hard_cores", []) or [] if re.search(r"u_btab\..*g_btb\[\d+\]\.u_m$", h.get("inst", ""))]
        if mac:
            rd = [v for k, v in rs.items() if re.search(r"u_btab\..*g_read\[", k)]
            if not rd:
                out.append(f"FINDING C2-REACH {tn} btab: {len(mac)} g_btb macros, no planned g_read register site "
                           "(placer free; measured kit: rd_out -> g_read[0].q 8 wire buffers, TT -153)")
            else:
                for h in mac:
                    c = [h["origin_um"][0] + h["outline_um"][0] / 2, h["origin_um"][1] + h["outline_um"][1] / 2]
                    near = min(md(c, v) for v in rd)
                    if near > CBC_HOP_UM:
                        out.append(f"{'FINDING' if near > REACH_UM else 'ADVISORY'} C2-REACH {tn} btab {h['inst']}: "
                                   f"nearest g_read site {near:.0f} um")
    return out




def findings(raw, plan_path=None, tree=None, **_kw):
    """WARN ADV-C2-REACH lines; FINDING-tier lines carry 'reach', ADVISORY-tier 'cbc'"""
    out = []
    for ln in check_c2(raw):
        tier, rest = ln.split(" C2-REACH ", 1)
        out.append(f"WARN ADV-C2-REACH {'reach' if tier == 'FINDING' else 'cbc'} {rest}")
    if out:
        nf = sum(" reach " in x for x in out)
        out.append(f"WARN ADV-C2-REACH summary: {nf} hop(s) > {REACH_UM:.0f} um or missing btab read sites, "
                   f"{len(out) - nf} hop(s) > CBC {CBC_HOP_UM:.0f} um")
    return out
