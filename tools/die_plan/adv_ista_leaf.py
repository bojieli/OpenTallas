"""ADV-ISTA-LEAF (FP-CONVERGE-QC 11-25; WARN only, never a gate): a non-core internal_stations entry whose kit route
start (leaf_um) is not at the register that really launches (out bus: from_um) / captures (in bus: to_um) the bus.
kit_istations is_chan_bits / is_bits start every bit's station path at leaf_um, so the first hop is d(launch, leaf) + L/edges;
flagged when it exceeds the kit limit 403 um.  Measured: sle_fw_v1 x2 / slw_fw_v1 sc_eo / sc_wo leaf (622.08, 6.17) vs launch
u_bin_x_sc_i on the E face (y 1068-1193): u_bin_x_sc_i/q -> u_ist_sc_eo_0/q 1390 um, TT setup_est -150..-195 (SETUP_TRIAGE)."""
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


def check_c3(P, types=None):
    out = []
    for tn, t in sorted(P["partition_types"].items()):
        if types and tn not in types:
            continue
        buses = {b["name"]: b for b in t.get("buses", [])}
        for e in t.get("internal_stations", []) or []:
            if e.get("core") or "leaf_um" not in e or not e.get("regs_um"):
                continue
            if not (e.get("from_um") and e.get("to_um") and e.get("conn", "").startswith("bus:")):
                continue
            b = buses.get(e["conn"][4:])
            if not b or b.get("dir") not in ("in", "out"):
                continue
            ref = e["from_um"] if b["dir"] == "out" else e["to_um"]
            d = md(e["leaf_um"], ref)
            n = len(e["regs_um"])
            if e.get("leg_order") == "channel" and e.get("channel_um"):
                _, hop = chan_sites(e, b.get("face"), b["dir"], int(e.get("bits", b.get("width", 1))))
            else:
                pin = e["to_um"] if b["dir"] == "out" else e["from_um"]
                hop = md(pin, e["leaf_um"]) / (n + 1)
            first = d + hop
            if first > KIT_LIMIT_UM:
                out.append(f"FINDING C3-ISTA-LEAF {tn} {e['conn']} ({b['dir']} {b.get('face')}): kit route starts at "
                           f"leaf_um {e['leaf_um']} which is {d:.0f} um from the real "
                           f"{'launch' if b['dir'] == 'out' else 'capture'} register "
                           f"{'from_um' if b['dir'] == 'out' else 'to_um'} {ref}; first hop {first:.0f} um > "
                           f"{KIT_LIMIT_UM:.0f} (kit ideal hop {hop:.0f}); fix: leaf_um := "
                           f"{'from_um' if b['dir'] == 'out' else 'to_um'}, regs_um re-sited on the new route")
    return out




def findings(raw, plan_path=None, tree=None, **_kw):
    """WARN ADV-ISTA-LEAF lines (one per flagged entry) + a summary"""
    out = [ln.replace("FINDING C3-ISTA-LEAF ", "WARN ADV-ISTA-LEAF ", 1) for ln in check_c3(raw)]
    if out:
        out.append(f"WARN ADV-ISTA-LEAF summary: {len(out)} station chain(s) start > {KIT_LIMIT_UM:.0f} um from their "
                   "launch / capture register (fix: leaf_um := from_um (out) / to_um (in), re-site regs_um)")
    return out
