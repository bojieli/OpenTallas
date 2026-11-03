#!/usr/bin/env python3
"""S81-PROUTE-1 (OWNER 11-02 23:34, station parent-route pilot): dissolve the two east pure-station partitions
s_7S_x110 (slice_station__t30__clcedefe91) + s_7S_x111 (slice_station__t30__cl1653104c) into ONE parent partition
s_7S_x11p (type slice_station__p7S_x11, 1442.88 x 2453.76 at x110's origin, MY).  PILOT ONLY: writes a new plan +
kit RTL, never edits the plan of record.

    python3 proute_x11p.py plan  PLAN_IN PLAN_OUT
    python3 proute_x11p.py rtl   PLAN_OUT BOUND_X110.sv BOUND_X111.sv LIBS.f OUTDIR

plan: the shared plain seam (3 ports x111->x110 ft0/ft1, x110->x111 ft2) becomes partition-internal wire; every
outer pin keeps its die coordinate (x111 frame + 1226.88 um in y); stage counts unchanged per slot (9 = 4+5 / 4+5 /
5+4, so every lane is cycle-identical), the 9 stations re-spread evenly over the 2453.76 um column (hop <= 270 um,
METHODOLOGY 12.1e 405 um reach); clock taps, edge clocks, sink sites, landing pins and ring bands are the union of
both types (x111 names: clk -> clk_t17, clk_tK -> clk_t(17+K); cland_up_* -> cland_up_*_n).
rtl: the parent bound module = the two strict-bind bound modules instanced flat (u_s = x110, u_n = x111) with the
seam buses internal; the x111 half's synchronous reset comes from the parent arst_n through 3 registered relays
(<= 405 um hops; boot-only, no data cycle); reset_tree.tcl places both bound reset trees + the relays FIRM.
"""
import copy
import json
import sys
from pathlib import Path

T110, T111 = "slice_station__t30__clcedefe91", "slice_station__t30__cl1653104c"
P110, P111 = "s_7S_x110", "s_7S_x111"
NEW, PNEW = "slice_station__p7S_x11", "s_7S_x11p"
H = 1226.88
SEAM = {"unit__s_7N_LP__seqhost__3", "unit__seqhost__s_7N_LP__10", "tp__bk_sel__s_7S_LP__10"}
NTAP = 17                                    # x110 taps clk, clk_t1..clk_t16; x111 taps follow
N_SUFFIX = {"cland_up_ready": "cland_up_ready_n", "cland_up_fault": "cland_up_fault_n",
            "fclk_out_cland_up": "fclk_out_cland_up_n"}


def sh(xy, dy=H):
    return [xy[0], round(xy[1] + dy, 6)] + list(xy[2:])


def tap_n(name):
    """x111 tap name -> parent tap name"""
    k = 0 if name == "clk" else int(name.split("_t")[1])
    return f"clk_t{NTAP + k}"


def merged_type(a, b):
    """a = x110 type (south half), b = x111 type (north half, +H)."""
    t = dict(module=NEW, outline_um=[a["outline_um"][0], round(a["outline_um"][1] + b["outline_um"][1], 6)],
             hard=False, buses=[], contents=[], reset=copy.deepcopy(a["reset"]),
             landing_base_type=a.get("landing_base_type"),
             note=f"S81-PROUTE-1 pilot parent: {P110} ({T110}) + {P111} ({T111}) dissolved into one partition; "
                  "seam ft buses internal, stations unchanged per slot and re-spread, union taps/landings")
    W, Ht = t["outline_um"]
    slots = []
    for sa in a["ft_slots"]:
        sb = next(s for s in b["ft_slots"] if s["name"] == sa["name"])
        n = int(sa["stations"]) + int(sb["stations"])
        s = {k: v for k, v in sa.items() if k not in ("regs_um", "bit_sites_um", "bit_site_cell_um", "stations")}
        x = sum(sa["in_window_um"]) / 2
        # station sites = the two types' own sites (x111 frame +H); a half without regs_um takes the other half's
        # pattern (same column, same 306.7-um pitch), so every explicit clock tap keeps its own sinks
        if sa["in_face"] == "N":                     # N -> S: enters x111 (north half), leaves x110 S face
            assert sb["in_face"] == "N" and sa["out_face"] == "S"
            ra = sa["regs_um"]
            rb = sb.get("regs_um") or [list(r) for r in ra[:int(sb["stations"])]]
            regs = [sh(r) for r in rb] + [list(r) for r in ra]
        else:                                        # S -> N: enters x110 S face, leaves x111 N face
            assert sa["in_face"] == "S" and sb["out_face"] == "N"
            rb = sb["regs_um"]
            ra = sa.get("regs_um") or [list(r) for r in rb[:int(sa["stations"])]]
            regs = [list(r) for r in ra] + [sh(r) for r in rb]
        assert len(regs) == n
        s.update(stations=n, regs_um=regs)
        slots.append(s)
    t["ft_slots"] = slots
    ca, cb = a["clock"], b["clock"]
    c = {k: copy.deepcopy(v) for k, v in ca.items() if k not in ("landing_contract", "taps", "edge_clocks", "sink_sites_um")}
    c["taps"] = copy.deepcopy(ca["taps"]) + [dict(name=tap_n(x["name"]), xy=sh(x["xy"])) for x in cb["taps"]]
    c["edge_clocks"] = copy.deepcopy(ca["edge_clocks"]) + [dict(e, tap_um=sh(e["tap_um"])) for e in cb["edge_clocks"]]
    c["sink_sites_um"] = copy.deepcopy(ca["sink_sites_um"]) + [sh(x) for x in cb["sink_sites_um"]] + [
        sh(X111_RST_IN) + [1]] + [list(xy) + [1] for xy in [X110_RSTO0_RELAY] + ORL]
    c["taps"].append(dict(name=f"clk_t{len(c['taps'])}", xy=list(ORL[-1])))   # W-face reset-out relay of the merged type
    la, lb = ca["landing_contract"], cb["landing_contract"]
    pins = copy.deepcopy(la["pins"])
    for p in lb["pins"]:
        q = dict(p, name=N_SUFFIX.get(p["name"], p["name"]), xy_um=sh(p["xy_um"]))
        if "source_clock_port" in q:
            q["source_clock_port"] = tap_n(q["source_clock_port"])
        pins.append(q)
    # x111 half keeps its OWN die reset feed (s_7S_L3.rst_o_1, original hop 205.8 um) on a second registered reset
    # input at its original entry site: cycle-identical reset release for both halves
    pins.append(dict(name="arst_n_n", dir="in", kind="ctl", layer="M7", xy_um=sh(X111_RST_IN), epoch=False,
                     note="S81-PROUTE-1: x111-half synchronous reset in (die source s_7S_L3.rst_o_1)"))
    names = [p["name"] for p in pins]
    assert len(names) == len(set(names)), names
    bands = copy.deepcopy(la["bands"])
    for k, v in lb["bands"].items():
        assert k not in bands, k
        r = v["rect_um"]
        bands[k] = dict(v, rect_um=[r[0], round(r[1] + H, 6), r[2], round(r[3] + H, 6)])
    lc = {k: copy.deepcopy(v) for k, v in la.items() if k not in ("pins", "bands")}
    lc.update(pins=pins, bands=bands)
    # the north half's collector (own tree, own cland_up_*_n root) rides along, shifted, for the reset/landing sites
    tb = copy.deepcopy(lb["collector_tree"])
    tb["root"] = sh(tb["root"])
    for r in tb["relays"]:
        r["xy"] = sh(r["xy"])
    lc["collector_tree_n"] = tb
    lc["collector_local_sources"] = copy.deepcopy(la["collector_local_sources"]) + [
        dict(s, xy_um=sh(s["xy_um"]), pin_xy_um=sh(s["pin_xy_um"]),
             band=dict(s["band"], rect_um=[s["band"]["rect_um"][0], s["band"]["rect_um"][1] + H,
                                           s["band"]["rect_um"][2], s["band"]["rect_um"][3] + H]))
        for s in lb["collector_local_sources"]]
    c["landing_contract"] = lc
    t["clock"] = c
    return t


def cmd_plan(src, dst):
    p = json.load(open(src))
    pt = p["partition_types"]
    a, b = pt[T110], pt[T111]
    assert sum(1 for q in p["partitions"] if q["type"] in (T110, T111)) == 2, "pair types must be single-instance"
    pa = next(q for q in p["partitions"] if q["name"] == P110)
    pb = next(q for q in p["partitions"] if q["name"] == P111)
    assert pa["orient"] == pb["orient"] == "MY" and pa["origin_um"][0] == pb["origin_um"][0]
    assert abs(pb["origin_um"][1] - pa["origin_um"][1] - H) < 1e-6
    pt[NEW] = merged_type(a, b)
    del pt[T110], pt[T111]
    p["partitions"] = [q for q in p["partitions"] if q["name"] not in (P110, P111)] + [
        dict(name=PNEW, type=NEW, origin_um=list(pa["origin_um"]), orient="MY")]
    ports, dropped = [], []
    for q in p["ports"]:
        if q["id"] in SEAM:
            dropped.append(q["id"]); continue
        for side in ("src", "dst"):
            if q[side]["part"] in (P110, P111):
                q[side]["part"] = PNEW
        ports.append(q)
    assert sorted(dropped) == sorted(SEAM), dropped
    p["ports"] = ports
    nl = 0
    for ln in p.get("lanes", []):                # a lane's port chain loses the internal seam hop
        if any(x in SEAM for x in ln.get("ports", [])):
            ln["ports"] = [x for x in ln["ports"] if x not in SEAM]; nl += 1
    assert nl == len(SEAM), nl
    for e in p["clock"]["landing_network"]["edges"]:
        for side in ("src", "dst"):
            if e[side]["part"] == P111:
                e[side]["bus"] = N_SUFFIX.get(e[side]["bus"], e[side]["bus"])
            if e[side]["part"] in (P110, P111):
                e[side]["part"] = PNEW
    tw = p["clock"].get("tap_window", {}).get("per_type_ps", {})
    if T110 in tw or T111 in tw:
        tw[NEW] = max(tw.pop(T110, 0), tw.pop(T111, 0))
    ins = p["reset"].get("in_sites", {})
    if T110 in ins:
        ins[NEW] = ins.pop(T110)
        ins.pop(T111, None)
    for tn, t in pt.items():                     # parents' collector children name the new part (and _n pins)
        lc = t.get("clock", {}).get("landing_contract") or {}
        for ch in lc.get("collector_children", []):
            if ch.get("part") == P111:
                ch["part"] = PNEW
                ch["node_note"] = "S81-PROUTE-1: north half (cland_up_*_n)"
            elif ch.get("part") == P110:
                ch["part"] = PNEW
    p["note"] = p.get("note", "") + (f" | S81-PROUTE-1 PILOT (not of record): {P110}+{P111} -> {PNEW} ({NEW}); "
                                     f"seam ports {sorted(SEAM)} internal")
    Path(dst).write_text(json.dumps(p, indent=1) + "\n")
    print(f"plan {dst}: types {len(pt)} partitions {len(p['partitions'])} ports {len(p['ports'])} "
          f"(dropped {len(dropped)} seam ports)")


def bound_ports(sv):
    """[(dir, width, name)] of the module header of a bind bound module"""
    import re
    txt = Path(sv).read_text()
    m0 = re.search(r"^module\s+\w+\s*\(", txt, re.M)
    hdr = txt[m0.end(): txt.index(");", m0.end())]
    out = []
    for m in re.finditer(r"\b(input|output)\s+wire\s*(\[(\d+):0\])?\s*([A-Za-z_]\w*)", hdr):
        out.append((m.group(1), int(m.group(3)) + 1 if m.group(3) else 1, m.group(4)))
    return out


X111_RST_IN = [1434.72, 8.608]                              # reset.in_sites of both station types
X110_RSTO0_RELAY = [180.384, 1218.208]                      # x110 u_rrl_53 (its rst_o_0 relay, N face)
RST_O_MAP = {"rst_o_0": "s_rst_o_0", "rst_o_1": "s_rst_o_1"}
ORL = [[180.384, 1080.0], [17.28, 876.32]]                # x110 rst_o_0 relay (180.4,1218.2) -> W-face pin (8.16,876.3)


LC_A = {"17": "lc17", "18": "lc18"}    # x110 reset terminals without a clock tap (rst_n_t17/18): out of the tap namespace
RL_OFF = 100                           # x111 relay index offset (x110 relays u_rrl_0..60)
VKW = {"module", "endmodule", "wire", "assign", "input", "output", "logic", "reg", "default_nettype", "timescale"}


def _body(sv):
    import re
    txt = Path(sv).read_text()
    m0 = re.search(r"^module\s+\w+\s*\(", txt, re.M)
    i = txt.index(");", m0.end()) + 2
    return txt[i: txt.rindex("endmodule")]


def _decls(body):
    """local names declared in a bound body: wires (incl. wire x = y) and instance names"""
    import re
    names = set()
    for m in re.finditer(r"^\s*wire\s*(?:\[[^\]]+\]\s*)?([^;=]+?)\s*(?:=[^;]*)?;", body, re.M):
        names.update(x.strip() for x in m.group(1).split(","))
    for m in re.finditer(r"^\s*([A-Za-z_]\w*)\s*(?:#\s*\((?:[^()]|\([^()]*\))*\))?\s+([A-Za-z_]\w*)\s*\(", body, re.M):
        if m.group(1) not in VKW:
            names.add(m.group(2))
    return names


def _rename_body(body, portmap, rename):
    """token rename outside comments; '.pin(' names of sub-instances are kept"""
    import re
    out = []
    for line in body.split("\n"):
        code, sep, com = line.partition("//")
        code = re.sub(r"(?<![.\w`])([A-Za-z_]\w*)\b",
                      lambda m: portmap.get(m.group(1), rename.get(m.group(1), m.group(1))), code)
        out.append(code + sep + com)
    return "\n".join(out)


def flat_bodies(b110, b111, a_portmap, b_portmap):
    """ONE flat partition body: x110 (south) as bound, x111 (north) with its local names moved into the parent
    namespace: rst_n_t<k> -> rst_n_t<17+k> (x111 tap k = parent clk_t(17+k)), u_rrl_/rst_rl_<k> -> <k+100>, any other
    clashing local name +_n; the leaf alias rst_n is substituted by its terminal net (no alias left).  The seam buses are
    plain wires x_ft*.  Same cells, same nets as the 2-instance composition (only names differ)."""
    import re
    ba, bb = _body(b110), _body(b111)
    la, lb = _decls(ba), _decls(bb)
    ra = {}
    for n in la:
        m = re.search(r"rst_n_t(\d+)$", n)
        if m and m.group(1) in LC_A:
            ra[n] = n[: m.start(1) - 1] + LC_A[m.group(1)]
    leaf_a = re.search(r"^\s*wire\s+rst_n\s*=\s*(\w+)\s*;", ba, re.M).group(1)
    ba = re.sub(r"^\s*wire\s+rst_n\s*=\s*\w+\s*;\s*\n", "", ba, flags=re.M)
    ra["rst_n"] = ra.get(leaf_a, leaf_a)
    new_a = {ra.get(n, n) for n in la if n != "rst_n"} | set(a_portmap.values())
    rb = {}
    for n in lb:
        m = re.search(r"rst_n_t(\d+)$", n)
        m2 = re.search(r"(u_rrl|rst_rl)_(\d+)$", n)
        if m:
            rb[n] = n[: m.start(1)] + str(NTAP + int(m.group(1)))
        elif m2:
            rb[n] = n[: m2.start(2)] + str(RL_OFF + int(m2.group(2)))
        elif n == "u_rst_in" and n in new_a:
            rb[n] = f"u_rrl_{RL_OFF + 99}"          # entry relay: keeps the relay keep/follow class (u_rrl_<k>)
        elif n in new_a or n in b_portmap.values():
            rb[n] = n + "_n"
    leaf_b = re.search(r"^\s*wire\s+rst_n\s*=\s*(\w+)\s*;", bb, re.M).group(1)
    bb = re.sub(r"^\s*wire\s+rst_n\s*=\s*\w+\s*;\s*\n", "", bb, flags=re.M)
    rb["rst_n"] = rb.get(leaf_b, leaf_b)
    new_b = {rb.get(n, n) for n in lb if n != "rst_n"}
    clash = new_b & new_a
    assert not clash, sorted(clash)[:20]
    return (_rename_body(ba, a_portmap, ra), _rename_body(bb, b_portmap, rb), ra, rb)


def cmd_rtl(plan, b110, b111, libs, outdir):
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "tools" / "die_plan"))
    od = Path(outdir); od.mkdir(parents=True, exist_ok=True)
    p = json.load(open(plan))
    t = p["partition_types"][NEW]
    pa, pb = bound_ports(b110), bound_ports(b111)
    da = {n: (d, w) for d, w, n in pa}; db = {n: (d, w) for d, w, n in pb}
    seam = {"ft0": "x_ft0", "ft1": "x_ft1", "ft2": "x_ft2"}
    hdr, body = [], []
    conn_a, conn_b = [], []
    for d, w, n in pa:
        if n == "clk" or n.startswith("clk_t"):
            conn_a.append(f".{n}({n})")
        elif n in ("ft0_i", "ft1_i"):
            conn_a.append(f".{n}(x_{n[:3]})")
        elif n == "ft2_o":
            conn_a.append(f".{n}(x_ft2)")
        elif n in RST_O_MAP:
            conn_a.append(f".{n}({RST_O_MAP[n]})")
        else:
            conn_a.append(f".{n}({n})")
    for d, w, n in pb:
        if n == "clk" or n.startswith("clk_t"):
            conn_b.append(f".{n}({tap_n(n)})")
        elif n == "arst_n":
            conn_b.append(".arst_n(arst_n_n)")   # second registered reset input (plan landing-contract pin)
        elif n in ("ft0_o", "ft1_o"):
            conn_b.append(f".{n}(x_{n[:3]})")
        elif n == "ft2_i":
            conn_b.append(".ft2_i(x_ft2)")
        else:
            conn_b.append(f".{n}({N_SUFFIX.get(n, n)})")
    ports = {}
    for d, w, n in pa:
        if n in ("ft0_i", "ft1_i", "ft2_o"):
            continue
        ports[n] = (d, w)       # rst_o_0 / rst_o_1 keep their names, rewired below (RST_O_MAP)
    for d, w, n in pb:
        if n in ("ft0_o", "ft1_o", "ft2_i"):
            continue
        if n == "arst_n":
            ports["arst_n_n"] = ("input", 1); continue
        nn = tap_n(n) if (n == "clk" or n.startswith("clk_t")) else N_SUFFIX.get(n, n)
        assert nn not in ports, nn
        ports[nn] = (d, w)
    out_tap = f"clk_t{len(t['clock']['taps']) - 1}"
    for n in ("clk_t13", out_tap):                    # clocks of the two reset-out relays (u_orl_0 / u_orl_1)
        ports.setdefault(n, ("input", 1))
    widths = {"ft0": da["ft0_i"][1], "ft1": da["ft1_i"][1], "ft2": da["ft2_o"][1]}
    assert widths == {"ft0": db["ft0_o"][1], "ft1": db["ft1_o"][1], "ft2": db["ft2_i"][1]}
    plist = ",\n".join(f"    {d} wire {'[%d:0] ' % (w - 1) if w > 1 or n.startswith(('ft',)) else ''}{n}"
                       for n, (d, w) in ports.items())
    bm = NEW + "_bound"
    sv = [f"// GENERATED by physical/die_plan/s81/proute_1102/proute_x11p.py (S81-PROUTE-1 pilot): parent partition {PNEW}",
          f"// = {P110} ({T110}, u_s) + {P111} ({T111}, u_n) bound modules; the plain seam buses are internal wires.",
          "`timescale 1ns/1ps", "`default_nettype none", f"module {bm} (", plist, ");"]
    for k, w in widths.items():
        sv.append(f"    wire [{w - 1}:0] x_{k};   // former seam port (registered both ends, now partition-internal)")
    sv += [
           "    // reset wavefront outs of the merged type (gen: rst_o_0 W face y 175 -> fE3_p1_b2, rst_o_1 W face y 876",
           "    // -> fE3_p1_b1): x110 rst_o_1 drives rst_o_0 directly; x110 rst_o_0 (N-face relay, now interior) reaches",
           "    // the new W-face site through 2 relays (<= 405 um hops; boot only, +2 release cycles for fE3_p1_b1)",
           "    wire s_rst_o_0, s_rst_o_1, orl_0;",
           "    assign rst_o_0 = s_rst_o_1;",
           f"    ot_dp_rrelay u_orl_0 (.clk(clk_t13), .d(s_rst_o_0), .q(orl_0));",
           f"    ot_dp_rrelay u_orl_1 (.clk({out_tap}), .d(orl_0), .q(rst_o_1));",
           ]
    amap = {"ft0_i": "x_ft0", "ft1_i": "x_ft1", "ft2_o": "x_ft2", **RST_O_MAP}
    bmap = {"arst_n": "arst_n_n", "ft0_o": "x_ft0", "ft1_o": "x_ft1", "ft2_i": "x_ft2", **N_SUFFIX}
    for d, w, n in pb:
        if n == "clk" or n.startswith("clk_t"):
            bmap[n] = tap_n(n)
    body_a, body_b, ra, rb = flat_bodies(b110, b111, amap, bmap)
    sv += [f"    // ---- south half = former {P110} ({T110}) bound body, names as bound ({len(ra)} renamed)",
           body_a,
           f"    // ---- north half = former {P111} ({T111}) bound body, parent namespace ({len(rb)} renamed)",
           body_b, "endmodule", "`default_nettype wire", ""]
    (od / "flat_renames.json").write_text(json.dumps(dict(south=ra, north=rb), indent=1) + "\n")
    # the 2-instance composition (same cells/nets, original names) is kept as the equivalence reference
    comp = sv[:sv.index(f"    // ---- south half = former {P110} ({T110}) bound body, names as bound ({len(ra)} renamed)")]
    comp = [x.replace(f"module {NEW}_bound (", f"module {NEW}_comp (") for x in comp]
    comp += [f"    {T110}_bound u_s (", "        " + ",\n        ".join(conn_a), "    );",
             f"    {T111}_bound u_n (", "        " + ",\n        ".join(conn_b), "    );",
             "endmodule", "`default_nettype wire", ""]
    (od / f"{NEW}_comp.sv").write_text("\n".join(comp))
    (od / f"{bm}.sv").write_text("\n".join(sv))
    # kit wrapper (bind.py kit-rtl form): plan pins in gen order -> u_bound
    taps = [x["name"] for x in t["clock"]["taps"]]
    wp = []
    for n in taps:
        wp.append(f"    input  wire {n}")
    wp.append("    input  wire arst_n")
    for s in t["ft_slots"]:
        w = widths[s["name"]]
        wp.append(f"    input  wire [{w - 1}:0] {s['name']}_i")
        wp.append(f"    output wire [{w - 1}:0] {s['name']}_o")
    bop = []
    for n, (d, w) in ports.items():
        if n in taps or n == "arst_n" or n[:3] in ("ft0", "ft1", "ft2") and n[3:] in ("_i", "_o"):
            continue
        wp.append(f"    {d} wire [0:0] {n}")
        bop.append(dict(port=n, dir=d, width=w))
    wrap = [f"// GENERATED by proute_x11p.py (S81-PROUTE-1 pilot): kit RTL of plan type {NEW} = {bm} in a port-only wrapper.",
            "`timescale 1ns/1ps", "`default_nettype none", f"module {NEW} (", ",\n".join(wp), ");",
            f"    {bm} u_bound ("]
    wrap.append("        " + ",\n        ".join(f".{n}({n})" for n in ports) )
    wrap += ["    );", "endmodule", "`default_nettype wire", ""]
    (od / f"{NEW}.sv").write_text("\n".join(wrap))
    import shutil
    for f in (b110, b111):
        shutil.copyfile(f, od / Path(f).name)
    lib = [l.strip() for l in Path(libs).read_text().split() if l.strip()]
    files = [str(od / f"{NEW}.sv"), str(od / f"{bm}.sv")] + lib     # flat parent body (station bound copies = EQ reference only)
    (od / "kit_rtl.f").write_text("\n".join(files) + "\n")
    (od / "kit_rtl_sim.f").write_text("\n".join(files) + "\n")
    defs = []
    for f in (b110, b111):                   # the station kits' own kit-rtl defines (same die define set)
        kjp = Path(f).parent / "kit_rtl.json"
        if kjp.is_file():
            defs += [x for x in json.load(open(kjp)).get("defines", []) if x not in defs]
    kj = dict(schema="opentallas.die_plan.kit_rtl.v1", plan_type=NEW, plan_module=NEW, bound_type=NEW, bound_module=bm,
              variants=[NEW], bind_out=None, instances=[PNEW], params="", taps=taps[1:], spare_out_bits=[],
              spare_ft_passthrough=[], narrow_buses=[], plan_buses_unbound=[], bound_only_pins=bop, defines=defs,
              files=files, packages=[], sim_files="kit_rtl_sim.f", package_inlined={}, include_inlined={},
              module_dedup={}, hard_macros={}, unindexed_sources={}, native_station_geometry=None,
              hbm_spb_native_geometry=None,
              note="S81-PROUTE-2 pilot: ONE flat parent body = the two strict-bind station bound bodies (bind_ev2) in one namespace (flat_renames.json); EQ reference = _comp.sv")
    (od / "kit_rtl.json").write_text(json.dumps(kj, indent=1) + "\n")
    # reset_tree.tcl: both bound trees (exact hierarchical instance paths) + the x111 feed relays
    import reset_tree as RT
    lc = t["clock"]["landing_contract"]
    texts = []
    for pre, T in (("u_s", lc["collector_tree"]), ("u_n", lc["collector_tree_n"])):
        T = copy.deepcopy(T)
        T.setdefault("start", False); T.setdefault("relay_driver", False)
        names = ["u_rst_root" if T["entry"] == "sync" else "u_rst_in"] + [r["name"] for r in T["relays"]]
        rn = ra if pre == "u_s" else rb               # flat body names (flat_renames.json)
        texts.append(RT.tcl_text(T, native_paths={n: f"u_bound.{rn.get(n, n)}" for n in names}))
    feed = ["# S81-PROUTE-1: x111-half reset feed relays (parent arst_n -> u_n.arst_n), FIRM on the E edge",
            "set rtr_fh [open $::env(RESULTS_DIR)/ot_face_flops.txt a]", "set rtr_miss {}"]
    for k, xy in enumerate(ORL):
        feed.append(f"rtr_place orl{k} {{u_bound[./]u_orl_{k}[./]*}} {xy[0]:.3f} {xy[1]:.3f} rrl:out{k}")
    feed += ["close $rtr_fh", 'puts "OT_RESET_FEED placed [expr {2 - [llength $rtr_miss]}]/2 (missing: $rtr_miss)"']
    (od / "reset_tree.tcl").write_text("\n".join(texts) + "\n" + "\n".join(feed) + "\n")
    print(f"rtl {od}: {len(ports)} bound ports, wrapper pins {len(wp)}, bound-only {len(bop)}")


def _tcl_block(txt, var):
    """(start, end) of 'set <var> {\n ... \n}' in a generated tcl file"""
    i = txt.index(f"set {var} {{\n")
    return i, txt.index("\n}\n", i) + 3


def cmd_lp(gen_lp, lp110, lp111, renames):
    """landing_placement.tcl of the pilot kit: the generated procedures, with the group/status tables composed from the
    two station kits' own tables (same rings, collectors, raw-copy cells): x110 names as renamed (flat_renames south),
    x111 names in the parent namespace (north) and rects/points +H."""
    import re
    rn = json.load(open(renames))
    g = Path(gen_lp).read_text()
    src = {"s": Path(lp110).read_text(), "n": Path(lp111).read_text()}
    for var in ("cland_groups", "cland_optional_groups", "cland_status"):
        rows = []
        for half, txt in src.items():
            if f"set {var} {{" not in txt:
                continue
            a, b = _tcl_block(txt, var)
            ren = rn["south" if half == "s" else "north"]
            dy = H if half == "n" else 0.0
            for ln in txt[a:b].split("\n")[1:-2]:
                m = re.fullmatch(r"\s*\{(\S+) \{([\d.\s-]+)\}(.*)\}\s*", ln) if var != "cland_status" else None
                if m:
                    r = [float(x) for x in m.group(2).split()]
                    r = [r[0], r[1] + dy, r[2], r[3] + dy]
                    rows.append(f"  {{{ren.get(m.group(1), m.group(1))} {{{' '.join('%.5f' % x for x in r)}}}{m.group(3)}}}")
                    continue
                m = re.fullmatch(r"\s*\{(\S+) ([\d.-]+) ([\d.-]+)\}\s*", ln)
                assert m, (var, ln)
                rows.append(f"  {{{ren.get(m.group(1), m.group(1))} {float(m.group(2)):.5f} {float(m.group(3)) + dy:.5f}}}")
        if f"set {var} {{" in g:
            a, b = _tcl_block(g, var)
            g = g[:a] + f"set {var} {{\n" + "\n".join(rows) + "\n}\n" + g[b:]
        else:
            assert not rows, var
    Path(gen_lp).write_text(g)
    print(f"landing_placement {gen_lp}: composed from both station kits")


def _shift_rect(r):
    return [r[0], round(r[1] + H, 6), r[2], round(r[3] + H, 6)]


def _pref_band(b, pre, shift):
    b = copy.deepcopy(b)
    if shift:
        b["rect_um"] = _shift_rect(b["rect_um"])
    if b.get("instance"):
        b["instance"] = f"{pre}.{b['instance']}"
    return b


def cmd_sidecar(src, dst):
    """landed sidecar of the pilot plan: x110/x111 rows -> x11p (one clock region: the seam was PLAIN, both halves
    std_bg_78_0); the merged collector type = the x110 entry (its up pin / child 0 / tree) + the x111 half's landed
    inputs, local sources and bands (shifted +H, instance prefixed u_n.), x110 bands prefixed u_s."""
    sc = json.load(open(src))
    regs = [r for r in sc["regions"] if r["parts"] in ([P110], [P111])]
    assert len(regs) == 2 and len({r["tag"] for r in regs}) == 1, regs
    a, b = sorted(regs, key=lambda r: r["box_um"][1])
    a["box_um"] = [a["box_um"][0], a["box_um"][1], a["box_um"][2], b["box_um"][3]]
    a["parts"] = [PNEW]
    sc["regions"] = [r for r in sc["regions"] if r is not b]
    n = 0
    for r in sc["ports"]:
        for k in ("src", "dst"):
            if r[k] in (P110, P111):
                r[k] = PNEW; n += 1
    c = sc["collector"]
    for pn, e in c["parts"].items():
        if e.get("parent") in (P110, P111):
            e["parent"] = PNEW
    c["parts"][PNEW] = dict(c["parts"].pop(P110), type=NEW)
    c["parts"].pop(P111)
    for tn, e in c["types"].items():
        for ch in e.get("children", []):
            if ch.get("part") == P110:
                ch["part"] = PNEW
            elif ch.get("part") == P111:
                ch.update(part=PNEW, child_up_suffix="_n")   # parent pins unchanged; the child drives cland_up_*_n
    for e in c["edges"]:
        for k in ("src", "dst"):
            if e[k] in (P110, P111):
                if e[k] == P111:
                    e["src_pin_suffix"] = "_n"
                e[k] = PNEW
    ta, tb = c["types"].pop(T110), c["types"].pop(T111)
    t = copy.deepcopy(ta)
    t["mask"]["inputs"] = sorted(set(ta["mask"]["inputs"]) | set(tb["mask"]["inputs"]))
    t["mask"]["outputs"] = sorted(set(ta["mask"]["outputs"]) | set(tb["mask"]["outputs"]))
    t["local_sources"] = [dict(s, band=_pref_band(s["band"], "u_s", False)) for s in ta["local_sources"]] + [
        dict(s, xy_um=sh(s["xy_um"]), pin_xy_um=sh(s["pin_xy_um"]), band=_pref_band(s["band"], "u_n", True))
        for s in tb["local_sources"]]
    t["bands"] = {k: _pref_band(v, "u_s", False) for k, v in ta["bands"].items()}
    for k, v in tb["bands"].items():
        assert k not in t["bands"], k
        t["bands"][k] = _pref_band(v, "u_n", True)
    t["tree_n"] = copy.deepcopy(tb["tree"])
    t["note"] = "S81-PROUTE-2 pilot merged collector type (x110 up/children/tree; x111 half = tree_n, cland_up_*_n)"
    c["types"][NEW] = t
    bt = c.get("base_type_by_part", {})
    if P110 in bt:
        bt[PNEW] = bt.pop(P110); bt.pop(P111, None)
    Path(dst).write_text(json.dumps(sc, indent=1) + "\n")
    print(f"sidecar {dst}: regions {len(sc['regions'])} landed port endpoints renamed {n}")


if __name__ == "__main__":
    if sys.argv[1] == "plan":
        cmd_plan(*sys.argv[2:4])
    elif sys.argv[1] == "lp":
        cmd_lp(*sys.argv[2:6])
    elif sys.argv[1] == "sidecar":
        cmd_sidecar(*sys.argv[2:4])
    elif sys.argv[1] == "rtl":
        cmd_rtl(*sys.argv[2:7])
    else:
        sys.exit(__doc__)
