#!/usr/bin/env python3
"""Feedthrough pushdown generators (FT-TOOL / FT-PUSH, FT-PLAN owner 10-23).  Stdlib only.

Input: one ft spec per hosting block (README "ft spec", schema opentallas.die_feedthrough.ftspec.v1, written by plan.py).
Every coordinate is in the block MASTER frame (orientation undone).

    pushdown.py wrapper  SPEC.json --kit-top MOD (--kit-verilog F | --kit-ports P.json) --out DIR
                         [--station-module ot_dvrly_st|ft_pipe_reg|<same-port cell>] [--hc 1]
                         [--clock PORT] [--reset PORT] [--kit-param NAME=VAL ...]
    pushdown.py pins     SPEC.json --out DIR [--layers die.json|layers.json] [--dbu 1000] [--pin-len-um 0.32]
    pushdown.py contract SPEC.json --out DIR [--layers ...] [--margin-um 2] [--signal-min M2] [--adjust 0.5]
    pushdown.py check    SPEC.json --lef BLOCK.lef [--max-cover 0.05] [--allow-stripes 0.48:8.64]
    pushdown.py die      SPEC_DIR --plan PLAN.json --die-verilog die.v --out DIR [--census C.json.gz]

wrapper  -> DIR/<variant>.v (+ ft_pipe_reg), DIR/<variant>.ft.json (paths, register names, repeater sites).
   module <variant> = UNMODIFIED kit top (every port passed through, kit RTL never edited) + per path k a chain of
   `stages` station instances ft<k>_s0..ft<k>_s<n-1> from ft<k>_i to ft<k>_o.  Station = ot_dvrly_st #(W, HC)
   (rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dvh.sv: ck, rs active-low, i, o, ck_o) or the emitted ft_pipe_reg
   (same ports; plain posedge D-flops, no reset on data, ck_o = ck).  Static schedule: no valid/ready, no backpressure.
   clock "block": every station on the block clock (--clock, default: first kit input named clk*/ck*), ck_o unused.
   clock "forwarded": ft<k>_ck_i -> s0.ck, s<j>.ck_o -> s<j+1>.ck, last ck_o -> ft<k>_ck_o (spec ports may name them).
   rs = --reset (default: first kit input rst_n/rstn/rs*), required by stations that have a reset pin register.
   Repeaters are NOT RTL: block P&R (repair_design) inserts them; their sites are only listed (comment + sidecar).
pins     -> DIR/<variant>.pins.tcl: `place_pin -pin_name {ft3_i[5]} -layer M8 -location {x y} -pin_size {l w}` per bit,
   bits spread evenly over [lo, hi] at a step that is an integer multiple of the layer track pitch, snapped to the
   track grid (offset + k*pitch; ASAP7 M8/M9: 0.116 + k*0.080).  Placement depends only on (lo, hi, bits, layer), so
   the in and out ports of a straight path and the abutting neighbour's ports get identical offsets.  A forwarded
   clock pin takes the middle slot.  Also DIR/<variant>.pins.json and an OPTIONAL commented-out register hint block
   (each flop of ft<k>_s<j> at the stage x (W/E path) or y (N/S path) and at its bit's pin track).
contract -> DIR/<variant>.fastroute.tcl (ORFS FASTROUTE_TCL), DIR/<variant>.contract.json, DIR/<variant>.ft_audit.tcl.
   MECHANISM (OpenROAD 26Q3-1510, openroad/orfs:asap7lock, checked 10-23): there is NO per-net layer range: help
   lists only `set_routing_layers [-signal min-max] [-clock min-max]` (global; its body calls define_layer_range /
   define_clock_layer_range), `set_min_layer`/`set_max_layer` (global), `set_global_routing_layer_adjustment layer adj`
   and `set_global_routing_region_adjustment region [-layer] [-adjustment]`; NDRs (create_ndr/assign_ndr) carry
   width/spacing/via only; no set_net_routing_layer.  Chosen: signal range M2-M9 globally (so DRT/GRT may use the ft
   layers), base adjustment on M2..signal_max, and region adjustment 1.0 (zero GRT capacity) on every ft layer over
   the block outline MINUS the ft corridors (the straight/L bands from the in pin range to the out pin range, plus a
   margin).  Non-ft nets therefore get no M8/M9 outside the corridors, and the corridors are sized for the ft bits at
   0.6 occupancy, so M8/M9 is effectively ft-only; DRT follows the guides.  Same primitive as tools/w15_trunk_m89.tcl
   and tools/qwen_corridor_gate.py.  It is a capacity fence, not a per-net rule: ft_audit.tcl (run after
   global_route) lists every non-ft net with an M8/M9 guide (ft = nets reached from ft<k>_* ports/stations through
   buffers/inverters) and fails if any is outside a corridor.  Rejected: -clock range hack (moves real clocks to M8/M9);
   pre-routed special nets (repair_design's repeaters break the wire; future option).
check    -> check_abstract(lef_text, spec): FAIL if an OBS on an ft layer covers > max_cover of the outline (stripes
   narrower than the --allow-stripes width are excluded and only fail above 1.25 x width/pitch density), or if an ft
   pin bit is missing, has no shape on its spec layer, is not on its spec face or lies outside [lo, hi].
die      -> DIR/die_eco.json + DIR/die_eco.tcl (BEST-EFFORT SKELETON): per pushed-down lane (plan lanes[] with
   keep_channel false and block segments) delete the lane's channel relays (lanes[].relays, the census longest chain),
   delete the inter-relay nets, and chain src nets -> blk1/ft_i .. blk1/ft_o -> new net -> blk2/ft_i ... -> dst nets
   with OpenROAD connect_pin / make_net / delete_instance / delete_net.  die.v is only READ (net names at the relay
   pins); it is never rewritten.  TODOs are listed per lane in the JSON.
"""
import argparse
import gzip
import json
import math
import os
import re
import sys
from pathlib import Path

SPEC_SCHEMA = "opentallas.die_feedthrough.ftspec.v1"
EPS = 1e-6
# ASAP7 defaults (die.json "layers" from odb_dump + platforms/asap7/openRoad/make_tracks.tcl offsets for M8/M9)
ASAP7_LAYERS = {
    "M1": dict(dir="VERTICAL", pitch=0.036, width=0.018, offset=0.0),
    "M2": dict(dir="HORIZONTAL", pitch=0.036, width=0.018, offset=0.0),
    "M3": dict(dir="VERTICAL", pitch=0.036, width=0.018, offset=0.0),
    "M4": dict(dir="HORIZONTAL", pitch=0.048, width=0.024, offset=0.0),
    "M5": dict(dir="VERTICAL", pitch=0.048, width=0.024, offset=0.0),
    "M6": dict(dir="HORIZONTAL", pitch=0.064, width=0.032, offset=0.0),
    "M7": dict(dir="VERTICAL", pitch=0.064, width=0.032, offset=0.0),
    "M8": dict(dir="HORIZONTAL", pitch=0.08, width=0.04, offset=0.116),
    "M9": dict(dir="VERTICAL", pitch=0.08, width=0.04, offset=0.116),
}


# ---------------------------------------------------------------------------------------------------- common
def load_json(path):
    op = gzip.open if str(path).endswith(".gz") else open
    with op(path, "rt") as f:
        return json.load(f)


def load_spec(path):
    spec = load_json(path)
    if spec.get("schema") != SPEC_SCHEMA:
        raise ValueError(f"{path}: schema {spec.get('schema')!r} != {SPEC_SCHEMA}")
    return spec


def load_layers(path=None):
    """{name: dir, pitch, width, offset}; path = die.json (key "layers") or a bare list/dict; ASAP7 defaults fill gaps."""
    lay = {k: dict(v) for k, v in ASAP7_LAYERS.items()}
    if path:
        js = load_json(path)
        js = js.get("layers", js) if isinstance(js, dict) else js
        items = js.items() if isinstance(js, dict) else ((d["name"], d) for d in js)
        for n, d in items:
            base = lay.get(n, dict(offset=0.0, width=d.get("pitch", 0.08) / 2))
            base.update({k: d[k] for k in ("dir", "pitch", "width", "offset") if k in d})
            lay[n] = base
    return lay


def ft_ports(spec):
    """data + clock ports: [{name, dir, bits, path, face, lo, hi, layer, role}]; forwarded clock ports added if absent."""
    names = {p["name"] for p in spec["ports"]}
    out = [dict(p, role="data") for p in spec["ports"]]
    if spec.get("clock") == "forwarded":
        for p in spec["paths"]:
            for src, d, nm in (("in", "input", f"ft{p['path']}_ck_i"), ("out", "output", f"ft{p['path']}_ck_o")):
                dp = next(q for q in spec["ports"] if q["name"] == p[src])
                ck = clock_port_name(spec, p, d)
                if ck not in names:
                    out.append(dict(name=nm, dir=d, bits=1, path=p["path"], face=dp["face"], lo=dp["lo"], hi=dp["hi"],
                                    layer=dp["layer"], role="clock", data_port=dp["name"]))
                else:
                    for q in out:
                        if q["name"] == ck:
                            q.update(role="clock", data_port=dp["name"])
    return out


def clock_port_name(spec, path, d):
    k = path["path"]
    want = f"ft{k}_ck_i" if d == "input" else f"ft{k}_ck_o"
    for q in spec["ports"]:   # explicit clock port in the spec (same path, 1 bit, *_ck_i / *_ck_o)
        if q.get("path") == k and q.get("bits") == 1 and q["dir"] == d and re.search(r"_ck_[io]$", q["name"]):
            return q["name"]
    return want


# ---------------------------------------------------------------------------------------------------- 1. wrapper
_PORT_RE = re.compile(r"^\s*(input|output|inout)\s+(?:(?:wire|logic|reg|var|signed|unsigned)\s+)*"
                      r"(\[[^\]]+\])?\s*(.*)$", re.S)


def _strip_comments(t):
    return re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", t, flags=re.S))


def _skip_parens(t, i):
    """t[i] == '(' -> index after the matching ')'."""
    depth = 0
    for j in range(i, len(t)):
        if t[j] == "(":
            depth += 1
        elif t[j] == ")":
            depth -= 1
            if depth == 0:
                return j + 1
    raise ValueError("unbalanced parentheses")


def parse_kit_ports_verilog(text, module):
    """ANSI header only: module NAME [#(...)] ( input wire [a:b] x, y, output ... );  -> [{name, dir, range}]."""
    t = _strip_comments(text)
    m = re.search(r"\bmodule\s+" + re.escape(module) + r"\b", t)
    if not m:
        raise ValueError(f"module {module} not found")
    i = m.end()
    while t[i].isspace():
        i += 1
    if t[i] == "#":
        i = _skip_parens(t, t.index("(", i))
        while t[i].isspace():
            i += 1
    if t[i] != "(":
        raise ValueError(f"module {module}: no ANSI port list")
    body = t[i + 1:_skip_parens(t, i) - 1]
    ports, cur = [], None
    for item in [s.strip() for s in body.split(",")]:
        if not item:
            continue
        mm = _PORT_RE.match(item)
        if mm:
            cur = (mm.group(1), (mm.group(2) or "").replace(" ", ""))
            name = mm.group(3).strip()
        elif cur and re.fullmatch(r"[A-Za-z_]\w*", item):
            name = item   # continuation: input wire [3:0] a, b
        else:
            raise ValueError(f"module {module}: unsupported port item {item!r} (ANSI headers only)")
        ports.append(dict(name=name, dir=cur[0], range=cur[1]))
    return ports


def parse_kit_ports_json(obj):
    """[{name, dir, range|bits}] or {name: {dir, bits|range}}."""
    items = obj.items() if isinstance(obj, dict) else ((d["name"], d) for d in obj)
    out = []
    for n, d in items:
        rng = d.get("range") or (f"[{int(d['bits']) - 1}:0]" if int(d.get("bits", 1)) > 1 else "")
        out.append(dict(name=n, dir=d["dir"], range=rng))
    return out


FT_PIPE_REG = """\
// ft_pipe_reg (pushdown.py): generic feedthrough pipeline register, same ports as ot_dvrly_st.
// Plain posedge D-flops, no reset on data (static schedule: no valid/ready, no backpressure); rs unused; ck_o = ck.
module ft_pipe_reg #(parameter integer W = 1, parameter integer HC = 0) (
    input wire ck, input wire rs, input wire [W-1:0] i, output wire [W-1:0] o, output wire ck_o);
    reg [W-1:0] q;
    always @(posedge ck) q <= i;
    assign o = q;
    assign ck_o = ck;
    wire unused_rs = rs;
endmodule
"""


def _pick(ports, explicit, pats, what):
    ins = [p["name"] for p in ports if p["dir"] == "input"]
    if explicit:
        if explicit not in ins:
            raise ValueError(f"--{what} {explicit!r} is not a kit input (inputs: {', '.join(ins)})")
        return explicit
    for pat in pats:
        for n in ins:
            if re.fullmatch(pat, n, re.I):
                return n
    return None


def rep_sites(spec_path_rec, port_by_name, outline):
    """even repeater sites on the in-pin -> regs -> out-pin polyline (positions only; P&R inserts the buffers)."""
    n = int(spec_path_rec.get("rep_sites", 0) or 0)
    if n <= 0:
        return []
    pts = [_port_center(port_by_name[spec_path_rec["in"]], outline)] + \
        [tuple(r) for r in spec_path_rec.get("regs_um", [])] + [_port_center(port_by_name[spec_path_rec["out"]], outline)]
    seg = [abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in zip(pts, pts[1:])]
    L = sum(seg)
    out = []
    for j in range(1, n + 1):
        t, acc = L * j / (n + 1), 0.0
        for (a, b), s in zip(zip(pts, pts[1:]), seg):
            if acc + s >= t - EPS and s > 0:
                f = (t - acc) / s
                # Manhattan leg: horizontal first then vertical
                dx, dy = b[0] - a[0], b[1] - a[1]
                d = f * (abs(dx) + abs(dy))
                if d <= abs(dx):
                    out.append([round(a[0] + math.copysign(d, dx), 3), round(a[1], 3)])
                else:
                    out.append([round(b[0], 3), round(a[1] + math.copysign(d - abs(dx), dy), 3)])
                break
            acc += s
    return out


def _port_center(p, outline):
    W, H = outline
    m = (p["lo"] + p["hi"]) / 2
    return {"W": (0.0, m), "E": (W, m), "S": (m, 0.0), "N": (m, H)}[p["face"]]


def gen_wrapper(spec, kit_top, kit_ports, station="ot_dvrly_st", hc=1, clock=None, reset=None, kit_params=None):
    """-> (verilog_text, sidecar_dict).  The kit module is instantiated as u_kit, never edited."""
    variant, fwd = spec["variant"], spec.get("clock") == "forwarded"
    kit_names = {p["name"] for p in kit_ports}
    ports = ft_ports(spec)
    clash = [p["name"] for p in ports if p["name"] in kit_names]
    if clash:
        raise ValueError(f"ft port names collide with kit ports: {clash}")
    clk = _pick(kit_ports, clock, [r"clk", r"ck", r"clk\w*", r"ck\w*"], "clock")
    rst = _pick(kit_ports, reset, [r"rst_n", r"rstn", r"rs", r"rst\w*", r"rs\w*"], "reset")
    if not fwd and clk is None:
        raise ValueError("clock 'block' needs a block clock: no kit input looks like a clock, pass --clock")
    if station != "ft_pipe_reg" and rst is None:
        raise ValueError(f"station {station} has a reset pin register: no kit reset input found, pass --reset")
    pb = {p["name"]: p for p in ports}
    L = [f"// GENERATED by tools/die_feedthrough/pushdown.py wrapper -- do not edit; regenerate from the ft spec.",
         f"// die {spec.get('die')} block {spec.get('block')} master {spec.get('master')} -> variant {variant}",
         f"// kit top {kit_top} instantiated UNMODIFIED as u_kit; ft clock '{spec.get('clock', 'block')}', "
         f"station {station}" + (f" HC={hc}" if station != "ft_pipe_reg" else "") +
         f", block clock {clk}, reset {rst} (active-low rs).",
         f"// Repeaters are NOT RTL: block P&R inserts buffers at the listed sites (<= rep_um apart).",
         "`default_nettype none", f"module {variant} ("]
    decl = [f"    {p['dir']} wire {p['range'] + ' ' if p['range'] else ''}{p['name']}" for p in kit_ports]
    for p in ports:
        rng = f"[{p['bits'] - 1}:0] " if p["bits"] > 1 else ""
        decl.append(f"    {p['dir']} wire {rng}{p['name']}")
    L.append(",\n".join(decl))
    L.append(");")
    par = ""
    if kit_params:
        par = " #(" + ", ".join(f".{k}({v})" for k, v in kit_params.items()) + ")"
    conns = ",\n".join(f"        .{p['name']}({p['name']})" for p in kit_ports)
    L.append(f"    {kit_top}{par} u_kit (\n{conns}\n    );")
    side = dict(schema="opentallas.die_feedthrough.wrapper.v1", variant=variant, kit_top=kit_top, station=station,
                hc=hc if station != "ft_pipe_reg" else None, clock=spec.get("clock", "block"), block_clock=clk,
                reset=rst, paths=[])
    for path in spec["paths"]:
        k, W, n = path["path"], int(path["bits"]), int(path["stages"])
        pin, pout = path["in"], path["out"]
        if pb[pin]["bits"] != W or pb[pout]["bits"] != W:
            raise ValueError(f"path {k}: port widths {pb[pin]['bits']}/{pb[pout]['bits']} != bits {W}")
        sites = rep_sites(path, pb, spec["outline"])
        L.append(f"    // ---- ft path {k}: lane {path.get('lane')} {path.get('src', '')} -> {path.get('dst', '')}, "
                 f"{W} b, {n} stage(s), {path.get('len_um')} um")
        L.append(f"    //      repeater sites (P&R-inserted, not RTL): {sites if sites else 'none'}")
        cki, cko = (clock_port_name(spec, path, "input"), clock_port_name(spec, path, "output")) if fwd else (None, None)
        regs = []
        if n == 0:
            L.append(f"    assign {pout} = {pin};   // WARNING: unregistered crossing (stages 0)")
            if fwd:
                L.append(f"    assign {cko} = {cki};")
        for j in range(n):
            src = pin if j == 0 else f"ft{k}_p{j}"
            dst = pout if j == n - 1 else f"ft{k}_p{j + 1}"
            if j < n - 1:
                L.append(f"    wire [{W - 1}:0] ft{k}_p{j + 1};")
            if fwd:
                ck = cki if j == 0 else f"ft{k}_ck{j}"
                cko_n = cko if j == n - 1 else f"ft{k}_ck{j + 1}"
                if j < n - 1:
                    L.append(f"    wire ft{k}_ck{j + 1};")
            else:
                ck, cko_n = clk, ""
            prm = f"#(.W({W}))" if station == "ft_pipe_reg" else f"#(.W({W}), .HC({hc}))"
            rs = rst if rst else "1'b1"   # only ft_pipe_reg (rs unused) may run without a kit reset
            nm = f"ft{k}_s{j}"
            L.append(f"    {station} {prm} {nm} (.ck({ck}), .rs({rs}), .i({src}), .o({dst}), .ck_o({cko_n}));")
            xy = path.get("regs_um", [])
            regs.append(dict(inst=nm, xy=xy[j] if j < len(xy) else None))
        side["paths"].append(dict(path=k, lane=path.get("lane"), bits=W, stages=n, **{"in": pin, "out": pout},
                                  ck_in=cki, ck_out=cko, regs=regs, rep_sites=sites))
    L += ["endmodule", "`default_nettype wire", ""]
    text = "\n".join(L)
    if station == "ft_pipe_reg":
        text += FT_PIPE_REG
    else:
        text += "// ft_pipe_reg fallback (select with --station-module ft_pipe_reg):\n" + FT_PIPE_REG
    return text, side


# ---------------------------------------------------------------------------------------------------- 2. pins
def pin_offsets(lo, hi, n, pitch, offset=0.0):
    """n positions on the track grid (offset + k*pitch) inside [lo, hi], evenly spread at an integer multiple of the
    pitch, centred in the range.  Pure function of its arguments (neighbours with equal ranges get equal offsets)."""
    k_lo = math.ceil((lo - offset) / pitch - 1e-9)
    k_hi = math.floor((hi - offset) / pitch + 1e-9)
    avail = k_hi - k_lo + 1
    if n > avail:
        raise ValueError(f"{n} bits do not fit [{lo}, {hi}] at pitch {pitch} ({avail} tracks)")
    step = 1 if n <= 1 else max(1, (avail - 1) // (n - 1))
    used = (n - 1) * step + 1
    k0 = k_lo + (avail - used) // 2
    return [round(offset + (k0 + i * step) * pitch, 6) for i in range(n)]


def slot_range(p, n, lay):
    """[lo, hi] holding n track slots: the spec range, widened symmetrically when a forwarded clock slot (bits + 1)
    does not fit a range plan.py sized for the data bits only (warning, not an error)."""
    lo, hi, pitch, off = p["lo"], p["hi"], lay["pitch"], lay.get("offset", 0.0)
    avail = math.floor((hi - off) / pitch + 1e-9) - math.ceil((lo - off) / pitch - 1e-9) + 1
    if n > avail:
        g = math.ceil((n - avail) / 2) * pitch
        return lo - g, hi + g, True
    return lo, hi, False


def port_bit_names(name, bits):
    return [f"{name}[{b}]" for b in range(bits)] if bits > 1 else [name]


def place_ports(spec, layers, pin_len=0.32):
    """-> [{port, pin, layer, face, location[x, y], size[w, h], offset}] in the master frame."""
    W, H = spec["outline"]
    ports = ft_ports(spec)
    clocks = {p["data_port"]: p for p in ports if p["role"] == "clock" and p.get("data_port")}
    out = []
    for p in ports:
        if p["role"] == "clock" and p.get("data_port"):
            continue   # placed with its data port
        lay = layers[p["layer"]]
        horiz = p["face"] in ("W", "E")
        if (lay["dir"] == "HORIZONTAL") != horiz:
            raise ValueError(f"{p['name']}: layer {p['layer']} ({lay['dir']}) cannot carry a pin on face {p['face']}")
        names = port_bit_names(p["name"], p["bits"])
        ck = clocks.get(p["name"])
        if ck:   # forwarded clock: middle slot of bits + 1
            mid = len(names) // 2
            names = names[:mid] + [ck["name"]] + names[mid:]
        lo, hi, widened = slot_range(p, len(names), lay)
        if widened:
            print(f"WARNING {spec['variant']}: {p['name']} widened to [{lo:.3f}, {hi:.3f}] for its clock slot "
                  "(plan.py: size forwarded ports for bits + 1)", file=sys.stderr)
        offs = pin_offsets(lo, hi, len(names), lay["pitch"], lay.get("offset", 0.0))
        wdt = lay["width"]
        for nm, o in zip(names, offs):
            if p["face"] == "W":
                loc, size = (pin_len / 2, o), (pin_len, wdt)
            elif p["face"] == "E":
                loc, size = (W - pin_len / 2, o), (pin_len, wdt)
            elif p["face"] == "S":
                loc, size = (o, pin_len / 2), (wdt, pin_len)
            else:
                loc, size = (o, H - pin_len / 2), (wdt, pin_len)
            out.append(dict(port=(ck["name"] if nm == ck["name"] else p["name"]) if ck else p["name"], pin=nm,
                            layer=p["layer"], face=p["face"], offset=o,
                            location=[round(loc[0], 6), round(loc[1], 6)], size=[round(size[0], 6), round(size[1], 6)]))
    return out


def gen_pins(spec, layers, pin_len=0.32, dbu=1000):
    pl = place_ports(spec, layers, pin_len)
    by_pin = {p["pin"]: p for p in pl}
    T = [f"# GENERATED by pushdown.py pins: ft pins of {spec['variant']} (master frame, um; dbu {dbu}).",
         "# Tracks: offset + k*pitch per layer; in/out ranges equal -> equal offsets (neighbours abut on the same tracks)."]
    for p in pl:
        T.append(f"place_pin -pin_name {{{p['pin']}}} -layer {p['layer']} -location {{{p['location'][0]:.4f} "
                 f"{p['location'][1]:.4f}}} -pin_size {{{p['size'][0]:.4f} {p['size'][1]:.4f}}} -force_to_die_boundary")
    hints = []
    T += ["", "# ---- OPTIONAL register placement hints (uncomment after synthesis; flops of ft<k>_s<j> at the stage",
          "# coordinate along the path and at their bit's pin track across it; detailed_placement legalises).",
          "# proc ft_place_stage {pfx x y horiz pins} {",
          "#   foreach inst [[ord::get_db_block] getInsts] {",
          "#     set n [$inst getName]",
          "#     if {[string first $pfx $n] != 0 || ![regexp {\\[(\\d+)\\]} $n -> b]} { continue }",
          "#     if {$b >= [llength $pins]} { continue }",
          "#     set t [lindex $pins $b]",
          "#     if {$horiz} { set px $x; set py $t } else { set px $t; set py $y }",
          "#     $inst setLocation [expr {round($px * [[ord::get_db_block] getDbUnitsPerMicron])}] \\",
          "#         [expr {round($py * [[ord::get_db_block] getDbUnitsPerMicron])}]",
          "#     $inst setPlacementStatus PLACED",
          "#   }", "# }"]
    pb = {q["name"]: q for q in spec["ports"]}
    for path in spec["paths"]:
        k = path["path"]
        for j, xy in enumerate(path.get("regs_um", [])):
            # the leg a register sits on: the port whose band contains its across-coordinate (L paths), else the in port
            pp = pb[path["in"]]
            for nm in (path["in"], path["out"]):
                q = pb[nm]
                c = xy[1] if q["face"] in ("W", "E") else xy[0]
                if q["lo"] - EPS <= c <= q["hi"] + EPS:
                    pp = q
                    break
            horiz = pp["face"] in ("W", "E")
            tracks = [by_pin[b]["offset"] for b in port_bit_names(pp["name"], int(path["bits"]))]
            hints.append(dict(inst=f"ft{k}_s{j}", xy=xy, horiz=horiz, bit_tracks=tracks))
            T.append(f"# ft_place_stage ft{k}_s{j} {xy[0]} {xy[1]} {int(horiz)} {{{' '.join(f'{t:g}' for t in tracks)}}}")
    js = dict(schema="opentallas.die_feedthrough.pins.v1", variant=spec["variant"], outline=spec["outline"], dbu=dbu,
              pins=pl, reg_hints=hints)
    return "\n".join(T) + "\n", js


# ---------------------------------------------------------------------------------------------------- 3. contract
def _lnum(name):
    m = re.search(r"(\d+)$", name)
    return int(m.group(1)) if m else 0


def corridor_rects(spec, margin=2.0):
    """ft corridors (master frame): per path the band from the in pin range to the out pin range (straight or L)."""
    W, H = spec["outline"]
    pb = {p["name"]: p for p in spec["ports"]}
    rects = []
    for path in spec["paths"]:
        a, b = pb[path["in"]], pb[path["out"]]
        rs = []
        ha, hb = a["face"] in ("W", "E"), b["face"] in ("W", "E")
        if ha and hb:
            rs.append((0, min(a["lo"], b["lo"]), W, max(a["hi"], b["hi"])))
        elif not ha and not hb:
            rs.append((min(a["lo"], b["lo"]), 0, max(a["hi"], b["hi"]), H))
        else:
            h, v = (a, b) if ha else (b, a)   # h: band on a W/E face (y range), v: band on N/S face (x range)
            xs = (0, v["hi"]) if h["face"] == "W" else (v["lo"], W)
            ys = (0, h["hi"]) if v["face"] == "S" else (h["lo"], H)
            rs.append((xs[0], h["lo"], xs[1], h["hi"]))
            rs.append((v["lo"], ys[0], v["hi"], ys[1]))
        for xy in path.get("regs_um", []):   # registers off the bands (plan jogs): cover them too
            if not any(r[0] - EPS <= xy[0] <= r[2] + EPS and r[1] - EPS <= xy[1] <= r[3] + EPS for r in rs):
                rs.append((xy[0], xy[1], xy[0], xy[1]))
        for r in rs:
            rects.append((max(0.0, r[0] - margin), max(0.0, r[1] - margin), min(W, r[2] + margin),
                          min(H, r[3] + margin)))
    return rects


def complement_rects(W, H, holes):
    """outline minus the union of holes, as disjoint rectangles (coordinate compression, row runs merged)."""
    xs = sorted({0.0, float(W)} | {min(max(v, 0.0), W) for r in holes for v in (r[0], r[2])})
    ys = sorted({0.0, float(H)} | {min(max(v, 0.0), H) for r in holes for v in (r[1], r[3])})
    out = []
    for yi in range(len(ys) - 1):
        y0, y1 = ys[yi], ys[yi + 1]
        if y1 - y0 < EPS:
            continue
        run = None
        for xi in range(len(xs) - 1):
            x0, x1 = xs[xi], xs[xi + 1]
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            free = x1 - x0 > EPS and not any(r[0] <= cx <= r[2] and r[1] <= cy <= r[3] for r in holes)
            if free:
                run = (run[0], x1) if run else (x0, x1)
            elif run:
                out.append((run[0], y0, run[1], y1))
                run = None
        if run:
            out.append((run[0], y0, run[1], y1))
    # merge vertically identical runs
    out.sort(key=lambda r: (r[0], r[2], r[1]))
    merged = []
    for r in out:
        if merged and abs(merged[-1][0] - r[0]) < EPS and abs(merged[-1][2] - r[2]) < EPS and \
                abs(merged[-1][3] - r[1]) < EPS:
            merged[-1] = (merged[-1][0], merged[-1][1], merged[-1][2], r[3])
        else:
            merged.append(r)
    return merged


def gen_contract(spec, margin=2.0, signal_min="M2", base_adjust=0.5):
    lc = spec.get("layer_contract", {})
    smax, ftl, pgmax = lc.get("signal_max", "M7"), list(lc.get("ft_layers", ["M8", "M9"])), lc.get("pg_max", "M7")
    top = max(ftl, key=_lnum)
    W, H = spec["outline"]
    corr = corridor_rects(spec, margin)
    fence = complement_rects(W, H, corr)
    ports = ft_ports(spec)
    js = dict(schema="opentallas.die_feedthrough.contract.v1", variant=spec["variant"], block=spec.get("block"),
              signal_min=signal_min, signal_max=smax, ft_layers=ftl, pg_max=pgmax, route_max=top,
              ft_nets=[p["name"] for p in ports] + [f"ft{p['path']}_p*" for p in spec["paths"]],
              ft_insts=[f"ft{p['path']}_s{j}" for p in spec["paths"] for j in range(int(p["stages"]))],
              obs_rule="export exact routed geometry; no full-footprint blanket on M8/M9",
              mechanism="global signal range {}-{} + region adjustment 1.0 on {} outside the ft corridors "
                        "(OpenROAD 26Q3 has no per-net layer range)".format(signal_min, top, "/".join(ftl)),
              orfs_env=dict(MIN_ROUTING_LAYER=signal_min, MAX_ROUTING_LAYER=top,
                            FASTROUTE_TCL=f"{spec['variant']}.fastroute.tcl"),
              corridors=[[round(v, 4) for v in r] for r in corr], fence=[[round(v, 4) for v in r] for r in fence])
    T = [f"# GENERATED by pushdown.py contract: block layer contract of {spec['variant']} (ORFS FASTROUTE_TCL).",
         f"# Signals {signal_min}-{smax}; PG <= {pgmax}; {'/'.join(ftl)} for ft nets only.  OpenROAD 26Q3 has no per-net",
         "# layer range, so the ft layers get ZERO global-routing capacity outside the ft corridors (region adjustment",
         "# 1.0); inside the corridors they are open.  Run ft_audit.tcl after global_route.",
         f"# ORFS: export MIN_ROUTING_LAYER={signal_min} MAX_ROUTING_LAYER={top} FASTROUTE_TCL=<this file>",
         f"if {{[info exists ::env(ROUTING_LAYER_ADJUSTMENT)]}} {{ set ft_adj $::env(ROUTING_LAYER_ADJUSTMENT) }} "
         f"else {{ set ft_adj {base_adjust} }}",
         f"set_global_routing_layer_adjustment {signal_min}-{smax} $ft_adj",
         f"set_global_routing_layer_adjustment {min(ftl, key=_lnum)}-{top} 0.0",
         f"set_routing_layers -signal {signal_min}-{top}",
         f"# fence: {len(fence)} rectangles x {len(ftl)} layers (outline {W} x {H} um minus {len(corr)} corridors)"]
    for r in fence:
        for lay in ftl:
            T.append(f"set_global_routing_region_adjustment {{{r[0]:.4f} {r[1]:.4f} {r[2]:.4f} {r[3]:.4f}}} "
                     f"-layer {lay} -adjustment 1.0")
    audit = gen_audit_tcl(spec, ftl, corr)
    return "\n".join(T) + "\n", js, audit


def gen_audit_tcl(spec, ftl, corr):
    """post-GRT audit: non-ft nets with guides on ft layers (FAIL if outside a corridor)."""
    return f"""# GENERATED by pushdown.py contract: ft layer audit for {spec['variant']} (source after global_route).
# ft net = net on an ft<k>_* port, or on a pin of an ft<k>_s<j>* instance, closed through BUF/INV/HB cells.
proc ft_audit {{}} {{
  set block [ord::get_db_block]
  set dbu [$block getDbUnitsPerMicron]
  set ftl {{{' '.join(ftl)}}}
  set corr {{{' '.join('{' + ' '.join(f'{v:.4f}' for v in r) + '}' for r in corr)}}}
  set ft [dict create]
  set work {{}}
  foreach n [$block getNets] {{
    set nm [$n getName]
    set hit [regexp {{^ft[0-9]+_}} $nm]
    if {{!$hit}} {{
      foreach it [$n getITerms] {{ if {{[regexp {{^ft[0-9]+_s[0-9]+}} [[$it getInst] getName]]}} {{ set hit 1; break }} }}
    }}
    if {{$hit}} {{ dict set ft $nm 1; lappend work $n }}
  }}
  while {{[llength $work]}} {{
    set n [lindex $work end]; set work [lrange $work 0 end-1]
    foreach it [$n getITerms] {{
      set inst [$it getInst]
      if {{![regexp {{^(BUF|INV|HB)}} [[$inst getMaster] getName]]}} {{ continue }}
      foreach it2 [$inst getITerms] {{
        set n2 [$it2 getNet]
        if {{$n2 eq "NULL" || [$n2 getSigType] ne "SIGNAL"}} {{ continue }}
        if {{![dict exists $ft [$n2 getName]]}} {{ dict set ft [$n2 getName] 1; lappend work $n2 }}
      }}
    }}
  }}
  set bad 0; set inside 0
  foreach n [$block getNets] {{
    if {{[dict exists $ft [$n getName]]}} {{ continue }}
    foreach g [$n getGuides] {{
      if {{[lsearch -exact $ftl [[$g getLayer] getName]] < 0}} {{ continue }}
      set b [$g getBox]
      set cx [expr {{([$b xMin] + [$b xMax]) / 2.0 / $dbu}}]
      set cy [expr {{([$b yMin] + [$b yMax]) / 2.0 / $dbu}}]
      set in 0
      foreach r $corr {{ lassign $r x0 y0 x1 y1; if {{$cx >= $x0 && $cx <= $x1 && $cy >= $y0 && $cy <= $y1}} {{ set in 1; break }} }}
      if {{$in}} {{ incr inside }} else {{ incr bad; if {{$bad <= 20}} {{ puts "FT_AUDIT non-ft [$n getName] on [[$g getLayer] getName] at $cx $cy" }} }}
    }}
  }}
  puts "FT_AUDIT ft_nets [dict size $ft] nonft_ft_layer_guides_outside $bad inside_corridors $inside"
  if {{$bad > 0}} {{ puts "FT_AUDIT FAIL" }} else {{ puts "FT_AUDIT PASS" }}
  return $bad
}}
ft_audit
"""


# ---------------------------------------------------------------------------------------------------- 3b. LEF check
def parse_lef_macro(text, name=None):
    """-> {name, size(w, h), pins{pin: [(layer, (x0, y0, x1, y1))]}, obs[(layer, rect)]} of MACRO name (or the first)."""
    toks = re.sub(r"#[^\n]*", "", text)
    stmts = [s.split() for s in toks.replace(";", " ;\n").split("\n")]
    out, cur, pin, in_obs, layer = None, None, None, False, None
    for st in stmts:
        if not st:
            continue
        k = st[0]
        if k == "MACRO" and cur is None and (name is None or st[1] == name):
            cur = dict(name=st[1], size=None, pins={}, obs=[])
        elif cur is None:
            continue
        elif k == "SIZE":
            cur["size"] = (float(st[1]), float(st[3]))
        elif k == "PIN":
            pin, in_obs = st[1], False
            cur["pins"].setdefault(pin, [])
        elif k == "OBS":
            in_obs, pin = True, None
        elif k == "LAYER":
            layer = st[1]
        elif k == "RECT":
            v = [x for x in st[1:] if x != ";"]
            if v and v[0] == "MASK":
                v = v[2:]
            x0, y0, x1, y1 = map(float, v[:4])
            r = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
            if in_obs:
                cur["obs"].append((layer, r))
            elif pin is not None:
                cur["pins"][pin].append((layer, r))
        elif k == "END" and len(st) > 1 and st[1] == cur["name"]:
            out = cur
            break
        elif k == "END" and len(st) > 1 and pin is not None and st[1] == pin:
            pin = None
        elif k == "END" and len(st) == 1 and in_obs:
            in_obs = False
    if out is None and cur is not None:
        out = cur
    if out is None:
        raise ValueError(f"MACRO {name or '(any)'} not found")
    return out


def union_area(rects):
    """area of the union of axis-parallel rectangles (x sweep over y-interval unions)."""
    if not rects:
        return 0.0
    xs = sorted({r[0] for r in rects} | {r[2] for r in rects})
    area = 0.0
    for x0, x1 in zip(xs, xs[1:]):
        iv = sorted((r[1], r[3]) for r in rects if r[0] <= x0 and r[2] >= x1)
        tot, cs, ce = 0.0, None, None
        for a, b in iv:
            if cs is None or a > ce:
                if cs is not None:
                    tot += ce - cs
                cs, ce = a, b
            else:
                ce = max(ce, b)
        if cs is not None:
            tot += ce - cs
        area += tot * (x1 - x0)
    return area


def check_abstract(lef_text, spec, max_cover=0.05, allow_stripes=None, macro=None, tol_um=0.01, layers=None):
    """-> {ok, fails[], cover{layer}, stripe_cover{layer}}.  allow_stripes = (width_um, pitch_um) or None."""
    if not macro:
        macro = next((n for n in (spec.get("variant"), spec.get("master")) if _has_macro(lef_text, n)), None)
    m = parse_lef_macro(lef_text, macro)
    W, H = m["size"] or spec["outline"]
    ftl = spec.get("layer_contract", {}).get("ft_layers", ["M8", "M9"])
    fails, cover, scover = [], {}, {}
    for lay in ftl:
        rs = [r for l_, r in m["obs"] if l_ == lay]
        stripes = []
        if allow_stripes:
            sw = allow_stripes[0] + tol_um
            stripes = [r for r in rs if min(r[2] - r[0], r[3] - r[1]) <= sw]
            rs = [r for r in rs if r not in stripes]
        cover[lay] = round(union_area(rs) / (W * H), 5)
        scover[lay] = round(union_area(stripes) / (W * H), 5)
        if cover[lay] > max_cover:
            fails.append(f"OBS {lay} covers {cover[lay]:.1%} of the outline (> {max_cover:.0%}): blanket on an ft layer")
        if allow_stripes and scover[lay] > 1.25 * allow_stripes[0] / allow_stripes[1]:
            fails.append(f"OBS {lay} stripes cover {scover[lay]:.1%} (> 1.25 x {allow_stripes[0]}/{allow_stripes[1]})")
    layers = layers or load_layers()
    ports = ft_ports(spec)
    nck = {q["data_port"] for q in ports if q["role"] == "clock" and q.get("data_port")}
    for p in ports:
        dp = p if p["role"] == "data" else next((q for q in ports if q["name"] == p.get("data_port")), p)
        lo, hi, _ = slot_range(dp, dp["bits"] + (dp["name"] in nck), layers[dp["layer"]]) \
            if dp["layer"] in layers else (dp["lo"], dp["hi"], False)
        for b in port_bit_names(p["name"], p["bits"]):
            shapes = m["pins"].get(b)
            if not shapes:
                fails.append(f"pin {b} missing")
                continue
            on = [r for l_, r in shapes if l_ == p["layer"]]
            if not on:
                fails.append(f"pin {b} not on {p['layer']} (layers {sorted({l_ for l_, _ in shapes})})")
                continue
            ok = False
            for r in on:
                face_ok = {"W": r[0] <= tol_um, "E": r[2] >= W - tol_um, "S": r[1] <= tol_um,
                           "N": r[3] >= H - tol_um}[p["face"]]
                c = (r[1] + r[3]) / 2 if p["face"] in ("W", "E") else (r[0] + r[2]) / 2
                if face_ok and lo - tol_um <= c <= hi + tol_um:
                    ok = True
            if not ok:
                fails.append(f"pin {b} not on face {p['face']} within [{lo}, {hi}]")
    return dict(ok=not fails, macro=m["name"], fails=fails, cover=cover, stripe_cover=scover)


def _has_macro(text, name):
    return bool(name) and re.search(r"^\s*MACRO\s+" + re.escape(name) + r"\s*$", text, re.M) is not None


# ---------------------------------------------------------------------------------------------------- 4. die ECO
def _split_concat(expr):
    e = expr.strip()
    if e.startswith("{") and e.endswith("}"):
        return [x.strip() for x in e[1:-1].split(",") if x.strip()]
    return [e] if e else []


def read_die_insts(path, names):
    """stream die.v statements; -> {inst: {master, pins{pin: [nets MSB..LSB]}}} for the requested instance names."""
    want = set(names)
    clean = {n.lstrip("\\"): n for n in want}
    out = {}
    op = gzip.open if str(path).endswith(".gz") else open
    buf = ""
    with op(path, "rt") as f:
        for chunk in iter(lambda: f.read(1 << 22), ""):
            buf += chunk
            parts = buf.split(";")
            buf = parts.pop()
            for st in parts:
                m = re.match(r"\s*([A-Za-z_][\w$]*)\s+(\\\S+|[A-Za-z_][\w$]*)\s*\(", st)
                if not m:
                    continue
                inst = m.group(2).lstrip("\\")
                if inst not in clean:
                    continue
                pins = {}
                for pm in re.finditer(r"\.(\w+)\s*\(\s*(\{[^}]*\}|[^()]*?)\s*\)", st[m.end():]):
                    pins[pm.group(1)] = _split_concat(pm.group(2))
                out[clean[inst]] = dict(master=m.group(1), pins=pins)
                if len(out) == len(want):
                    return out
    return out


def _tcl(s):
    return "{" + s + "}"


def _data_pins(rec):
    """relay data pin pair (in, out): i/o, a/b, d/q, else the unique equal-width pair (census convention)."""
    pins = rec["pins"]
    for a, b in (("i", "o"), ("a", "b"), ("y", "b"), ("d", "q")):
        if a in pins and b in pins:
            return a, b
    return None, None


def gen_die_eco(spec_dir, plan, die_verilog):
    specs = {}
    for f in sorted(Path(spec_dir).glob("*.json")):
        s = load_json(f)
        if isinstance(s, dict) and s.get("schema") == SPEC_SCHEMA:
            specs[s["block"]] = s
    lanes = [l for l in plan.get("lanes", []) if not l.get("keep_channel") and
             any(s.get("kind") == "block" for s in l.get("segments", []))]
    need = {r for l in lanes for r in l.get("relays", [])}
    insts = read_die_insts(die_verilog, need) if need else {}
    ops, recs = [], []
    for lane in lanes:
        rec = dict(lane=lane["id"], bits=lane["bits"], relays=list(lane.get("relays", [])), todo=[], ops=0)
        chain = [r for r in lane.get("relays", [])]
        miss = [r for r in chain if r not in insts]
        if not chain or miss:
            rec["todo"].append(f"relays missing in die.v or plan: {miss or 'no relays listed'}")
            recs.append(rec)
            continue
        di, do = _data_pins(insts[chain[0]])
        _, do_last = _data_pins(insts[chain[-1]])
        if di is None or do_last is None:
            rec["todo"].append("relay data pins not recognised (i/o, a/b, d/q)")
            recs.append(rec)
            continue
        src = insts[chain[0]]["pins"][di]
        dst = insts[chain[-1]]["pins"][do_last]
        n = lane["bits"]
        if len(src) != n or len(dst) != n:
            rec["todo"].append(f"width mismatch: src {len(src)} dst {len(dst)} lane {n} (taps / partial chains)")
            recs.append(rec)
            continue
        src, dst = list(reversed(src)), list(reversed(dst))   # concat MSB..LSB -> bit index
        mid = set()   # data nets between relays of the chain (+ the forwarded clock nets between them)
        for r in chain:
            pi_, po_ = _data_pins(insts[r])
            for p_ in (pi_, po_):
                mid.update(insts[r]["pins"].get(p_, []))
        ck_first = (insts[chain[0]]["pins"].get("ck") or [None])[0]
        ck_last = (insts[chain[-1]]["pins"].get("ck_o") or [None])[0]
        mid.update((insts[r]["pins"].get("ck_o") or [None])[0] for r in chain[:-1])
        mid -= set(src) | set(dst) | {ck_first, ck_last, None}
        lo = len(ops)
        for r in chain:
            ops.append(dict(op="delete_instance", inst=r))
        for nn in sorted(x for x in mid if x and not re.match(r"^\d*'[bhd]", x)):
            ops.append(dict(op="delete_net", net=nn))
        cur, cur_ck = src, ck_first
        segs = [s for s in lane["segments"] if s.get("kind") == "block"]
        if lane.get("channel_stages"):
            rec["todo"].append(f"{lane['channel_stages']} new channel relay stage(s) at t={lane.get('channel_regs_t')} "
                               "not inserted (make_instance of the die relay master + placement): TODO")
        for si, s in enumerate(segs):
            sp = specs.get(s["block"])
            path = next((p for p in (sp or {}).get("paths", []) if p.get("lane") == lane["id"]), None)
            if path is None:
                rec["todo"].append(f"no ft spec path for lane {lane['id']} in block {s['block']}")
                break
            last = si == len(segs) - 1
            for b in range(n):
                ops.append(dict(op="connect_pin", net=cur[b], pin=f"{s['block']}/{port_bit_names(path['in'], n)[b]}"))
            nxt = dst if last else [f"ftl_{lane['id']}_{si}[{b}]" for b in range(n)]
            for b in range(n):
                if not last:
                    ops.append(dict(op="make_net", net=nxt[b]))
                ops.append(dict(op="connect_pin", net=nxt[b], pin=f"{s['block']}/{port_bit_names(path['out'], n)[b]}"))
            if sp.get("clock") == "forwarded":
                if cur_ck is None or (last and ck_last is None):
                    rec["todo"].append(f"{s['block']}: forwarded clock nets not found on the relay ck/ck_o pins")
                else:
                    ops.append(dict(op="connect_pin", net=cur_ck, pin=f"{s['block']}/{clock_port_name(sp, path, 'input')}"))
                    nck = ck_last if last else f"ftl_{lane['id']}_{si}_ck"
                    if not last:
                        ops.append(dict(op="make_net", net=nck))
                    ops.append(dict(op="connect_pin", net=nck, pin=f"{s['block']}/{clock_port_name(sp, path, 'output')}"))
                    cur_ck = nck
            cur = nxt
        rec["todo"].append("census relays[] is the LONGEST chain only: other chains of the group (taps) need review")
        rec["todo"].append("MX/MY-oriented blocks mirror bit order on their face: confirm neighbour bit alignment")
        rec["ops"] = len(ops) - lo
        recs.append(rec)
    T = ["# GENERATED by pushdown.py die: feedthrough die ECO (best-effort skeleton; review the TODOs in die_eco.json).",
         "# Order: delete relays and their internal nets, then reconnect lanes through the block ft ports."]
    for o in ops:
        if o["op"] == "delete_instance":
            T.append(f"delete_instance {_tcl(o['inst'])}")
        elif o["op"] == "delete_net":
            T.append(f"delete_net {_tcl(o['net'])}")
        elif o["op"] == "make_net":
            T.append(f"make_net {_tcl(o['net'])}")
        elif o["op"] == "connect_pin":
            T.append(f"connect_pin {_tcl(o['net'])} {_tcl(o['pin'])}")
    js = dict(schema="opentallas.die_feedthrough.die_eco.v1", plan_lanes=len(plan.get("lanes", [])),
              pushed_lanes=len(lanes), relays_deleted=sum(1 for o in ops if o["op"] == "delete_instance"),
              lanes=recs, ops=ops)
    return js, "\n".join(T) + "\n"


# ---------------------------------------------------------------------------------------------------- CLI
def _write(path, text):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w") as f:
        f.write(text if isinstance(text, str) else json.dumps(text, indent=1) + "\n")
    print(path)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("wrapper")
    w.add_argument("spec")
    w.add_argument("--kit-top", required=True)
    g = w.add_mutually_exclusive_group(required=True)
    g.add_argument("--kit-ports")
    g.add_argument("--kit-verilog")
    w.add_argument("--out", required=True)
    w.add_argument("--station-module", default="ot_dvrly_st")
    w.add_argument("--hc", type=int, default=1, help="ot_dvrly_st HC (1 = half-cycle forwarded, S81)")
    w.add_argument("--clock", default=None)
    w.add_argument("--reset", default=None)
    w.add_argument("--kit-param", action="append", default=[], metavar="NAME=VAL")
    p = sub.add_parser("pins")
    p.add_argument("spec")
    p.add_argument("--out", required=True)
    p.add_argument("--layers")
    p.add_argument("--dbu", type=int, default=1000)
    p.add_argument("--pin-len-um", type=float, default=0.32)
    c = sub.add_parser("contract")
    c.add_argument("spec")
    c.add_argument("--out", required=True)
    c.add_argument("--margin-um", type=float, default=2.0)
    c.add_argument("--signal-min", default="M2")
    c.add_argument("--adjust", type=float, default=0.5, help="M2..signal_max adjustment if ROUTING_LAYER_ADJUSTMENT unset")
    k = sub.add_parser("check")
    k.add_argument("spec")
    k.add_argument("--lef", required=True)
    k.add_argument("--macro")
    k.add_argument("--max-cover", type=float, default=0.05)
    k.add_argument("--allow-stripes", help="WIDTH:PITCH um, e.g. 0.48:8.64")
    d = sub.add_parser("die")
    d.add_argument("spec_dir")
    d.add_argument("--plan", required=True)
    d.add_argument("--die-verilog", required=True)
    d.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    if a.cmd == "die":
        js, tcl = gen_die_eco(a.spec_dir, load_json(a.plan), a.die_verilog)
        _write(os.path.join(a.out, "die_eco.json"), js)
        _write(os.path.join(a.out, "die_eco.tcl"), tcl)
        print(f"pushed lanes {js['pushed_lanes']}, relays deleted {js['relays_deleted']}, "
              f"lanes with TODOs {sum(1 for l in js['lanes'] if l['todo'])}")
        return 0
    spec = load_spec(a.spec)
    v = spec["variant"]
    if a.cmd == "wrapper":
        if a.kit_verilog:
            kp = parse_kit_ports_verilog(Path(a.kit_verilog).read_text(), a.kit_top)
        else:
            kp = parse_kit_ports_json(load_json(a.kit_ports))
        params = dict(x.split("=", 1) for x in a.kit_param)
        text, side = gen_wrapper(spec, a.kit_top, kp, station=a.station_module, hc=a.hc, clock=a.clock,
                                 reset=a.reset, kit_params=params)
        _write(os.path.join(a.out, f"{v}.v"), text)
        _write(os.path.join(a.out, f"{v}.ft.json"), side)
    elif a.cmd == "pins":
        tcl, js = gen_pins(spec, load_layers(a.layers), a.pin_len_um, a.dbu)
        _write(os.path.join(a.out, f"{v}.pins.tcl"), tcl)
        _write(os.path.join(a.out, f"{v}.pins.json"), js)
    elif a.cmd == "contract":
        tcl, js, audit = gen_contract(spec, a.margin_um, a.signal_min, a.adjust)
        _write(os.path.join(a.out, f"{v}.fastroute.tcl"), tcl)
        _write(os.path.join(a.out, f"{v}.contract.json"), js)
        _write(os.path.join(a.out, f"{v}.ft_audit.tcl"), audit)
    elif a.cmd == "check":
        st = tuple(float(x) for x in a.allow_stripes.split(":")) if a.allow_stripes else None
        r = check_abstract(Path(a.lef).read_text(), spec, a.max_cover, st, a.macro)
        print(json.dumps(r, indent=1))
        return 0 if r["ok"] else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
