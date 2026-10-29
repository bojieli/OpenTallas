"""Boundary-register guard on the Yosys netlist of a partition kit (CP1-R10, COORD 10-24).

    python3 tools/die_plan/face_guard.py NETLIST.v [--top MOD] [--pins pins.json] [--out face_guard.json]   # exit 1 = FAIL

Every planned face register (R2 face flops, one per pin bit of the R5 bit-level census) must survive synthesis as its
OWN flop:
  - an output port bit is driven by a flop (Q/QN, through single-fanout buffers / inverters) whose
    output net reaches nothing but that port;
  - an input port bit loads exactly one cell pin, which leads (through single-fanout buffers / inverters) to the D pin
    of a flop.
Failure classes (the bugs this guards against): `merged` (Yosys opt_merge folded identical boundary flops of different
buses into one flop driving several ports: CP1 r6 u_bout_x_o0.q[718] -> frame_int_o0[892], S81-P9 shared epoch flops),
`shared` (the face flop also feeds internal logic), `const` (constant-D flop removed, port tied), `dropped` (input bit
with no register: its q was unused), `feedthrough` (port wired to port), `unregistered` (combinational logic between
the port and its flop).
The source-side prevention is gen_rtl.CELLS: ot_dp_st / ot_dp_ste / ot_dp_ep carry (* keep_hierarchy, keep *).
run_kit.sh runs this guard right after `make synth` and stops the kit on FAIL.
"""
import argparse
import itertools
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

OUT_PINS = {"Y", "Q", "QN", "H", "L", "CON", "SN", "Z", "ZN", "O"}
# Clocks and the reset/START *inputs* (arst_n / rst_n / start_i: root synchroniser or typed control) are not face
# registers.  The registered wavefront OUTS rst_o_<k> / start_o_<k> ARE partition pins and are checked like data: one
# dedicated relay per pin (reset_tree.py out relays; owner rule: register every partition pin, no shared fanout).
SKIP_RE = r"^(clk(_t[0-9]+|_c[0-9]+)?|arst_n|rst_n|start_i)$"


def is_ff(master):
    return "DFF" in master.upper()


def is_buf(master):
    m = master.upper()
    return m.startswith(("BUF", "INV", "HB", "$_NOT_", "$_BUF_"))


# ---- structural Verilog (Yosys write_verilog) ---------------------------------------------------------------------
_TOK = re.compile(r"\s*(?:(\\\S+)|([A-Za-z_][A-Za-z0-9_$]*)|(\d+'[bhdoBHDO][0-9a-fA-FxXzZ_]+)|(\d+)|(.))", re.S)


def _tokens(text):
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"\(\*.*?\*\)", " ", text, flags=re.S)
    text = re.sub(r"//[^\n]*", " ", text)
    pos, n, out = 0, len(text), []
    while pos < n:
        m = _TOK.match(text, pos)
        if not m or m.end() == pos:
            break
        pos = m.end()
        esc, ident, const, num, ch = m.groups()
        if esc:
            out.append(("id", esc[1:]))
        elif ident:
            out.append(("id", ident))
        elif const:
            out.append(("const", const))
        elif num:
            out.append(("num", num))
        elif ch and not ch.isspace():
            out.append(("p", ch))
    return out


def _const_bits(c):
    w, v = c.split("'")
    w, base, digits = int(w), v[0].lower(), v[1:].replace("_", "")
    if any(ch in "xXzZ" for ch in digits):
        return ["CONST_X"] * w
    val = int(digits, {"b": 2, "h": 16, "d": 10, "o": 8}[base])
    return [f"CONST_{(val >> i) & 1}" for i in range(w - 1, -1, -1)]     # msb first


class Module:
    def __init__(self, name):
        self.name, self.ports, self.dirs, self.wires = name, [], {}, {}
        self.cells, self.assigns = [], []        # cells: (type, inst, {pin: [bits msb..lsb]})


def parse(text):
    toks = _tokens(text)
    mods, i = {}, 0

    def expect(v):
        nonlocal i
        if toks[i][1] != v:
            raise ValueError(f"expected {v} got {toks[i]} near token {i}")
        i += 1

    def rng():
        nonlocal i
        if toks[i] == ("p", "["):
            i += 1
            a = int(toks[i][1])
            i += 2
            b = int(toks[i][1])
            i += 2
            return a, b
        return None

    while i < len(toks):
        if toks[i] != ("id", "module"):
            i += 1
            continue
        i += 1
        M = Module(toks[i][1])
        i += 1
        if toks[i] == ("p", "("):
            while toks[i] != ("p", ")"):
                if toks[i][0] == "id":
                    M.ports.append(toks[i][1])
                i += 1
            i += 1
        expect(";")

        def expr():
            """-> bits msb first (names 'w' or 'w[i]', or CONST_*)."""
            nonlocal i
            t = toks[i]
            if t == ("p", "{"):
                i += 1
                bits = []
                while toks[i] != ("p", "}"):
                    if toks[i] == ("p", ","):
                        i += 1
                        continue
                    bits += expr()
                i += 1
                return bits
            if t[0] == "const":
                i += 1
                return _const_bits(t[1])
            if t[0] == "num":
                i += 1
                return _const_bits(f"32'd{t[1]}")
            name = t[1]
            i += 1
            if toks[i] == ("p", "["):
                i += 1
                a = int(toks[i][1])
                i += 1
                if toks[i] == ("p", ":"):
                    i += 1
                    b = int(toks[i][1])
                    i += 2
                    step = -1 if a >= b else 1
                    return [f"{name}[{k}]" for k in range(a, b + step, step)]
                i += 1
                return [f"{name}[{a}]"]
            r = M.wires.get(name)
            if r is None:
                return [name]
            a, b = r
            step = -1 if a >= b else 1
            return [f"{name}[{k}]" for k in range(a, b + step, step)]

        while toks[i] != ("id", "endmodule"):
            t = toks[i]
            if t[0] == "id" and t[1] in ("input", "output", "inout", "wire", "reg"):
                kind = t[1]
                i += 1
                if toks[i] in (("id", "wire"), ("id", "reg"), ("id", "signed")):
                    i += 1
                r = rng()
                while True:
                    nm = toks[i][1]
                    i += 1
                    if r:
                        M.wires[nm] = r
                    if kind in ("input", "output", "inout"):
                        M.dirs[nm] = kind
                    if toks[i] == ("p", ","):
                        i += 1
                        continue
                    break
                expect(";")
            elif t == ("id", "assign"):
                i += 1
                lhs = expr()
                expect("=")
                rhs = expr()
                expect(";")
                M.assigns.append((lhs, rhs))
            elif t[0] == "id":
                typ = t[1]
                i += 1
                if toks[i] == ("p", "#"):                  # parameters (not in Yosys netlists, but skip them)
                    d = 0
                    i += 1
                    while True:
                        d += toks[i] == ("p", "(")
                        d -= toks[i] == ("p", ")")
                        i += 1
                        if d == 0:
                            break
                inst = toks[i][1]
                i += 1
                expect("(")
                conns = {}
                while toks[i] != ("p", ")"):
                    if toks[i] == ("p", ","):
                        i += 1
                        continue
                    expect(".")
                    pin = toks[i][1]
                    i += 1
                    expect("(")
                    conns[pin] = expr() if toks[i] != ("p", ")") else []
                    expect(")")
                i += 1
                expect(";")
                M.cells.append((typ, inst, conns))
            else:
                i += 1
        i += 1
        mods[M.name] = M
    return mods


def _bits_of(M, name):
    r = M.wires.get(name)
    if r is None:
        return [name]
    a, b = r
    step = -1 if a >= b else 1
    return [f"{name}[{k}]" for k in range(a, b + step, step)]


class Flat:
    """flattened bit-level connectivity: union-find over net bits, std cells with pin directions."""

    def __init__(self, mods, top):
        self.par = {}
        self.cells = []        # (master, path, {pin: (dir, [netbits])})
        self._flat(mods, top, "", None)

    def find(self, x):
        p = self.par.setdefault(x, x)
        while p != self.par.setdefault(p, p):
            self.par[p] = self.par[self.par[p]]
            p = self.par[p]
        self.par[x] = p
        return p

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            if rb.startswith("CONST_"):
                ra, rb = rb, ra
            self.par[rb] = ra

    def _flat(self, mods, mname, pfx, portmap):
        M = mods[mname]

        def net(b):
            if b.startswith("CONST_"):
                return b
            return pfx + b

        if portmap is not None:
            for p in M.ports:
                for b, outer in zip(_bits_of(M, p), portmap.get(p, [])):
                    self.union(net(b), outer)
        for lhs, rhs in M.assigns:
            for a, b in zip(lhs[::-1], rhs[::-1]):
                self.union(net(a), net(b))
        for typ, inst, conns in M.cells:
            path = pfx + inst
            if typ in mods:
                sub = mods[typ]
                pm = {}
                for p, bits in conns.items():
                    w = len(_bits_of(sub, p))
                    bits = [net(b) for b in bits]
                    pm[p] = (["CONST_X"] * (w - len(bits)) + bits)[-w:] if bits else []
                self._flat(mods, typ, path + "/", pm)
            else:
                pins = {p: ("out" if p in OUT_PINS else "in", [net(b) for b in bits]) for p, bits in conns.items()}
                self.cells.append((typ, path, pins))


def read_ft1(path):
    """slot names with ONE station from a kit's ft_stations.txt (`slot stations in_face out_face ...`)."""
    out = set()
    for ln in Path(path).read_text().splitlines():
        f = ln.split()
        if f and not f[0].startswith("#") and len(f) >= 2 and f[1] == "1":
            out.add(f[0])
        elif f and f[0] == "pair" and len(f) == 3:     # core kit one-station bus pair (gen_core_kit_qc ft1_pairs)
            out.add(f"{f[1]}>{f[2]}")
    return out


def _pairs(ft1):
    """declared core bus pairs {(I, O)} of the ft1 set ('I>O' entries written by read_ft1 from `pair I O` lines)."""
    return {tuple(x.split(">", 1)) for x in ft1 if ">" in x}


def _bus_bit(b):
    m = re.match(r"^(.+?)(?:\[(\d+)\])?$", b)
    return m.group(1), (None if m.group(2) is None else int(m.group(2)))


def _ft1_pair(bs, ft1, dirs=None):
    """True when the bits are exactly S_i[k] and S_o[k] of one 1-station ft slot S: that slot's single station register
    is by plan both the in-face and the out-face register (ELEM-S81 10-24: slice_station types), or bit k of the input
    bus I and bit k of the output bus O of a declared core pair `I>O` (direction from the netlist port directions:
    the input member must belong to I, the output member to O).  The declaration only names the pair; guard() verifies
    each declared pair structurally (I[k] -> buffers -> exactly one flop D, its Q -> buffers -> O[k], no other load)."""
    if len(bs) != 2:
        return False
    if dirs is not None:
        (n0, k0), (n1, k1) = (_bus_bit(b) for b in bs)
        d0, d1 = dirs.get(n0), dirs.get(n1)
        for (ni, di), (no, do_) in (((n0, d0), (n1, d1)), ((n1, d1), (n0, d0))):
            if di == "input" and do_ == "output" and (ni, no) in _pairs(ft1) and k0 == k1:
                return True
    m = [re.match(r"^(.+)_([io])(\[\d+\])?$", b) for b in bs]
    return (all(m) and m[0].group(1) == m[1].group(1) and m[0].group(1) in ft1 and m[0].group(3) == m[1].group(3)
            and {m[0].group(2), m[1].group(2)} == {"i", "o"})


STRAP_RE = re.compile(r"^strap_[A-Za-z0-9_]+$")   # = straps.STRAP_RE (kept inline: kits copy this file alone)


def strap_list(names):
    """declared ID strap bus names (OWNER 10-25 option B rule 1: strap_*, unique); anything else -> ValueError"""
    sl = list(names or [])
    bad = [n for n in sl if not isinstance(n, str) or not STRAP_RE.match(n)]
    if bad or len(set(sl)) != len(sl):
        raise ValueError(f"straps must be unique strap_<id> names (OWNER 10-25 option B): {bad or sl}")
    return sl


def kit_strap_list(kitdir):
    """the kit's declared straps: straps.json, else sdc_lint.json "straps", else core.json report.straps
    kind == id_strap (same order as straps.kit_straps).  [] when none."""
    kd = Path(kitdir)
    if (kd / "straps.json").is_file():
        d = json.loads((kd / "straps.json").read_text())
        return strap_list(d.get("straps", []) if isinstance(d, dict) else d)
    if (kd / "sdc_lint.json").is_file():
        s = json.loads((kd / "sdc_lint.json").read_text()).get("straps")
        if s:
            return strap_list(s)
    if (kd / "core.json").is_file():
        rep = (json.loads((kd / "core.json").read_text()).get("report") or {}).get("straps") or []
        return strap_list([x["port"] for x in rep if isinstance(x, dict) and x.get("kind") == "id_strap"])
    return []


def kit_land(path):
    """declared landing-ring buses of a kit land_slots.json {"schema": ..., "buses": {bus: D}} (S81-CORE-LAT-R21)."""
    d = json.loads(Path(path).read_text())
    return {str(k): (dict(v) if isinstance(v, dict) else int(v)) for k, v in (d.get("buses") or {}).items()}


START_RE = r"^cland_fstart_in_[A-Za-z0-9_]+$"


def kit_starts(path):
    """declared landing START inputs of a kit land_slots.json {"starts": {port: {"insts": [..], "max_loads": n}}}
    (COORD 10-28 21:38 HEAD-KITS-1 ASK1).  ValueError on a malformed entry."""
    d = json.loads(Path(path).read_text())
    out = {}
    for k, v in (d.get("starts") or {}).items():
        out[str(k)] = start_spec(str(k), v)
    return out


def start_spec(port, v):
    """(insts, max_loads) of one declared START input; only cland_fstart_in_* ports, >= 1 instance, max_loads >= 1."""
    if not re.match(START_RE, port):
        raise ValueError(f"land_slots start {port}: only cland_fstart_in_* ports can be declared START pins")
    if not isinstance(v, dict) or set(v) - {"insts", "max_loads"}:
        raise ValueError(f"land_slots start {port} spec {v}: want {{insts, max_loads}}")
    insts = [str(x) for x in (v.get("insts") or [])]
    ml = int(v.get("max_loads", 0))
    if not insts or ml < 1 or any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", x) for x in insts):
        raise ValueError(f"land_slots start {port} spec {v}: want >= 1 top-level instance name and max_loads >= 1")
    return tuple(insts), ml


LAND_FORMS = ("icg", "hold_mux")


def land_spec(v):
    """(D, form) of one declared landing bus: an int D = the ICG slot form (S81-CORE-LAT-R21); a dict
    {"D": n, "form": "hold_mux"} = the enable-mux slot form (COORD 10-28 06:30, DIE-HEAD-8 witness).  ValueError else."""
    if isinstance(v, dict):
        if set(v) - {"D", "form"} or v.get("form", "icg") not in LAND_FORMS:
            raise ValueError(f"land_slots bus spec {v}: want {{D, form in {LAND_FORMS}}}")
        return int(v["D"]), str(v.get("form", "icg"))
    return int(v), "icg"


# ---- single-output std-cell boolean models (hold_mux slot proof; a cell without a model rejects the slot) --------
def _cell_base(m):
    return re.sub(r"x(p\d+|\d+).*$", "", m.split("_ASAP7")[0])


def cell_fn(m, ins):
    """ins {pin: bool} -> output bool of a single-output ASAP7 combinational cell; KeyError when not modelled."""
    b = _cell_base(m)
    if b.startswith(("BUF", "HB")):
        return ins["A"]
    if b.startswith("INV"):
        return not ins["A"]
    if b in ("TIEHI",):
        return True
    if b in ("TIELO",):
        return False
    mm = re.fullmatch(r"(N?AND|N?OR|XN?OR)(\d)", b)
    if mm:
        op, n = mm.group(1), int(mm.group(2))
        v = [ins[c] for c in "ABCDE"[:n]]
        if op in ("AND", "NAND"):
            o = all(v)
        elif op in ("OR", "NOR"):
            o = any(v)
        else:
            o = sum(v) % 2 == 1
        return (not o) if op in ("NAND", "NOR", "XNOR") else o
    mm = re.fullmatch(r"(AOI|OAI|AO|OA)(\d+)", b)
    if mm:
        kind, sizes = mm.group(1), [int(c) for c in mm.group(2)]
        vals = []
        for gi, n in enumerate(sizes):
            L = chr(65 + gi)
            v = [ins[L]] if n == 1 else [ins[f"{L}{j}"] for j in range(1, n + 1)]
            vals.append(all(v) if kind.startswith("AO") else any(v))
        o = any(vals) if kind.startswith("AO") else all(vals)
        return (not o) if kind.endswith("I") else o
    if b == "A2O1A1I":
        return not (((ins["A1"] and ins["A2"]) or ins["B"]) and ins["C"])
    if b == "O2A1O1I":
        return not (((ins["A1"] or ins["A2"]) and ins["B"]) or ins["C"])
    if b in ("MAJ", "MAJI"):
        o = (ins["A"] + ins["B"] + ins["C"]) >= 2
        return (not o) if b == "MAJI" else o
    raise KeyError(f"no boolean model for {m}")


def kit_bump_list(kitdir):
    """the kit's declared hard-IP line side (budget.json bump_ports, gen_phys KV-KITS-4): [(port, dir, width)]."""
    b = Path(kitdir) / "budget.json"
    if not b.is_file():
        return []
    return [(x["port"], x["dir"], int(x["width"])) for x in json.loads(b.read_text()).get("bump_ports") or []]


DEAD_SCHEMA = "opentallas.kit_dead_inputs.v1"
_DEAD_BIT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\[[0-9]+\])?$")


def dead_input_list(doc):
    """QK-CORES-5 10-27 (COORD ruling: 'declare dead only with a proof receipt'): a kit dead_inputs.json names input
    pin bits that are provably unobservable in this core's parameterisation (no flop to register them: synthesis
    removes their whole cone).  Fail-closed: schema, unique exact bit names (no regex), and a proof record with
    verdict PASS, a method and a receipt are required; anything else -> ValueError."""
    if not isinstance(doc, dict) or doc.get("schema") != DEAD_SCHEMA:
        raise ValueError(f"dead_inputs.json: schema must be {DEAD_SCHEMA}")
    bits = doc.get("bits")
    if not isinstance(bits, list) or not bits or len(set(bits)) != len(bits) or \
            not all(isinstance(b, str) and _DEAD_BIT.match(b) for b in bits):
        raise ValueError(f"dead_inputs.json: bits must be unique exact port bit names: {bits}")
    pr = doc.get("proof")
    if not isinstance(pr, dict) or pr.get("verdict") != "PASS" or not pr.get("method") or not pr.get("receipt"):
        raise ValueError("dead_inputs.json: proof needs verdict PASS + method + receipt")
    return list(bits)


def kit_dead_list(kitdir):
    """the kit's declared proven-dead input bits (dead_inputs.json), [] when none."""
    f = Path(kitdir) / "dead_inputs.json"
    return dead_input_list(json.loads(f.read_text())) if f.is_file() else []


def _std_cell(master):
    return "_ASAP7_" in master.upper() or master.startswith("$")


def sdc_clock_ports(text):
    """port names of every `create_clock ... [get_ports NAME]` in a kit SDC (virtual clocks have no port)."""
    out = []
    for m in re.finditer(r"^\s*create_clock\b[^\n]*\[get_ports\s+\{?([A-Za-z_][A-Za-z0-9_]*)\}?\s*\]", text, re.M):
        if m.group(1) not in out:
            out.append(m.group(1))
    return out


def sdc_clock_exports(text):
    """[(output port, source port)] of every `create_generated_clock ... -source [get_ports S] ... [get_ports T]`
    with -divide_by 1 (a forwarded clock output, landing_contract.sdc)."""
    out = []
    for m in re.finditer(r"^\s*create_generated_clock\b([^\n]*)$", text, re.M):
        ln = m.group(1)
        src = re.search(r"-source\s+\[get_ports\s+\{?([A-Za-z_][A-Za-z0-9_]*)\}?\s*\]", ln)
        tgt = re.search(r"\[get_ports\s+\{?([A-Za-z_][A-Za-z0-9_]*)\}?\s*\]\s*$", ln)
        if src and tgt and re.search(r"-divide_by\s+1\b", ln) and (tgt.group(1), src.group(1)) not in out:
            out.append((tgt.group(1), src.group(1)))
    return out


def guard(text, top=None, skip_re=SKIP_RE, pins=None, ft1=(), straps=(), bumps=(), clocks=(), land=None, dead=(),
          exports=(), starts=None):
    """straps: declared ID strap ports (OWNER 10-25 option B, straps.py): quasi-static strap_* inputs tied at the
    parent need no pin register -> exempt (recorded in the result); any other name is refused (ValueError).
    bumps: declared hard-IP line-side ports [(port, dir, width)] (plan bump_ports, KV-KITS-4 10-27): the bump IS the
    hard macro's own pin, so it carries no pin register; instead every bit must wire straight to exactly one pin of
    one hard (non-standard-cell) macro with no other driver or load (anything else fails class "bump").
    land: declared landing-ring input buses {bus: D} (S81-CORE-LAT-R21, COORD S81-CORE-LAT-R20 ruling (a): face register
    per landing slot, no added cycle): every bit of such a bus must load EXACTLY D cell pins, each the D pin of a
    distinct flop (no buffer, no logic: the slots are the face registers), the D flops clocked by D DISTINCT integrated
    clock gates (one ICG* per slot; its GCLK net feeds flop clock pins only), all D ICGs gated from ONE clock net (the
    lane's forwarded clock).  Anything else
    fails class "land_slot"; a declared bus that is not an input port fails too.
    A bus declared {"D": n, "form": "hold_mux"} (COORD 10-28 06:30: the enable-mux slot form, no ICG) instead needs,
    per bit: EXACTLY D cell-pin loads; everything reachable forward from each load through combinational std cells is
    ONE flop D pin (no port, macro, other flop pin or second flop: no leak), the D flops distinct and on one clock net;
    each flop's D cone (leaves = the bit, the flop's OWN Q/QN, control leaves) evaluates exhaustively to the bit when
    its write condition W holds and to its own state otherwise (own-Q hold, never written -> FAIL), W uses no landing
    bit and no undriven/macro leaf, and the D write conditions are pairwise mutually exclusive.  Each slot flop is that
    bit's face register (two bits on one slot flop -> merged).
    exports: declared forwarded clock outputs [(T, S)] (kit SDC create_generated_clock -source [get_ports S] -divide_by 1
    [get_ports T], DIE-HEAD-9 FACE (c)): T is an output port wired from clock port S through single-driver,
    single-load buffers / an even number of inverters only, the T net and every chain net carry nothing else; then T
    is a clock role (recorded in clock_exports), not face data.  Anything else fails class "clock_export".
    starts: declared landing START inputs {port: {"insts": [I..], "max_loads": n}} (land_slots.json "starts", COORD
    10-28 21:38): a count-aligned sender start forwarded with fclk (cland_fstart_in_<b>) that feeds the receiver ring's
    write reset t_rst_n and/or a child origin's p_start.  It is a declared START pin, not a face register, and is still
    proved on the netlist: a 1-bit cland_fstart_in_* input, its net undriven and on no other port, 1..max_loads direct
    cell loads, and everything reachable forward through combinational std cells is a flop D pin of a cell inside one
    of the declared top-level instances I (no port, macro, clock/reset/other pin, no flop outside I); every declared
    instance is reached.  Anything else fails class "start"; an undeclared start port keeps the normal face checks.
    dead: declared proven-dead input bits (kit dead_inputs.json, dead_input_list): each must be an input port bit
    whose net has NO load and no driver in the netlist -- then it is recorded (dead_declared), not a face register;
    a declared bit that is not an input port bit, or that still loads anything, fails class "dead"."""
    # QC-KITS-R1 10-27: extra clock roles of a bound partition (e.g. coll clk_coll / clk_serdes) are clock ports, not
    # face data: the kit SDC create_clock list (generated from the plan) exempts them like clk / clk_tN.
    clocks = [c for c in (clocks or ()) if not re.fullmatch(skip_re, c)]
    if clocks:
        if pins is not None and set(clocks) & {str(x.get("bus")) for x in pins}:
            raise ValueError(f"face_guard: SDC clock port(s) also planned as face data bits: "
                             f"{sorted(set(clocks) & {str(x.get('bus')) for x in pins})}")
        skip_re = r"(?:" + skip_re + r")|^(?:" + "|".join(re.escape(x) for x in clocks) + r")$"
    bump_names = [b[0] for b in (bumps or ())]
    if bump_names:
        skip_re = r"(?:" + skip_re + r")|^(?:" + "|".join(re.escape(x) for x in bump_names) + r")$"
    if straps:
        sl = strap_list(straps)
        skip_re = r"(?:" + skip_re + r")|^(?:" + "|".join(re.escape(x) for x in sl) + r")$"
        if pins is not None:
            pins = [x for x in pins if str(x.get("bus")) not in set(sl)]
    mods = parse(text)
    if top is None:
        used = {typ for M in mods.values() for typ, _, _ in M.cells}
        tops = [m for m in mods if m not in used]
        if len(tops) != 1:
            raise ValueError(f"cannot pick the top module: {tops}")
        top = tops[0]
    T = mods[top]
    F = Flat(mods, top)
    drv, loads = defaultdict(list), defaultdict(list)
    for ci, (m, path, pp) in enumerate(F.cells):
        for p, (d, bits) in pp.items():
            for b in bits:
                r = F.find(b)
                (drv if d == "out" else loads)[r].append((ci, p))
    port_root = {}
    for p in T.ports:
        for b in _bits_of(T, p):
            port_root[b] = F.find(b)
    roots_ports = defaultdict(list)
    for b, r in port_root.items():
        roots_ports[r].append(b)
    res = dict(top=top, checked=0, ok=0, fails=defaultdict(list), flops={}, straps_exempt=sorted(straps or ()))
    dead = set(dead or ())
    dead_seen = set()
    res["dead_declared"] = []
    claimed = defaultdict(list)

    def fail(cls, b, why):
        res["fails"][cls].append(f"{b}: {why}")

    res["bumps_exempt"] = sorted(bump_names)
    for name, d, w in (bumps or ()):             # a declared bump: port of that dir/width, wired only to one macro pin
        if T.dirs.get(name) != d:
            fail("bump", name, f"declared {d} bump port is {T.dirs.get(name)} in the netlist")
            continue
        bits = _bits_of(T, name)
        if len(bits) != w:
            fail("bump", name, f"declared width {w}, netlist {len(bits)}")
            continue
        for b in bits:
            r = port_root[b]
            others = [x for x in roots_ports[r] if x != b]
            # pin direction of a macro is unknown to this reader (OUT_PINS covers std cells only): the bit's net must
            # touch exactly one cell pin in total, and that cell is a hard macro
            hard = drv[r] + loads[r]
            if others or len(hard) != 1 or _std_cell(F.cells[hard[0][0]][0]):
                fail("bump", b, f"not a direct single hard-macro pin (ports {others[:2]}, {len(hard)} cell pins "
                                f"{[F.cells[c][0] for c, _ in hard[:3]]})")
                continue
            res["bump_bits"] = res.get("bump_bits", 0) + 1
    land_form = {}
    land_raw = dict(land or {})
    land = {}
    for x, v in land_raw.items():
        land[x], land_form[x] = land_spec(v)
    for x, dd in land.items():                   # a declared landing bus: an input port, D >= 2
        if T.dirs.get(x) != "input" or int(dd) < 2:
            fail("land_slot", x, f"declared landing bus is {T.dirs.get(x)} with D {dd} (want input, D >= 2)")
    starts = {str(k): (v if isinstance(v, tuple) else start_spec(str(k), v)) for k, v in (starts or {}).items()}
    for x in starts:                             # a declared START pin: a 1-bit input port, not a landing bus
        if T.dirs.get(x) != "input" or len(_bits_of(T, x)) != 1 or x in land:
            fail("start", x, f"declared START pin is {T.dirs.get(x)} width {len(_bits_of(T, x)) if x in T.ports else 0}"
                             f"{' and a landing bus' if x in land else ''} (want a 1-bit input)")
    res["start_pins"] = {}
    land_roots = {port_root[b] for x in land if x in T.ports for b in _bits_of(T, x)}
    out_port_roots = {port_root[b] for x in T.ports if T.dirs.get(x) == "output" for b in _bits_of(T, x)}
    lmemo = {}

    def _single_drv(net):
        return drv[net][0] if len(drv[net]) == 1 else None

    def _leaves(net):
        """cone leaves of net back through single-driver combinational std cells (stop at flops, ports, consts,
        macros, undriven/multi-driven nets)."""
        if net in lmemo:
            return lmemo[net]
        d = _single_drv(net)
        if net.startswith("CONST_") or net in roots_ports or d is None:
            lmemo[net] = frozenset([net])
            return lmemo[net]
        m, _, pp = F.cells[d[0]]
        if is_ff(m) or not _std_cell(m):
            lmemo[net] = frozenset([net])
            return lmemo[net]
        lmemo[net] = frozenset()                 # combinational loop guard
        acc = set()
        for k, (dd_, v) in pp.items():
            if dd_ == "in" and v:
                acc |= _leaves(F.find(v[0]))
        lmemo[net] = frozenset(acc)
        return lmemo[net]

    def _ev(net, asg, memo):
        if net in asg:
            return asg[net]
        if net == "CONST_1":
            return True
        if net == "CONST_0":
            return False
        if net in memo:
            return memo[net]
        ci = _single_drv(net)[0]
        m, _, pp = F.cells[ci]
        memo[net] = cell_fn(m, {k: _ev(F.find(v[0]), asg, memo) for k, (dd_, v) in pp.items() if dd_ == "in" and v})
        return memo[net]

    def _depth(src, dst, memo):
        if dst == src:
            return 0
        if dst in memo:
            return memo[dst]
        d = _single_drv(dst)
        memo[dst] = -1
        if d is None or dst in roots_ports or is_ff(F.cells[d[0]][0]) or not _std_cell(F.cells[d[0]][0]):
            return -1
        best = -1
        for k, (dd_, v) in F.cells[d[0]][2].items():
            if dd_ == "in" and v:
                x = _depth(src, F.find(v[0]), memo)
                if x >= 0:
                    best = max(best, x + 1)
        memo[dst] = best
        return best

    def _fwd(ci, seen, out):
        """sinks reachable from cell ci's output through combinational std cells"""
        m, path, pp = F.cells[ci]
        for k, (dd_, v) in pp.items():
            if dd_ != "out" or not v:
                continue
            n = F.find(v[0])
            if n in out_port_roots or (n in roots_ports and n not in out_port_roots):
                out.append(("port", n))
            for cj, pin in loads[n]:
                if (cj, pin) in seen:
                    continue
                seen.add((cj, pin))
                mj = F.cells[cj][0]
                if is_ff(mj):
                    out.append(("ff_D" if pin == "D" else f"ff_{pin}", cj))
                elif not _std_cell(mj):
                    out.append(("macro", cj))
                else:
                    _fwd(cj, seen, out)

    def land_mux(b, r, D):
        """(None, flops, depths) = OK, else (failure text, [], [])."""
        ld = loads[r]
        if len(ld) != D:
            return f"{len(ld)} loads on {r}, declared D {D}", [], []
        if drv[r]:
            return f"landing bit net also driven by {F.cells[drv[r][0][0]][1]}", [], []
        ffs, per = [], []
        for ci, pin in ld:
            m, path, pp = F.cells[ci]
            if is_ff(m):
                sinks = [("ff_D" if pin == "D" else f"ff_{pin}", ci)]
            elif not _std_cell(m):
                return f"load {m} {path} is a macro pin", [], []
            else:
                sinks = []
                _fwd(ci, {(ci, pin)}, sinks)
            bad = sorted({k for k, _ in sinks if k != "ff_D"})
            fl = sorted({c for k, c in sinks if k == "ff_D"})
            if bad or len(fl) != 1:
                return f"load {path} reaches {bad or ''} {len(fl)} slot flop(s) (want exactly one flop D)", [], []
            ffs.append(fl[0])
        if len(set(ffs)) != D:
            return f"{len(set(ffs))} distinct slot flops for {D} loads", [], []
        clks, depths = set(), []
        for fi in ffs:
            m, path, pp = F.cells[fi]
            ck = [v for k, (dd_, v) in pp.items() if k in ("CLK", "C", "CK") and len(v) == 1]
            dn = [v for k, (dd_, v) in pp.items() if k == "D" and len(v) == 1]
            st = [(k, F.find(v[0])) for k, (dd_, v) in pp.items() if k in ("Q", "QN") and v]
            if len(ck) != 1 or len(dn) != 1:
                return f"slot flop {path} clock/D pin not found", [], []
            if len(st) != 1:
                return f"slot flop {path} has {len(st)} connected Q/QN (want one own state)", [], []
            clks.add(F.find(ck[0][0]))
            dnet = F.find(dn[0][0])
            L = _leaves(dnet)
            sp, sn = st[0]
            if r not in L:
                return f"slot flop {path} D cone does not contain the bit", [], []
            if sn not in L:
                return f"slot flop {path}: own {sp} not in its D cone (no hold feedback)", [], []
            ctl = sorted(x for x in L if x not in (r, sn) and not x.startswith("CONST_"))
            for x in ctl:
                if x in land_roots:
                    return f"slot flop {path} write condition uses landing bit {roots_ports[x][0]}", [], []
                d = _single_drv(x)
                if x not in roots_ports and (d is None or not is_ff(F.cells[d[0]][0])):
                    return f"slot flop {path} control leaf {x} is not a flop output or port", [], []
            if len(ctl) > 14:
                return f"slot flop {path}: {len(ctl)} control leaves (too wide to prove)", [], []
            W = set()
            for vals in itertools.product((False, True), repeat=len(ctl)):
                a0 = dict(zip(ctl, vals))
                res_ = []
                try:
                    for bv in (False, True):
                        for sv in (False, True):
                            a = dict(a0)
                            a[r], a[sn] = bv, sv
                            res_.append((bv, (not sv) if sp == "QN" else sv, _ev(dnet, a, {})))
                except KeyError as e:
                    return f"slot flop {path} D cone: {e.args[0]}", [], []
                if all(dv == bv for bv, s_, dv in res_):
                    W.add(vals)
                elif not all(dv == s_ for bv, s_, dv in res_):
                    return f"slot flop {path}: D is neither the bit nor its own state at {a0}", [], []
            if not W:
                return f"slot flop {path} is never written", [], []
            per.append((ctl, W))
            depths.append(_depth(r, dnet, {}))
        if len(clks) != 1:
            return f"slot flops on {len(clks)} clock nets (want one forwarded clock)", [], []
        allc = sorted({x for c, _ in per for x in c})
        if len(allc) > 16:
            return f"{len(allc)} union control leaves (too wide to prove exclusivity)", [], []
        for vals in itertools.product((False, True), repeat=len(allc)):
            a = dict(zip(allc, vals))
            if sum(1 for c, Wk in per if tuple(a[x] for x in c) in Wk) > 1:
                return f"write conditions not mutually exclusive at {a}", [], []
        return None, ffs, depths

    def start_pin(b, r, insts, max_loads):
        """None = OK (record), else the failure text."""
        ld = loads[r]
        if drv[r]:
            return f"START net also driven by {F.cells[drv[r][0][0]][1]}"
        if not 1 <= len(ld) <= max_loads:
            return f"{len(ld)} direct loads on {r} (declared 1..{max_loads})"
        sinks, seen = [], set()
        for ci, pin in ld:
            m, path, pp = F.cells[ci]
            if is_ff(m):
                sinks.append(("ff_D" if pin == "D" else f"ff_{pin}", ci))
            elif not _std_cell(m):
                sinks.append(("macro", ci))
            elif (ci, pin) not in seen:
                seen.add((ci, pin))
                _fwd(ci, seen, sinks)
        bad = sorted({k for k, _ in sinks if k != "ff_D"})
        if bad:
            return f"START cone reaches {bad} (want flop D pins only)"
        hit, outside = set(), []
        for _, ci in sinks:
            path = F.cells[ci][1]
            top_i = re.split(r"[/.]", path, maxsplit=1)[0]
            if top_i in insts:
                hit.add(top_i)
            else:
                outside.append(path)
        if outside:
            return f"START cone reaches flop(s) outside {list(insts)}: {sorted(set(outside))[:3]}"
        if hit != set(insts):
            return f"declared instance(s) {sorted(set(insts) - hit)} not reached"
        res["start_pins"][b] = dict(loads=len(ld), flops=len({c for _, c in sinks}), insts=sorted(hit))
        return None

    def land_slot(b, r, D):
        """None = OK (the D slot flops), else the failure text."""
        ld = loads[r]
        if len(ld) != D:
            return f"{len(ld)} loads on {r}, declared D {D}"
        ffs, icgs, roots = [], set(), set()
        for ci, pin in ld:
            m, path, pp = F.cells[ci]
            if not is_ff(m) or pin != "D":
                return f"load {m} {path}.{pin} is not a slot flop D pin"
            ck = [v for k, (dd_, v) in pp.items() if k in ("CLK", "C", "CK") and len(v) == 1]
            if len(ck) != 1:
                return f"slot flop {path} clock pin not found"
            cn = F.find(ck[0][0])
            g = [(cj, pn) for cj, pn in drv[cn] + loads[cn]
                 if pn == "GCLK" and F.cells[cj][0].upper().startswith("ICG")]
            # the slot's ICG gates the whole slot word (other bits' slot flops): every other pin on the gated clock
            # net must be a flop clock pin (no logic, no second driver)
            others = [(cj, pn) for cj, pn in drv[cn] + loads[cn]
                      if (cj, pn) not in g and not (is_ff(F.cells[cj][0]) and pn in ("CLK", "C", "CK"))]
            if len(g) != 1 or others:
                return f"slot flop {path} clock net {cn} is not one ICG GCLK feeding flop clocks only ({len(g)} ICG, {len(others)} other pins)"
            gi = g[0][0]
            gck = [v for k, (dd_, v) in F.cells[gi][2].items() if k == "CLK" and len(v) == 1]
            if len(gck) != 1:
                return f"ICG {F.cells[gi][1]} CLK pin not found"
            ffs.append(ci)
            icgs.add(gi)
            roots.add(F.find(gck[0][0]))
        if len(set(ffs)) != D or len(icgs) != D:
            return f"{len(set(ffs))} distinct slot flops / {len(icgs)} distinct ICGs, declared D {D}"
        if len(roots) != 1:
            return f"slot ICGs gated from {len(roots)} clock nets (want one forwarded clock)"
        return None

    res["clock_exports"] = {}
    exp_names = set()
    for t_, s_ in (exports or ()):               # a declared forwarded clock output: buffers only from its source port
        exp_names.add(t_)
        if T.dirs.get(t_) != "output" or len(_bits_of(T, t_)) != 1 or T.dirs.get(s_) != "input" or \
                not re.match(skip_re, s_) or len(_bits_of(T, s_)) != 1:
            fail("clock_export", t_, f"export {t_} ({T.dirs.get(t_)}) from {s_} ({T.dirs.get(s_)}): want a 1-bit output "
                                     f"from a 1-bit clock input port")
            continue
        cur, inv, why, seen = port_root[_bits_of(T, t_)[0]], 0, None, set()
        src_r = port_root[_bits_of(T, s_)[0]]
        first = True
        while cur != src_r:
            if not first and cur in roots_ports:
                why = f"wired from port {roots_ports[cur][0]}, contract source {s_}"
                break
            if cur in seen or len(drv[cur]) != 1 or len(loads[cur]) != (0 if first else 1) or \
                    len(roots_ports.get(cur, [])) != (1 if first else 0):
                why = f"net {cur}: {len(drv[cur])} driver(s), {len(loads[cur])} load(s), ports {roots_ports.get(cur, [])[:3]}"
                break
            seen.add(cur)
            first = False
            ci, _ = drv[cur][0]
            m, path, pp = F.cells[ci]
            ins = [v for k, (dd, v) in pp.items() if dd == "in"]
            if not is_buf(m) or len(ins) != 1 or len(ins[0]) != 1:
                why = f"driven by {m} {path} (want buffers/inverters only)"
                break
            inv += m.upper().startswith(("INV", "$_NOT_"))
            cur = F.find(ins[0][0])
        if why is None and first:
            why = f"{t_} is the same net as {s_} (no driver)"
        if why is None and inv % 2:
            why = f"odd inversion count {inv}"
        if why:
            fail("clock_export", t_, why)
        else:
            res["clock_exports"][t_] = s_
    for x in (straps or ()):                     # an exempt strap must be an input port of this block (rule 1)
        if T.dirs.get(x) != "input":
            fail("strap", x, f"declared ID strap is not an input port ({T.dirs.get(x)})")
    for p in T.ports:
        if re.match(skip_re, p) or p in exp_names:
            continue
        d = T.dirs.get(p)
        for b in _bits_of(T, p):
            res["checked"] += 1
            r = port_root[b]
            others = [x for x in roots_ports[r] if x != b]
            if others:
                fail("feedthrough", b, f"wired to port(s) {others[:3]}")
                continue
            if r.startswith("CONST_"):
                fail("const", b, f"tied {r}")
                continue
            if b in dead:
                dead_seen.add(b)
                if d != "input" or loads[r] or drv[r]:
                    fail("dead", b, f"declared dead but {d} with {len(loads[r])} load(s) / {len(drv[r])} driver(s)")
                else:
                    res["dead_declared"].append(b)
                continue
            if d == "output":
                cur, chain, ff = r, [], None
                ok = True
                seen = set()
                while True:
                    if cur in seen:
                        fail("unregistered", b, "buffer/inverter cycle before boundary flop")
                        ok = False
                        break
                    seen.add(cur)
                    if len(drv[cur]) != 1:
                        fail("unregistered", b, f"{len(drv[cur])} drivers")
                        ok = False
                        break
                    expect = 0 if cur == r else 1       # the port net feeds only the port; a chain net one stage
                    if len(loads[cur]) != expect:
                        fail("shared", b, f"net {cur} has {len(loads[cur]) - expect} loads besides the port chain")
                        ok = False
                        break
                    ci, pin = drv[cur][0]
                    m, path, pp = F.cells[ci]
                    if is_ff(m):
                        ff = (ci, path)
                        break
                    if not is_buf(m):
                        fail("const" if m.upper().startswith("TIE") else "unregistered", b, f"driven by {m} {path}")
                        ok = False
                        break
                    ins = [v for k, (dd, v) in pp.items() if dd == "in"]
                    if len(ins) != 1 or len(ins[0]) != 1:
                        fail("unregistered", b, f"buffer {path} pins")
                        ok = False
                        break
                    chain.append(path)
                    cur = F.find(ins[0][0])
                    if cur in roots_ports:
                        fail("feedthrough", b, f"buffered from port {roots_ports[cur][0]}")
                        ok = False
                        break
                if not ok:
                    continue
            elif p in starts:
                why = start_pin(b, r, *starts[p])
                if why:
                    fail("start", b, why)
                else:
                    res["ok"] += 1
                continue
            elif p in land and land_form[p] == "hold_mux":
                why, mffs, dep = land_mux(b, r, int(land[p]))
                if why:
                    fail("land_slot", b, why)
                    continue
                for ci in mffs:
                    claimed[ci].append(b)
                for x in dep:
                    h = res.setdefault("land_mux_depth", {})
                    h[str(x)] = h.get(str(x), 0) + 1
                res["flops"][b] = F.cells[mffs[0]][1]
                res["land_slot_bits"] = res.get("land_slot_bits", 0) + 1
                res["land_mux_bits"] = res.get("land_mux_bits", 0) + 1
                res["ok"] += 1
                continue
            elif p in land:
                why = land_slot(b, r, int(land[p]))
                if why:
                    fail("land_slot", b, why)
                    continue
                for ci, pin in loads[r]:
                    claimed[ci].append(b)
                res["flops"][b] = F.cells[loads[r][0][0]][1]
                res["land_slot_bits"] = res.get("land_slot_bits", 0) + 1
                res["ok"] += 1
                continue
            else:
                cur, ff, ok = r, None, True
                seen = set()
                while True:
                    if cur in seen:
                        fail("unregistered", b, "buffer/inverter cycle before boundary flop")
                        ok = False
                        break
                    seen.add(cur)
                    if cur != r and cur in roots_ports:
                        fail("feedthrough", b, f"chain reaches port {roots_ports[cur][0]}")
                        ok = False
                        break
                    if cur != r and len(drv[cur]) != 1:
                        fail("unregistered", b, f"{len(drv[cur])} drivers on input chain")
                        ok = False
                        break
                    ld = loads[cur]
                    if not ld:
                        fail("dropped", b, f"no load on {cur} (register removed)")
                        ok = False
                        break
                    if len(ld) != 1:
                        fail("shared", b, f"{len(ld)} loads on {cur}")
                        ok = False
                        break
                    ci, pin = ld[0]
                    m, path, pp = F.cells[ci]
                    if is_ff(m):
                        if pin != "D":
                            fail("unregistered", b, f"reaches {path}.{pin}, not D")
                            ok = False
                        else:
                            ff = (ci, path)
                        break
                    if not is_buf(m):
                        fail("unregistered", b, f"loads {m} {path}")
                        ok = False
                        break
                    outs = [v for k, (dd, v) in pp.items() if dd == "out"]
                    cur = F.find(outs[0][0])
                if not ok:
                    continue
            claimed[ff[0]].append(b)
            res["flops"][b] = ff[1]
            res["ok"] += 1
    for b in sorted(dead - dead_seen):
        fail("dead", b, "declared dead bit is not a checked port bit of this netlist")
    pair_ok = set()
    for ci, bs in claimed.items():
        if len(bs) > 1 and _ft1_pair(bs, ft1, T.dirs):
            res["ft1_stations"] = res.get("ft1_stations", 0) + 1
            pair_ok.update(bs)
            continue
        if len(bs) > 1:
            for b in bs:
                fail("merged", b, f"flop {F.cells[ci][1]} also registers {[x for x in bs if x != b][:3]}")
            res["ok"] -= len(bs)
    # every declared core pair I>O is verified bit by bit, never trusted from the generator text (COORD 10-27 11:56):
    # I input / O output of equal width, and each I[k] / O[k] the two (only) bits of one flop: I[k] -> buffers ->
    # that flop's D, its output -> buffers -> O[k], single driver and no other load on any net of either chain (the
    # per-bit traces above), so a missing, extra (two-flop), cross-wired, reversed or fanned-out pair fails class "pair"
    pairs = sorted(_pairs(ft1))
    res["pairs_declared"] = [f"{i}>{o}" for i, o in pairs]
    for i, o in pairs:
        if T.dirs.get(i) != "input" or T.dirs.get(o) != "output":
            fail("pair", f"{i}>{o}", f"declared pair needs input {i} ({T.dirs.get(i)}) and output {o} ({T.dirs.get(o)})")
            continue
        bi, bo = _bits_of(T, i), _bits_of(T, o)
        if len(bi) != len(bo):
            fail("pair", f"{i}>{o}", f"widths differ {len(bi)} vs {len(bo)}")
            continue
        nv = 0
        for x, y in zip(bi, bo):
            fx, fy = res["flops"].get(x), res["flops"].get(y)
            if x not in pair_ok or y not in pair_ok or fx is None or fx != fy:
                fail("pair", x, f"declared pair bit is not one flop {x} -> {fx} -> {y} ({fy})")
                continue
            if drv[port_root[x]]:
                fail("pair", x, f"input net also driven by {[F.cells[c][1] for c, _ in drv[port_root[x]]][:2]}")
                continue
            nv += 1
        res.setdefault("pairs_verified", {})[f"{i}>{o}"] = nv
    if pins is not None:
        want = {x['bus'] if x.get('bit') is None else f"{x['bus']}[{x['bit']}]" for x in pins}
        have = {b for p in T.ports if not re.match(skip_re, p) for b in _bits_of(T, p)}
        for b in sorted(want - have)[:50]:
            fail("missing_port", b, "planned pin bit not a netlist port")
        miss = len(want - have)
        res["planned_bits"] = len(want)
        res["missing_ports"] = miss
    res["fails"] = {k: v for k, v in res["fails"].items()}
    nf = sum(len(v) for v in res["fails"].values())
    res["fail_counts"] = {k: len(v) for k, v in res["fails"].items()}
    res["fails"] = {k: v[:50] for k, v in res["fails"].items()}
    empty = pins is not None and not res.get("planned_bits") and res["checked"] == 0    # a planned port-less type
    res["verdict"] = "PASS" if nf == 0 and (res["checked"] > 0 or empty) else "FAIL"
    res["flops"] = dict(list(res["flops"].items())[:20])
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("netlist")
    ap.add_argument("--top")
    ap.add_argument("--pins")
    ap.add_argument("--out")
    ap.add_argument("--ft", help="kit ft_stations.txt (default: beside --pins): 1-station slots share one register")
    ap.add_argument("--straps", help="kit straps.json (default: beside --pins): declared ID straps, exempt")
    ap.add_argument("--budget-dir", help="kit dir with budget.json (default: beside --pins): declared bump_ports")
    ap.add_argument("--sdc", help="kit constraint.sdc (default: beside --pins): create_clock ports are clock pins")
    ap.add_argument("--land", help="kit land_slots.json (default: beside --pins): declared landing-ring buses "
                                   "{bus: D} (ICG form) or {bus: {D, form: hold_mux}}; "
                                   "and declared START inputs {starts: {cland_fstart_in_<b>: {insts, max_loads}}}")
    a = ap.parse_args(argv)
    stf = a.straps or (str(Path(a.pins).parent) if a.pins else None)
    sl = kit_strap_list(Path(stf).parent if stf.endswith(".json") else stf) if stf else []
    pins = json.loads(Path(a.pins).read_text()) if a.pins else None
    ftf = a.ft or (str(Path(a.pins).with_name("ft_stations.txt")) if a.pins else None)
    ft1 = read_ft1(ftf) if ftf and Path(ftf).exists() else set()
    bd = a.budget_dir or (str(Path(a.pins).parent) if a.pins else None)
    bl = kit_bump_list(bd) if bd else []
    sdc = a.sdc or (str(Path(a.pins).with_name("constraint.sdc")) if a.pins else None)
    ck = sdc_clock_ports(Path(sdc).read_text()) if sdc and Path(sdc).exists() else []
    ex = sdc_clock_exports(Path(sdc).read_text()) if sdc and Path(sdc).exists() else []
    lf = a.land or (str(Path(a.pins).with_name("land_slots.json")) if a.pins else None)
    land = kit_land(lf) if lf and Path(lf).exists() else None
    st = kit_starts(lf) if lf and Path(lf).exists() else None
    dl = kit_dead_list(Path(a.pins).parent) if a.pins else []
    r = guard(Path(a.netlist).read_text(), a.top, pins=pins, ft1=ft1, straps=sl, bumps=bl, clocks=ck, land=land, dead=dl, exports=ex,
              starts=st)
    r["netlist"] = a.netlist
    if a.out:
        Path(a.out).write_text(json.dumps(r, indent=1) + "\n")
    print(f"FACE_GUARD {r['verdict']} top {r['top']} bits {r['checked']} ok {r['ok']} fails {r['fail_counts']}")
    return 0 if r["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
