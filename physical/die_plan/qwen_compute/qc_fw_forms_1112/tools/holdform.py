#!/usr/bin/env python3
"""DIE-QC-97 fwderive H1/H2 (11-11): structural hold forms from a MEASURED min-delay STA of a pilot (no margin).

Input: OpenSTA `report_checks -path_delay min -corner C -format full_clock` of every violating endpoint, one report
per corner (h2.tcl on the pilot's 4_cts or 5_1_grt), and the pilot's AUTO-GEOM dump (register sites).

 H1  zero-logic seam hold (input port -> u_bin_<bus> / ft slot input): HOLDFORM-1 bus "hold_hb4" N =
     ceil(FF deficit / hb4_FF) (signoff.py gates hold at FF only; TT deficits are reported), hb4_c = the smallest HB4xp67_ASAP7_75t_R arc of that corner's
     Liberty (FF 33.8 ps, TT 45.7 ps at 5 ps / 0.36 fF), no hold margin (owner 11-02), cap 8 (schema).
     Output seam (u_bout_<bus> -> port, out_min): reported only.  gen_rtl HOLDFORM-1 pads in-boundary flops only and
     the v2 chain hold form (hold_patch.py) has no output pad, so no plan field exists for it.
 H2  cross-tap reg-reg hold (launch and capture on different tap ports: the per-type tap_window early source latency
     has no common path, CPPR gives no credit; same-tap pairs get it): clock.tap_pair_affinity (QC-TYPES-6, kit
     tap_pair_affinity.tcl) sized to put the measured violating pairs on one tap:
       pair_um  = smallest 10-um step covering every violating cross-tap pair that is pairable, capped at tap_radius_um
       depth    = max combinational depth of those pairs (cap 4)
       max_group / merge_max = largest coherent component of those pairs (union-find), cap min(1200, tap_max_sinks)
     not pairable (reported as residual): reset relays / synchronisers (tap_pair_affinity.tcl never moves them),
     named delay-chain bits (tap_chain_affinity owns them), pairs farther than tap_radius_um, depth > 4.
     The census after is the kit planner's coherent-pair outcome assuming every pairable component fits one tap
     (taps already at cap donate only: not modelled).
"""
import collections, json, math, re, sys
from pathlib import Path

HB4_MIN_PS = {"bc": 33.8167, "ff": 33.8167, "tc": 45.6555, "tt": 45.6555}   # asap7 INVBUF RVT FF / TT, 5 ps, 0.36 fF
HB4_MAX_N = 8
HOLD_GATE = ("bc", "ff")      # signoff.py hold_ff: hold is gated at FF only (TT hold reported, never sized on)
NOPAIR = re.compile(r"(^|[/.])(u_rsync_t\d+|u_rst_root|u_rst_in|u_run_root|u_run_in|u_[rs]rl_\d+(_[rgb])?)[/.]")
CHAIN = re.compile(r"(u_d\d+_|u_lpad_|u_r8b_strap_|u_pd\d+_)")


def parse_report(path, corner):
    """[{sp, ep, sl, corner, sp_port, ep_port, ltap, ctap, depth, group}] of a full_clock min report"""
    txt = Path(path).read_text()
    out = []
    for blk in txt.split("Startpoint: ")[1:]:
        lines = blk.split("\n")
        sp = lines[0].split()[0]
        m = re.search(r"Endpoint: (\S+)\s*(?:\n\s*)?\(([^)]*)\)", blk)
        if not m:
            continue
        ep, ekind = m.group(1), m.group(2)
        s = re.search(r"(-?[\d.]+)\s+slack", blk)
        if not s:
            continue
        sl = float(s.group(1))
        taps = re.findall(r"\^ (clk_t\d+) \(in\)", blk)
        ia = next((i for i, l in enumerate(lines) if "data arrival time" in l), len(lines))
        ld = lines[:ia]
        k0 = next((i for i, l in enumerate(ld) if (sp + "/CLK ") in l or (sp + " (in)") in l), 0)
        pins = [l for l in ld[k0 + 1:] if re.search(r"\S \(\w+\)\s*$", l)]
        port_sp = "(input port" in "\n".join(lines[:2])
        cells = pins[:-1] if port_sp else pins[1:-1]
        out.append(dict(sp=sp, ep=ep, sl=sl, corner=corner, sp_port=port_sp, ep_port="output port" in ekind,
                        ltap=taps[0] if port_sp is False and taps else None,
                        ctap=taps[-1] if taps and "output port" not in ekind else None,
                        depth=len(cells), group="asynchronous" if "Path Group: asynchronous" in blk else "clk"))
    return out


def bus_of(name):
    """port name -> bus; instance pin -> (u_bin_<bus>|u_bout_<bus>|other instance group)"""
    n = name.replace("\\", "").replace("u_bound.", "")
    return re.split(r"\[|/q|\$|/D|/eq", n)[0]


def inst_of(name):
    return name.replace("\\", "")


def h1(t, rows, rep):
    width = {b["name"]: int(b["width"]) for b in t["buses"]}
    bdir = {b["name"]: b.get("dir") for b in t["buses"]}
    fts = {s["name"]: s for s in t.get("ft_slots", [])}
    defi = collections.defaultdict(dict)                  # bus -> corner -> worst deficit
    outd = collections.defaultdict(dict)
    for r in rows:
        if r["sl"] >= 0:
            continue
        if r["sp_port"]:
            b = bus_of(r["sp"])
            defi[b][r["corner"]] = max(defi[b].get(r["corner"], 0.0), -r["sl"])
        elif r["ep_port"]:
            b = bus_of(r["ep"])
            outd[b][r["corner"]] = max(outd[b].get(r["corner"], 0.0), -r["sl"])
    res = dict(hb4_min_ps={c: HB4_MIN_PS[c] for c in sorted({r["corner"] for r in rows})}, buses={}, ft={}, out_report={}, cells=0)
    gate = lambda dc: {c: d for c, d in dc.items() if c in HOLD_GATE} or None
    for b, dc in sorted(defi.items()):
        g = gate(dc)
        if g is None:
            res["buses"][b] = dict(deficit_ps={c: round(d, 2) for c, d in dc.items()}, n=0, note="no FF deficit (sign-off hold is FF only)")
            continue
        n = max(math.ceil(d / HB4_MIN_PS[c]) for c, d in g.items())
        row = dict(deficit_ps={c: round(d, 2) for c, d in dc.items()}, n_needed=n, n=min(n, HB4_MAX_N))
        if n > HB4_MAX_N:
            row["short_ps"] = round(max(d - HB4_MAX_N * HB4_MIN_PS[c] for c, d in g.items()), 1)
        if bdir.get(b) == "in":
            rec = next(x for x in t["buses"] if x["name"] == b)
            rec["hold_hb4"] = max(int(rec.get("hold_hb4") or 0), row["n"])
            row.update(width=width[b], cells=row["n"] * (width[b] + 1))
            res["buses"][b] = row
        elif b in fts or (b.endswith("_i") and b[:-2] in fts):
            b = b if b in fts else b[:-2]
            fts[b]["hold_hb4"] = max(int(fts[b].get("hold_hb4") or 0), row["n"])
            row.update(width=int(fts[b]["width"]), cells=row["n"] * int(fts[b]["width"]))
            res["ft"][b] = row
        else:
            row["skipped"] = "not an in-bus or ft slot of the type"
            res["buses"][b] = row
        res["cells"] += row.get("cells", 0)
    for b, dc in sorted(outd.items()):
        g = gate(dc) or {}
        n = max([math.ceil(d / HB4_MIN_PS[c]) for c, d in g.items()] or [0])
        res["out_report"][b] = dict(deficit_ps={c: round(d, 2) for c, d in dc.items()}, n_would_be=n,
                                    width=width.get(b), note="no output pad form (HOLDFORM-1 in-boundary only)")
    rep["H1"] = res


def h2(t, rows, D, rep):
    ck = t["clock"]
    rad = float(ck.get("tap_radius_um", 200.0)); cap = min(1200, int(ck.get("tap_max_sinks", 1200)))
    xy = {}
    for c in (D.cells.values() if isinstance(D.cells, dict) else D.cells):
        if len(c) < 7:
            continue
        xy[c[6].replace("\\", "")] = ((float(c[2]) + float(c[4])) / 2, (float(c[3]) + float(c[5])) / 2)
    cross, same = [], 0
    best = {}
    for r in rows:
        if r["sp_port"] or r["ep_port"] or r["sl"] >= 0 or not r["ltap"] or not r["ctap"]:
            continue
        if r["ltap"] == r["ctap"]:
            same += 1
            continue
        k = (r["sp"], r["ep"])
        if k not in best or r["sl"] < best[k]["sl"]:
            best[k] = r
    for (sp, ep), r in best.items():
        a, b = inst_of(sp), inst_of(ep)
        pa, pb = xy.get(a), xy.get(b)
        dist = None if pa is None or pb is None else abs(pa[0] - pb[0]) + abs(pa[1] - pb[1])
        why = None
        if NOPAIR.search("/" + a + "/") or NOPAIR.search("/" + b + "/"):
            why = "reset relay / synchroniser (kit never moves them)"
        elif CHAIN.search(a) or CHAIN.search(b):
            why = "named delay chain (tap_chain_affinity owns it)"
        elif dist is None:
            why = "register not in geom"
        elif dist > rad:
            why = f"farther than tap_radius_um {rad:g}"
        elif r["depth"] > 4:
            why = "combinational depth > 4"
        cross.append(dict(sp=sp, ep=ep, a=a, b=b, sl=r["sl"], corner=r["corner"], dist=dist, depth=r["depth"], why=why,
                          group=f"{bus_of(sp)} -> {bus_of(ep)}"))
    ok = [c for c in cross if c["why"] is None]
    par = {}
    def f(x):
        while par.setdefault(x, x) != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    for c in ok:
        par[f(c["a"])] = f(c["b"])
    size = collections.Counter(f(n) for n in {c["a"] for c in ok} | {c["b"] for c in ok})
    gmax = max(size.values()) if size else 0
    big = {k for k, v in size.items() if v > cap}
    res = dict(same_tap_violators=same, cross_tap_pairs_before=len(cross),
               worst_before=round(min((c["sl"] for c in cross), default=0.0), 2))
    if ok:
        pair_um = min(rad, math.ceil(max(c["dist"] for c in ok) / 10.0) * 10.0)
        depth = min(4, max(c["depth"] for c in ok))
        g = max(2, min(cap, gmax))
        ck["tap_pair_affinity"] = dict(radius_um=rad, max_group=g, merge_max=g, pair_um=pair_um, depth=depth)
        res["tap_pair_affinity"] = ck["tap_pair_affinity"]
    resid = [c for c in cross if c["why"] is not None or f(c["a"]) in big]
    by = collections.defaultdict(list)
    for c in resid:
        by[(c["group"], c["why"] or "component > cap")].append(c["sl"])
    res["residual_by_reason"] = dict(collections.Counter(c["why"] or "component > cap" for c in resid))
    res.update(pairable=len(ok), largest_component=gmax, components_over_cap=len(big),
               cross_tap_pairs_after=len(resid), worst_after=round(min((c["sl"] for c in resid), default=0.0), 2),
               residual_by_class=[dict(pairs=len(v), worst=round(min(v), 2), group=g, why=w)
                                  for (g, w), v in sorted(by.items(), key=lambda kv: min(kv[1]))],
               pairable_by_group={g: n for g, n in collections.Counter(c["group"] for c in ok).most_common(12)},
               dist_um_p50_p95_max=[round(sorted(c["dist"] for c in ok)[int(q * (len(ok) - 1))], 1) for q in (0.5, 0.95, 1.0)] if ok else [])
    rep["H2"] = res


def apply(t, sta_args, geom, src, rep):
    rows = []
    for s in sta_args:
        corner, path = s.split("=", 1)
        rows += parse_report(path, corner)
    rep["sta"] = dict(reports=sta_args, paths=len(rows))
    h1(t, rows, rep)
    sys.path.insert(0, str(Path(src) / "tools/autopilot"))
    import geom_rules as G
    h2(t, rows, G.Design(geom), rep)
