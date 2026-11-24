#!/usr/bin/env python3
"""station_xref.py -- PRE class STNXREF (STATION-MOVE-HELPER 11-24, COORD from a FABLE-RC-KV class note).  REPORT ONLY (WARN, r703:
no date switch to FAIL).

Class: a plan row moves, removes or re-seats a station (ft slot station, internal station) and a DERIVED record still names or
sits on the old one.  Three times on 11-23/24, each found at bind emit or G0 an hour or more later:
  KV-INCORE-R2 C2T (A5t3): NOSEAM took kv3_io_cor_v1 ft4 6->4, ft15 5->4 and re-seated the kept stations, but reset.bank_taps
      still named u_ft_ft4_o_4/_5, u_ft_ft15_o_4 (EMIT 'sink u_ft_ft4_o_4 is not an emitted ot_dp_st') and kept every re-seated
      station on its old tap.
  S81-T2-REFLOOR D2 (vs B1): 116 clock-landing edges kept relays / endpoints of ports that moved (G0 'actual endpoint hop 903 um
      exceeds 405'), stations ~1 um off a face pin.
  KV-HG-CAP ENTRYFOOT: a tap re-point / respace left records keyed by the old tap name or site.

Every station / relay the plan references is cross-checked against each record derived from it.  Forms (WARN STNXREF-<FORM>):
  BANKSINK    reset.bank_taps sink names no bank of the plan: u_ft_<slot>_o_<k> with k >= stations (or no slot), u_ist_<bus>_<k>
              past the internal_stations row, u_bin_ / u_bout_ of no bus; a sink listed twice.                       (plan only)
  BANKFOLLOW  a station whose site moved against BASE (> BANK_MOVE_UM, to a site no BASE station of the slot had) is still on the
              same bank tap id as in BASE (the tap was never re-derived for the new site).                        (baseline)
  BITCOUNT    ft slot bit_sites_um has != stations-1 patterns (pattern j belongs to station j >= 1).               (plan only)
  BITFOLLOW   station j moved to a new site against BASE and its bit-pattern centre now lies farther from it than any BASE
              pattern of the slot lay from its own station (+ TOL_UM): the pattern stayed behind.                   (baseline)
  LANDPIN     a clock.landing_network edge endpoint {part, bus} names no landing_contract pin of the part's type.  (plan only)
  LANDHOP     a landing edge chain pin -> relays -> pin has an L1 hop over the edge max_hop_um (default 405); with BASE only
              hops that are new or worse than BASE are listed (BASE over-limit hops are counted, not listed).
  LANDFOLLOW  an ft slot's station 0 moved against BASE (type frame) but its landing in-pins (fclk_in_<slot>_i,
              cland_fstart_in_<slot>_i) did not, or the reverse.                                                    (baseline)
  STAGECNT    plan latency.lanes[L].stations != the stations the plan prices for L (schema.Plan.lane_latency: the ft
              stations + built extras of every crossed slot) -- the price / LATCHECK stage count was not re-derived.
  TAPKEY      an explicit clock.added_taps name whose site moved against BASE while a record keyed by that NAME
              (landing_contract pin source_clock_tap, edge_clocks) is unchanged: the name silently re-targets.     (baseline)

    python3 -I tools/die_plan/station_xref.py --plan PLAN [--baseline-plan BASE] [--json OUT] [--max-list N]
    exit 0 always (report only); 2 = bad input.  plan_gate_pre runs it (class STNXREF, --skip STNXREF).
The repair for every form is station_move.py (move / remove / reseat with every derived record together).
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # -I drops the script dir
TOL_UM = 1.0
BANK_MOVE_UM = 50.0       # a station moved less than this may keep its tap (one tap pitch is >= 100 um on every die)
HOP_UM = 405.0
EPS = 1e-3
MAX_LIST = 6
FORMS = ("BANKSINK", "BANKFOLLOW", "BITCOUNT", "BITFOLLOW", "LANDPIN", "LANDHOP", "LANDFOLLOW", "STAGECNT", "TAPKEY")
FT = re.compile(r"^u_ft_(\w+?)_o_(\d+)$")
IST = re.compile(r"^u_ist_(\w+?)_(\d+)$")
BUS = re.compile(r"^u_b(?:in|out)_(\w+)$")


def man(a, b):
    return abs(float(a[0]) - float(b[0])) + abs(float(a[1]) - float(b[1]))


def _ptypes(raw):
    return raw.get("partition_types") or {}


def station_sites(t):
    """{bank inst name: (x, y)} of every planned station of type t (type frame): ft slot station k = regs_um[k] (when the plan has
    one site per station), internal station u_ist_<bus>_<k> = internal_stations[conn bus:<bus>].regs_um[k]."""
    out = {}
    for s in t.get("ft_slots") or []:
        regs = s.get("regs_um") or []
        n = int(s.get("stations", 1) or 1)
        if len(regs) == n:
            for k, r in enumerate(regs):
                out[f"u_ft_{s['name']}_o_{k}"] = (float(r[0]), float(r[1]))
    for e in t.get("internal_stations") or []:
        c = str(e.get("conn") or "")
        if c.startswith("bus:"):
            for k, r in enumerate(e.get("regs_um") or []):
                out.setdefault(f"u_ist_{c[4:]}_{k}", (float(r[0]), float(r[1])))
    return out


def bank_exists(t, inst):
    m = FT.match(inst)
    if m:
        s = next((x for x in t.get("ft_slots") or [] if x.get("name") == m.group(1)), None)
        if s is None:
            return f"no ft slot {m.group(1)}"
        n = int(s.get("stations", 1) or 1)
        return None if int(m.group(2)) < n else f"slot {m.group(1)} has {n} station(s) (0..{n - 1})"
    m = IST.match(inst)
    if m:
        rows = [e for e in t.get("internal_stations") or [] if e.get("conn") == f"bus:{m.group(1)}"]
        if not rows:
            return None if any(b.get("name") == m.group(1) for b in t.get("buses") or []) else f"no internal_stations / bus {m.group(1)}"
        n = max(len(e.get("regs_um") or []) for e in rows)
        return None if (n == 0 or int(m.group(2)) < n) else f"bus {m.group(1)} has {n} internal station(s)"
    m = BUS.match(inst)
    if m:
        return None if any(b.get("name") == m.group(1) for b in t.get("buses") or []) else f"no bus {m.group(1)}"
    return None


def bank_map(t):
    return {s: r.get("tap") for r in ((t.get("reset") or {}).get("bank_taps") or []) for s in r.get("sinks") or []}


def _centre(ent, cell):
    if not ent:
        return None
    cw, ch = (cell or (0.0, 0.0))[:2]
    xs = [float(p[0]) for p in ent]
    ys = [float(p[1]) for p in ent]
    return ((min(xs) + max(xs) + cw) / 2.0, (min(ys) + max(ys) + ch) / 2.0)


def _cap(lines, form, max_list):
    if len(lines) <= max_list:
        return lines
    return lines[:max_list] + [f"WARN STNXREF-{form} ... {len(lines) - max_list} more"]


def check_banks(raw, base=None):
    sink, follow = [], []
    bt_base = _ptypes(base) if base else {}
    for tn, t in sorted(_ptypes(raw).items()):
        rows = (t.get("reset") or {}).get("bank_taps") or []
        if not rows:
            continue
        seen = {}
        for r in rows:
            for s in r.get("sinks") or []:
                why = bank_exists(t, s)
                if why:
                    sink.append(f"WARN STNXREF-BANKSINK {tn}: bank_taps tap {r.get('tap')} sink {s}: {why} (the station was removed or "
                                f"renumbered; re-derive bank_taps: station_move.py)")
                if s in seen:
                    sink.append(f"WARN STNXREF-BANKSINK {tn}: sink {s} on taps {seen[s]} and {r.get('tap')}")
                seen[s] = r.get("tap")
        b = bt_base.get(tn)
        if not b:
            continue
        old_sites, new_sites, old_map = station_sites(b), station_sites(t), bank_map(b)
        for s, tap in seen.items():
            if not (s in old_sites and s in new_sites and old_map.get(s) == tap):
                continue
            owner = next((n for n, q in old_sites.items() if man(q, new_sites[s]) <= TOL_UM), None)
            if owner is not None:                    # the site is a BASE station's (kept / renumbered): its tap, not the name's
                if owner != s and old_map.get(owner) not in (None, tap):
                    follow.append(f"WARN STNXREF-BANKFOLLOW {tn}: {s} now sits on the site of BASE {owner} (tap {old_map.get(owner)}) "
                                  f"but kept the tap of its old name ({tap}): renumbered, tap followed the name not the site")
                continue
            if man(old_sites[s], new_sites[s]) > BANK_MOVE_UM:
                follow.append(f"WARN STNXREF-BANKFOLLOW {tn}: {s} moved {man(old_sites[s], new_sites[s]):.1f} um "
                              f"({_xy(old_sites[s])} -> {_xy(new_sites[s])}) but stays on bank tap {tap} (not re-derived for the new site)")
    return sink, follow


def _xy(p):
    return f"({p[0]:.2f}, {p[1]:.2f})"


def check_bits(raw, base=None):
    cnt, follow = [], []
    bt = _ptypes(base) if base else {}
    for tn, t in sorted(_ptypes(raw).items()):
        bslots = {s.get("name"): s for s in (bt.get(tn) or {}).get("ft_slots") or []}
        for s in t.get("ft_slots") or []:
            bits = s.get("bit_sites_um")
            if bits is None:
                continue
            n = int(s.get("stations", 1) or 1)
            if len(bits) != n - 1:
                cnt.append(f"WARN STNXREF-BITCOUNT {tn} {s['name']}: {len(bits)} bit-site pattern(s) for {n} station(s) (want {n - 1})")
                continue
            o = bslots.get(s["name"])
            if not o or o.get("bit_sites_um") is None:
                continue
            r1, r0, b0 = s.get("regs_um") or [], o.get("regs_um") or [], o["bit_sites_um"]
            if len(r1) != n or len(r0) != len(b0) + 1:
                continue
            offs = [man(c, r0[j]) for j in range(1, len(r0)) for c in [_centre(b0[j - 1], o.get("bit_site_cell_um"))] if c]
            if not offs:
                continue
            lim = max(offs) + TOL_UM
            for j in range(1, n):
                if any(man(q, r1[j]) <= TOL_UM for q in r0):
                    continue                                   # station not moved (possibly renumbered)
                c1 = _centre(bits[j - 1], s.get("bit_site_cell_um"))
                if c1 is not None and man(c1, r1[j]) > lim:
                    near = min(r0, key=lambda q: man(q, r1[j]))
                    follow.append(f"WARN STNXREF-BITFOLLOW {tn} {s['name']} station {j}: moved {man(near, r1[j]):.1f} um, its bit pattern "
                                  f"is now {man(c1, r1[j]):.1f} um from it (BASE max {max(offs):.1f}): the pattern did not follow")
    return cnt, follow


def _pins(t):
    return {p["name"]: p for p in ((t.get("clock") or {}).get("landing_contract") or {}).get("pins") or [] if "name" in p}


class _Frame:
    """die frame of a raw plan without building schema.Plan (same transform as schema.Plan.to_die)"""

    def __init__(self, raw):
        self.parts = {p["name"]: p for p in raw.get("partitions") or [] if "name" in p}
        self.types = _ptypes(raw)
        self.pins = {}

    def pin(self, part, bus):
        p = self.parts.get(part)
        if p is None:
            return None
        tn = p.get("type")
        if tn not in self.pins:
            self.pins[tn] = _pins(self.types.get(tn) or {})
        q = self.pins[tn].get(bus)
        if q is None or "xy_um" not in q:
            return None
        w, h = (self.types.get(tn) or {}).get("outline_um") or (0.0, 0.0)
        x, y = q["xy_um"]
        o = p.get("orient", "R0") or "R0"
        X, Y = {"R0": (x, y), "N": (x, y), "MX": (x, h - y), "FS": (x, h - y), "MY": (w - x, y), "FN": (w - x, y),
                "R180": (w - x, h - y), "S": (w - x, h - y)}.get(o, (x, y))
        return (p["origin_um"][0] + X, p["origin_um"][1] + Y)


def _edge_hops(F, e):
    a = F.pin(e["src"]["part"], e["src"]["bus"])
    b = F.pin(e["dst"]["part"], e["dst"]["bus"])
    if a is None or b is None:
        return None
    chain = [a] + [tuple(r["xy_um"]) for r in e.get("relays") or [] if r.get("xy_um")] + [b]
    return [man(chain[i], chain[i + 1]) for i in range(len(chain) - 1)]


def check_landing(raw, base=None):
    pin, hop = [], []
    edges = ((raw.get("clock") or {}).get("landing_network") or {}).get("edges") or []
    if not edges:
        return pin, hop, 0
    F = _Frame(raw)
    FB = _Frame(base) if base else None
    bedges = {e.get("id"): e for e in ((base or {}).get("clock") or {}).get("landing_network", {}).get("edges") or []} if base else {}
    base_over = 0
    for e in edges:
        for side in ("src", "dst"):
            ep = e.get(side) or {}
            if F.pin(ep.get("part"), ep.get("bus")) is None:
                pin.append(f"WARN STNXREF-LANDPIN {e.get('id')}: {side} {ep.get('part')}.{ep.get('bus')} is no landing_contract pin of "
                           f"its type (port renamed / removed; re-derive the edge)")
        hs = _edge_hops(F, e)
        if not hs:
            continue
        lim = float(e.get("max_hop_um") or HOP_UM)
        worst = max(hs)
        if worst <= lim + EPS:
            continue
        old = None
        if FB is not None and e.get("id") in bedges:
            ho = _edge_hops(FB, bedges[e["id"]])
            old = max(ho) if ho else None
        if old is not None and old > lim + EPS and worst <= old + EPS:
            base_over += 1
            continue
        hop.append(f"WARN STNXREF-LANDHOP {e.get('id')} {e['src']['part']}.{e['src']['bus']} -> {e['dst']['part']}.{e['dst']['bus']}: "
                   f"hop {worst:.1f} um > {lim:g} with {len(e.get('relays') or [])} relay(s)"
                   + (f" (BASE {old:.1f})" if old is not None else "") + " (endpoint moved, relays not re-derived)")
    return pin, hop, base_over


def check_landfollow(raw, base):
    out = []
    if not base:
        return out
    bt = _ptypes(base)
    for tn, t in sorted(_ptypes(raw).items()):
        b = bt.get(tn)
        if not b:
            continue
        p1, p0 = _pins(t), _pins(b)
        bs = {s.get("name"): s for s in b.get("ft_slots") or []}
        for s in t.get("ft_slots") or []:
            o = bs.get(s["name"])
            if not o or not s.get("regs_um") or not o.get("regs_um"):
                continue
            ds = man(s["regs_um"][0], o["regs_um"][0])
            for pn in (f"fclk_in_{s['name']}_i", f"cland_fstart_in_{s['name']}_i"):
                if pn in p1 and pn in p0 and "xy_um" in p1[pn] and "xy_um" in p0[pn]:
                    dp = man(p1[pn]["xy_um"], p0[pn]["xy_um"])
                    if (ds > TOL_UM) != (dp > TOL_UM):
                        out.append(f"WARN STNXREF-LANDFOLLOW {tn} {s['name']}: station 0 moved {ds:.1f} um, landing pin {pn} moved "
                                   f"{dp:.1f} um (one did not follow the other)")
                    break
    return out


def check_stagecnt(raw, plan_path=None):
    """price / LATCHECK stage count: plan latency.lanes[L].stations vs schema.Plan.lane_latency(L)['stations']"""
    lanes = (raw.get("latency") or {}).get("lanes") or {}
    if not lanes:
        return []
    sys.path.insert(0, str(HERE))
    import schema as S
    P = S.Plan(raw, plan_path) if plan_path else S.Plan(raw)
    out = []
    for lid, row in lanes.items():
        if lid not in P.lanes or "stations" not in row:
            continue
        try:
            st = P.lane_latency(lid)["stations"]
        except Exception as e:  # noqa: BLE001 - a lane that does not price names itself
            out.append(f"WARN STNXREF-STAGECNT {lid}: not priced ({type(e).__name__}: {str(e)[:100]})")
            continue
        if int(row["stations"]) != int(st):
            out.append(f"WARN STNXREF-STAGECNT {lid}: latency table stations {row['stations']} != planned stations {st} "
                       f"(cycles {row.get('cycles')}; re-price: plan_gate_pre.py reprice / stn_reprice.py)")
    return out


def check_tapkey(raw, base):
    out = []
    if not base:
        return out
    bt = _ptypes(base)
    for tn, t in sorted(_ptypes(raw).items()):
        b = bt.get(tn)
        if not b:
            continue
        a1 = {x["name"]: x.get("xy") for x in (t.get("clock") or {}).get("added_taps") or [] if "name" in x}
        a0 = {x["name"]: x.get("xy") for x in (b.get("clock") or {}).get("added_taps") or [] if "name" in x}
        moved = {n for n in a1 if n in a0 and a1[n] and a0[n] and man(a1[n], a0[n]) > TOL_UM}
        if not moved:
            continue
        p1, p0 = _pins(t), _pins(b)
        for pn, p in p1.items():
            tap = p.get("source_clock_tap")
            if tap in moved and p0.get(pn, {}).get("source_clock_tap") == tap and p0[pn].get("xy_um") == p.get("xy_um"):
                out.append(f"WARN STNXREF-TAPKEY {tn}: {pn} keeps source_clock_tap {tap}, whose site moved {man(a1[tap], a0[tap]):.1f} um "
                           f"(name-keyed record re-targets; re-pick by site)")
    return out


def findings(raw, base=None, plan_path=None, max_list=MAX_LIST, forms=FORMS):
    """-> WARN STNXREF-<FORM> lines (capped per form) + one LIST STNXREF counts line.  Never FAIL (r703)."""
    got = {f: [] for f in FORMS}
    extra, crash, bad = "", [], set()
    fs = set(forms)

    def run(names, fn):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 - a checker crash names itself, it never passes silently; other forms still run
            crash.append(f"WARN STNXREF not checked ({'/'.join(names)}): {type(e).__name__}: {str(e)[:200]}")
            bad.update(names)
            return None
    if {"BANKSINK", "BANKFOLLOW"} & fs:
        r = run(("BANKSINK", "BANKFOLLOW"), lambda: check_banks(raw, base))
        if r:
            got["BANKSINK"], got["BANKFOLLOW"] = r
    if {"BITCOUNT", "BITFOLLOW"} & fs:
        r = run(("BITCOUNT", "BITFOLLOW"), lambda: check_bits(raw, base))
        if r:
            got["BITCOUNT"], got["BITFOLLOW"] = r
    if {"LANDPIN", "LANDHOP"} & fs:
        r = run(("LANDPIN", "LANDHOP"), lambda: check_landing(raw, base))
        if r:
            got["LANDPIN"], got["LANDHOP"], bo = r
            extra = f" landhop_base_unchanged={bo}" if bo else ""
    for f, fn in (("LANDFOLLOW", lambda: check_landfollow(raw, base)), ("TAPKEY", lambda: check_tapkey(raw, base)),
                  ("STAGECNT", lambda: check_stagecnt(raw, plan_path))):
        if f in fs:
            got[f] = run((f,), fn) or []
    out = list(crash)
    for f in FORMS:
        if f in forms:
            out += _cap(got[f], f, max_list)
    cnt = " ".join(f"{f}={'ERR' if f in bad else len(got[f])}" for f in FORMS if f in forms)
    out.append(f"LIST STNXREF {cnt}{extra} baseline={'yes' if base else 'no'} (report only, r703)")
    return out


def counts(lines):
    m = next((x for x in lines if x.startswith("LIST STNXREF ")), "")
    return {k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", m)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--plan", required=True)
    ap.add_argument("--baseline-plan")
    ap.add_argument("--json")
    ap.add_argument("--max-list", type=int, default=MAX_LIST)
    ap.add_argument("--forms", default=",".join(FORMS))
    a = ap.parse_args(argv)
    try:
        raw = json.loads(Path(a.plan).read_text())
        base = json.loads(Path(a.baseline_plan).read_text()) if a.baseline_plan else None
    except (OSError, ValueError) as e:
        print(f"station_xref: bad input: {e}", file=sys.stderr)
        return 2
    lines = findings(raw, base, a.plan, a.max_list, tuple(x.strip().upper() for x in a.forms.split(",") if x.strip()))
    print("\n".join(lines))
    if a.json:
        Path(a.json).write_text(json.dumps({"lines": lines, "counts": counts(lines)}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
