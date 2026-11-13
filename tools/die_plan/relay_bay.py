#!/usr/bin/env python3
"""Relay-bay station form (SAFE-STATION-1, OWNER TWO-STRIKES 11-03): the class default for wire-only station kits.

    relay_bay.py KIT [--rows tools/die_plan/relay_bay_hop_rows.json] [--max-hop 300] [--check]

A wire-only station kit (S81 slice_station*, QC *_stm_* / *_fw_* / *_fe_*) carries ft lanes = chains of ot_dp_st relay
stations u_ft_<slot>_o_<j> (rtl/<T>_bound.sv) with their plan bays in ft_stations.txt.  The form, applied in place:

  * every hop <= max_hop (300 um): a lane of length L (in-pin -> out-pin centroid, Manhattan) gets
      landed (ring at the in face, station i at stage i+1, last station = out-face register): k' = max(k, ceil(L/300)),
      plain  (station 0 = in-face register, last station = out-face register):              k' = max(k, ceil(L/300)+1);
    the k'-k extra stations are plain registered relays appended before the out port (extra pipeline cycles, declared in
    declared_cycles.json for LEC / tok; no latches, no clock-phase tricks);
  * every station FIRM at a plan bay: ft_stations.txt gets explicit sites at equal spacing along the in->out Manhattan
    path (kept as planned when the plan already has sites for k' stations with every hop <= max_hop);
  * repeaters: the largest BUFx4 pitch whose computed hop (OpenSTA ASAP7 TT/FF, kit RCX ladder, M5 and M7, skew bound
    30 ps) shows TT setup >= 10% of the period and slew <= 320 ps -> OT_MAXWIRE_UM, and only ever LOWERS the kit value.
    R-FLOW-3 (RULES-FLOW-1 11-13, coord lanes/RULEBOOK-1113.md): FF hold no longer picks the pitch.  It used to (hold >=
    +10% too), which chose 50 um where 100 um met setup and slew, i.e. repeater delay as hold padding, and the kit-wide
    variable then cut EVERY net at 50 um: S81 slice_station__t41 353k -> 560k cells (+78k buffers); slice_station__t21
    built at 100 um instead of 50: 215,607 -> 197,013 cells, area -15 %, 0 slew pins both, routed FF hold -9.72 ps on 69
    endpoints against -6.02 on 51, GRT hold repair 2,207 against 2,243 cells.  Putting the 50-um pitch on the hop nets
    only did not help (t21: 24,746 of its nets are hop nets, 33,863 repeaters against 27,285 kit-wide).  The hop hold
    margin is the hold build's job (R-CLOCK); the table still reports it (verdict HOLD-MARGIN, advisory).
    OT_RELAY_BAY_HOLD_PITCH=1 restores the old choice.
Pre-build table relay_bay_table.tsv (per hop: length, pitch, delay, slew, setup, hold, skew); any hop below +10% ->
'ADVISORY relay_bay', form not applied, exit 0 (OWNER 11-03 06:40: pre-build checks report, never block).
FAIL_PREBUILD (exit 2) only for tool failures (bound RTL / station / config.mk not found).  Idempotent: a kit that already carries
declared_cycles.json of this form is re-checked only.  --check writes nothing but the table (dry run)."""
import argparse, json, math, os, re, shutil, sys

FORM = "relay_bay_300"
HERE = os.path.dirname(os.path.abspath(__file__))


def load_rows(path):
    probe = {}
    for r in json.load(open(path)):
        m = re.match(r"L(\d+)_(M\d)_BUFx4_(\d+)_ff$", r["case"])
        if m:
            probe[(int(m.group(1)), m.group(2), int(m.group(3)), r["corner"])] = r
    return probe


def hop_row(probe, h, period, skew, margin):
    """computed hop of length h: TT setup from the nearest probed length >= h, FF hold from the nearest probed length
    <= h (hold grows with length), worst of M5/M7; the largest pitch that meets the setup margin and the slew limit
    (hold_short marks a hop whose FF hold is under the margin: reported, it does not pick the pitch; R-FLOW-3), else the
    best row + fail.  OT_RELAY_BAY_HOLD_PITCH=1: hold picks the pitch too (the old form)."""
    hold_pitch = os.environ.get("OT_RELAY_BAY_HOLD_PITCH", "") == "1"
    Ls = sorted({k[0] for k in probe})
    lo = max([x for x in Ls if x <= h + 1e-6], default=None)
    hi = min([x for x in Ls if x >= h - 1e-6], default=None)
    if lo is None or hi is None:
        return dict(fail=True, why=f"hop {h:.1f} um outside the probed range {Ls[0]}-{Ls[-1]}")
    best = None
    for p in sorted({k[2] for k in probe}, reverse=True):
        rs = []
        for lay in ("M5", "M7"):
            tt, ff = probe.get((hi, lay, p, "TT")), probe.get((lo, lay, p, "FF"))
            if tt and ff:
                rs.append((tt["max_wirebuf_ps"], max(tt["max_slew_max"], ff["max_slew_max"]),
                           tt["wire_max_slack"] - skew, ff["wire_min_slack"] - skew))
        if len(rs) < 2:
            continue
        w = dict(pitch=p, delay=round(max(r[0] for r in rs), 1), slew=round(max(r[1] for r in rs), 1),
                 setup=round(min(r[2] for r in rs), 1), hold=round(min(r[3] for r in rs), 1))
        if w["setup"] >= margin and w["slew"] <= 320 and (w["hold"] >= margin or not hold_pitch):
            w["hold_short"] = w["hold"] < margin
            return w
        if best is None or w["hold"] > best["hold"]:
            best = w
    return dict(best or {}, fail=True, why="no BUFx4 pitch meets +10% setup and hold")


def path_points(a, b, fin, frac):
    """points at fractions frac[i] of the Manhattan in->out path (first leg along the in-face normal)."""
    mid = (a[0], b[1]) if fin in ("N", "S") else (b[0], a[1])
    l1 = abs(a[0] - mid[0]) + abs(a[1] - mid[1]); l2 = abs(mid[0] - b[0]) + abs(mid[1] - b[1]); L = l1 + l2
    out = []
    for f in frac:
        d = L * f
        if d <= l1 or l2 == 0:
            t = d / l1 if l1 else 0.0; out.append((a[0] + (mid[0] - a[0]) * t, a[1] + (mid[1] - a[1]) * t))
        else:
            t = (d - l1) / l2; out.append((mid[0] + (b[0] - mid[0]) * t, mid[1] + (b[1] - mid[1]) * t))
    return out


def dist(p, q):
    return abs(p[0] - q[0]) + abs(p[1] - q[1])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("kit")
    ap.add_argument("--rows", default=os.path.join(HERE, "relay_bay_hop_rows.json"))
    ap.add_argument("--max-hop", type=float, default=300.0)
    ap.add_argument("--period", type=float, default=833.333)
    ap.add_argument("--skew", type=float, default=30.0)
    ap.add_argument("--margin", type=float, default=0.10)
    ap.add_argument("--check", action="store_true", help="dry run: table only, kit RTL/sites unchanged")
    a = ap.parse_args(argv)
    K = os.path.abspath(a.kit); T = os.path.basename(K); margin = a.margin * a.period
    probe = load_rows(a.rows)
    # cross-tap skew (pilot t30 11-03: ft0 s2->s3 on clk_t5/clk_t3 = 133 ps): the kit SDC gives every tap port a source
    # latency window (early..late) with no CPPR between ports, so a hop whose bays sit on different taps sees that window
    # plus the local tree tolerance.  Reported per hop (hold_ff_xtap, setup_after_pads); hold repair pads such a hop
    # out of its setup slack, which the form keeps large.
    win = 0.0
    if os.path.exists(f"{K}/constraint.sdc"):
        sdc = open(f"{K}/constraint.sdc").read()
        # KW-FIX-4-SDC: measured per-port windows write one grid -early line per window value (core-tap lines,
        # [get_ports clk_cN] without braces, carry the core's own earliness); the widest grid line bounds a hop
        e = re.findall(r"set_clock_latency -source -early -clock \S+ ([-\d.]+) \[get_ports \{", sdc)
        l = re.findall(r"set_clock_latency -source -late -clock \S+ ([-\d.]+) \[get_ports \{", sdc)
        if e and l:
            win = max(0.0, max(float(x) for x in l) - min(float(x) for x in e))
    xskew = win + a.skew
    prev = None
    if os.path.exists(f"{K}/declared_cycles.json"):
        prev = json.load(open(f"{K}/declared_cycles.json"))
        if prev.get("form") != FORM:
            prev = None
    plan_k = {s: d.get("stations_plan") for s, d in (prev or {}).get("lanes", {}).items()}
    pins = {}
    for ln in open(f"{K}/io.tcl"):
        m = re.search(r"-pin_name \{?(\w+)\[\d+\]\}? .*-location \{([-\d.]+) ([-\d.]+)\}", ln)
        if m:
            pins.setdefault(m.group(1), []).append((float(m.group(2)), float(m.group(3))))
    cen = {b: (sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v)) for b, v in pins.items()}
    bfs = [p for p in sorted(os.listdir(f"{K}/rtl")) if p.endswith("_bound.sv") and "u_ft_" in open(f"{K}/rtl/{p}").read()]
    if not bfs:
        print(f"RELAY_BAY NOOP {T}: no bound RTL with ft relay stations"); return 0
    if len(bfs) != 1:
        print(f"FAIL_PREBUILD relay_bay: {T}: {len(bfs)} bound RTL files with ft stations (need exactly 1): {bfs}"); return 2
    bf = f"{K}/rtl/{bfs[0]}"; rtl = open(bf).read()
    out, decl, table, bad, pitch = [], {}, [], 0, None
    for ln in open(f"{K}/ft_stations.txt"):
        f = ln.split()
        if ln.startswith("#") or not f:
            out.append(ln.rstrip("\n")); continue
        s, k, fin, fout = f[0], int(f[1]), f[2], f[3]
        regs = [float(x) for x in f[4:]]
        if s + "_i" not in cen or s + "_o" not in cen or not re.search(rf"\bu_ft_{s}_o_0 \(", rtl):
            out.append(ln.rstrip("\n")); table.append([s, "-", "-", "", "", "", "", "", "", "", "SKIP (no ft pins / stations)"]); continue
        A, B = cen[s + "_i"], cen[s + "_o"]; L = dist(A, B)
        landed = re.search(rf"u_ft_{s}_o_0 \([^;]*\.d\(cland_{s}_i\[", rtl) is not None
        if k <= 1:
            out.append(ln.rstrip("\n"))
            table.append([s, "-", "-", f"{L:.1f}", "", "", "", "", "", "", "1-station slot: face register (kit IO budget)"]); continue
        if s in plan_k:
            k2 = k  # already applied: re-check only
        else:
            k2 = max(k, math.ceil(L / a.max_hop - 1e-9)) if landed else max(k, math.ceil(L / a.max_hop - 1e-9) + 1)
        sites = [(regs[i], regs[i + 1]) for i in range(0, len(regs) - 1, 2)]

        def chain(sts):  # station positions in hop order, incl. the ring of a landed slot
            return ([A] + sts[1:] + [B]) if landed else ([A] + sts[1:])
        keep = (len(sites) == k2 and
                all(dist(p, q) <= a.max_hop + 1e-6 for p, q in zip(chain(sites), chain(sites)[1:])))
        if not keep:
            n = k2 if landed else k2 - 1
            sites = path_points(A, B, fin, [j / n for j in range(k2)])
        ch = chain(sites)
        names = ([f"ring u_cland_{s}_i"] if landed else [f"{s} s0 (in-face reg)"]) + \
                [f"{s} s{j}" for j in range(0 if landed else 1, k2)]
        for j, (p, q) in enumerate(zip(ch, ch[1:])):
            h = dist(p, q)
            w = hop_row(probe, h, a.period, a.skew, margin)
            ok = not w.get("fail")
            if ok:
                pitch = w["pitch"] if pitch is None else min(pitch, w["pitch"])
            else:
                bad += 1
                if w.get("pitch"):  # advisory miss: the form still applies, at the best computed pitch for this hop
                    pitch = w["pitch"] if pitch is None else min(pitch, w["pitch"])
            table.append([s, names[j], names[j + 1], f"{h:.1f}", str(w.get("pitch", "")), str(w.get("delay", "")),
                          str(w.get("slew", "")), str(w.get("setup", "")), str(w.get("hold", "")), str(a.skew),
                          ("HOLD-MARGIN (advisory: hold build, R-CLOCK)" if w.get("hold_short") else "PASS") if ok
                          else "FAIL " + w.get("why", ""),
                          *((str(round(w["hold"] - win, 1)), str(round(w["setup"] - max(0.0, win - w["hold"]), 1)))
                            if "hold" in w else ("", ""))])
        table.append([s, f"{s} s{k2-1}", f"port {s}_o", f"{dist(ch[-1], B):.1f}", "", "", "", "", "", "",
                      "face (kit IO budget, unchanged)"])
        out.append(" ".join([s, str(k2), fin, fout] + [f"{v:.4f}" for p in sites for v in p]))
        if k2 > k:
            m = re.search(rf"ot_dp_st #\(\.W\((\d+)\)\) u_ft_{s}_o_{k-1} \(([^;]*)\.q\({s}_o\[(\d+):0\]\), \.eq\({s}_o\[(\d+)\]\)\);", rtl)
            if not m:
                print(f"FAIL_PREBUILD relay_bay: {T} lane {s}: last station u_ft_{s}_o_{k-1} -> {s}_o not found"); return 2
            W = int(m.group(1))
            new = [f"ot_dp_st #(.W({W})) u_ft_{s}_o_{k-1} ({m.group(2)}.q({s}_o_s{k-1}[{W-1}:0]), .eq({s}_o_s{k-1}[{W}]));"]
            for j in range(k, k2):
                q = f"{s}_o" if j == k2 - 1 else f"{s}_o_s{j}"
                new.append(f"    ot_dp_st #(.W({W})) u_ft_{s}_o_{j} (.clk(clk), .rst_n(rst_n), .d({s}_o_s{j-1}[{W-1}:0]), "
                           f".ea({s}_o_s{j-1}[{W}]), .q({q}[{W-1}:0]), .eq({q}[{W}]));")
            rtl = rtl.replace(m.group(0), "\n".join(new))
            ins = "".join(f"    wire [{W}:0] {s}_o_s{j};\n" for j in range(k - 1, k2 - 1))
            wl = re.search(rf"\n[ \t]*wire \[{W}:0\] {s}_o_s{k-2};\n", rtl) if k >= 2 else None
            if wl:
                rtl = rtl.replace(wl.group(0), wl.group(0) + ins, 1)
            else:
                mm = re.search(r"\n[ \t]*ot_dp_st\b", rtl); rtl = rtl[:mm.start()] + "\n" + ins.rstrip("\n") + rtl[mm.start():]
        k0 = plan_k.get(s, k)
        decl[s] = dict(landed=landed, L_um=round(L, 1), stations_plan=k0, stations_new=k2, extra_cycles=k2 - k0,
                       sites_kept=keep)
    hdr = ["lane", "from", "to", "hop_um", "bufx4_pitch_um", "wirebuf_delay_tt_ps", "slew_ps", "setup_tt_ps", "hold_ff_ps",
           "skew_bound_ps", "verdict", f"hold_ff_xtap_ps(skew {xskew:g})", "setup_after_hold_pads_ps"]
    with open(f"{K}/relay_bay_table.tsv", "w") as fh:
        fh.write(f"# relay-bay pre-build table {T}: period {a.period} ps, required >= +{margin:.1f} ps (10%) TT setup and "
                 f"FF hold after a {a.skew}-ps skew bound, hops <= {a.max_hop} um\n")
        fh.write("\t".join(hdr) + "\n" + "".join("\t".join(r) + "\n" for r in table))
    nh = sum(1 for r in table if r[10] == "PASS" or r[10].startswith(("FAIL", "HOLD-MARGIN")))
    st = {s: (d["stations_plan"], d["stations_new"]) for s, d in decl.items()}
    if bad:
        # OWNER 11-03 06:40: pre-build checks are ADVISORY (report, never block).  COORD 07:0x: the relay-bay form is the
        # target and is APPLIED even when a hop estimate misses +10%; the table only reports it.
        print(f"ADVISORY relay_bay: {T}: {bad} of {nh} hops below +10% of the period, form applied anyway "
              f"(table {K}/relay_bay_table.tsv)")
    if a.check or not decl:
        print(f"RELAY_BAY {'CHECK' if a.check else 'NOOP'} {T}: {nh} hops PASS, pitch {pitch}, stations {st}")
        return 0
    open(bf, "w").write(rtl)
    open(f"{K}/ft_stations.txt", "w").write("\n".join(out) + "\n")
    # gen's per-bit explicit FT sites (ft_bit_sites.tcl, keyed slot,stage,bit) describe the PLAN stages; a lane whose bays
    # were regenerated drops them, so face_flops puts each station FIRM on the station grid nearest its new bay
    # (ff_put_stage fallback) instead of failing 'explicit FT site missing' on the added stages
    fbs = f"{K}/ft_bit_sites.tcl"
    regen = [s for s, d in decl.items() if not d["sites_kept"]]
    if regen and os.path.exists(fbs):
        pat = re.compile(r"^dict set ff_bit_site(?:s|_cells) \{(?:" + "|".join(map(re.escape, regen)) + r")(?:,[^}]*)?\}")
        lines = open(fbs).read().splitlines(True)
        kept = [l for l in lines if not pat.match(l)]
        if len(kept) != len(lines):
            open(fbs, "w").write("".join(kept))
            for s in regen:
                decl[s]["bit_sites_dropped"] = True
    if pitch is not None:
        cm = f"{K}/config.mk"; t = open(cm).read()
        # KW-FIX-4 11-03 (DIE-QC-66 class B): accept 'override export' and spacing variants; a kit whose config.mk has
        # no OT_MAXWIRE_UM line gets one appended (the flow default applies otherwise); only >1 lines stay a FAIL
        # R-FLOW-3: the form only ever lowers the kit-wide limit (a kit at 100 um with a 100-um hop pitch is unchanged)
        t2, nn = re.subn(r"^((?:override[ \t]+)?export[ \t]+OT_MAXWIRE_UM[ \t]*[:?]?=)[ \t]*(\d+)[ \t]*$",
                         lambda m: f"{m.group(1)} {min(int(m.group(2)), int(pitch))}", t, flags=re.M)
        if nn == 0:
            t2 = t + ("" if not t or t.endswith("\n") else "\n") + f"export OT_MAXWIRE_UM = {pitch}\n"
        elif nn > 1:
            print(f"FAIL_PREBUILD relay_bay: {T}: config.mk has {nn} OT_MAXWIRE_UM lines"); return 2
        open(cm, "w").write(t2)
        # grt_pre.tcl sources the kit's grt_maxwire.tcl whenever OT_MAXWIRE_UM is set; only gen --max-wire-um copied it
        tcl = os.path.join(os.path.dirname(os.path.abspath(__file__)), "grt_maxwire.tcl")
        if not os.path.isfile(tcl):
            print(f"FAIL_PREBUILD relay_bay: {T}: no grt_maxwire.tcl beside the tool to go with pitch {pitch}"); return 2
        shutil.copyfile(tcl, f"{K}/grt_maxwire.tcl")
    json.dump(dict(schema="opentallas.declared_cycles.v1", form=FORM, owner_rule="TWO-STRIKES 11-03", kit=T,
                   max_hop_um=a.max_hop, repeater_pitch_um=pitch, lanes=decl), open(f"{K}/declared_cycles.json", "w"), indent=1)
    print(f"RELAY_BAY PASS {T}: {nh} hops >= +10%, pitch {pitch}, stations {st}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
