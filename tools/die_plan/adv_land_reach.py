"""ADV-LAND-REACH (QC-LANDCORE-SWEEP, COORD 11-23; an estimator, never a gate; proposal to PRECHECK).

A hard clock-landing core (clock.landing_contract.bands[].hard_core) captures its bus on the forwarded clock.  For a falling-edge
writer (param_wrap WFALL/WNEG = 1) the kit pads the cland fclk to input max + DATA_ALLOWANCE_PS + setup (cland_fclk_target.py), so
the port -> core pin DATA wire may use only DATA_ALLOWANCE_PS = 45 ps (~66 um at PS_PER_UM).  A core seated farther from its port
than that has negative setup before CTS runs.  Real positive (FABLE-RC-QC 11-23 20:48, sle_ctl cla4f6f12f): hard cland ~300 um from
its pins = 192 ps port -> pin against 45 ps; this check gives max 299.7 um / 205 ps for x_hc1_st_b_i and finds cws1_i / cws2_i of
the same class (QC C1-noSU 12b66c0e4829 and V4 81fd3e6370c0: 22 FAIL + 19 EDGE of 108 hard landings).

For every band with a hard_core:
  core pins = LEF d[k] pin centres (core master, via c["lef"] under the tree), placed with origin_um + orient; with no readable LEF
              the core rectangle (nearest point, a lower bound) is used;
  port      = bus k spread over buses[].window_um of its face (lsb_low); else the contract pin fclk_in_<bus> (ft slots);
  distance  = Manhattan port -> pin per bit; delay = distance x PS_PER_UM;
  allowance = DATA_ALLOWANCE_PS for a fall writer; for a rise writer T - input max - DEFAULT_SETUP_PS (input max: IO budget 0.2 T,
              ft slots ring_hold.ft_ring_max_ps or (1 - ft_hop_in_share) T).
FAIL (flag) = static worst-bit margin < the die threshold (DIE_CAL: QC -100 ps, KV -10 ps; OT_ADV_LANDREACH_MARGIN_PS overrides), WATCH = margin < 0 only, OK otherwise.  Half-cycle (fall) landings are listed first.

    rows(raw, tree=None) -> [dict]      findings(raw, plan_path, tree=None, **kw) -> ["WARN ADV-LAND-REACH ..."]
"""
import os
import re
import sys
from pathlib import Path

CHECK = "LAND-REACH"
DATA_ALLOWANCE_PS = 45.0        # cland_fclk_target.DATA_ALLOWANCE_PS
DEFAULT_SETUP_PS = 95.0         # cland_fclk_target.DEFAULT_SETUP_PS
PS_PER_UM = 0.6845              # adv_hop_gap.PS_PER_UM (repeated wire)
MAX_LINES = 20
PORT_NEAR_UM = 20.0
FCLK_CAP_UM = 350.0       # an fclk-pin stand-in farther than this from the core is not a plausible data wire (KV A3b 500-1600 um): not judged
CORE_SMALL_UM = 150.0     # fclk pin stands in for the data port only for a core this small (its pins span <= the core)
# Calibration (FABLE-RC-QC 11-23 21:01, hub 207fb235): static worst-bit margin vs measured slack on the three measured landings.
# The static number is 30-115 ps pessimistic (the 45 ps allowance is not the whole eye), so the advisory flag sits at -100 ps.
MARGIN_FLAG_PS = float(os.environ.get("OT_ADV_LANDREACH_MARGIN_PS", "-100"))
# Per-die calibration.  flag = static worst-bit margin (ps) below which a landing is FAIL; far = judge a big core whose only port
# reference is the contract fclk pin even when that pin is > FCLK_CAP_UM away (KV-LAND-REACH-CAL 11-27: on KV the fclk pin IS the data
# port reference: 116 of 116 "not judged" landings failed placed, -92..-1054 ps).
DIE_CAL = {
    "qwen_compute": {"flag": -100.0, "far": False},
    "qwen_kvsys": {"flag": -10.0, "far": True},
}
CALIBRATED_DIES = tuple(DIE_CAL)      # measured slack exists for QC and KV; other dies print one summary line (PRECHECK ruling 11-23)
CALIBRATION = (("sle_ctl x_hc1_st_b_i", -160, -55.8), ("sle_ctl cws2_i", -154, -40.4), ("st_a b_hw_ctl_hc0_i", -44, -11.97))
# KV (KV-INT-R3/LANDREACH 11-27): 3_detailed_place.rpt worst setup path of every fclk_in_<landing> group (endpoint = the cland core d pin)
# of 77 placed kits, joined to this check on each kit's own plan form (463 plan/type/landing, 52 types): placed slack = 18.2 - 0.70 *
# worst-bit Manhattan um (r = -0.83; the model is 0.6845 ps/um with a 45 ps allowance, so the static margin is ~27 ps optimistic).
# Flag at static margin < -10 ps (worst bit > ~80 um) against the placed -42 ps setup gate: TP 447 FP 1 FN 0 TN 15.
CALIBRATION_KV = "placed slack = 18.2 - 0.70 x worst-bit um (n=463, r=-0.83); flag margin < -10: TP 447 FP 1 FN 0 TN 15 vs placed -42 ps"
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
try:                            # keep the per-um model in one place when the tree has it
    from adv_hop_gap import PS_PER_UM  # noqa: F811,E402
except Exception:               # noqa: BLE001
    pass

_PIN = re.compile(r"PIN\s+d\[(\d+)\](.*?)END\s+d\[\1\]", re.S)
_RECT = re.compile(r"RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)")
_SIZE = re.compile(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)")


def _lef_pins(path):
    text = Path(path).read_text()
    w, h = (float(v) for v in _SIZE.search(text).groups())
    pins = {}
    for m in _PIN.finditer(text):
        r = [float(v) for v in _RECT.search(m.group(2)).groups()]
        pins[int(m.group(1))] = ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
    return w, h, pins


def _xf(o, x, y, w, h):
    return {"R0": (x, y), "MY": (w - x, y), "MX": (x, h - y), "R180": (w - x, h - y), "R90": (h - y, x),
            "R270": (y, w - x), "MXR90": (y, x), "MYR90": (h - y, w - x)}.get(o or "R0", (x, y))


def _pct(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, int(p * (len(v) - 1) + 0.5))]


def _core_pins(c, tree):
    """absolute pin centres {k: (x, y)}; ({}, rect) when the LEF is not readable"""
    ox, oy = c["origin_um"]
    ow, oh = c["outline_um"]
    lef = c.get("lef")
    if lef and tree:
        try:
            w, h, pins = _lef_pins(Path(tree) / lef)
            if pins:
                return {k: (ox + _xf(c.get("orient"), x, y, w, h)[0], oy + _xf(c.get("orient"), x, y, w, h)[1])
                        for k, (x, y) in pins.items()}, None
        except (OSError, AttributeError, ValueError):
            pass
    return {}, (ox, oy, ox + ow, oy + oh)


def _cal(raw):
    return DIE_CAL.get(str((raw.get("die") or {}).get("name") or ""), {})


def _thr(raw, margin_ps=None):
    """margin_ps argument > OT_ADV_LANDREACH_MARGIN_PS > the die calibration > -100"""
    if margin_ps is not None:
        return float(margin_ps)
    if "OT_ADV_LANDREACH_MARGIN_PS" in os.environ:
        return MARGIN_FLAG_PS
    return float(_cal(raw).get("flag", MARGIN_FLAG_PS))


def rows(raw, tree=None, margin_ps=None, detail=None):
    """detail: optional list; one dict per judged-or-not landing {type, landing, core, ports, pins, rect, basis, face} for the
    generator fix (land_reach.py).  Off (None) the output is unchanged."""
    thr = _thr(raw, margin_ps)
    far = bool(_cal(raw).get("far"))
    out = []
    T = float((raw.get("die") or {}).get("period_ps") or 833.0)
    clk = raw.get("clock") or {}
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        lc = (t.get("clock") or {}).get("landing_contract") or {}
        cores = {c["inst"]: c for c in t.get("hard_cores") or []}
        buses = {b["name"]: b for b in t.get("buses") or []}
        fpin = {p["name"]: p["xy_um"] for p in lc.get("pins") or []}
        fts = {s["name"] + "_i" for s in t.get("ft_slots") or []}
        ftr = {s["name"] + "_i": s for s in t.get("ft_slots") or []}
        O = t.get("outline_um") or [0.0, 0.0]
        for bn, b in sorted((lc.get("bands") or {}).items()):
            c = cores.get(b.get("hard_core"))
            if not c:
                continue
            p = (c.get("param_wrap") or {}).get("params") or {}
            fall = p.get("WFALL") == 1 or p.get("WNEG") == 1
            ab, rect = _core_pins(c, tree)
            bus = buses.get(bn)
            if bus and bus.get("window_um"):
                lo, hi = bus["window_um"]
                W = max(1, int(bus["width"]))
                face = bus["face"]
                basis = "bus-window"
                ports = []
                for k in range(W):
                    s = lo + (k + 0.5) / W * (hi - lo)
                    ports.append({"S": (s, 0.0), "N": (s, O[1]), "W": (0.0, s), "E": (O[0], s)}[face])
            elif ("fclk_in_" + bn) in fpin:
                # no bus window: the data port position is unknown.  An ft slot's first station register (regs_um[0]) is the
                # port-side flop; trust it when the contract fclk pin sits beside it (< PORT_NEAR_UM); else the fclk pin stands in for the port only
                # for a small core (CORE_SMALL_UM).  Otherwise the fclk pin is NOT the data port (KV A3b: 700-1600 um): not judged.
                r0 = ((ftr.get(bn) or {}).get("regs_um") or [None])[0]
                f = fpin["fclk_in_" + bn]
                if r0 and abs(r0[0] - f[0]) + abs(r0[1] - f[1]) < PORT_NEAR_UM:
                    ports, basis, face = [tuple(r0)], "ft-reg0", (ftr[bn].get("in_face") or "ft")
                elif far or max(c["outline_um"]) <= CORE_SMALL_UM:
                    ports, basis, face = [tuple(f)], "fclk-pin", (ftr[bn].get("in_face") if bn in ftr else None) or "ft"
                else:
                    out.append(dict(type=tn, landing=bn, core=c["inst"], edge="half" if fall else "full", verdict="INFO",
                                    basis="fclk-pin", m50=0.0, note="port position unknown, not judged"))
                    continue
            else:
                continue
            if not ports:
                continue
            if detail is not None:
                detail.append(dict(type=tn, landing=bn, core=c["inst"], ports=[tuple(p) for p in ports], pins=ab or None, rect=rect,
                                   basis=basis, face=face, fall=fall))
            ds = []
            for k, (px, py) in enumerate(ports):
                if ab:
                    qx, qy = ab[min(k, max(ab))] if len(ports) > 1 else (None, None)
                    if qx is None:      # single reference port: distance to every pin, one entry per pin
                        ds += [abs(px - x) + abs(py - y) for (x, y) in ab.values()]
                        continue
                else:
                    qx = min(max(px, rect[0]), rect[2])
                    qy = min(max(py, rect[1]), rect[3])
                ds.append(abs(px - qx) + abs(py - qy))
            if fall:
                allow = DATA_ALLOWANCE_PS
            else:
                imax = float(((clk.get("ring_hold") or {}).get("ft_ring_max_ps"))
                             or (1 - float(clk.get("ft_hop_in_share", 0.08))) * T) if bn in fts else 0.2 * T
                allow = T - imax - DEFAULT_SETUP_PS
            d50, dmx = _pct(ds, 0.5), max(ds)
            if basis == "fclk-pin" and dmx > FCLK_CAP_UM and not far:
                out.append(dict(type=tn, landing=bn, core=c["inst"], edge="half" if fall else "full", verdict="INFO",
                                basis="fclk-pin", m50=0.0, note="port position unknown, not judged"))
                continue
            m50, mmx = allow - d50 * PS_PER_UM, allow - dmx * PS_PER_UM
            out.append(dict(type=tn, landing=bn, core=c["inst"], edge="half" if fall else "full", n=len(ds), d50=d50, dmax=dmx,
                            delay50=d50 * PS_PER_UM, delaymax=dmx * PS_PER_UM, allow=allow, m50=m50, mmax=mmx,
                            verdict="FAIL" if mmx < thr else ("WATCH" if mmx < 0 else "OK"), basis=basis,
                            exact=bool(ab), face=face))
    out.sort(key=lambda r: (r["edge"] != "half", r["m50"], r["type"], r["landing"]))
    return out


def findings(raw, plan_path=None, tree=None, margin_ps=None, **kw):
    """WARN ADV-LAND-REACH lines (capped at MAX_LINES) + one summary line; never raises."""
    try:
        if not isinstance(raw, dict) or not raw.get("partition_types"):
            return [f"WARN ADV-{CHECK} not checked: plan has no partition_types"]
        rs = rows(raw, tree, margin_ps)
        thr = _thr(raw, margin_ps)
        if not rs:
            return [f"WARN ADV-{CHECK} not checked: no hard landing cores in clock.landing_contract.bands"]
        if not any(r["verdict"] != "INFO" for r in rs):
            return [f"INFO ADV-{CHECK} {len(rs)} hard landings not judged: port position unknown (no bus window, no ft port register)"]
        unj = [r for r in rs if r["verdict"] == "INFO"]
        rs = [r for r in rs if r["verdict"] != "INFO"]
        bad = [r for r in rs if r["verdict"] == "FAIL"]
        die = str((raw.get("die") or {}).get("name") or "")
        if die not in CALIBRATED_DIES and os.environ.get("OT_ADV_LANDREACH_ALL", "0") != "1":
            return [f"WARN ADV-{CHECK} not calibrated for this die ({die or '?'}): {len(rs)} landings, {len(bad)} would be flagged "
                    f"(static only, no measured slack); set OT_ADV_LANDREACH_ALL=1 to list them"]
        edge = [r for r in rs if r["verdict"] == "WATCH"]
        lines = [f"WARN ADV-{CHECK} {r['type']}: hard landing {r['landing']} (core {r['core']}, {r['edge']}-cycle) parked "
                 f"{r['d50']:.0f} um median / {r['dmax']:.0f} um worst from its {r['face']} port = {r['delay50']:.0f} / "
                 f"{r['delaymax']:.0f} ps at {PS_PER_UM} ps/um against a {r['allow']:.0f} ps data allowance (margin "
                 f"{r['m50']:.0f} ps){'' if r['exact'] else ' [core rect, no LEF: lower bound]'}; fix: re-seat the core "
                 f"within ~{r['allow'] / PS_PER_UM:.0f} um of its pins, or move the pins to the core (advisory; static worst-bit margin "
                 f"{r['mmax']:.0f} ps < {thr:g})"
                 for r in bad[:MAX_LINES]]
        lines.append(f"WARN ADV-{CHECK} {len(bad)} flagged (static worst-bit margin < {thr:g} ps) + {len(edge)} WATCH (< 0, not flagged) of {len(rs)} hard landings in "
                     f"{len({r['type'] for r in rs})} types ({len({r['type'] for r in bad})} types flagged); half-cycle "
                     f"{sum(1 for r in rs if r['edge'] == 'half')}; allowance {DATA_ALLOWANCE_PS:g} ps = "
                     f"{DATA_ALLOWANCE_PS / PS_PER_UM:.0f} um"
                     + (f"; {len(unj)} not judged (port position unknown)" if unj else "")
                     + ("; top: " + ", ".join(f"{r['type']}/{r['landing']} {r['m50']:.0f}" for r in bad[:5]) if bad else ""))
        lines.append(f"WARN ADV-{CHECK} calibration static-vs-measured slack (ps): "
                     + ("KV " + CALIBRATION_KV if die == "qwen_kvsys" else
                        "; ".join(f"{n} {a} vs {m}" for n, a, m in CALIBRATION)
                        + "; static is 30-115 ps pessimistic")
                     + "; advisory only, threshold OT_ADV_LANDREACH_MARGIN_PS")
        return lines
    except Exception as e:  # noqa: BLE001
        return [f"WARN ADV-{CHECK} not checked: {type(e).__name__}: {str(e)[:200]}"]


if __name__ == "__main__":
    import json
    for ln in findings(json.load(open(sys.argv[1])), sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None):
        print(ln)
