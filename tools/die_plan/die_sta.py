#!/usr/bin/env python3
"""Die-level STA for top-down die plans (G4): abstract mode on partition ILMs, flat mode on stitched netlists.

    die_sta.py ilm   --netlist P/6_final.v --spef P/6_final.spef --out DIR/<type> [--libs ...]   # one abstract
    die_sta.py run   --top die_top.v --parts PARTS --out DIR [--mode ilm|flat|etm] [--corner TT|FF|SS ...]
    die_sta.py compare A/die_sta.json B/die_sta.json [--tol 2]                                  # seam agreement
    die_sta.py replica --netlist P/6_final.v --spef P/6_final.spef --n N --out DIR             # capacity vehicle

PARTS holds one directory per partition MODULE or type (``<dir>/6_final.v`` + ``6_final.spef``, as run_die.sh
expects), found through the module name written in each netlist.  The die top is a structural netlist that
instantiates the partitions and joins them with zero-length abutment wires (gen.py assembly die_top_struct.v, or the
pair die_top.v).  Seams are discovered from the die top: every internal die net that joins an output of one
partition to an input of another; they are reported per (destination instance, destination bus).

Modes
-----
* ``flat`` (signoff): every partition's routed netlist + its own SPEF (read_spef -path <instance>), stitched under
  the die top.  Exact, memory heavy (see the capacity note in README).
* ``ilm`` (continuous die check, default): every partition replaced by its interface logic model, extracted here from
  the routed netlist: the fan-out cone of every non-clock input to the first register, the fan-in cone of every
  output back to the launching registers, the clock network to those registers, and every other cell on a kept net
  as a side load (that input pin only), so each kept net keeps its exact routed RC and pin load.  The ILM SPEF is the
  partition SPEF filtered to the kept nets.  Boundary paths are timed with the same cells and parasitics as flat, so
  seam slacks agree with flat to numerical noise at every corner; internal reg-to-reg paths are dropped.  The ILM is
  corner independent (one abstract per partition type).
* ``etm``: OpenSTA write_timing_model (.lib) per partition type and corner.  OpenSTA be771a0 writes clock->output
  arcs from the MAX arrival only (MakeTimingModel::min_max_ is fixed to max), so ETM hold at a seam is optimistic by
  the clk->q max/min spread; etm is kept for setup cross-checks only and is never a hold verdict.

Constraints (AGENTS.md): one clock on the die clk port, period from --period-ps (default 833.333 = 1.2 GHz),
propagated through each partition's own routed tree, setup uncertainty 60 ps / hold 25 ps.  Signoff (owner,
2026-10-24): setup at TT, hold at FF, face-flop clock spread <= 80 ps per partition at TT and FF (``--corner TT
--corner FF``, the default); SS may be run for information and never gates.  Both checks are reported at every
corner.  Die spine:
``ideal`` (taps fed at the plan's common latency: the die top's zero-length clk wires), ``branch`` (spine_branch.json
of gen.py assembly: a generated clock with source latency offset_ps on every tap pin), or the routed die SPEF
(``--die-spef``) for channel seams and the routed spine.  Die IO ports of the window are unconstrained (not seams).

The result is DIR/die_sta.json: per corner, per seam group: worst setup (max) / hold (min) slack, path and violating
endpoint counts, TNS, launch/capture clock arrival (skew), and the worst start/end points; plus run time and peak RSS.
"""
import argparse
import gzip
import json
import os
import re
import resource
import shutil
import subprocess
import sys
import time
from collections import defaultdict, deque
from pathlib import Path

UNC_SETUP_PS = 60.0
UNC_HOLD_PS = 25.0
PERIOD_PS = 833.333
SIGNOFF = {"TT": "max", "FF": "min"}          # AGENTS.md (owner 2026-10-24): setup at TT, hold at FF; never SS
SPREAD_PS = 80.0                               # face-flop (pin-flop) clock arrival spread per partition
ORFS_LIBS = ("asap7sc7p5t_AO_RVT_{c}_nldm_211120.lib.gz", "asap7sc7p5t_INVBUF_RVT_{c}_nldm_220122.lib.gz",
             "asap7sc7p5t_OA_RVT_{c}_nldm_211120.lib.gz", "asap7sc7p5t_SIMPLE_RVT_{c}_nldm_211120.lib.gz",
             "asap7sc7p5t_SEQ_RVT_{c}_nldm_220123.lib", "asap7sc7p5t_DFFHQNH2V2X_RVT_{c}_nldm_FAKE.lib",
             "asap7sc7p5t_DFFHQNV2X_RVT_{c}_nldm_FAKE.lib")
LIB_DIRS = ("/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM", "~/.cache/opentallas/asap7_nldm")
ORFS_IMAGE = os.environ.get("OT_ORFS_IMAGE", "openroad/orfs:asap7lock")
CLOCK_PORT_RE = r"^clk(_t\d+)?$"


# ----------------------------------------------------------------------------------------------------------- libraries
def lib_dir(arg=None):
    """ASAP7 NLDM directory: --libdir, the ORFS image path, or the per-user cache (filled from the ORFS image)."""
    for d in ([arg] if arg else []) + [os.path.expanduser(x) for x in LIB_DIRS]:
        if d and Path(d, ORFS_LIBS[0].format(c="TT")).is_file():
            return Path(d)
    if arg:
        raise SystemExit(f"die_sta: no ASAP7 NLDM libs in {arg}")
    cache = Path(os.path.expanduser(LIB_DIRS[1]))
    cache.mkdir(parents=True, exist_ok=True)
    dk = ["docker"] if shutil.which("docker") and os.access("/var/run/docker.sock", os.W_OK) else ["sudo", "docker"]
    subprocess.run(dk + ["run", "--rm", "-v", f"{cache}:/o", ORFS_IMAGE, "bash", "-c",
                         f"cp /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT* /o/ && "
                         f"chown -R {os.getuid()}:{os.getgid()} /o"], check=True)
    return cache


def corner_libs(corner, libdir=None, extra=()):
    d = lib_dir(libdir)
    out = [str(d / f.format(c=corner)) for f in ORFS_LIBS]
    out += [x.format(c=corner, corner=corner, cl=corner.lower()) for x in extra]
    missing = [x for x in out if not Path(x).is_file()]
    if missing:
        raise SystemExit(f"die_sta: missing liberty {missing}")
    return out


def _open(p):
    return gzip.open(p, "rt", errors="replace") if str(p).endswith(".gz") else open(p, errors="replace")


def _blocks(text, kind):
    """yield (name, body) of every `kind (name) {...}` group in text (brace matched)."""
    pat = re.compile(r"\b" + kind + r"\s*\(\s*\"?([^\")]*)\"?\s*\)\s*\{")
    i = 0
    while True:
        m = pat.search(text, i)
        if not m:
            return
        depth, j = 1, m.end()
        while depth and j < len(text):
            c = text[j]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            j += 1
        yield m.group(1).strip(), text[m.end():j - 1]
        i = j


def read_liberty_cells(paths):
    """{cell: {"pins": {pin: "input"|"output"|"inout"}, "clock": {pins}, "seq": bool}} from liberty files.
    seq = the cell holds state (ff / latch / statetable / integrated clock gate) or has setup/clock->q arcs (macros);
    timing through a seq cell starts / ends at it.  Bus pins are listed under their base name."""
    cells = {}
    for p in paths:
        with _open(p) as f:
            text = f.read()
        for cname, body in _blocks(text, "cell"):
            pins, clk = {}, set()
            for kind in ("pin", "bus"):
                for pn, pb in _blocks(body, kind):
                    m = re.search(r"\bdirection\s*:\s*\"?(\w+)", pb)
                    for name in pn.split(","):
                        name = name.strip()
                        if kind == "pin" and name in pins:
                            continue
                        pins[name] = m.group(1) if m else "input"
                        if re.search(r"\bclock\s*:\s*\"?true", pb) or re.search(r"\bclock_gate_clock_pin\s*:\s*\"?true", pb):
                            clk.add(name)
            seq = bool(re.search(r"\b(ff|latch|ff_bank|latch_bank|statetable)\s*\(", body)
                       or "clock_gating_integrated_cell" in body
                       or re.search(r"timing_type\s*:\s*\"?(setup_|hold_|rising_edge|falling_edge)", body))
            cells[cname] = dict(pins=pins, clock=clk, seq=seq)
    return cells


# ------------------------------------------------------------------------------------------------------------- verilog
_TOK = re.compile(r"\\\S+|[A-Za-z_][A-Za-z0-9_$]*|\d+'[sS]?[bBhHdDoO][0-9a-fA-FxXzZ_?]+|\d+|//[^\n]*|/\*.*?\*/|\S",
                  re.S)


def vnorm(name):
    """canonical net / instance name: escaped identifier without the backslash, SPEF escapes removed."""
    if name.startswith("\\"):
        name = name[1:]
    return name.replace("\\", "")


class Netlist:
    """a flat structural Verilog module as OpenROAD write_verilog writes it (one module, cell instances, assigns)."""

    def __init__(self, name):
        self.name = name
        self.ports = []                 # [(dir, name, msb, lsb)] (msb None = scalar), header order
        self.wires = []                 # [(name, msb, lsb)]
        self.insts = []                 # [[cell, inst, [(pin, [net tokens])]]]
        self.assigns = []               # [(lhs token, rhs token)]

    def expand_buses(self):
        """whole-bus references ('w' for a declared [m:l] wire / port) -> their bits, msb first."""
        rng = {n: (m, l) for _, n, m, l in self.ports if m is not None}
        rng.update({n: (m, l) for n, m, l in self.wires if m is not None})
        if not rng:
            return

        def ex(bits):
            out = []
            for b in bits:
                if b in rng:
                    m, l = rng[b]
                    st = -1 if m >= l else 1
                    out += [f"{b}[{k}]" for k in range(m, l + st, st)]
                else:
                    out.append(b)
            return out
        for row in self.insts:
            row[2] = [(p, ex(bits)) for p, bits in row[2]]
        self.assigns = [(x, y) for l, r in self.assigns for x, y in zip(ex([l]), ex([r]))]

    def port_bits(self):
        for d, n, msb, lsb in self.ports:
            if msb is None:
                yield d, n, n
            else:
                step = -1 if msb >= lsb else 1
                for b in range(msb, lsb + step, step):
                    yield d, n, f"{n}[{b}]"


def _expr(toks, i):
    """parse a net expression at toks[i] -> ([bit tokens], next i).  Bit tokens: 'name', 'name[3]', '\\esc', const."""
    t = toks[i]
    if t == "{":
        out, i = [], i + 1
        while toks[i] != "}":
            if toks[i] == ",":
                i += 1
                continue
            o, i = _expr(toks, i)
            out += o
        return out, i + 1
    if t == ")":
        return [], i
    if i + 1 < len(toks) and toks[i + 1] == "[":
        j = toks.index("]", i)
        sel = "".join(toks[i + 2:j])
        if ":" in sel:
            a, b = (int(x) for x in sel.split(":"))
            step = -1 if a >= b else 1
            return [f"{vnorm(t)}[{k}]" for k in range(a, b + step, step)], j + 1
        return [f"{vnorm(t)}[{sel}]"], j + 1
    if "'" in t:
        return [t], i + 1
    return [vnorm(t)], i + 1


def read_verilog(path, want=None):
    """{module: Netlist} of a structural Verilog file (OpenROAD write_verilog / gen_rtl die top)."""
    with _open(path) as f:
        text = f.read()
    toks = [t for t in _TOK.findall(text) if not t.startswith("//") and not t.startswith("/*")]
    mods, i, n = {}, 0, len(toks)
    while i < n:
        if toks[i] != "module":
            i += 1
            continue
        nl = Netlist(vnorm(toks[i + 1]))
        i += 2
        if toks[i] == "#":                              # parameter list: skip
            depth, i = 0, i + 1
            while True:
                depth += toks[i] == "("
                depth -= toks[i] == ")"
                i += 1
                if depth == 0:
                    break
        ansi = {}
        if toks[i] == "(":                              # header
            j, cur = i + 1, None
            while toks[j] != ")":
                t = toks[j]
                if t in ("input", "output", "inout"):
                    cur = [t, None, None]
                    j += 1
                    continue
                if t in ("wire", "reg", "logic", "signed", ","):
                    j += 1
                    continue
                if t == "[" and cur:
                    k = toks.index("]", j)
                    a, b = "".join(toks[j + 1:k]).split(":")
                    cur[1], cur[2] = int(a), int(b)
                    j = k + 1
                    continue
                name = vnorm(t)
                if cur:
                    ansi[name] = (cur[0], cur[1], cur[2])
                nl.ports.append((None, name, None, None))
                j += 1
            i = j + 2
        nl.ports = [(ansi[p][0], p, ansi[p][1], ansi[p][2]) if p in ansi else (None, p, None, None)
                    for _, p, _, _ in nl.ports]
        pidx = {p[1]: k for k, p in enumerate(nl.ports)}
        while toks[i] != "endmodule":
            t = toks[i]
            if t in ("input", "output", "inout", "wire", "reg", "logic", "tri"):
                d, msb, lsb, j = t, None, None, i + 1
                while toks[j] in ("wire", "reg", "logic", "signed"):
                    j += 1
                if toks[j] == "[":
                    k = toks.index("]", j)
                    a, b = "".join(toks[j + 1:k]).split(":")
                    msb, lsb, j = int(a), int(b), k + 1
                while toks[j] != ";":
                    if toks[j] != ",":
                        nm = vnorm(toks[j])
                        if d in ("input", "output", "inout"):
                            if nm in pidx:
                                nl.ports[pidx[nm]] = (d, nm, msb, lsb)
                            else:
                                pidx[nm] = len(nl.ports)
                                nl.ports.append((d, nm, msb, lsb))
                        else:
                            nl.wires.append((nm, msb, lsb))
                    j += 1
                i = j + 1
            elif t == "assign":
                lhs, j = _expr(toks, i + 1)
                rhs, j = _expr(toks, j + 1)
                nl.assigns += list(zip(lhs, rhs))
                i = j + 1
            elif t in ("supply0", "supply1", "parameter", "localparam", "genvar"):
                i = toks.index(";", i) + 1
            else:                                       # instance: CELL [#(...)] inst ( .P(expr), ... );
                cell, j = vnorm(t), i + 1
                if toks[j] == "#":
                    depth, j = 0, j + 1
                    while True:
                        depth += toks[j] == "("
                        depth -= toks[j] == ")"
                        j += 1
                        if depth == 0:
                            break
                inst = vnorm(toks[j])
                j += 2                                  # past '('
                conns = []
                while toks[j] != ")":
                    if toks[j] == ",":
                        j += 1
                        continue
                    if toks[j] != ".":
                        raise SystemExit(f"die_sta: {path}: positional connection on {inst} not supported")
                    pin = vnorm(toks[j + 1])
                    bits, j = _expr(toks, j + 3)
                    conns.append((pin, bits))
                    j += 1                              # past ')'
                nl.insts.append([cell, inst, conns])
                i = j + 2                               # past ');'
        nl.expand_buses()
        mods[nl.name] = nl
        i += 1
        if want and want in mods:
            break
    return mods


def _vid(name):
    """Verilog identifier for a canonical name (escaped when needed)."""
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*", name) or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_$]*\[\d+\]", name):
        return name
    return "\\" + name + " "


# ----------------------------------------------------------------------------------------------------------------- ILM
def extract_ilm(nl, cells, clock_ports=None):
    """reduce a flat netlist to its interface logic model (see module doc).  -> (Netlist, kept nets, stats)."""
    clock_ports = clock_ports or set()
    in_bits = {b for d, _, b in nl.port_bits() if d == "input"}
    out_bits = {b for d, _, b in nl.port_bits() if d == "output"}
    ck_bits = {b for d, n, b in nl.port_bits() if d == "input" and (n in clock_ports or b in clock_ports)}
    unknown = set()
    # pin table: per instance index, [(pin, bit net, dir, is_clock)]
    drv, loads, pins = {}, defaultdict(list), []
    for k, (cell, inst, conns) in enumerate(nl.insts):
        c = cells.get(cell)
        if c is None:
            unknown.add(cell)
        row = []
        for pin, bits in conns:
            if c:
                d = c["pins"].get(pin, c["pins"].get(re.sub(r"\[\d+\]$", "", pin), "input"))
                isck = pin in c["clock"]
            else:
                d = "output" if re.match(r"^(Q|QN|Z|Y|O|DO|DOUT|.*_o(\[\d+\])?)$", pin) else "input"
                isck = bool(re.match(r"(?i)^(clk|ck|clock)", pin))
            for b in bits:
                if "'" in b:
                    continue
                row.append((pin, b, d, isck))
                if d == "output":
                    drv[b] = (k, pin)
                else:
                    loads[b].append((k, pin, isck))
        pins.append(row)
    for a, (lhs, rhs) in enumerate(nl.assigns):          # assign = a zero-delay buffer (pseudo instance -1-a)
        if "'" not in rhs:
            loads[rhs].append((-1 - a, "A", False))
        drv[lhs] = (-1 - a, "Y")
    seq = [bool(cells.get(c, {"seq": True})["seq"]) for c, _, _ in nl.insts]

    def is_seq(k):
        return k >= 0 and seq[k]

    def inputs_of(k):
        if k < 0:
            r = nl.assigns[-1 - k][1]
            return [] if "'" in r else [(r, False)]
        return [(b, ck) for _, b, d, ck in pins[k] if d != "output"]

    def outputs_of(k):
        if k < 0:
            return [nl.assigns[-1 - k][0]]
        return [b for _, b, d, _ in pins[k] if d == "output"]

    keep = set()                                   # instances on interface paths (all their driven pins kept)
    ck_walk = deque()
    # fan-out of every non-clock input to the first register
    q = deque(b for b in in_bits if b not in ck_bits)
    seen = set(q)
    while q:
        b = q.popleft()
        for k, pin, isck in loads.get(b, ()):
            if k in keep:
                continue
            keep.add(k)
            if is_seq(k):
                ck_walk.append(k)
                continue
            for o in outputs_of(k):
                if o not in seen:
                    seen.add(o)
                    q.append(o)
    # fan-in of every output back to the launching registers
    q = deque(out_bits)
    seen = set(q)
    while q:
        b = q.popleft()
        d = drv.get(b)
        if d is None:
            continue
        k = d[0]
        keep.add(k)
        if is_seq(k):
            ck_walk.append(k)
            continue
        for i, _ in inputs_of(k):                  # full fan-in (also of comb cells the input cone already kept)
            if i not in seen:
                seen.add(i)
                q.append(i)
    # clock network of every kept register (through buffers / inverters / clock gates' clock pins)
    q = deque(ck_walk)
    done = set()
    while q:
        k = q.popleft()
        if k in done:
            continue
        done.add(k)
        if is_seq(k):
            ins = [b for b, ck in inputs_of(k) if ck]
        else:
            ins = [b for b, _ in inputs_of(k)]
        for b in ins:
            d = drv.get(b)
            if d is not None:
                keep.add(d[0])
                q.append(d[0])
    # kept nets: driven by a kept instance or an input port
    kept_nets = set(in_bits)
    for k in keep:
        kept_nets.update(outputs_of(k))
    side = defaultdict(set)                         # side-load instance -> pins kept
    for b in kept_nets:
        for k, pin, _ in loads.get(b, ()):
            if k not in keep:
                side[k].add((pin, b))
    # build the reduced netlist
    out = Netlist(nl.name)
    out.ports = list(nl.ports)
    for k in sorted(keep | set(side)):
        if k < 0:
            lhs, rhs = nl.assigns[-1 - k]
            if k in keep and ("'" in rhs or rhs in kept_nets):
                out.assigns.append((lhs, rhs))
            continue
        cell, inst, conns = nl.insts[k]
        nc = []
        if k in keep:
            for pin, bits in conns:
                nb = [b if ("'" in b or b in kept_nets) else None for b in bits]
                if any(x is None for x in nb):
                    if len(nb) == 1:
                        continue                        # side input from removed logic: left open
                    nb = [x or "1'b0" for x in nb]      # (bus pin of a kept macro: open bits tied off)
                nc.append((pin, nb))
        else:
            sp = {p for p, _ in side[k]}
            for pin, bits in conns:
                if pin in sp and len(bits) == 1:
                    nc.append((pin, bits))
        out.insts.append([cell, inst, nc])
    port_bits = in_bits | out_bits | {b for _, _, b in nl.port_bits()}
    used = set()
    for _, _, conns in out.insts:
        for _, bits in conns:
            used.update(b for b in bits if "'" not in b)
    for lhs, rhs in out.assigns:
        used.update(x for x in (lhs, rhs) if "'" not in x)
    wires = {re.sub(r"\[\d+\]$", "", b) if _is_bus_wire(nl, b) else b for b in used if b not in port_bits}
    stats = dict(cells=len(nl.insts), ilm_cells=sum(1 for k in keep if k >= 0), side_loads=len(side),
                 nets_kept=len(kept_nets), unknown_cells=sorted(unknown))
    return out, kept_nets, wires, stats


def _is_bus_wire(nl, b):
    if not hasattr(nl, "_buswires"):
        nl._buswires = {n: (msb, lsb) for n, msb, lsb in nl.wires if msb is not None}
    m = re.fullmatch(r"(.+)\[(\d+)\]", b)
    return bool(m and m.group(1) in nl._buswires)


def write_ilm_verilog(nl, red, wires, path):
    bw = {n: (msb, lsb) for n, msb, lsb in nl.wires if msb is not None}
    L = [f"// GENERATED by tools/die_plan/die_sta.py ilm: interface logic model of {nl.name}. Do not edit.",
         f"module {_vid(nl.name)} (" + ",\n    ".join(_vid(p[1]) for p in red.ports) + ");"]
    for d, n, msb, lsb in red.ports:
        L.append(f"  {d} {'' if msb is None else f'[{msb}:{lsb}] '}{_vid(n)};")
    for w in sorted(wires):
        L.append(f"  wire [{bw[w][0]}:{bw[w][1]}] {_vid(w)};" if w in bw else f"  wire {_vid(w)};")

    def ex(b):
        return b if "'" in b else _vid(b)
    for lhs, rhs in red.assigns:
        L.append(f"  assign {ex(lhs)} = {ex(rhs)};")
    for cell, inst, conns in red.insts:
        cs = []
        for p, bits in conns:
            cs.append(f".{_vid(p).strip()}({ex(bits[0]) if len(bits) == 1 else '{' + ', '.join(ex(x) for x in bits) + '}'})")
        L.append(f"  {_vid(cell)} {_vid(inst)} ({', '.join(cs)});")
    L.append("endmodule\n")
    Path(path).write_text("\n".join(L))


# ---------------------------------------------------------------------------------------------------------------- SPEF
def filter_spef(src, dst, kept_nets):
    """copy SPEF src -> dst keeping only the *D_NET blocks of kept nets (canonical names) and the name-map entries
    they reference.  -> (nets kept, nets total)."""
    kept_norm = {vnorm(n) for n in kept_nets}
    head, nmap, ports, blocks = [], {}, [], []
    state = "head"
    cur, keep_cur, total = None, False, 0
    with _open(src) as f:
        for line in f:
            if state == "head":
                if line.startswith("*NAME_MAP"):
                    state = "map"
                    continue
                if line.startswith("*PORTS"):
                    state = "ports"
                    ports.append(line)
                    continue
                if line.startswith("*D_NET"):
                    state = "nets"
                else:
                    head.append(line)
                    continue
            if state == "map":
                if line.startswith("*PORTS"):
                    state = "ports"
                    ports.append(line)
                    continue
                if line.startswith("*D_NET"):
                    state = "nets"
                else:
                    s = line.split(None, 1)
                    if len(s) == 2 and s[0].startswith("*"):
                        nmap[s[0]] = s[1].rstrip("\n")
                    continue
            if state == "ports":
                if line.startswith("*D_NET"):
                    state = "nets"
                else:
                    ports.append(line)
                    continue
            if line.startswith("*D_NET"):
                total += 1
                tok = line.split()[1]
                name = nmap.get(tok, tok)
                keep_cur = vnorm(name) in kept_norm
                cur = [line] if keep_cur else None
                if keep_cur:
                    blocks.append(cur)
                continue
            if keep_cur:
                cur.append(line)
    refs = set()
    rx = re.compile(r"\*\d+")
    for b in blocks:
        for line in b:
            refs.update(rx.findall(line))
    for line in ports:
        refs.update(rx.findall(line))
    with open(dst, "w") as o:
        o.writelines(head)
        o.write("*NAME_MAP\n")
        for k, v in nmap.items():
            if k in refs:
                o.write(f"{k} {v}\n")
        o.write("\n")
        o.writelines(ports)
        o.write("\n")
        for b in blocks:
            o.writelines(b)
    return len(blocks), total


# --------------------------------------------------------------------------------------------------------- ilm command
def sdc_clock_ports(sdc):
    """ports of the kit SDC's real clocks (create_clock with ports; virtual clocks have none)."""
    if not sdc or not Path(sdc).is_file():
        return None
    text = Path(sdc).read_text(errors="replace").replace("\\\n", " ")
    out = set()
    for line in text.splitlines():
        if line.strip().startswith("create_clock"):
            out.update(re.findall(r"get_ports\s+\{?([^}\]\s]+)\}?", line))
    return out or None


def make_ilm(netlist, spef, out, libs, sdc=None, clock_re=CLOCK_PORT_RE):
    t0 = time.time()
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    cells = read_liberty_cells(libs)
    mods = read_verilog(netlist)
    if len(mods) != 1:
        raise SystemExit(f"die_sta ilm: {netlist}: expected one flat module, found {sorted(mods)}")
    nl = next(iter(mods.values()))
    used = {c for c, _, _ in nl.insts}
    hier = used & set(mods)
    if hier:
        raise SystemExit(f"die_sta ilm: hierarchical netlist ({sorted(hier)[:3]}): flatten first")
    cps = sdc_clock_ports(sdc) or {n for d, n, *_ in nl.ports if d == "input" and re.match(clock_re, n)}
    red, kept, wires, st = extract_ilm(nl, cells, cps)
    write_ilm_verilog(nl, red, wires, out / "6_final.v")
    nk, nt = filter_spef(spef, out / "6_final.spef", kept) if spef else (0, 0)
    st.update(module=nl.name, clock_ports=sorted(cps), spef_nets=nt, spef_nets_kept=nk, netlist=str(netlist),
              spef=str(spef), seconds=round(time.time() - t0, 1))
    (out / "ilm.json").write_text(json.dumps(st, indent=1) + "\n")
    return st


# --------------------------------------------------------------------------------------------------------- die top/seams
def module_of(netlist):
    with _open(netlist) as f:
        for line in f:
            m = re.match(r"\s*module\s+(\\\S+|[A-Za-z_][A-Za-z0-9_$]*)", line)
            if m:
                return vnorm(m.group(1))
    return None


def find_parts(parts_dir):
    """{module: dir} for every PARTS/<x>/6_final.v."""
    out = {}
    for v in sorted(Path(parts_dir).glob("*/6_final.v")):
        m = module_of(v)
        if m:
            out[m] = v.parent
    return out


def port_dirs(netlist):
    """{port: (direction, msb, lsb)} from a netlist header (stops at the first wire / instance)."""
    out = {}
    with _open(netlist) as f:
        for line in f:
            m = re.match(r"\s*(input|output|inout)\s+(?:wire\s+)?(?:\[(\d+):(\d+)\]\s*)?(.*);", line)
            if m:
                for n in m.group(4).split(","):
                    out[vnorm(n.strip())] = (m.group(1), int(m.group(2)) if m.group(2) else None,
                                             int(m.group(3)) if m.group(3) else None)
            elif out and re.match(r"\s*(wire|reg)\b", line):
                break
            elif out and re.match(r"\s*[A-Za-z_\\]\S*\s+\S+\s*\(", line):
                break
    return out


def die_seams(top_nl, part_dirs_by_module):
    """[{net, src, src_pin, dst, dst_pin, dst_bus}] of the die top's internal nets that join an output of one
    partition to an input of another (bit level)."""
    pdir = {m: port_dirs(d / "6_final.v") for m, d in part_dirs_by_module.items()}
    top_ports = {b for _, _, b in top_nl.port_bits()}
    on = defaultdict(list)
    for cell, inst, conns in top_nl.insts:
        dirs = pdir.get(cell, {})
        for pin, bits in conns:
            base = re.sub(r"\[\d+\]$", "", pin)
            d, msb, lsb = dirs.get(base, ("input", None, None))
            if msb is not None and pin == base:
                st = -1 if msb >= lsb else 1
                pbits = [f"{base}[{k}]" for k in range(msb, lsb + st, st)]
            else:
                pbits = [pin]
            # Verilog width mismatch: bits connect from the LSB, the rest of the port stays open
            k = min(len(pbits), len(bits))
            for pb, b in zip(pbits[len(pbits) - k:], bits[len(bits) - k:]):
                if "'" not in b:
                    on[b].append((inst, pb, base, d))
    seams = []
    for net, ends in sorted(on.items()):
        if net in top_ports:
            continue
        for s in (e for e in ends if e[3] == "output"):
            for e in ends:
                if e[3] == "input" and e[0] != s[0]:
                    seams.append(dict(net=net, src=s[0], src_pin=s[1], dst=e[0], dst_pin=e[1],
                                      dst_bus=e[2]))
    return seams


# --------------------------------------------------------------------------------------------------------------- STA tcl
def sta_tcl(top_path, top_name, inst_mods, mod_files, corner, libs, out_txt, mode, period_ps, groups, spine=None,
            die_spef=None, etm_libs=None, seam_paths=100000, reduce=False):
    L = [f"# GENERATED by tools/die_plan/die_sta.py: die STA mode {mode} corner {corner}.",
         "set t0 [clock milliseconds]",
         # 1212: ASAP7 'timing group from output port'; 1655: SPEF port node of a bit tied to a die IO port (window
         # boundary, not a seam) -- seam port nodes connect; both flood the log at die scale
         "catch {suppress_msg 1212 1655}"]
    L += [f"read_liberty {x}" for x in libs]
    if mode == "etm":
        L += [f"read_liberty {x}" for x in etm_libs]
    else:
        L += [f"read_verilog {mod_files[m]['v']}" for m in sorted(set(inst_mods.values()))]
    L += [f"read_verilog {top_path}", f"link_design {top_name}", "puts \"OT_LINKED [expr {[clock milliseconds]-$t0}]\""]
    if mode != "etm":
        for inst, m in sorted(inst_mods.items()):
            if mod_files[m].get("spef"):
                L.append(f"read_spef{' -reduce' if reduce else ''} -path {inst} {mod_files[m]['spef']}")
    if die_spef:
        L.append(f"read_spef {die_spef}")
    L += ["puts \"OT_PARASITICS [expr {[clock milliseconds]-$t0}]\"",
          f"create_clock -name clk -period {period_ps:.4f} [get_ports clk]"]
    if spine:
        for inst, taps in sorted(spine.items()):
            for port, off in sorted(taps.items()):
                ck = f"ck_{inst}_{port}"
                L.append(f"create_generated_clock -name {ck} -source [get_ports clk] -divide_by 1 [get_pins {inst}/{port}]")
                L.append(f"set_clock_latency -source {off:.4f} [get_clocks {ck}]")
    L += ["set_propagated_clock [all_clocks]",
          f"set_clock_uncertainty {UNC_SETUP_PS:.4f} -setup [all_clocks]",
          f"set_clock_uncertainty {UNC_HOLD_PS:.4f} -hold [all_clocks]",
          f"set fh [open {out_txt} w]",
          f"puts $fh \"mode {mode} corner {corner}\"",
          f"proc ot_ck {{pin}} {{ if {{[catch {{set a [get_property $pin arrival_max_rise]}}] || $a eq \"\"}} {{ return NA }}; "
          f"if {{$a >= {period_ps / 2:.4f}}} {{ set a [expr {{$a - {period_ps / 2:.4f}}}] }}; return [format %.2f $a] }}",
          "proc ot_ckpin {pin} { set i [file dirname $pin]; foreach c {CLK CK clk} { set q [get_pins -quiet $i/$c]; "
          "if {$q ne \"\"} { return $q } }; return \"\" }",
          "proc ot_arr {pin} { set q [ot_ckpin $pin]; if {$q eq \"\"} { return NA }; return [ot_ck $q] }"]
    # seams per BIT: worst slack through the seam = min slack_max / slack_min over the leaf load pins of the seam net
    # inside the destination (only paths through the seam reach them); one timing update, O(1) per pin.  Face-flop
    # spread: clock arrival (rise, T/2 folded) at the registers on both ends of every seam bit (registered boundary).
    tab = Path(out_txt).with_name(Path(out_txt).stem + "_seams.tcl")
    with open(tab, "w") as f:
        f.write("set OT_SEAMS {\n")
        for gname, bits in groups:
            f.write("{" + gname + " {" + " ".join("{" + d + " " + sp + "}" for d, sp in bits) + "}}\n")
        f.write("}\n")
    L += [f"source {tab}",
          "proc ot_leaf {p dir} { set q [get_pins -quiet $p]; if {$q eq \"\"} { return {} }; "
          "if {![get_property $q is_hierarchical]} { return [list $q] }; set n [get_nets -quiet $p]; "
          "if {$n eq \"\"} { return {} }; set out {}; foreach x [get_pins -of_objects $n] { "
          "if {[get_property $x is_hierarchical]} { continue }; if {[get_property $x direction] eq $dir} { lappend out $x } }; "
          "return $out }",
          "array set ffarr {}",
          "foreach g $OT_SEAMS { lassign $g gname bits",
          "  foreach dly {max min} { set n($dly) 0; set nneg($dly) 0; set tns($dly) 0.0; set w($dly) \"\"; set wq($dly) \"\" }",
          "  foreach b $bits { lassign $b d s; set lv [ot_leaf $d input]",
          "    foreach dly {max min} { set best \"\"; foreach q $lv { set x [get_property $q slack_$dly]; "
          "if {$x eq \"\" || [string match *INF* $x]} { continue }; if {$best eq \"\" || $x < $best} { set best $x; set bq $q } }; "
          "if {$best eq \"\"} { continue }; incr n($dly); if {$best < 0} { incr nneg($dly); set tns($dly) [expr {$tns($dly) + $best}] }; "
          "if {$w($dly) eq \"\" || $best < $w($dly)} { set w($dly) $best; set wq($dly) $bq } }",
          "    if {[llength $lv]} { foreach q [get_fanout -from $lv -endpoints_only -flat] { set nm [get_full_name $q]; set a [ot_arr $nm]; if {$a ne \"NA\"} { lappend ffarr([lindex [split $nm /] 0]) $a } } }",
          "    set lo [ot_leaf $s output]; if {[llength $lo]} { foreach q [get_fanin -to $lo -startpoints_only -flat] { set nm [get_full_name $q]; set a [ot_arr $nm]; if {$a ne \"NA\"} { lappend ffarr([lindex [split $nm /] 0]) $a } } } }",
          "  foreach dly {max min} { if {$n($dly) == 0} { puts $fh \"SEAM $gname $dly NO_PATH\"; continue }",
          "    set ps [find_timing_paths -through $wq($dly) -path_delay $dly -group_path_count 1]; set p [lindex $ps 0]",
          "    set sp [get_full_name [get_property $p startpoint]]; set ep [get_full_name [get_property $p endpoint]]",
          "    puts $fh [format \"SEAM %s %s paths %d worst %.3f neg %d tns %.3f launch %s capture %s from %s to %s\" "
          "$gname $dly $n($dly) $w($dly) $nneg($dly) $tns($dly) [ot_arr $sp] [ot_arr $ep] $sp $ep] } }",
          "foreach i [lsort [array names ffarr]] { set v [lsort -unique -real $ffarr($i)]; set mn [tcl::mathfunc::min {*}$v]; "
          "set mx [tcl::mathfunc::max {*}$v]; puts $fh [format \"FFSPREAD %s n %d min %.2f max %.2f spread %.2f\" "
          "$i [llength $ffarr($i)] $mn $mx [expr {$mx - $mn}]] }",
          "puts \"OT_SEAMS [expr {[clock milliseconds]-$t0}]\"",
          "puts $fh \"WNS [sta::worst_slack_cmd max] WHS [sta::worst_slack_cmd min]\"",
          "puts $fh \"SECONDS [expr {([clock milliseconds]-$t0)/1000.0}]\"",
          "close $fh"]
    return "\n".join(L) + "\n"


def parse_sta(txt):
    res = dict(seams={})
    for line in Path(txt).read_text().splitlines():
        f = line.split()
        if not f:
            continue
        if f[0] == "SEAM":
            g, dly = f[1], f[2]
            if f[3] == "NO_PATH":
                res["seams"].setdefault(g, {})[dly] = None
                continue
            d = dict(zip(f[3::2], f[4::2]))
            res["seams"].setdefault(g, {})[dly] = dict(
                paths=int(d["paths"]), worst=float(d["worst"]), neg=int(d["neg"]), tns=float(d["tns"]),
                launch=d["launch"], capture=d["capture"], start=d["from"], end=d["to"])
        elif f[0] == "FFSPREAD":
            d = dict(zip(f[2::2], f[3::2]))
            res.setdefault("ffspread", {})[f[1]] = dict(n=int(d["n"]), min=float(d["min"]), max=float(d["max"]),
                                                       spread=float(d["spread"]))
        elif f[0] == "WNS":
            res["wns_ps"], res["whs_ps"] = round(float(f[1]) * 1e12, 3), round(float(f[3]) * 1e12, 3)
        elif f[0] == "SECONDS":
            res["sta_seconds"] = float(f[1])
    return res


def _sta_bin():
    b = shutil.which("sta") or os.path.expanduser("~/.local/opentallas-tools/bin/sta")
    if not Path(b).is_file():
        raise SystemExit("die_sta: OpenSTA `sta` not found (PATH=$HOME/.local/opentallas-tools/bin:$PATH)")
    return b


THREADS = 1


def run_sta(tcl, log):
    """run OpenSTA on tcl; -> (exit code, seconds, peak RSS GB)."""
    t0 = time.time()
    with open(log, "w") as lf:
        p = subprocess.Popen([_sta_bin(), "-no_splash", "-threads", str(THREADS), "-exit", str(tcl)], stdout=lf, stderr=subprocess.STDOUT)
        _, status, ru = os.wait4(p.pid, 0)
    return os.waitstatus_to_exitcode(status), round(time.time() - t0, 1), round(ru.ru_maxrss / 1048576.0, 2)


# ----------------------------------------------------------------------------------------------------------------- ETM
def etm_tcl(netlist, spef, module, libs, clock_ports, corner, period_ps, out_lib):
    L = [f"# GENERATED by tools/die_plan/die_sta.py etm: {module} corner {corner}"]
    L += [f"read_liberty {x}" for x in libs]
    L += [f"read_verilog {netlist}", f"link_design {module}"]
    if spef:
        L.append(f"read_spef {spef}")
    for p in sorted(clock_ports):           # one clock per tap port: each arc stays related to its own tap pin
        L.append(f"create_clock -name ck_{re.sub(r'[^A-Za-z0-9_]', '_', p)} -period {period_ps:.4f} [get_ports {{{p}}}]")
    L += ["set_propagated_clock [all_clocks]",
          f"write_timing_model -library_name {module}_{corner} -cell_name {module} {out_lib}"]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------------------------------------------------- run
def load_spine(path, insts):
    """spine_branch.json (gen.py assembly) -> {instance: {tap port: source latency ps}}."""
    if not path:
        return None
    br = json.loads(Path(path).read_text())
    out = {}
    for n, r in br["parts"].items():
        inst = re.sub(r"[^A-Za-z0-9_]", "_", n)
        if inst in insts:
            out[inst] = {port: float(v["offset_ps"]) for port, v in r["taps"].items()}
    return out


def cmd_run(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    tops = read_verilog(a.top)
    top = tops[a.top_module] if a.top_module else next(iter(tops.values()))
    parts = find_parts(a.parts)
    inst_mods = {inst: cell for cell, inst, _ in top.insts if cell in parts}
    missing = sorted({cell for cell, inst, _ in top.insts if cell not in parts})
    if missing:
        raise SystemExit(f"die_sta: die top instantiates modules without a PARTS dir: {missing}")
    seams = die_seams(top, {m: parts[m] for m in set(inst_mods.values())})
    groups = defaultdict(set)
    for s in seams:
        groups[f"{s['src']}->{s['dst']}/{s['dst_bus']}"].add((f"{s['dst']}/{s['dst_pin']}", f"{s['src']}/{s['src_pin']}"))
    groups = sorted((g, sorted(p)) for g, p in groups.items())
    (out / "seams.json").write_text(json.dumps(dict(top=top.name, seams=seams), indent=0) + "\n")
    mod_files, abstracts = {}, {}
    for m in sorted(set(inst_mods.values())):
        d = parts[m]
        sp = d / "6_final.spef"
        if a.mode == "flat":
            mod_files[m] = dict(v=str(d / "6_final.v"), spef=str(sp) if sp.is_file() else None)
        elif a.mode == "ilm":
            ad = out / "ilm" / m
            if not (ad / "ilm.json").is_file() or a.rebuild:
                st = make_ilm(d / "6_final.v", sp if sp.is_file() else None, ad, corner_libs("TT", a.libdir, a.lib),
                              sdc=d / "6_final.sdc")
            else:
                st = json.loads((ad / "ilm.json").read_text())
            abstracts[m] = st
            mod_files[m] = dict(v=str(ad / "6_final.v"), spef=str(ad / "6_final.spef") if sp.is_file() else None)
    res = dict(top=top.name, mode=a.mode, reduce=a.reduce, period_ps=a.period_ps, unc_setup_ps=UNC_SETUP_PS, unc_hold_ps=UNC_HOLD_PS,
               spine="branch" if a.spine_branch else ("routed" if a.die_spef else "ideal"), instances=inst_mods,
               parts={m: str(parts[m]) for m in mod_files or parts}, abstracts=abstracts, corners={},
               seam_groups=len(groups), seam_bits=len(seams))
    for corner in a.corner:
        # '{c}' in --spine-branch: one spine file per corner (die_trial.py writes spine_<corner>.json)
        spine = load_spine(a.spine_branch.replace("{c}", corner) if a.spine_branch else None, set(inst_mods))
        libs = corner_libs(corner, a.libdir, a.lib)
        etm_libs = None
        if a.mode == "etm":
            etm_libs = []
            for m in sorted(set(inst_mods.values())):
                d = parts[m]
                lib = out / "etm" / f"{m}_{corner}.lib"
                lib.parent.mkdir(parents=True, exist_ok=True)
                sp = d / "6_final.spef"
                cps = sdc_clock_ports(d / "6_final.sdc") or {n for n, dd in port_dirs(d / "6_final.v").items()
                                                             if dd[0] == "input" and re.match(CLOCK_PORT_RE, n)}
                tcl = out / "etm" / f"{m}_{corner}.tcl"
                tcl.write_text(etm_tcl(d / "6_final.v", sp if sp.is_file() else None, m, libs, cps, corner,
                                       a.period_ps, lib))
                rc, sec, rss = run_sta(tcl, tcl.with_suffix(".log"))
                if rc or not lib.is_file():
                    raise SystemExit(f"die_sta etm: {m} {corner} failed (rc {rc}), see {tcl.with_suffix('.log')}")
                etm_libs.append(str(lib))
        txt = out / f"sta_{a.mode}_{corner}.txt"
        tcl = out / f"sta_{a.mode}_{corner}.tcl"
        tcl.write_text(sta_tcl(Path(a.top).resolve(), top.name, inst_mods, mod_files, corner, libs, txt, a.mode,
                               a.period_ps, groups, spine, a.die_spef, etm_libs, reduce=a.reduce))
        rc, sec, rss = run_sta(tcl, tcl.with_suffix(".log"))
        r = parse_sta(txt) if txt.is_file() else dict(seams={})
        r.update(exit=rc, seconds=sec, peak_rss_gb=rss, gates={"TT": "setup + spread", "FF": "hold + spread"}.get(
            corner, "info only (not a signoff corner)"))
        if a.mode == "etm" and corner in ("FF",):
            r["note"] = "ETM hold is optimistic (OpenSTA be771a0 clk->out arcs from max arrival); not a hold verdict"
        res["corners"][corner] = r
    res["verdict"] = verdict(res)
    (out / "die_sta.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(dict(verdict=res["verdict"], corners={c: dict(seconds=r["seconds"], rss_gb=r["peak_rss_gb"],
                                                                    exit=r["exit"]) for c, r in res["corners"].items()}),
                     indent=1))
    return res


def verdict(res):
    """worst seam slacks per corner; PASS only if TT setup and FF hold ran, every seam slack there is >= 0 and every
    partition's face-flop spread is <= SPREAD_PS at TT and FF (AGENTS.md, owner 2026-10-24).  SS is info only."""
    v = {}
    for corner, r in res["corners"].items():
        for dly in ("max", "min"):
            w = [s[dly]["worst"] for s in r["seams"].values() if s.get(dly)]
            if w:
                key = ("setup" if dly == "max" else "hold") + f"_{corner}"
                v[key] = round(min(w), 3)
                v[key + "_neg_endpoints"] = sum(s[dly]["neg"] for s in r["seams"].values() if s.get(dly))
        sp = r.get("ffspread") or {}
        if sp:
            v[f"ffspread_{corner}"] = round(max(x["spread"] for x in sp.values()), 2)
    ran = {c for c, r in res["corners"].items() if r.get("exit") == 0}
    if res["mode"] == "etm":
        v["status"] = "INFO (etm: setup cross-check only)"
    elif not {"TT", "FF"} <= ran:
        v["status"] = "NOT RUN (signoff needs TT setup + FF hold)"
    else:
        ok = v.get("setup_TT", -1) >= 0 and v.get("hold_FF", -1) >= 0
        ok = ok and all(v.get(f"ffspread_{c}", 0) <= SPREAD_PS for c in ("TT", "FF"))
        v["status"] = "PASS" if ok else "FAIL"
    return v


def cmd_compare(a):
    A, B = (json.loads(Path(x).read_text()) for x in (a.a, a.b))
    rows, worst = [], 0.0
    for corner in sorted(set(A["corners"]) & set(B["corners"])):
        sa, sb = A["corners"][corner]["seams"], B["corners"][corner]["seams"]
        for g in sorted(set(sa) | set(sb)):
            for dly in ("max", "min"):
                x, y = (sa.get(g) or {}).get(dly), (sb.get(g) or {}).get(dly)
                if x is None and y is None:
                    continue
                if x is None or y is None:
                    rows.append(dict(corner=corner, seam=g, check=dly, a=x and x["worst"], b=y and y["worst"],
                                     delta=None))
                    worst = float("inf")
                    continue
                d = y["worst"] - x["worst"]
                worst = max(worst, abs(d))
                rows.append(dict(corner=corner, seam=g, check=dly, a=x["worst"], b=y["worst"], delta=round(d, 3),
                                 paths_a=x["paths"], paths_b=y["paths"]))
        fa, fb = A["corners"][corner].get("ffspread") or {}, B["corners"][corner].get("ffspread") or {}
        for i in sorted(set(fa) & set(fb)):
            d = fb[i]["spread"] - fa[i]["spread"]
            worst = max(worst, abs(d))
            rows.append(dict(corner=corner, seam=i, check="ffspread", a=fa[i]["spread"], b=fb[i]["spread"],
                             delta=round(d, 3)))
    res = dict(a=a.a, b=a.b, mode_a=A["mode"], mode_b=B["mode"], max_abs_delta_ps=worst, tol_ps=a.tol,
               status="AGREE" if worst <= a.tol else "DISAGREE", rows=rows)
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    for r in rows:
        print(f"{r['corner']} {r['check']} {r['seam']}: {r['a']} vs {r['b']} delta {r['delta']}")
    print(f"max |delta| {worst} ps (tol {a.tol}) -> {res['status']}")
    return res


# ------------------------------------------------------------------------------------------------------------- replica
def cmd_replica(a):
    """synthetic flat-capacity vehicle: N copies of one routed partition chained output->input (ft buses joined in
    name order) under a generated top, each with its own read_spef -path.  Times setup on the stitched netlist."""
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    m = module_of(a.netlist)
    dirs = {}
    with _open(a.netlist) as f:
        for line in f:
            mm = re.match(r"\s*(input|output)\s+(?:\[(\d+):(\d+)\]\s*)?(\S+);", line)
            if mm:
                w = int(mm.group(2)) - int(mm.group(3)) + 1 if mm.group(2) else 1
                dirs[vnorm(mm.group(4))] = (mm.group(1), w)
            elif re.match(r"\s*wire\b", line) and dirs:
                break
    ins = [(p, w) for p, (d, w) in dirs.items() if d == "input"]
    outs = [(p, w) for p, (d, w) in dirs.items() if d == "output"]
    clocks = [p for p, _ in ins if re.match(CLOCK_PORT_RE, p) or p == "arst_n"]
    data_in = [(p, w) for p, w in ins if p not in clocks]
    # pair outputs of copy i with same-width inputs of copy i+1 (first fit)
    pairs, free = [], list(data_in)
    for p, w in outs:
        for k, (q, v) in enumerate(free):
            if v == w:
                pairs.append((p, q, w))
                free.pop(k)
                break
    L = [f"// GENERATED by die_sta.py replica: {a.n} x {m}", "module replica_top (clk, rst_n);",
         " input clk;", " input rst_n;"]
    for i in range(a.n):
        for p, q, w in pairs:
            L.append(f" wire [{w - 1}:0] w{i}_{p};")
    for i in range(a.n):
        c = [f".{p}(clk)" for p in clocks if p != "arst_n"] + ([".arst_n(rst_n)"] if "arst_n" in clocks else [])
        for p, q, w in pairs:
            c.append(f".{p}(w{i}_{p})")
            if i > 0:
                c.append(f".{q}(w{i - 1}_{p})")
        L.append(f" {m} u{i} ({', '.join(c)});")
    L.append("endmodule")
    (out / "replica_top.v").write_text("\n".join(L) + "\n")
    libs = corner_libs(a.corner, a.libdir, a.lib)
    T = ["catch {suppress_msg 1212 1655}"] + [f"read_liberty {x}" for x in libs] + ["set t0 [clock milliseconds]", f"read_verilog {Path(a.netlist).resolve()}",
                                               f"read_verilog {out.resolve()}/replica_top.v", "link_design replica_top",
                                               "puts \"OT_T link [expr {[clock milliseconds]-$t0}]\""]
    if a.spef:
        T += [f"read_spef{' -reduce' if a.reduce else ''} -path u{i} {Path(a.spef).resolve()}" for i in range(a.n)]
    T += ["puts \"OT_T spef [expr {[clock milliseconds]-$t0}]\"",
          f"create_clock -name clk -period {a.period_ps:.4f} [get_ports clk]", "set_propagated_clock [all_clocks]",
          f"set_clock_uncertainty {UNC_SETUP_PS} -setup [all_clocks]",
          f"set_clock_uncertainty {UNC_HOLD_PS} -hold [all_clocks]",
          "report_wns", "puts \"OT_T wns [expr {[clock milliseconds]-$t0}]\"",
          "report_worst_slack -min", "puts \"OT_T whs [expr {[clock milliseconds]-$t0}]\"",
          f"report_checks -path_delay max -through [get_pins u{a.n // 2}/{pairs[0][1]}[0]]" if pairs and a.n > 1 else "",
          "puts \"OT_T seam [expr {[clock milliseconds]-$t0}]\"",
          "puts \"OT_INSTANCES [llength [get_cells -hierarchical *]]\""]
    tcl = out / f"replica_{a.n}.tcl"
    tcl.write_text("\n".join(T) + "\n")
    rc, sec, rss = run_sta(tcl, tcl.with_suffix(".log"))
    log = tcl.with_suffix(".log").read_text(errors="replace")
    marks = {k: int(v) / 1000.0 for k, v in re.findall(r"OT_T (\w+) (\d+)", log)}
    ninst = re.search(r"OT_INSTANCES (\d+)", log)
    res = dict(module=m, n=a.n, reduce=a.reduce, exit=rc, seconds=sec, peak_rss_gb=rss, marks_s=marks,
               instances=int(ninst.group(1)) if ninst else None, corner=a.corner, host=os.uname().nodename,
               netlist=str(a.netlist), spef=str(a.spef), seam_pairs=len(pairs))
    (out / f"replica_{a.n}.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))
    return res


# ------------------------------------------------------------------------------------------------------------- extract
EXTRACT_TCL = """# GENERATED by tools/die_plan/die_sta.py extract: routed netlist + SPEF of a routed ODB (ORFS final RCX rules)
set PL /OpenROAD-flow-scripts/flow/platforms/asap7
read_db /in/ODB
define_process_corner -ext_model_index 0 X
extract_parasitics -ext_model_file $PL/rcx_patterns.rules
write_spef /out/6_final.spef
write_verilog /out/6_final.v
puts OT_RCX_DONE
"""


def cmd_extract(a):
    """PARTS/<name>/6_final.v|.spef(|.sdc) from a kit's routed ODB (run_kit.sh route stops at 5_route.odb), in the
    pinned ORFS image (same RCX rules as ORFS final_report)."""
    odb = Path(a.odb).resolve()
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "extract.tcl").write_text(EXTRACT_TCL.replace("ODB", odb.name))
    sdc = sorted(odb.parent.glob("5_*.sdc")) + sorted(odb.parent.glob("6_final.sdc")) + sorted(odb.parent.glob("4_cts.sdc"))
    if sdc:
        shutil.copyfile(sdc[-1] if "6_final" in sdc[-1].name else sdc[0], out / "6_final.sdc")
    dk = ["docker"] if os.access("/var/run/docker.sock", os.W_OK) else ["sudo", "docker"]
    cmd = dk + ["run", "--rm", f"--memory={a.mem}g", f"--memory-swap={a.mem}g", "-v", f"{odb.parent}:/in:ro",
                "-v", f"{out}:/out", a.image, "bash", "-lc",
                "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /out/extract.tcl > /out/rcx.log 2>&1; "
                f"rc=$?; chown -R {os.getuid()}:{os.getgid()} /out; exit $rc"]
    rc = subprocess.run(cmd).returncode
    ok = rc == 0 and "OT_RCX_DONE" in (out / "rcx.log").read_text(errors="replace")
    (out / "SOURCE.txt").write_text(f"odb {odb}\nimage {a.image}\n")
    print(f"extract {odb} -> {out}: {'OK' if ok else 'FAIL'}")
    return 0 if ok else 1


# ----------------------------------------------------------------------------------------------------------------- top
def write_top(plan, out, views=None):
    """structural die top of a plan (the netlist gen.py assembly writes as die_top_struct.v): partitions joined by the
    zero-length abutment wires w_<port>, clk / rst_n fanned to every partition's (connected) taps.  views/<type>/
    ot_clock_taps.json (from the kits) drops the taps a kit found without sinks."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import schema as S
    import gen_rtl
    import gen_phys
    raw = json.loads(Path(plan).read_text())
    P = S.Plan(raw)
    dropped = gen_phys.dropped_taps(P, views) if views else {}
    v = gen_rtl.die_top(P, gen_rtl.bus_epochs(P), dropped)
    plain = "\n".join(re.sub(r"^endmodule\s*:.*$", "endmodule", ln) for ln in v.splitlines() if not ln.startswith("`"))
    Path(out).write_text(plain + "\n")
    return out


# ---------------------------------------------------------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("ilm", help="interface logic model of one routed partition")
    g.add_argument("--netlist", required=True)
    g.add_argument("--spef")
    g.add_argument("--sdc")
    g.add_argument("--out", required=True)
    g.add_argument("--libdir")
    g.add_argument("--lib", action="append", default=[], help="extra liberty (macros); {c} = corner")
    r = sub.add_parser("run", help="die STA (ilm | flat | etm)")
    r.add_argument("--top", required=True, help="die top structural netlist")
    r.add_argument("--top-module")
    r.add_argument("--parts", required=True, help="dir of <x>/6_final.v|.spef per partition")
    r.add_argument("--out", required=True)
    r.add_argument("--mode", choices=("ilm", "flat", "etm"), default="ilm")
    r.add_argument("--corner", action="append", choices=("SS", "FF", "TT"))
    r.add_argument("--period-ps", type=float, default=PERIOD_PS)
    r.add_argument("--spine-branch", help="spine_branch.json (gen.py assembly): branch clock model; '{c}' = corner (die_trial spine_{c}.json)")
    r.add_argument("--die-spef", help="routed die SPEF (spine + channel seams)")
    r.add_argument("--libdir")
    r.add_argument("--lib", action="append", default=[])
    r.add_argument("--rebuild", action="store_true", help="re-extract ILMs that exist in OUT/ilm")
    r.add_argument("--reduce", action="store_true", help="read_spef -reduce (pi-Elmore at read; capacity lever)")
    c = sub.add_parser("compare", help="seam slack agreement of two die_sta.json")
    c.add_argument("a")
    c.add_argument("b")
    c.add_argument("--tol", type=float, default=2.0)
    c.add_argument("--out")
    p = sub.add_parser("replica", help="flat capacity vehicle: N stitched copies of one routed partition")
    p.add_argument("--netlist", required=True)
    p.add_argument("--spef", help="omit: netlist-only cost (no parasitics)")
    p.add_argument("--n", type=int, required=True)
    p.add_argument("--reduce", action="store_true", help="read_spef -reduce (pi-Elmore at read: less memory)")
    p.add_argument("--out", required=True)
    p.add_argument("--corner", default="TT")
    p.add_argument("--period-ps", type=float, default=PERIOD_PS)
    p.add_argument("--libdir")
    p.add_argument("--lib", action="append", default=[])
    t = sub.add_parser("top", help="structural die top netlist of a plan")
    t.add_argument("--plan", required=True)
    t.add_argument("--out", required=True)
    t.add_argument("--views", help="dir of <type>/ot_clock_taps.json (kit results): drops sinkless taps")
    e = sub.add_parser("extract", help="6_final.v + .spef of a routed kit ODB (docker ORFS RCX)")
    e.add_argument("--odb", required=True)
    e.add_argument("--out", required=True)
    e.add_argument("--mem", type=int, default=32)
    e.add_argument("--image", default=ORFS_IMAGE)
    for x in (g, r, p):
        x.add_argument("--threads", type=int, default=1, help="OpenSTA -threads")
    a = ap.parse_args(argv)
    global THREADS
    THREADS = getattr(a, "threads", 1)
    if a.cmd == "ilm":
        st = make_ilm(a.netlist, a.spef, a.out, corner_libs("TT", a.libdir, a.lib), sdc=a.sdc)
        print(json.dumps(st, indent=1))
    elif a.cmd == "run":
        a.corner = a.corner or ["TT", "FF"]
        res = cmd_run(a)
        return 0 if all(r["exit"] == 0 for r in res["corners"].values()) else 1
    elif a.cmd == "extract":
        return cmd_extract(a)
    elif a.cmd == "top":
        print(write_top(a.plan, a.out, a.views))
    elif a.cmd == "compare":
        return 0 if cmd_compare(a)["status"] == "AGREE" else 1
    elif a.cmd == "replica":
        return cmd_replica(a)["exit"]
    return 0


if __name__ == "__main__":
    sys.exit(main())
