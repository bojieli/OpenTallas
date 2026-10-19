#!/usr/bin/env python3
"""QXPQ-FIX/FSTA (10-18): frame-region STA netlist for the q-element clock compensation check.

Builds, from a generated S81-DV frame master (rtl/dsrom_sys/s81_dv/frame*/col_*.sv), a flat structural netlist that
keeps every q element (ot_v41_rom_elem_q_qxpq_w10) and every instance of its linked neighbour types (dsfd_qbank_S,
dsfd_qbank_N, ot_s81_cfg7_seq) as black-box ETM lib cells, with the frame's real inter-pin wiring between them.
Every net that also touches a non-modelled instance or a frame port is cut to a top-level port and left
unconstrained, so only child<->child register paths are timed (the q<->neighbour pin groups this check is about).

Wire model: per net a star RC from the driver pin to each sink pin, Manhattan length from the frame floorplan
(cluster_extract boxes of the c26l column cluster this frame master was cut from + LEF pin positions, R0/MY orient),
ASAP7 ORFS signal RC (set_wire_rc -signal: 0.0265684 kohm/um, 0.165790 fF/um). Written as SPEF.
Also emits a zero-wire variant (no SPEF) for the hold bound.

usage: fsta_build.py FRAME_SV CLUSTER_JSON_GZ SOURCE_V_GZ OUTDIR QBANK_S_VIEWDIR
"""
import gzip, json, os, re, sys, hashlib

R_PER_UM = 0.0265684   # kohm/um (ORFS asap7 setRC.tcl, set_wire_rc -signal)
C_PER_UM = 0.165790    # fF/um

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), *[".."] * 5))
KEEP = {
    "ot_v41_rom_elem_q_qxpq_w10": "physical/s81_die_views/q_elem_qs5f_rstp",
    "dsfd_qbank_N": "physical/ref_tile/s81fill2_qbank_n/views/dsfd_qbank_N",
    "dsfd_qbank_S": None,  # argv
    "ot_s81_cfg7_seq": "physical/ref_tile/s81coll_cfg7_seq_pr/views/ot_s81_cfg7_seq",
}
CLKPIN = {"ot_v41_rom_elem_q_qxpq_w10": "clk", "dsfd_qbank_N": "ck", "dsfd_qbank_S": "ck", "ot_s81_cfg7_seq": "clk"}


def parse_lef(path, macro):
    txt = open(path).read()
    m = re.search(r"MACRO\s+%s\b(.*?)END\s+%s\b" % (re.escape(macro), re.escape(macro)), txt, re.S)
    body = m.group(1)
    w, h = map(float, re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", body).groups())
    pins = {}
    for pm in re.finditer(r"PIN\s+(\S+)(.*?)END\s+\1(?=\s)", body, re.S):
        name, pb = pm.group(1), pm.group(2)
        d = re.search(r"DIRECTION\s+(\w+)", pb).group(1)
        r = re.search(r"RECT\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)", pb)
        xy = ((float(r.group(1)) + float(r.group(3))) / 2, (float(r.group(2)) + float(r.group(4))) / 2) if r else (w / 2, h / 2)
        pins[name] = (d, xy)
    return (w, h), pins


def port_widths(pins):
    """port base -> sorted bit indices (descending) or None for scalar"""
    out = {}
    for p in pins:
        m = re.match(r"(.+)\[(\d+)\]$", p)
        if m:
            out.setdefault(m.group(1), []).append(int(m.group(2)))
        else:
            out[p] = None
    return {k: (sorted(v, reverse=True) if v is not None else None) for k, v in out.items()}


INST_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s+(?:#\((.*?)\)\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\((\..*)\);\s*$")


def split_top(s, sep=","):
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch in "({":
            depth += 1
        elif ch in ")}":
            depth -= 1
        if ch == sep and depth == 0:
            out.append(cur); cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return out


def expr_bits(e):
    e = e.strip()
    if e.startswith("{"):
        bits = []
        for t in split_top(e[1:-1]):
            bits += expr_bits(t)
        return bits
    m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\[(\d+):(\d+)\]$", e)
    if m:
        a, b = int(m.group(2)), int(m.group(3))
        rng = range(a, b - 1, -1) if a >= b else range(a, b + 1)
        return ["%s[%d]" % (m.group(1), i) for i in rng]
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*(\[\d+\])?$", e):
        return [e]
    if e == "":
        return []
    raise ValueError("unsupported port expression %r" % e[:80])


def parse_instances(lines, types):
    insts = []
    for ln in lines:
        m = INST_RE.match(ln)
        if not m or m.group(1) not in types:
            continue
        conns = {}
        for c in split_top(m.group(4)):
            c = c.strip()
            pm = re.match(r"^\.([A-Za-z_][A-Za-z0-9_]*)\((.*)\)$", c, re.S)
            conns[pm.group(1)] = expr_bits(pm.group(2))
        insts.append({"type": m.group(1), "name": m.group(3), "conns": conns})
    return insts


def main():
    frame_sv, cl_json, src_v, outdir, qbs_view = sys.argv[1:6]
    KEEP["dsfd_qbank_S"] = os.path.relpath(os.path.abspath(qbs_view), REPO)
    os.makedirs(outdir, exist_ok=True)
    views = {}
    for t, d in KEEP.items():
        (w, h), pins = parse_lef(os.path.join(REPO, d, t + ".lef") if os.path.exists(os.path.join(REPO, d, t + ".lef"))
                                  else [os.path.join(REPO, d, f) for f in os.listdir(os.path.join(REPO, d)) if f.endswith(".lef")][0], t)
        views[t] = {"dir": d, "size": (w, h), "pins": pins, "ports": port_widths(pins)}
    fl = open(frame_sv).read().splitlines()
    top = re.search(r"^module\s+(\S+)", "\n".join(fl), re.M).group(1)
    insts = parse_instances(fl, set(KEEP))
    # pin-level connectivity
    pinmap = {}  # (inst, pinbit) -> net
    for ins in insts:
        ports = views[ins["type"]]["ports"]
        for p, bits in ins["conns"].items():
            if p not in ports:
                raise SystemExit("%s.%s not in LEF of %s" % (ins["name"], p, ins["type"]))
            idx = ports[p]
            if idx is None:
                assert len(bits) == 1, (ins["name"], p, len(bits)); pinmap[(ins["name"], p)] = bits[0]
            else:
                assert len(bits) == len(idx), (ins["name"], p, len(bits), len(idx))
                for i, b in zip(idx, bits):
                    pinmap[(ins["name"], "%s[%d]" % (p, i))] = b
    # nets touched by non-kept instances or the frame ports: every net name that appears outside the kept instances
    kept_lines = set(i["name"] for i in insts)
    outside = set()
    for ln in fl:
        m = INST_RE.match(ln)
        if m and m.group(3) in kept_lines:
            continue
        if m:
            for c in split_top(m.group(4)):
                pm = re.match(r"^\.([A-Za-z_][A-Za-z0-9_]*)\((.*)\)$", c.strip(), re.S)
                try:
                    outside.update(expr_bits(pm.group(2)))
                except ValueError:
                    pass
    port_decl = re.findall(r"^\s*(input|output)\s+wire\s+(?:\[(\d+):(\d+)\]\s+)?(\w+);", "\n".join(fl), re.M)
    frame_ports = set()
    for _, a, b, n in port_decl:
        if a:
            frame_ports.update("%s[%d]" % (n, i) for i in range(int(b), int(a) + 1))
        else:
            frame_ports.add(n)
    # placement: map frame instance -> source cluster child by net-signature overlap
    cl = json.load(gzip.open(cl_json))
    srcl = gzip.open(src_v, "rt").read().splitlines()
    # restrict source parse to the module this frame came from
    want = {"col_h9": "dsfd_column_h9_v10", "col_h10": "dsfd_column_h10a_v17"}
    base = re.sub(r"_l4$", "", top)
    src_mod_name = want[base]
    cdef = [c for c in cl["clusters"] if c["master"] == src_mod_name][0]
    boxes = {ch["instance"]: ch for ch in cdef["children"]}
    s0 = next(i for i, l in enumerate(srcl) if re.match(r"^module\s+%s\b" % src_mod_name, l))
    s1 = next(i for i in range(s0, len(srcl)) if srcl[i].startswith("endmodule"))
    sinsts = parse_instances(srcl[s0:s1], set(KEEP))
    sig = {}
    for si in sinsts:
        sig.setdefault(si["type"], []).append((si["name"], set(b for v in si["conns"].values() for b in v if b != "clk")))
    place = {}
    for ins in insts:
        mine = set(b for v in ins["conns"].values() for b in v if b != "clk")
        best = max(sig[ins["type"]], key=lambda s: len(mine & s[1]))
        ov = len(mine & best[1]) / max(1, len(mine))
        ch = boxes[best[0]]
        assert ch["master"] == ins["type"]
        place[ins["name"]] = {"src": best[0], "overlap": round(ov, 3), "box": ch["box_um"], "orient": ch["orient"]}
    for n, p in place.items():
        if p["overlap"] < 0.5:
            print("WARN low placement match", n, p)

    def pin_xy(inst, pin):
        t = next(i["type"] for i in insts if i["name"] == inst)
        x0, y0, w, h = place[inst]["box"]
        px, py = views[t]["pins"][pin][1]
        if place[inst]["orient"] == "MY":
            px = views[t]["size"][0] - px
        elif place[inst]["orient"] != "R0":
            raise SystemExit("orient " + place[inst]["orient"])
        return (x0 + px, y0 + py)

    itype = {i["name"]: i["type"] for i in insts}
    nets = {}
    for (inst, pin), net in pinmap.items():
        nets.setdefault(net, []).append((inst, pin))
    def clkpin(t):
        cp = CLKPIN[t]
        return cp if views[t]["ports"][cp] is None else "%s[%d]" % (cp, views[t]["ports"][cp][0])
    clocknets = set(pinmap[(i["name"], clkpin(i["type"]))] for i in insts)
    vlines, ports, wires = [], [], []
    spef_nets = []
    meta_nets = []
    internal = 0
    for net, conns in sorted(nets.items()):
        drivers = [(i, p) for i, p in conns if views[itype[i]]["pins"][p][0] == "OUTPUT"]
        sinks = [(i, p) for i, p in conns if views[itype[i]]["pins"][p][0] != "OUTPUT"]
        is_port = net in clocknets or net in outside or net in frame_ports or not drivers or not sinks
        if is_port:
            ports.append((net, "input" if not drivers or net in clocknets else "output"))
        else:
            wires.append(net)
            internal += 1
        if drivers and sinks and net not in clocknets:
            assert len(drivers) == 1, (net, drivers)
            d = drivers[0]
            dx, dy = pin_xy(*d)
            segs = []
            for s in sinks:
                sx, sy = pin_xy(*s)
                segs.append((s, abs(sx - dx) + abs(sy - dy)))
            spef_nets.append((net, d, segs))
            meta_nets.append({"net": net, "drv": "%s/%s" % d, "sinks": ["%s/%s" % s for s, _ in segs],
                              "len_um": [round(L, 1) for _, L in segs], "cut_to_port": is_port})
    esc0 = lambda n: ("\\" + n + " ") if "[" in n else n
    # the frame clock net is split into two top ports so the frame trunk is a per-port source latency:
    # clk_q = region root (q clock pins), clk_n = shared trunk (every neighbour clock pin)
    clkpins = {(i["name"], clkpin(i["type"])): ("clk_q" if i["type"] == "ot_v41_rom_elem_q_qxpq_w10" else "clk_n") for i in insts}
    ports = [(p, d) for p, d in ports if p not in clocknets] + [("clk_q", "input"), ("clk_n", "input")]
    esc = esc0
    with open(os.path.join(outdir, "netlist.v"), "w") as f:
        f.write("// generated by fsta_build.py from %s (sha256 %s)\n" % (os.path.relpath(frame_sv, REPO), hashlib.sha256(open(frame_sv, 'rb').read()).hexdigest()))
        f.write("module fsta_top (%s);\n" % ", ".join(esc(p) for p, _ in ports))
        for p, d in ports:
            f.write("  %s %s;\n" % (d, esc(p)))
        for w in wires:
            f.write("  wire %s;\n" % esc(w))
        for ins in insts:
            ports_t = views[ins["type"]]["ports"]
            cs = []
            for p in ins["conns"]:
                idx = ports_t[p]
                pn = lambda b: clkpins.get((ins["name"], b)) or esc(pinmap[(ins["name"], b)])
                if idx is None:
                    cs.append(".%s(%s)" % (p, pn(p)))
                else:
                    cs.append(".%s({%s})" % (p, ", ".join(pn("%s[%d]" % (p, i)) for i in idx)))
            f.write("  %s %s (%s);\n" % (ins["type"], ins["name"], ", ".join(cs)))
        f.write("endmodule\n")
    # SPEF (star RC); names escaped per SPEF: brackets kept via *NAME_MAP-free direct names with \[ \]
    sp = lambda s: s  # *BUS_DELIMITER [ ]: bus bits written plain
    with open(os.path.join(outdir, "wire.spef"), "w") as f:
        f.write('*SPEF "IEEE 1481-1998"\n*DESIGN "fsta_top"\n*DATE "2026-10-18"\n*VENDOR "OpenTallas"\n*PROGRAM "fsta_build.py"\n*VERSION "1"\n'
                '*DESIGN_FLOW "PIN_CAP NONE"\n*DIVIDER /\n*DELIMITER :\n*BUS_DELIMITER [ ]\n*T_UNIT 1 PS\n*C_UNIT 1 FF\n*R_UNIT 1 KOHM\n*L_UNIT 1 HENRY\n\n')
        for net, d, segs in spef_nets:
            tot = sum(L for _, L in segs) * C_PER_UM + 1e-6
            f.write("*D_NET %s %.6f\n*CONN\n*I %s:%s O\n" % (sp(net), tot, d[0], sp(d[1])))
            for s, _ in segs:
                f.write("*I %s:%s I\n" % (s[0], sp(s[1])))
            f.write("*CAP\n")
            k = 1
            drv = "%s:%s" % (d[0], sp(d[1]))
            f.write("%d %s %.6f\n" % (k, drv, 1e-6)); k += 1
            for s, L in segs:
                f.write("%d %s:%s %.6f\n" % (k, s[0], sp(s[1]), L * C_PER_UM)); k += 1
            f.write("*RES\n")
            k = 1
            for s, L in segs:
                f.write("%d %s %s:%s %.6f\n" % (k, drv, s[0], sp(s[1]), max(L * R_PER_UM, 1e-4))); k += 1
            f.write("*END\n\n")
    meta = {
        "frame": os.path.relpath(frame_sv, REPO), "frame_sha256": hashlib.sha256(open(frame_sv, 'rb').read()).hexdigest(), "top": top,
        "views": {t: v["dir"] for t, v in views.items()},
        "instances": {i["name"]: {"type": i["type"], **place[i["name"]]} for i in insts},
        "clock_pins": {i["name"]: "%s/%s" % (i["name"], clkpin(i["type"])) for i in insts},
        "clock_nets": sorted(clocknets), "clock_ports": {"clk_q": "q clock pins (region root)", "clk_n": "neighbour clock pins (shared trunk)"}, "internal_nets": internal, "ports": len(ports),
        "timed_nets": meta_nets,
        "wire_model": {"r_kohm_per_um": R_PER_UM, "c_ff_per_um": C_PER_UM, "topology": "star from driver pin, Manhattan, unbuffered"},
    }
    json.dump(meta, open(os.path.join(outdir, "meta.json"), "w"), indent=1)
    print("top", top, "insts", len(insts), "internal nets", internal, "ports", len(ports), "timed nets", len(meta_nets),
          "max len", max((max(n["len_um"]) for n in meta_nets), default=0))


if __name__ == "__main__":
    main()
