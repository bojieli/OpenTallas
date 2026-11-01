#!/usr/bin/env python3
"""DIE-S81-44 10-31: one-block fix per type: serdes__t13 (lk_EN2) and serdes__t4 (lk_WN3) PHY lot -> shore band.

S81-SERDES-PHY-3 (delta_pma_views_1031) left these two types without the PMA pair: their PHY lot is a 1668 / 1854 um wide
column beside the core strip (S81.IR split 10-25), narrower than the 2246.4 um pair that OWNER 10-29 lays along the
shore.  Fix = the form of the sibling serdes types (t15/t16, same 2885.76 x 1226.88 outline, same 681.372 W-face window
top): the PHY domain / clock keepout becomes the full-width shore band above the highest W/E face window, the lot is that
band minus the 63.64 um guard on the inner and side edges, the core strip is the band below.  Per type, inside the type
only (outline, pins, buses, ft slots, stations unchanged): u_phy lot, clock.keepouts_um, the instance's die.pg.domains
record (rect, phy_macro_um, bumps.rect_um, core_strip_um) and die.io phy_macro record (rect, sites), then the PMA pair
(delta_pma_views_1031.place/part) and the KP4 decoder SRAMs + line-side pads + rck pad clock
(delta_kp4_srams_1031.place/part/PADS/rck_pad_clock) exactly as on the other serdes types.  Refuses a second run.

    python3 physical/die_plan/s81/delta_serdes_lots_1031.py PLAN_IN PLAN_OUT RECEIPT
"""
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools" / "die_plan"))
import schema as S  # noqa: E402


def _mod(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


PMA = _mod("delta_pma_views_1031")
KP4 = _mod("delta_kp4_srams_1031")
TYPES = ("serdes__t13", "serdes__t4")
GUARD = 63.64            # the S81.IR split PHY guard inside the partition (all serdes types)
SITE_PITCH = 150.0       # die.io phy_macro sites: C4 150 um array over the PHY macro (die_io.py)


def to_die(P, inst, rect):
    """type rect [x0,y0,x1,y1] -> die rect of instance inst (inverse of P.to_type, checked by round trip)"""
    p = P.parts[inst]
    (ox, oy), (W, H) = p["origin_um"], P.types[p["type"]]["outline_um"]
    o = p.get("orient", "R0")
    f = {"R0": lambda x, y: (ox + x, oy + y), "MX": lambda x, y: (ox + x, oy + H - y),
         "MY": lambda x, y: (ox + W - x, oy + y), "R180": lambda x, y: (ox + W - x, oy + H - y)}[o]
    a, b = f(rect[0], rect[1]), f(rect[2], rect[3])
    out = [round(min(a[0], b[0]), 4), round(min(a[1], b[1]), 4), round(max(a[0], b[0]), 4), round(max(a[1], b[1]), 4)]
    back = [P.to_type(inst, out[:2]), P.to_type(inst, out[2:])]
    bt = [min(back[0][0], back[1][0]), min(back[0][1], back[1][1]), max(back[0][0], back[1][0]), max(back[0][1], back[1][1])]
    if any(abs(u - v) > 1e-3 for u, v in zip(bt, rect)):
        raise SystemExit(f"{inst}: to_die round trip {rect} -> {out} -> {bt}")
    return out


def band(t):
    """(keepout, lot origin, lot outline, core strip) in type coords: shore = local top (every S81 serdes type)"""
    W, H = t["outline_um"]
    side = []
    for s in t.get("ft_slots", []) or []:
        for fk, wk in (("in_face", "in_window_um"), ("out_face", "out_window_um")):
            if s.get(fk) == "N":
                raise SystemExit("an ft window on the shore face")
            if s.get(fk) in ("W", "E"):
                side.append(s[wk][1])
    for b in t.get("buses", []) or []:
        if b["face"] == "N":
            raise SystemExit("a bus on the shore face")
        if b["face"] in ("W", "E"):
            side.append(b["window_um"][1])
    ky = max(side)
    ly = round(ky + GUARD, 4)
    return [0, ky, W, H], [GUARD, ly], [round(W - 2 * GUARD, 4), round(H - ly, 4)], [0, 0, W, ky]


def corner_sites(t, taps):
    """KP4 SRAM pair for a TURNING-slot type (t13 / t4: every ft slot S<->W, so the windows are S-face x ranges and
    W-face y ranges and delta_kp4_srams_1031.place, which reads every window as a y band, finds no band): the pair sits
    in the corner the slots never cross, east of the last S-face window (+ the 10.8 macro channel) and below the PHY
    keepout (- 10.8), at the highest site with no grid tap in the tap clearance, nearest the rx PMA centre
    (delta_kp4_srams_1031._row: same grid, gap and clearance)."""
    W, Ht = t["outline_um"]
    ko = t["clock"]["keepouts_um"][0]
    sx = [s[k][1] for s in t["ft_slots"] for f, k in (("in_face", "in_window_um"), ("out_face", "out_window_um"))
          if s[f] == "S"] + [b["window_um"][1] for b in t["buses"] if b["face"] == "S"]
    x_min = max(sx) + KP4.GAP
    rx = next(q for c in t["contents"] for q in c.get("physical_parts", []) if q["physical_master"] == "ot_s81_pma_rxm")
    xc = max(rx["origin_um"][0] + rx["outline_um"][0] / 2, x_min + 200.0)
    span = sum(w for _, _, w in KP4.LEAVES) + KP4.GAP
    y_top = math.floor((ko[1] - KP4.GAP - KP4.H - KP4.Y_OFF) / KP4.Y_GRID) * KP4.Y_GRID + KP4.Y_OFF
    for j in range(0, 400):
        y = y_top - j * KP4.Y_GRID
        if y < KP4.CLEAR:
            break
        got = KP4._row(y, xc, span, W, taps)
        if got and got[0][3] >= x_min:
            return got
    return None


def block(lines, i0, old):
    """line span [i0, i1) of a multi-line indent-1 JSON value starting at line i0 that equals old"""
    ind = len(lines[i0]) - len(lines[i0].lstrip())
    txt = json.dumps(old, indent=1).split("\n")
    head = lines[i0].lstrip()
    pre = head[:len(head) - len(txt[0])] if head.endswith(txt[0]) else None
    if pre is None:
        raise SystemExit(f"line {i0}: block head mismatch")
    n = len(txt)
    got = [lines[i0][ind + len(pre):]] + [ln[ind:] for ln in lines[i0 + 1:i0 + n]]
    want = txt
    if got[:-1] != want[:-1] or got[-1].rstrip(",") != want[-1]:
        raise SystemExit(f"line {i0}: block text is not the indent-1 rendering of the record")
    return n, ind, pre


def replace_block(lines, i0, old, new):
    n, ind, pre = block(lines, i0, old)
    comma = "," if lines[i0 + n - 1].endswith(",") else ""
    txt = json.dumps(new, indent=1).split("\n")
    rep = [" " * ind + pre + txt[0]] + [" " * ind + ln for ln in txt[1:]]
    rep[-1] += comma
    lines[i0:i0 + n] = rep
    return len(rep) - n


def main(src, dst, receipt):
    text = Path(src).read_text()
    plan = json.loads(text)
    P = S.Plan(json.loads(text), src)
    rows = []
    lines = text.split("\n")
    for tn in TYPES:
        t = plan["partition_types"][tn]
        c = next(c for c in t["contents"] if c.get("module") == "ot_pdie_serdes")
        if c.get("physical_parts") or t.get("pads") or "pad_clock" in t["clock"]:
            raise SystemExit(f"{tn}: already has PMA parts / pads / pad_clock (second run refused)")
        ko, lo, lw, strip = band(t)
        old_c, old_clock = json.loads(json.dumps(c)), json.loads(json.dumps(t["clock"]))
        # ---- the lot and the keepout (type)
        c["origin_um"], c["outline_um"] = lo, lw
        t["clock"]["keepouts_um"] = [ko]
        lot = [lo[0], lo[1], lo[0] + lw[0], lo[1] + lw[1]]
        got = PMA.place(lo, lw)
        if got is None or got[2] is None:
            raise SystemExit(f"{tn}: PMA pair does not fit the new lot {lo} {lw}")
        x, y_tx, y_rx = got
        c["physical_parts"] = [PMA.part(*PMA.LEAVES[0], x, y_tx), PMA.part(*PMA.LEAVES[1], x, y_rx)]
        c["note"] = c.get("note", "") + ("; DIE-S81-44 10-31 (delta_serdes_lots_1031): lot = full-width shore band (form of "
                                         "t15/t16) so the PMA pair lies along the shore (OWNER 10-29); + PMA abstracts "
                                         "u_ptx/u_prx + KP4 decoder SRAMs (delta_pma_views_1031 / delta_kp4_srams_1031 "
                                         "placement functions)")
        # ---- die PG domain + die io of every instance (single-instance types)
        insts = [n for n, p in P.parts.items() if p["type"] == tn]
        drows = []
        for inst in insts:
            d = next(d for d in plan["die"]["pg"]["domains"] if d["name"] == f"phy_{inst}")
            io = next(r for r in plan["die"]["io"] if r["name"] == f"io_{inst}_u_phy")
            od, oio = json.loads(json.dumps(d)), json.loads(json.dumps(io))
            rd, rl, rs = to_die(P, inst, ko), to_die(P, inst, lot), to_die(P, inst, strip)
            d["rect_um"], d["phy_macro_um"], d["bumps"]["rect_um"], d["core_strip_um"] = rd, rl, list(rl), [rs]
            mm2 = round(lw[0] * lw[1] / 1e6, 2)
            d["note"] += (f"; DIE-S81-44 10-31: shore band (t15/t16 form) PHY macro {lw[0]:.0f} x {lw[1]:.0f} um = {mm2} mm2 "
                          f"so the 2246.4-um PMA pair lies along the shore")
            io["rect_um"] = list(rl)
            io["sites"] = int(math.floor(lw[0] / SITE_PITCH) * math.floor(lw[1] / SITE_PITCH))
            io["note"] += (f"; DIE-S81-44 10-31: window = shore band PHY macro {lw[0]:.0f} x {lw[1]:.0f} um = {mm2} mm2 "
                           f"(t15/t16 form; PMA pair along the shore)")
            drows.append(dict(inst=inst, domain_old=od["rect_um"], domain_new=rd, macro_old=od["phy_macro_um"],
                              macro_new=rl, io_sites=[oio["sites"], io["sites"]]))
            for key, old, new in (("domain", od, d), ("io", oio, io)):
                i0 = [i for i, ln in enumerate(lines) if ln.strip() == f'"name": "{new["name"]}",']
                if len(i0) != 1:
                    raise SystemExit(f"{inst}: {key} record name line not unique ({len(i0)})")
                i0 = i0[0] - 1
                replace_block(lines, i0, old, new)
        rows.append(dict(type=tn, keepout_old=old_clock.get("keepouts_um"), keepout_new=[ko], lot_old=[old_c["origin_um"],
                         old_c["outline_um"]], lot_new=[lo, lw], pma=dict(x=x, y_tx=y_tx, y_rx=y_rx), die=drows))
        # ---- type text: u_phy compact line + clock block, written now so the kp4 step below sees the new keepout
        keys = {ln[3:ln.index('"', 3)]: i for i, ln in enumerate(lines)
                if ln.startswith('  "') and not ln.startswith('   ') and ln.endswith('": {')}
        i0 = keys[tn]
        i1 = min([i for i in keys.values() if i > i0] or [len(lines)])
        line = "    " + json.dumps(old_c, separators=(",", ":"))
        hit = [i for i in range(i0, i1) if lines[i].rstrip(",") == line]
        if len(hit) != 1:
            raise SystemExit(f"{tn}: u_phy record is not one compact line in its type block ({len(hit)})")
        lines[hit[0]] = "    " + json.dumps(c, separators=(",", ":")) + ("," if lines[hit[0]].endswith(",") else "")
        ck = [i for i in range(i0, i1) if lines[i] == '   "clock": {']
        if len(ck) != 1:
            raise SystemExit(f"{tn}: clock is not one multi-line record ({len(ck)})")
        replace_block(lines, ck[0], old_clock, t["clock"])
    # ---- KP4 decoder SRAMs + pads + rck pad clock, on the plan with the new keepouts (tap grid)
    mid = "\n".join(lines)
    if json.loads(mid) != plan:
        raise SystemExit("textual rewrite (lots) does not equal the edited plan")
    P2 = S.Plan(json.loads(mid), src)
    for r in rows:
        tn = r["type"]
        t = plan["partition_types"][tn]
        c = next(c for c in t["contents"] if c.get("module") == "ot_pdie_serdes")
        old_c, old_clock = json.loads(json.dumps(c)), json.loads(json.dumps(t["clock"]))
        taps = [(x, y) for _, x, y in S.tap_grid(P2, tn)]
        got, in_ft = corner_sites(t, taps), "corner"
        if got is None:
            raise SystemExit(f"{tn}: no KP4 SRAM site")
        c["physical_parts"] += [KP4.part(*g) for g in got]
        t["core_pg_connect"] = True
        t["pads"] = [json.loads(json.dumps(p)) for p in KP4.PADS]
        rx = next(q for q in c["physical_parts"] if q["physical_master"] == "ot_s81_pma_rxm")
        t["clock"]["pad_clock"] = KP4.rck_pad_clock(P2, t, rx, c["physical_parts"])
        r["sram_sites"], r["sram_in_ft_band"] = [[g[1], g[3], g[4]] for g in got], in_ft
        keys = {ln[3:ln.index('"', 3)]: i for i, ln in enumerate(lines)
                if ln.startswith('  "') and not ln.startswith('   ') and ln.endswith('": {')}
        i0 = keys[tn]
        i1 = min([i for i in keys.values() if i > i0] or [len(lines)])
        line = "    " + json.dumps(old_c, separators=(",", ":"))
        hit = [i for i in range(i0, i1) if lines[i].rstrip(",") == line]
        if len(hit) != 1:
            raise SystemExit(f"{tn}: u_phy record is not one compact line ({len(hit)})")
        lines[hit[0]] = "    " + json.dumps(c, separators=(",", ":")) + ("," if lines[hit[0]].endswith(",") else "")
        assert lines[i0 + 1].startswith('   "module": ') and lines[i0 + 1].endswith(","), tn
        lines[i0 + 2:i0 + 2] = ['   "core_pg_connect": true,',
                                '   "pads": ' + json.dumps(t["pads"], separators=(",", ":")) + ',']
        i1 += 2
        ck = [i for i in range(i0, i1) if lines[i] == '   "clock": {']
        if len(ck) != 1:
            raise SystemExit(f"{tn}: clock is not one multi-line record ({len(ck)})")
        lines.insert(ck[0] + 1, '    "pad_clock": ' + json.dumps(t["clock"]["pad_clock"], separators=(",", ":")) + ',')
    out = "\n".join(lines)
    if json.loads(out) != plan:
        raise SystemExit("textual rewrite does not equal the edited plan")
    Path(dst).write_text(out)
    sha = lambda s: hashlib.sha256(s.encode()).hexdigest()[:12]
    Path(receipt).write_text(json.dumps(dict(kind="S81_SERDES_LOTS_1031", plan_in=sha(text), plan_out=sha(out), rows=rows,
                                             unchanged="outlines, pins, buses, ft slots, stations, cycles, other types"),
                                        indent=1) + "\n")
    print(json.dumps(dict(plan_in=sha(text), plan_out=sha(out), rows=rows)))


if __name__ == "__main__":
    main(*sys.argv[1:4])
