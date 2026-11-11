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
import gzip
import hashlib
import subprocess
import itertools
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

# Isolated python (-I) omits the script directory; staged helpers are local.
sys.path.insert(0, str(Path(__file__).resolve().parent))

OUT_PINS = {"Y", "Q", "QN", "H", "L", "CON", "SN", "Z", "ZN", "O"}
# Clocks and the reset/START *inputs* (arst_n / rst_n / start_i: root synchroniser or typed control) are not face
# registers.  The registered wavefront OUTS rst_o_<k> / start_o_<k> ARE partition pins and are checked like data: one
# dedicated relay per pin (reset_tree.py out relays; owner rule: register every partition pin, no shared fanout).
SKIP_RE = r"^(clk(_t[0-9]+|_c[0-9]+)?|arst_n|rst_n|start_i)$"


def is_ff(master):
    return "DFF" in master.upper()


# S81-RF1 face lockup (DIE-S81-51/CLK crossing table row 1, 11-03; FLOW-LATCH-1): a registered output may leave its
# flop through ONE negative-level latch (transparent while clk is LOW), no logic, no fan-out: flop -> latch -> port.
# The flop stays the face register (the latch only moves the port change to the falling edge, 0 cycles).  Accepted
# only when the latch is transparent-low w.r.t. the face flop's own clock: a DLLx* / $_DLATCH_N_ whose CLK / E is the
# flop's clock net (through buffers, same inversion parity), or a DHLx* / $_DLATCH_P_ on the INVERTED flop clock
# (synthesis may fold `if (!clk)` that way), and the face flop is rising-edge.  Any other latch stays unregistered.
LATCH_LOW_RE = re.compile(r"^(DLLx\d+_ASAP7_75t_[RLS]+|\$_DLATCH_N_)$")
LATCH_HIGH_RE = re.compile(r"^(DHLx\d+_ASAP7_75t_[RLS]+|\$_DLATCH_P_)$")
RISE_FF_RE = re.compile(r"^(S?DFFH|DFFASRH|\$_(?:S?DFFC?E?|DFFSRE?|ALDFFE?)_P)")


def is_latch_low(master):
    return bool(LATCH_LOW_RE.match(master))


def latch_level(master):
    """'low' / 'high' (the level at which the latch cell is transparent on its own enable pin) or None."""
    return "low" if LATCH_LOW_RE.match(master) else "high" if LATCH_HIGH_RE.match(master) else None


def is_rise_ff(master):
    return bool(RISE_FF_RE.match(master))


def clk_pin(pp):
    """the clock / enable pin of a flop or latch: ASAP7 CLK, Yosys C (flops) / E (latches)."""
    for k in ("CLK", "C", "E"):
        if k in pp and pp[k][0] == "in" and len(pp[k][1]) == 1:
            return pp[k][1][0]
    return None


ASYNC_RESET_PINS = {"RESETN", "SETN", "R", "S"}   # ASAP7 DFFASRHQN async pins; Yosys $_DFF_P[NP][01]_ R / $_DFFSR_ S


def _reset_spine_landing(F, lds, max_flops=8):
    """DIE-KV-57: True iff every load of an input net is an asynchronous set/reset pin of a flop, 1..max_flops flops,
    all in ONE parent instance (one ot_dp_rsync synchroniser bit)."""
    if not lds or len(lds) > max_flops:
        return False
    parents = set()
    for ci, pin in lds:
        m, path, _ = F.cells[ci]
        if not is_ff(m) or pin not in ASYNC_RESET_PINS:
            return False
        parents.add(path.rsplit(".", 1)[0] if "." in path else "")
    return len(parents) == 1


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
        self.module_types = {} # retained hierarchy types, not instance-name exemptions
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
        self.module_types[pfx.rstrip("/")] = mname

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


def hier_module_types(text, top=None):
    """(top, {instance path: original module type}) of a HIERARCHICAL netlist (the kit 1_2_yosys.v). An ODB
    write_verilog netlist is flat (one module) yet keeps the same hierarchical instance paths, so the typed
    status-copy / origin proofs read module types from this map (guard types=); an untyped path stays untyped."""
    mods = parse(text)
    if top is None:
        used = {typ for M in mods.values() for typ, _, _ in M.cells}
        tops = [m for m in mods if m not in used]
        if len(tops) != 1:
            raise ValueError(f"cannot pick the top module: {tops}")
        top = tops[0]
    out = {}

    def walk(mname, pfx):
        out[pfx.rstrip("/")] = mname
        for typ, inst, _ in mods[mname].cells:
            if typ in mods:
                walk(typ, pfx + inst + "/")
    walk(top, "")
    return top, out


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
    buses = {str(k): (dict(v) if isinstance(v, dict) else int(v)) for k, v in (d.get("buses") or {}).items()}
    for v in buses.values():
        if isinstance(v, dict) and v.get('form') == 'hard_child':
            p = Path(v['evidence'])
            if (p.is_absolute() or '..' in p.parts or len(p.parts) != 3
                    or p.parts[:2] != ('macros', 'landing')):
                raise ValueError('hard landing evidence must be inside the kit')
            v['evidence'] = str(Path(path).parent / p)
    return buses


LAND_FORMS = ("icg", "hold_mux")

# S81-GUNIT-FORM-1 11-07 "replica": a registered input whose bit lands, with no logic, in D kept replica flops (the
# N32 fan-out copies of a pin register: dsdv_gunit_l1f_bf W face wqc x9 / adc x5 / cbc x32 ...): the D flops ARE the
# bit's face registers (flop-to-flop crossing, no added cycle), as the ICG / hold_mux slots are.
# OPT-IN, KEYED BY THE PLAN (COORD 11-07 23:3x): the form is accepted only in a spec {"D", "form": "replica", "plan": P}
# whose plan event P lists the guarded top module here; a replica spec without a listed plan raises (fails closed), and
# no other kit can reach this form, so every other kit's guard result is byte-same (test_face_guard replica tests,
# face_guard_byte_same.py corpus receipt).
REPLICA_PLANS = {
    "s81/delta_gunit_l1f_band_1107": ("dsdv_gunit_l1f_bf",),
    # S81-SVCRS-3 11-10 (COORD ruling): the v5 svc provider boxes; fanout_dup.py copies a pin register whose Q drives
    # more than 64 census loads (smd i_pv x5, sml i_sv x3, attn_tr_x w_g 4 bits x2), declared per bit ("bits").
    "s81/svc_prov_1109_v5": ("ot_s81_su_smd_fold2", "ot_s81_su_sml_fold2", "ot_hdc_v41x_attn_tr_x"),
}


def replica_bits(v):
    """the per-bit D map {bit index (int): D >= 2} of a replica spec {"bits": {...}, "form": "replica", "plan": P}
    (S81-SVCRS-3 11-10, COORD ruling: only the copied bits carry D; every other bit of the bus keeps the ordinary
    single face register check), or None for the uniform {"D": n, ...} form.  ValueError on a bad map."""
    if not isinstance(v, dict) or "bits" not in v:
        return None
    b = v["bits"]
    if not isinstance(b, dict) or not b:
        raise ValueError(f"land_slots replica bits {b}: want a nonempty {{bit index: D >= 2}} map")
    out = {}
    for k, d in b.items():
        if not str(k).isdigit() or isinstance(d, bool) or not isinstance(d, int) or d < 2:
            raise ValueError(f"land_slots replica bits entry {k}: {d}: want bit index -> integer D >= 2")
        out[int(k)] = d
    return out


def land_spec(v):
    """(D, form) of one declared landing bus: an int D = the ICG slot form (S81-CORE-LAT-R21); a dict
    {"D": n, "form": "hold_mux"} = the enable-mux slot form (COORD 10-28 06:30, DIE-HEAD-8 witness); a dict
    {"D": n, "form": "replica", "plan": P} = D kept replica pin registers, opt-in for the tops plan event P lists in
    REPLICA_PLANS (S81-GUNIT-FORM-1 11-07, replica_slot); a dict
    {"form": "ring_start", "ring": R} (DIE-HEAD-21, no D) = the count-aligned ring START input -> (0, "ring_start")
    (ring_spec gives R).  ValueError else."""
    if isinstance(v, dict) and v.get('form') == 'hard_child':
        keys = {'form', 'D', 'instance', 'master', 'port', 'width', 'clock_pin', 'clock_port', 'evidence'}
        if (set(v) != keys or v['port'] not in ('d', 't_rst_n') or v['clock_pin'] != 'fclk'
                or int(v['width']) < 1 or int(v['D']) < 2
                or any(not isinstance(v[k], str) or not v[k] for k in
                       ('instance', 'master', 'clock_port', 'evidence'))):
            raise ValueError('invalid typed hard-child landing declaration')
        return int(v['D']), 'hard_child'
    if isinstance(v, dict) and v.get("form") == "origin_start":
        origin_spec(v)
        return 0, "origin_start"
    if isinstance(v, dict) and v.get("form") == "ring_start":
        ring_spec(v)
        return 0, "ring_start"
    if isinstance(v, dict) and v.get("form") == "replica":
        if set(v) == {"bits", "form", "plan"} and v["plan"] in REPLICA_PLANS:
            return max(replica_bits(v).values()), "replica"
        if set(v) != {"D", "form", "plan"} or v["plan"] not in REPLICA_PLANS or int(v["D"]) < 2:
            raise ValueError(f"land_slots replica spec {v}: want exactly {{D >= 2 | bits: {{bit: D >= 2}}, form: "
                             f"replica, plan in {sorted(REPLICA_PLANS)}}} (opt-in keyed by the plan)")
        return int(v["D"]), "replica"
    if isinstance(v, dict):
        if set(v) - {"D", "form"} or v.get("form", "icg") not in LAND_FORMS:
            raise ValueError(f"land_slots bus spec {v}: want {{D, form in {LAND_FORMS}}}")
        return int(v["D"]), str(v.get("form", "icg"))
    return int(v), "icg"


def ring_spec(v):
    """declared ring bus names of a {"form": "ring_start", "ring": R | [R, ...]} spec (unique non-empty str);
    ValueError else."""
    rg = v.get("ring") if isinstance(v, dict) else None
    rl = [rg] if isinstance(rg, str) else rg
    if set(v) != {"form", "ring"} or not isinstance(rl, list) or not rl or len(set(rl)) != len(rl) or \
            not all(isinstance(x, str) and x for x in rl):
        raise ValueError(f"land_slots ring_start spec {v}: want exactly {{form: ring_start, ring: <bus> | [<bus>..]}}")
    return list(rl)


def origin_spec(v):
    """One explicitly emitted count origin; its module type and clock are proved below."""
    if (not {"form", "origin"} <= set(v) or set(v) - {"form", "origin", "copies", "stages"}
            or not isinstance(v.get("origin"), str) or not v["origin"]):
        raise ValueError(f"land_slots origin_start spec {v}: want exactly {{form: origin_start, origin: <instance>}}")
    if "copies" in v:
        cp = v["copies"]
        if (not isinstance(cp, list) or not cp or not all(isinstance(x, str) and x for x in cp)
                or len(set(cp)) != len(cp) or v["origin"] in cp):
            raise ValueError(f"land_slots origin_start copies {cp}: want distinct nonempty instance names")
    if "stages" in v:
        # Writer START transport (clock.landing_writer_start on a relay type): the first registered stage samples the
        # same input as the origin, on its own local raw reset, and hands on to the next relay; never a face copy.
        st = v["stages"]
        if (not isinstance(st, list) or not st or not all(isinstance(x, str) and x for x in st)
                or len(set(st)) != len(st) or v["origin"] in st or set(st) & set(v.get("copies", ()))):
            raise ValueError(f"land_slots origin_start stages {st}: want distinct nonempty instance names")
    return v["origin"]


# ---- single-output std-cell boolean models (hold_mux slot proof; a cell without a model rejects the slot) --------
def _cell_base(m):
    return re.sub(r"x(p\d+|\d+).*$", "", m.split("_ASAP7")[0])


def cell_fn(m, ins, output=None):
    """ins {pin: bool} -> output bool of a single-output ASAP7 combinational cell; KeyError when not modelled."""
    b = _cell_base(m)
    if b == "HA":
        # ASAP7 SIMPLE RVT TT liberty: CON = (!A)+(!B), SN = !(A^B).
        # Both outputs occur in mapped binary-count decode cones.  Unknown
        # output names still reject the proof instead of guessing a function.
        if output == "CON":
            return not (ins["A"] and ins["B"])
        if output == "SN":
            return ins["A"] == ins["B"]
        raise KeyError(f"no boolean model for {m} output {output}")
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


SPARE_SCHEMA = "opentallas.kit_spare_out.v1"


def spare_out_list(doc):
    """DIE-S81-46 / COORD 10-30 14:0x (2)(b): a kit spare_out.json (gen_phys, from the bind's kit_rtl.json
    spare_out_bits) names the plan output bits the kit-rtl wrapper ties to a constant (plan bus wider than the bound
    port).  Unique exact port bit names; anything else -> ValueError."""
    if not isinstance(doc, dict) or doc.get("schema") != SPARE_SCHEMA:
        raise ValueError(f"spare_out.json: schema must be {SPARE_SCHEMA}")
    bits = doc.get("bits")
    if not isinstance(bits, list) or len(set(bits)) != len(bits) or \
            not all(isinstance(b, str) and _DEAD_BIT.match(b) for b in bits):
        raise ValueError(f"spare_out.json: bits must be unique exact port bit names: {bits}")
    return list(bits)


def kit_spare_list(kitdir):
    """the kit's declared spare (constant) output bits (spare_out.json), [] when none."""
    f = Path(kitdir) / "spare_out.json"
    return spare_out_list(json.loads(f.read_text())) if f.is_file() else []


TIMED_SCHEMA = "opentallas.kit_timed_face.v1"
# DIE-KV-61/hr 11-02: classes a declared timed-face bus may carry.  feedthrough (port wired to port) is never exempt:
# it has no core-side timing arc the IO budget could bound.
TIMED_CLASSES = frozenset({"unregistered", "shared", "dropped", "const"})


def timed_face_list(doc):
    """DIE-KV-61/hr 11-02 (HR raw memory-port / boot-handshake faces): a kit timed_face.json names whole port BUSES
    whose bits the zero-cycle face transform cannot register (an async-FIFO storage cut wdata/rdata/wr/rd, an SRAM
    address/data port, boot-barrier inputs read through logic).  Such a bit is a timed boundary: core STA times it
    against the kit SDC IO budget (set_input_delay / set_output_delay on every non-clock port), exactly as a hard
    macro pin is timed.  Its unregistered / shared / dropped / const finding is recorded in timed_declared instead
    of failing; every other class (feedthrough, merged, ...) and every undeclared bus keeps the ordinary checks.
    Fail-closed: schema, unique exact bus names (no regex, no bit index), a non-empty ruling and reason."""
    if not isinstance(doc, dict) or doc.get("schema") != TIMED_SCHEMA:
        raise ValueError(f"timed_face.json: schema must be {TIMED_SCHEMA}")
    buses = doc.get("buses")
    if not isinstance(buses, list) or not buses or len(set(buses)) != len(buses) or \
            not all(isinstance(b, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", b) for b in buses):
        raise ValueError(f"timed_face.json: buses must be unique exact port names: {buses}")
    if not str(doc.get("ruling") or "").strip() or not str(doc.get("reason") or "").strip():
        raise ValueError("timed_face.json: ruling and reason are required")
    return list(buses)


def kit_timed_list(kitdir):
    """the kit's declared timed-face buses (timed_face.json), [] when none."""
    f = Path(kitdir) / "timed_face.json"
    return timed_face_list(json.loads(f.read_text())) if f.is_file() else []


SEAM_SCHEMA = "opentallas.kit_seam_face.v1"
# HBM-Q2NF-RF 11-10 (COORD ruling, Q2NF 2-way split): classes a declared intra-pair seam bus may carry.  A seam port
# joins two sibling children of ONE parent core; the pair-level STA across both routed views times every seam path,
# so the per-port face rule does not apply to it.  feedthrough, dropped, const and every die-facing bus keep the guard.
SEAM_CLASSES = frozenset({"shared", "merged", "unregistered"})


def seam_face_map(doc):
    """kit seam_face.json -> {bus: frozenset(classes)}.  Fail-closed: schema, a partner child name, exact unique bus
    names (no regex, no bit index), a non-empty class list per bus drawn from SEAM_CLASSES, a ruling and a reason."""
    if not isinstance(doc, dict) or doc.get("schema") != SEAM_SCHEMA:
        raise ValueError(f"seam_face.json: schema must be {SEAM_SCHEMA}")
    if not isinstance(doc.get("partner"), str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", doc["partner"]):
        raise ValueError("seam_face.json: partner must name the sibling child module")
    buses = doc.get("buses")
    if not isinstance(buses, dict) or not buses:
        raise ValueError("seam_face.json: buses must be a non-empty {bus: [classes]} object")
    out = {}
    for b, cls in buses.items():
        if not isinstance(b, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", b):
            raise ValueError(f"seam_face.json: bus must be an exact port name: {b!r}")
        if not isinstance(cls, list) or not cls or len(set(cls)) != len(cls) or not set(cls) <= SEAM_CLASSES:
            raise ValueError(f"seam_face.json: {b}: classes must be a non-empty unique subset of {sorted(SEAM_CLASSES)}")
        out[b] = frozenset(cls)
    if not str(doc.get("ruling") or "").strip() or not str(doc.get("reason") or "").strip():
        raise ValueError("seam_face.json: ruling and reason are required")
    return out


def kit_seam_map(kitdir):
    """the kit's declared intra-pair seam buses (seam_face.json), {} when none."""
    f = Path(kitdir) / "seam_face.json"
    return seam_face_map(json.loads(f.read_text())) if f.is_file() else {}


def _std_cell(master):
    return "_ASAP7_" in master.upper() or master.startswith("$")


def clock_pins_from_liberties(files):
    """Actual selected native Liberty clock:true INPUT pins; config may select a subset only."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from signoff import _lib_groups
    roles = {}
    for path in files:
        path = Path(path)
        text = gzip.open(path, 'rt').read() if path.suffix == '.gz' else path.read_text()
        text = re.sub(r'"(?:\\.|[^"\\])*"|/\*.*?\*/|//[^\n]*',
                      lambda m: m[0] if m[0].startswith('"') else '', text, flags=re.S)
        for master, body in _lib_groups(text, 'cell'):
            for pin, definition in _lib_groups(body, 'pin'):
                role = bool(re.search(r'\bclock\s*:\s*true\s*;', definition) and
                            re.search(r'\bdirection\s*:\s*input\s*;', definition))
                if (master, pin) in roles and roles[master, pin] != role:
                    raise ValueError(f'conflicting consumed Liberty clock role: {master}/{pin}')
                roles[master, pin] = role
    return {key for key, clock in roles.items() if clock}


def kit_pad_clocks(kit, library_receipt=None, execute=subprocess.run):
    """Validate opaque endpoints against effective ORFS libraries or an actual loaded-library receipt."""
    kit = Path(kit); sidecar = kit / 'pad_clock.json'
    if not sidecar.exists():
        return [], set()
    ps = json.loads(sidecar.read_text())['pins']
    if not any(p.get('sink_pins') for p in ps):
        return ps, set()
    files = []
    if library_receipt:
        receipt = json.loads(Path(library_receipt).read_text())
        if receipt.get('status') != 'LOADED':
            raise ValueError('pad clock native loaded-library receipt unavailable')
        for row in receipt['libraries']:
            source = row['path']
            if source.startswith('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/'):
                continue
            if not source.startswith('/work/') or '..' in Path(source).parts:
                raise ValueError('pad clock native consumed library is outside the kit')
            path = kit / source[len('/work/'):]
            if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
                raise ValueError('pad clock consumed native library changed')
            files.append(path)
    else:
        # Same effective make configuration/environment as the pre-floor
        # synthesis invocation; resolve the actual native views, no glob/guess.
        cmd = ['make', '--no-print-directory', '-s', '-C', '/OpenROAD-flow-scripts/flow',
               f'DESIGN_CONFIG={kit / "config.mk"}', f'WORK_HOME={kit / "run"}',
               'FLOW_VARIANT=base', 'print-LIB_FILES']
        result = execute(cmd, capture_output=True, text=True)
        values = re.findall(r'^LIB_FILES\s*[:=]\s*(.+)$', result.stdout, re.M)
        if result.returncode or len(values) != 1 or '$' in values[0]:
            raise ValueError('pad clock actual ORFS LIB_FILES unavailable')
        files = [Path(p) for p in values[0].split()
                 if not p.startswith('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/')]
    if not files:
        raise ValueError('pad clock actual native Liberty list is empty')
    return ps, clock_pins_from_liberties(files)


def sdc_clock_ports(text):
    """port names of every `create_clock ... [get_ports NAME]` in a kit SDC (virtual clocks have no port)."""
    out = []
    for m in re.finditer(r"^\s*create_clock\b[^\n]*\[get_ports\s+\{?([A-Za-z_][A-Za-z0-9_]*)(?:\[0\])?\}?\s*\]", text, re.M):
        if m.group(1) not in out:
            out.append(m.group(1))
    return out


def sdc_clock_exports(text):
    """[(output port, source port)] of every `create_generated_clock ... -source [get_ports S] ... [get_ports T]`
    with -divide_by 1 (a forwarded clock output, landing_contract.sdc)."""
    out = []
    for m in re.finditer(r"^\s*create_generated_clock\b([^\n]*)$", text, re.M):
        ln = m.group(1)
        src = re.search(r"-source\s+\[get_ports\s+\{?([A-Za-z_][A-Za-z0-9_]*)(?:\[0\])?\}?\s*\]", ln)
        tgt = re.search(r"\[get_ports\s+\{?([A-Za-z_][A-Za-z0-9_]*)(?:\[0\])?\}?\s*\]\s*$", ln)
        if src and tgt and re.search(r"-divide_by\s+1\b", ln) and (tgt.group(1), src.group(1)) not in out:
            out.append((tgt.group(1), src.group(1)))
    return out


def _spare_tie(F, drv, r, limit=16):
    """the TIE cell path (or CONST_ root) a declared spare output net is tied to through single-input buffers /
    inverters, else None."""
    cur = r
    for _ in range(limit):
        if cur.startswith("CONST_"):
            return cur
        if len(drv[cur]) != 1:
            return None
        m, path, pp = F.cells[drv[cur][0][0]]
        if m.upper().startswith("TIE"):
            return path
        ins = [v for k, (dd, v) in pp.items() if dd == "in"]
        if not is_buf(m) or len(ins) != 1 or len(ins[0]) != 1:
            return None
        cur = F.find(ins[0][0])
    return None


def guard(text, top=None, skip_re=SKIP_RE, pins=None, ft1=(), straps=(), bumps=(), clocks=(), land=None, dead=(),
          exports=(), types=None, pad_clocks=(), native_clock_pins=(), spare=(), timed=(), seam=None):
    """types: (top, {path: module}) from hier_module_types of the hierarchical netlist this flat netlist was written
    from (kit ODB write_verilog pass); fills only paths the netlist itself does not type; its top must match.
    straps: declared ID strap ports (OWNER 10-25 option B, straps.py): quasi-static strap_* inputs tied at the
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
    A bus declared {"form": "ring_start", "ring": R} (DIE-HEAD-21: the count-aligned ring's forwarded START, t_rst_n of
    ot_meso_ring_ca and p_start of the count origin; it must NOT get a face flop -- that would shift the partition's
    count frame by one cycle) needs: R (one bus or a list) declared hold_mux in the same land dict and proving its own
    slots; the START net undriven inside, wired to no other port; and everything reachable forward from each bit
    through combinational std cells ends at flop D pins ONLY (no port, macro, clock/other flop pin), each either
    (1) a ring-writer flop: clocked by the clock net of R's slot flops AND in the same parent instance as R's slot
    flops (ot_meso_ring_ca state: slots, lap, tag, write count, write-valid), or a write-enable flop of R proven
    at-most-one-hot (WREG-1, _registered_atmost_one), or
    (2) an origin start sampler flop: in ONE parent instance whose last path segment contains "origin" (the emitted
    u_cland_origin), at most 2 such flops (sf negedge + s0 first synchroniser stage), all on ONE clock net that is a
    clock input port and not a ring clock, each D cone's leaves only the bit, declared strap ports and Q/QN of flops on
    that same clock, and some leaf assignment makes D equal to the bit (it samples START).
    Typed ot_meso_ca_status_copy descendants directly within the same ring parent also count as writers only on
    that exact ring clock. At least one writer flop is required for ring_start. An explicitly emitted
    {form: origin_start, origin: <instance>} instead requires the same <=2 sampler proof in that exact instance,
    whose original module type must be ot_dp_landing_origin[_s] or the one-flop ot_dp_landing_relay; no ring writer is required for this separate input.
    Dedicated origin export copies are still checked independently as ordinary exclusive registered output pins.
    A "stages" list names writer START first stages on the same input (clock.landing_writer_start on a relay type):
    typed relay, one sampler, same clock, start reset-masked on its own raw reset, sole load the next typed relay.
    Anything else fails class "land_slot". Matched flops: res["ring_start"].
    exports: declared forwarded clock outputs [(T, S)] (kit SDC create_generated_clock -source [get_ports S] -divide_by 1
    [get_ports T], DIE-HEAD-9 FACE (c)): T is an output port wired from clock port S through single-driver,
    single-load buffers / an even number of inverters only, the T net and every chain net carry nothing else; then T
    is a clock role (recorded in clock_exports), not face data.  Anything else fails class "clock_export".
    dead: declared proven-dead input bits (kit dead_inputs.json, dead_input_list): each must be an input port bit
    whose net has NO load and no driver in the netlist -- then it is recorded (dead_declared), not a face register;
    a declared bit that is not an input port bit, or that still loads anything, fails class "dead".
    spare: declared spare output bits (kit spare_out.json = the bind's kit_rtl.json spare_out_bits, the plan bits the
    kit-rtl wrapper ties to 0): an output bit whose driver chain (single-input buffers / inverters, any fanout on the
    shared tie net) ends at a TIE cell or a constant is recorded (spare_declared, counted ok) instead of failing
    shared / const.  A declared bit that is anything else takes the ordinary checks unchanged."""
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
    if types is not None:
        if types[0] != top:
            raise ValueError(f"types netlist top {types[0]} != {top}")
        for k, v in types[1].items():
            F.module_types.setdefault(k, v)
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
    def clk_root(bit):
        """a clock net bit -> (root net, inversion parity) through single-driver BUF/INV/HB cells."""
        cur, par, seen = F.find(bit), 0, set()
        while cur not in seen and len(drv[cur]) == 1:
            seen.add(cur)
            ci, _ = drv[cur][0]
            m, _, pp = F.cells[ci]
            ins = [v for k, (dd, v) in pp.items() if dd == "in"]
            if not is_buf(m) or len(ins) != 1 or len(ins[0]) != 1:
                break
            if m.upper().startswith(("INV", "$_NOT_")):
                par ^= 1
            cur = F.find(ins[0][0])
        return cur, par

    def face_lockup_why(lci, fci):
        """'' when latch lci is transparent-low on the clock of the rising-edge face flop fci, else the reason."""
        lm, _, lpp = F.cells[lci]
        fm, fpath, fpp = F.cells[fci]
        if not is_rise_ff(fm):
            return f"face flop {fpath} ({fm}) is not rising-edge"
        lc, fc = clk_pin(lpp), clk_pin(fpp)
        if lc is None or fc is None:
            return "latch / flop clock pin not found"
        (lr, lp), (fr, fp) = clk_root(lc), clk_root(fc)
        if lr != fr:
            return f"latch enable {lr} is not the face flop clock {fr}"
        level = latch_level(lm)
        if (level == "low") != (lp == fp):
            return f"{lm} on {'inverted ' if lp != fp else ''}clock is transparent-high (want negative-level)"
        return ""

    roots_ports = defaultdict(list)
    for b, r in port_root.items():
        roots_ports[r].append(b)
    res = dict(top=top, checked=0, ok=0, fails=defaultdict(list), flops={}, straps_exempt=sorted(straps or ()))
    dead = set(dead or ())
    dead_seen = set()
    res["dead_declared"] = []
    spare = set(spare or ())
    if spare:
        res["spare_declared"] = []
    claimed = defaultdict(list)

    timed = set(timed or ())
    if timed:
        res["timed_declared"] = []

    seam = dict(seam or {})
    if seam:
        res["seam_declared"] = []

    def seam_cls(b):
        return seam.get(re.sub(r"\[\d+\]$", "", str(b)), frozenset())

    def fail(cls, b, why):
        if timed and cls in TIMED_CLASSES and re.sub(r"\[\d+\]$", "", str(b)) in timed:
            res["timed_declared"].append(f"{b}: {cls} {why}")   # DIE-KV-61/hr: declared timed-face bit
            return
        if cls != "merged" and cls in seam_cls(b):
            res["seam_declared"].append(f"{b}: {cls} {why}")    # HBM-Q2NF-RF 11-10: declared intra-pair seam bit
            return
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
        if land_form[x] == "replica" and top not in REPLICA_PLANS[v["plan"]]:
            raise ValueError(f"land_slots replica bus {x}: plan {v['plan']} does not list top {top}")
    for x, dd in land.items():                   # a declared landing bus: an input port, D >= 2
        if land_form[x] in ("ring_start", "origin_start"):
            if T.dirs.get(x) != "input":
                fail("land_slot", x, f"declared ring_start bus is {T.dirs.get(x)} (want input)")
            continue
        if T.dirs.get(x) != "input" or int(dd) < 2:
            fail("land_slot", x, f"declared landing bus is {T.dirs.get(x)} with D {dd} (want input, D >= 2)")
    # the ring START is a write-enable leaf of its own ring's slots (if (t_rst_n) s_d <= t_d): not a landing data bit
    rep_bits = {x: replica_bits(land_raw[x]) for x in land if land_form[x] == "replica"}
    for x, m in rep_bits.items():
        if m is not None:
            idx = {int(b_[len(x) + 1:-1]) for b_ in _bits_of(T, x) if b_ != x}
            bad = sorted(k for k in m if k not in idx)
            if bad:
                fail("land_slot", x, f"replica bits {bad[:4]} are not bits of {x}")

    def _land_bit(x, b_):
        """False for a bit of a per-bit replica bus that the map does not list (it is an ordinary input bit)"""
        m = rep_bits.get(x)
        if m is None:
            return True
        return b_ != x and int(b_[len(x) + 1:-1]) in m

    land_roots = {port_root[b] for x in land if x in T.ports and land_form[x] not in ("ring_start", "origin_start") for b in _bits_of(T, x) if _land_bit(x, b)}
    out_port_roots = {port_root[b] for x in T.ports if T.dirs.get(x) == "output" for b in _bits_of(T, x)}
    hard_proofs = {}
    hard_buses = {}

    def prove_hard_bus(bus):
        import hard_landing
        spec = land_raw[bus]
        try:
            evidence = spec['evidence']
            if evidence not in hard_proofs:
                hard_proofs[evidence] = hard_landing.prove(evidence)
            receipt, proof = hard_proofs[evidence]
            if receipt['master'] != spec['master'] or receipt['D'] != spec['D']:
                return 'selected hard child master/depth differs from proved evidence'
            width = receipt['width'] if spec['port'] == 'd' else 1
            bits = _bits_of(T, bus)
            if width != spec['width'] or len(bits) != width:
                return 'parent bus/child port width differs from proved evidence'
            matches = [(i, pp) for i, (master, path, pp) in enumerate(F.cells)
                       if master == spec['master'] and path.replace('/', '.') == spec['instance'].replace('/', '.')]
            if len(matches) != 1:
                return 'selected hard child instance/master not uniquely present'
            ci, pp = matches[0]
            port = pp.get(spec['port'])
            if port is None or len(port[1]) != width:
                return 'actual hard child port width differs from proved evidence'
            if [F.find(x) for x in port[1]] != [port_root[x] for x in bits]:
                return 'parent bus is not wired in order to the exact child port'
            if any(drv[port_root[b]] or loads[port_root[b]] != [(ci, spec['port'])] for b in bits):
                return 'hard landing input must exclusively load its exact child pin'
            clock = spec['clock_port']
            cp = pp.get(spec['clock_pin'])
            if (T.dirs.get(clock) != 'input' or len(_bits_of(T, clock)) != 1 or cp is None
                    or len(cp[1]) != 1 or F.find(cp[1][0]) != port_root[_bits_of(T, clock)[0]]):
                return 'actual child forwarded clock does not match declared parent clock input'
            if not re.fullmatch(skip_re, clock):
                return 'forwarded clock is not an actual SDC clock input'
            res.setdefault('hard_landings', {})[bus] = dict(instance=spec['instance'], master=spec['master'],
                port=spec['port'], width=width, clock_port=clock,
                child_landing_bits=proof['land_mux_bits'], child_start=proof['ring_start']['t_rst_n'])
        except (KeyError, ValueError, OSError) as e:
            return f'hard landing evidence rejected: {e}'
        return None

    def hard_child(bus, bit, root):
        if bus not in hard_buses:
            hard_buses[bus] = prove_hard_bus(bus)
        return hard_buses[bus]

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

    def _shift_class(net, clk, limit=16):
        """(root, depth, parity) of a net: back through single-driver BUF/INV cells and plain rising D flops on clock
        root `clk` (only D + clock inputs).  Two nets with equal (root, depth) carry the same value (xor parity) every
        cycle once `depth` cycles have passed: same-cycle reset relay copies (ot_dp_rrelay chains) of one reset root
        (DIE-QC-84 11-06, START relay face copy on its own local reset leaf).  Anything else stops the walk."""
        cur, depth, par, seen = net, 0, 0, set()
        while depth <= limit and cur not in seen:
            seen.add(cur)
            d = _single_drv(cur)
            if d is None or cur in roots_ports or cur.startswith("CONST_"):
                break
            m, _, pp = F.cells[d[0]]
            ins = {k: v for k, (dd_, v) in pp.items() if dd_ == "in"}
            if is_buf(m) and len(ins) == 1 and all(len(v) == 1 for v in ins.values()):
                if m.upper().startswith(("INV", "$_NOT_")):
                    par ^= 1
                cur = F.find(next(iter(ins.values()))[0])
                continue
            cp = clk_pin(pp)
            if not (is_rise_ff(m) and cp is not None and clk_root(cp) == clk and set(ins) == {"D", next(
                    k for k in ("CLK", "C") if k in ins)} and len(ins["D"]) == 1):
                break
            if d[1].upper() == "QN":
                par ^= 1
            cur, depth = F.find(ins["D"][0]), depth + 1
        return cur, depth, par

    def _ev(net, asg, memo):
        if net in asg:
            return asg[net]
        if net == "CONST_1":
            return True
        if net == "CONST_0":
            return False
        if net in memo:
            return memo[net]
        ci, output = _single_drv(net)
        m, _, pp = F.cells[ci]
        memo[net] = cell_fn(m, {k: _ev(F.find(v[0]), asg, memo) for k, (dd_, v) in pp.items() if dd_ == "in" and v}, output)
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

    # Actual ASAP7 RVT Liberty: DFFHQNx{1,2,3} has ff(IQN,IQNN),
    # clocked_on="CLK", next_state="!D", and QN.function="IQN".
    # Restrict the sequential proofs to that model; a pin named QN alone
    # does not establish its polarity or its active clock edge.
    def native_inverted_ff(master, pin):
        return bool(re.fullmatch(r"DFFHQNx[123]_ASAP7_75t_R", master) and pin == "QN")

    def native_inverted_ff_either_edge(master, pin):
        """DFFHQN or DFFLQN (a WFALL ring writer maps to DFFLQN): same QN state model, only the clock edge differs."""
        return bool(re.fullmatch(r"DFF[HL]QNx[123]_ASAP7_75t_R", master) and pin == "QN")

    def _reset_port(port):
        return bool(re.fullmatch(skip_re, port)
                    and re.fullmatch(r"(?:a?rst_n|reset_n|rsi|rs_[A-Za-z0-9_]+)(?:\[\d+\])?", port))

    def _reset_level(net, stack, clock, port_ok):
        """(value of net while the reset input is asserted low, register depth to that input), else KeyError."""
        if net in stack:
            raise KeyError("reset feedback")
        stack = stack | {net}
        if net in roots_ports:
            ports = roots_ports[net]
            if (len(ports) != 1 or T.dirs.get(re.sub(r"\[\d+\]$", "", ports[0])) != "input"
                    or not port_ok(ports[0])):
                raise KeyError("not a reset input")
            return False, 0
        d = _single_drv(net)
        if d is None:
            raise KeyError("ambiguous reset source")
        ci, pin = d; m, _, pp = F.cells[ci]
        ins = {p: F.find(v[0]) for p, (dd, v) in pp.items() if dd == "in" and len(v) == 1}
        if is_ff(m):
            if not native_inverted_ff_either_edge(m, pin) or set(ins) != {"CLK", "D"} or _ckpin(ci) != clock:
                raise KeyError("unsupported reset register")
            val, depth = _reset_level(ins["D"], stack, clock, port_ok)
            return (not val if pin == "QN" else val), depth + 1
        if not is_buf(m) or len(ins) != 1:
            raise KeyError("reset chain is not buffers and registers")
        p, upstream = next(iter(ins.items()))
        val, depth = _reset_level(upstream, stack, clock, port_ok)
        return cell_fn(m, {p: val}, pin), depth

    onehot_memo = {}

    def _registered_onehot(control, D, clock):
        """Prove reset establishment and a D-cycle rotation from the mapped FF equations.

        This is a reachable-state proof, not an assumption that FF outputs are
        one-hot. The reset chain must lead to a real active-low reset input;
        its measured register depth is reported for the core reset contract.
        """
        key = (tuple(control), D, clock)
        if key in onehot_memo:
            return onehot_memo[key]
        onehot_memo[key] = None
        if len(control) != D or not 2 <= D <= 8:
            return None
        regs, dn, inv = [], [], []
        for net in control:
            driver = _single_drv(net)
            if driver is None:
                return None
            ci, pin = driver
            m, path, pp = F.cells[ci]
            if (not native_inverted_ff(m, pin) or _ckpin(ci) != clock
                    or {p for p, (dd, _) in pp.items() if dd == "in"} != {"CLK", "D"}):
                return None
            regs.append(ci); dn.append(F.find(pp["D"][1][0])); inv.append(True)
        parents = {_parent(F.cells[ci][1]) for ci in regs}
        if len(set(regs)) != D or len(parents) != 1:
            return None
        parent = next(iter(parents))
        if not _module_is(parent, "ot_pl_land_local_kw"):
            return None
        extra = set().union(*(_leaves(n) for n in dn)) - set(control)
        extra = {n for n in extra if not n.startswith("CONST_")}
        if len(extra) != 1:
            return None
        reset = next(iter(extra))

        try:
            reset_value, reset_depth = _reset_level(reset, set(), clock, _reset_port)
            if reset_depth >= 64:
                return None
            def step(state, rv):
                assignment = dict(zip(control, state)); assignment[reset] = rv
                return tuple(bool(_ev(n, assignment, {})) ^ flip for n, flip in zip(dn, inv))
            def hot(state):
                return sum(bool(value) ^ flip for value, flip in zip(state, inv)) == 1
            all_states = list(itertools.product((False, True), repeat=D))
            initial = {step(state, reset_value) for state in all_states}
            if len(initial) != 1 or not hot(next(iter(initial))):
                return None
            valid = {state for state in all_states if hot(state)}
            state = next(iter(initial)); visited = set()
            for _ in range(D):
                if state not in valid or state in visited:
                    return None
                visited.add(state); state = step(state, not reset_value)
            if visited != valid or state != next(iter(initial)):
                return None
        except (KeyError, RecursionError):
            return None
        proof = dict(parent=parent, reset_chain_edges=reset_depth,
                     reset_asserted_edges_required=reset_depth + 1,
                     cycle=D, reset_vector=list(next(iter(initial))))
        res.setdefault("registered_onehot", {})[parent] = proof
        onehot_memo[key] = valid
        return valid

    atmost_memo = {}
    atmost_regs = set()              # control flops of a proven at-most-one write-enable set: they are ring writers

    def _registered_atmost_one(control, D, clock):
        """WREG-1: prove per-(slot, chunk) write-enable flops at-most-one-hot from the mapped FF equations.

        The flops share no parent and need not rotate on their own, so the rotation proof does not apply.  Instead,
        on the native DFFHQN / DFFLQN model and one clock: (a) every control net is a QN flop with only CLK and D; (b) over
        every assignment of the D cones' leaves at most one D is 1, so the state after ANY edge is at-most-one-hot
        whatever the prior state; (c) a leaf traced through buffers/registers to a declared ring start
        (or a real reset input) forces every D to 0 while asserted, so that state is established by reset, and every
        D can be 1 once it is released.  All other leaves must be QN flops on the same clock (no port, macro or
        other-domain leaf: those could decode differently at each flop).  Returns the valid states (QN level, in
        control order) or None; only an at-most-one state may reach the caller's write-conflict check."""
        key = (tuple(control), D, clock)
        if key in atmost_memo:
            return atmost_memo[key]
        atmost_memo[key] = None
        if len(control) != D or not 2 <= D <= 8:
            return None
        regs, dn = [], []
        for net in control:
            driver = _single_drv(net)
            if driver is None:
                return None
            ci, pin = driver
            m, _, pp = F.cells[ci]
            if (not native_inverted_ff_either_edge(m, pin) or _ckpin(ci) != clock
                    or {p for p, (dd, _) in pp.items() if dd == "in"} != {"CLK", "D"}):
                return None
            regs.append(ci); dn.append(F.find(pp["D"][1][0]))
        if len(set(regs)) != D or len({F.cells[ci][0][:4] for ci in regs}) != 1:   # one edge across the set
            return None
        leaves = sorted({x for n in dn for x in _leaves(n) if not x.startswith("CONST_")})
        if len(leaves) > 14:
            return None

        def start_port(port):
            return land_form.get(re.sub(r"\[\d+\]$", "", port)) == "ring_start" or _reset_port(port)

        starts = {}
        for x in leaves:
            try:
                starts[x] = _reset_level(x, set(), clock, start_port)
            except (KeyError, RecursionError):
                pass
            d = _single_drv(x)
            if x in starts and x in roots_ports:
                continue
            if d is None or not native_inverted_ff_either_edge(F.cells[d[0]][0], d[1]) or _ckpin(d[0]) != clock:
                return None
        rows = []
        try:
            for vals in itertools.product((False, True), repeat=len(leaves)):
                a = dict(zip(leaves, vals))
                rows.append((a, [bool(_ev(n, a, {})) for n in dn]))
        except (KeyError, TypeError, RecursionError):
            return None
        if any(sum(dv) > 1 for _, dv in rows):
            return None
        forcing = sorted(x for x, (lvl, depth) in starts.items() if depth < 64
                         and not any(any(dv) for a, dv in rows if a[x] == lvl))
        if not forcing:
            return None
        start = min(forcing, key=lambda x: starts[x][1])
        lvl = starts[start][0]
        if not all(any(dv[k] for a, dv in rows if a[start] != lvl) for k in range(D)):
            return None
        atmost_regs.update(regs)
        res.setdefault("registered_atmost_one", {})[F.cells[regs[0]][1]] = dict(
            flops=[F.cells[ci][1] for ci in regs], leaves=leaves, start=start,
            start_chain_edges=starts[start][1], start_asserted_edges_required=starts[start][1] + 1)
        valid = {s for s in itertools.product((False, True), repeat=D) if sum(not v for v in s) <= 1}
        atmost_memo[key] = valid
        return valid

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
                valid = _registered_onehot(allc, D, next(iter(clks)))
                if valid is None:
                    valid = _registered_atmost_one(allc, D, next(iter(clks)))
                if valid is not None and vals not in valid:
                    continue
                return f"write conditions not mutually exclusive at {a}", [], []
        return None, ffs, depths

    def _ckpin(ci):
        ck = [v for k, (dd_, v) in F.cells[ci][2].items() if k in ("CLK", "C", "CK") and len(v) == 1]
        return F.find(ck[0][0]) if len(ck) == 1 else None

    def _parent(path):
        return path.rsplit("/", 1)[0] if "/" in path else ""

    def _module_is(path, family):
        # Yosys parameterized names contain the original module as a complete
        # backslash-delimited component, sometimes followed by parameters.
        return family in F.module_types.get(path, "").split("\\")

    def _status_descendant(ci, ring_parent):
        path = _parent(F.cells[ci][1])
        return _parent(path) == ring_parent and _module_is(path, "ot_meso_ca_status_copy")

    ring_memo = {}

    def ring_of(R):
        """(None, clock net, slot parent instances) of declared hold_mux ring bus R, else (failure text, None, None)."""
        if R in ring_memo:
            return ring_memo[R]
        if land_form.get(R) != "hold_mux" or T.dirs.get(R) != "input":
            ring_memo[R] = (f"ring {R} is not a declared hold_mux input bus ({land_form.get(R)}, {T.dirs.get(R)})",
                            None, None)
            return ring_memo[R]
        cks, pars = set(), set()
        for rb in _bits_of(T, R):
            if rb in dead:  # DIE-QC-69 11-04: a declared dead bit has no slot; the dead class below proves it has no load
                continue
            why, ffs, _ = land_mux(rb, port_root[rb], int(land[R]))
            if why:
                ring_memo[R] = (f"ring {R} slots do not prove ({rb}: {why})", None, None)
                return ring_memo[R]
            cks |= {_ckpin(ci) for ci in ffs}
            pars |= {_parent(F.cells[ci][1]) for ci in ffs}
        ring_memo[R] = (None, cks, pars) if len(cks) == 1 else (f"ring {R} slots on {len(cks)} clocks", None, None)
        return ring_memo[R]

    clock_port_roots = {port_root[b] for p in T.ports if T.dirs.get(p) == "input" and re.match(skip_re, p)
                        for b in _bits_of(T, p)}
    strap_roots = {port_root[b] for p in (straps or ()) if p in T.ports for b in _bits_of(T, p)}

    def _private_copy_output(ci):
        """A copy's sole output drives one face output through private BUF/INV cells."""
        outs = [F.find(v[0]) for _, (dd, v) in F.cells[ci][2].items() if dd == "out" and len(v) == 1]
        if len(outs) != 1:
            return None
        net, seen = outs[0], set()
        while net not in seen:
            seen.add(net)
            if net in roots_ports:
                ports = roots_ports[net]
                if len(ports) != 1 or net not in out_port_roots or loads[net]:
                    return None
                return ports[0]
            if len(loads[net]) != 1 or len(drv[net]) != 1:
                return None
            cj, _ = loads[net][0]
            if not is_buf(F.cells[cj][0]):
                return None
            pp = F.cells[cj][2]
            ins = [v for _, (dd, v) in pp.items() if dd == "in"]
            outs = [v for _, (dd, v) in pp.items() if dd == "out"]
            if len(ins) != 1 or len(ins[0]) != 1 or len(outs) != 1 or len(outs[0]) != 1:
                return None
            net = F.find(outs[0][0])
        return None

    def _stage_next_relay(ci):
        """A writer START stage's sole output reaches, through private BUF/INV cells, one typed relay and nothing else."""
        outs = [F.find(v[0]) for _, (dd, v) in F.cells[ci][2].items() if dd == "out" and len(v) == 1]
        if len(outs) != 1:
            return None
        own = _parent(F.cells[ci][1])
        net, seen = outs[0], set()
        while net not in seen:
            seen.add(net)
            if net in roots_ports or len(loads[net]) != 1 or len(drv[net]) != 1:
                return None
            cj, _ = loads[net][0]
            nxt = _parent(F.cells[cj][1])
            if nxt != own and nxt and _module_is(nxt, "ot_dp_landing_relay"):
                return nxt      # the relay's own reset-mask gate or flop D; the sampler proof covers that relay's cone
            if not is_buf(F.cells[cj][0]):
                return None
            pp = F.cells[cj][2]
            ins = [v for _, (dd, v) in pp.items() if dd == "in"]
            outs = [v for _, (dd, v) in pp.items() if dd == "out"]
            if len(ins) != 1 or len(ins[0]) != 1 or len(outs) != 1 or len(outs[0]) != 1:
                return None
            net = F.find(outs[0][0])
        return None

    def ring_start(b, r, rings, origin=None, copies=(), stages=()):
        """(None, record) = OK, else (failure text, None)."""
        if drv[r]:
            return f"ring start net also driven by {F.cells[drv[r][0][0]][1]}", None
        rck, rdom = set(), set()
        for R in rings:
            why, cks, pars = ring_of(R)
            if why:
                return why, None
            rck |= cks
            rdom |= {(c, q) for c in cks for q in pars}     # (clock net, slot parent instance) of each ring
        sinks, seen = [], set()
        for ci, pin in loads[r]:
            seen.add((ci, pin))
            m = F.cells[ci][0]
            if is_ff(m):
                sinks.append(("ff_D" if pin == "D" else f"ff_{pin}", ci))
            elif not _std_cell(m):
                sinks.append(("macro", ci))
            else:
                _fwd(ci, seen, sinks)
        bad = sorted({(k, F.cells[c][1] if k != "port" else str(roots_ports.get(c, [c])[0])) for k, c in sinks
                      if k != "ff_D"})
        if bad:
            return f"ring start reaches {bad[:3]} (want flop D pins only)", None
        writers, samplers = set(), set()
        for _, ci in sinks:
            ck = _ckpin(ci)
            if (ci in atmost_regs and ck in rck) or any(ck == c and (_parent(F.cells[ci][1]) == q or _status_descendant(ci, q)) for c, q in rdom):
                writers.add(ci)
            else:
                samplers.add(ci)
        if not writers and origin is None:
            return f"ring start reaches no writer flop of ring {rings}", None
        if origin is not None and not samplers:
            return "origin start reaches no sampler flops", None
        origin_removed = None
        origin_is_stage = False
        if (origin is not None and (copies or stages) and origin not in F.module_types
                and not any(_parent(c[1]) == origin or c[1].startswith(origin + "/") for c in F.cells)):
            # DIE-QC-59 11-01: a relay partition whose own start (the typed origin's q) has no local consumer -- synthesis
            # removes the unloaded origin flop.  The declared same-D face copies are then the only samplers; the first
            # copy stands as the typed origin and every proof below (typed relay, one sampler each, same D/reset/clock
            # signature, private face port) still runs on all of them.  An origin that exists but is not reached FAILs.
            if copies:
                origin_removed, origin, copies = origin, copies[0], tuple(copies[1:])
            else:
                # every output of the relay type has a writer branch: the first stage stands as the sampler
                origin_removed, origin, stages, origin_is_stage = origin, stages[0], tuple(stages[1:]), True
        sp = sorted(F.cells[ci][1] for ci in samplers)
        if samplers:
            par = {_parent(p) for p in sp}
            sck = {_ckpin(ci) for ci in samplers}
            if origin is not None:
                declared = {origin, *copies, *stages}
                if par != declared or not any(_module_is(origin, t) for t in
                                              ("ot_dp_landing_origin", "ot_dp_landing_origin_s", "ot_dp_landing_origin_s_regional", "ot_dp_landing_relay")):
                    return f"origin start reaches {sp[:3]} outside declared typed origin {origin}", None
                if (copies or stages) and not all(_module_is(x, "ot_dp_landing_relay") for x in declared):
                    return "origin face copies require actual typed relay instances", None
                if _module_is(origin, "ot_dp_landing_relay"):
                    for parent in declared:
                        n = sum(_parent(F.cells[ci][1]) == parent for ci in samplers)
                        if n != 1:
                            return f"relay start {parent} reaches {n} sampler flops (want exactly one)", None
            if origin is None and (len(par) != 1 or "origin" not in next(iter(par)).rsplit("/", 1)[-1]):
                return f"ring start reaches non-writer flops {sp[:3]} outside one origin instance", None
            if not (copies or stages) and len(samplers) > 2:
                return f"ring start reaches {len(samplers)} origin flops {sp[:3]} (want <= 2 sampler flops)", None
            if len(sck) != 1 or not (sck <= clock_port_roots) or sck & rck:
                return f"origin sampler flops {sp} on clock(s) {sorted(map(str, sck))} (want one clock port, not the ring clock)", None
            sc = next(iter(sck))
            for ci in samplers:
                m, path, pp = F.cells[ci]
                dn = [v for k, (dd_, v) in pp.items() if k == "D" and len(v) == 1]
                dnet = F.find(dn[0][0])
                L = _leaves(dnet)
                if r not in L:
                    return f"origin sampler {path} D cone does not contain the start", None
                ctl = sorted(x for x in L if x != r and not x.startswith("CONST_"))
                for x in ctl:
                    d = _single_drv(x)
                    if (origin is not None and _module_is(origin, "ot_dp_landing_relay")
                            and d is not None and d[0] == ci):
                        return f"relay sampler {path}: D cone feeds back its own output", None
                    if x in roots_ports:
                        if x not in strap_roots:
                            return f"origin sampler {path} D cone leaf port {roots_ports[x][0]} (want declared straps only)", None
                    elif d is None or not is_ff(F.cells[d[0]][0]) or _ckpin(d[0]) != sc:
                        return f"origin sampler {path} D cone leaf {x} is not a flop on the sampler clock", None
                if len(ctl) > 12:
                    return f"origin sampler {path}: {len(ctl)} D cone leaves (too wide to prove)", None
                samp = False
                try:
                    for vals in itertools.product((False, True), repeat=len(ctl)):
                        a0 = dict(zip(ctl, vals))
                        if origin is not None and _module_is(origin, "ot_dp_landing_relay"):
                            # A relay is one reset-qualified FF, never an inverted,
                            # OR-set or feedback sampler under another control state.
                            dv = tuple(_ev(dnet, dict(a0, **{r: bv}), {}) for bv in (False, True))
                            if dv not in ((False, False), (False, True)):
                                return f"relay sampler {path}: D is not reset-masked start", None
                            samp |= dv == (False, True)
                        elif all(_ev(dnet, dict(a0, **{r: bv}), {}) == bv for bv in (False, True)):
                            samp = True
                            break
                except KeyError as e:
                    return f"origin sampler {path} D cone: {e.args[0]}", None
                if not samp:
                    return f"origin sampler {path}: D never equals the start (not a sampler)", None
        face_copies = {}
        if origin_removed is not None and not origin_is_stage:
            output = _private_copy_output(next(ci for ci in samplers if _parent(F.cells[ci][1]) == origin))
            if output is None:
                return f"relay copy {origin}: output is not one private face port (origin {origin_removed} removed)", None
            face_copies[origin] = output
        if copies:
            source = next(ci for ci in samplers if _parent(F.cells[ci][1]) == origin)
            sm, _, spp = F.cells[source]
            source_inputs = {k: F.find(v[0]) for k, (dd, v) in spp.items()
                             if dd == "in" and k not in ("CLK", "C", "CK") and len(v) == 1}
            for parent in copies:
                ci = next(ci for ci in samplers if _parent(F.cells[ci][1]) == parent)
                cm, _, cpp = F.cells[ci]
                inputs = {k: F.find(v[0]) for k, (dd, v) in cpp.items()
                          if dd == "in" and k not in ("CLK", "C", "CK") and len(v) == 1}
                if _cell_base(cm) != _cell_base(sm) or set(inputs) != set(source_inputs):
                    return f"relay copy {parent}: flop/reset signature differs from origin", None
                for pin in inputs:
                    a, z = source_inputs[pin], inputs[pin]
                    if a == z:
                        continue
                    leaves = sorted(x for x in (_leaves(a) | _leaves(z)) if not x.startswith("CONST_"))
                    # leaves that are equal-depth shift copies of one root (same-cycle reset relay leaves) share
                    # one variable; every other leaf stays free
                    sclk = clk_root(clk_pin(spp)) if clk_pin(spp) else None
                    cls = {}
                    for x in leaves:
                        r0, dep, par = _shift_class(x, sclk) if sclk else (x, 0, 0)
                        cls[x] = ((r0, dep) if dep > 0 else (x, 0), par if dep > 0 else 0)
                    groups = sorted({g for g, _ in cls.values()})
                    if len(groups) > 13:
                        return f"relay copy {parent}: {pin} cone too wide to prove", None
                    try:
                        for vals in itertools.product((False, True), repeat=len(groups)):
                            gv = dict(zip(groups, vals))
                            assignment = {x: gv[g] ^ bool(par) for x, (g, par) in cls.items()}
                            if _ev(a, assignment, {}) != _ev(z, assignment, {}):
                                return f"relay copy {parent}: {pin} function differs from origin", None
                    except KeyError as e:
                        return f"relay copy {parent}: {pin} cone {e.args[0]}", None
                output = _private_copy_output(ci)
                if output is None or output in face_copies.values():
                    return f"relay copy {parent}: output is not one private face port", None
                face_copies[parent] = output
        writer_stages = {}
        if stages or origin_is_stage:
            sm = F.cells[next(ci for ci in samplers if _parent(F.cells[ci][1]) == origin)][0]
            for parent in ((origin,) if origin_is_stage else ()) + tuple(stages):
                ci = next(ci for ci in samplers if _parent(F.cells[ci][1]) == parent)
                if _cell_base(F.cells[ci][0]) != _cell_base(sm):
                    return f"writer stage {parent}: flop differs from origin", None
                # own raw reset, so not compared to the origin's, but it must mask the start: the sampler proof above
                # only showed D is never the inverted start
                dnet = F.find(next(v for k, (dd_, v) in F.cells[ci][2].items() if k == "D" and len(v) == 1)[0])
                ctl = sorted(x for x in _leaves(dnet) if x != r and not x.startswith("CONST_"))
                try:
                    masked = ctl and any(not _ev(dnet, dict(zip(ctl, vals), **{r: True}), {})
                                         for vals in itertools.product((False, True), repeat=len(ctl)))
                except KeyError as e:
                    return f"writer stage {parent}: D cone {e.args[0]}", None
                if not masked:
                    return f"writer stage {parent}: start is not reset-masked", None
                nxt = _stage_next_relay(ci)
                if nxt is None:
                    return f"writer stage {parent}: output is not one private typed relay", None
                writer_stages[parent] = nxt
        groups = defaultdict(int)
        for ci in writers:
            groups[re.sub(r"\[\d+\]", "[N]", F.cells[ci][1])] += 1
        record = dict(ring=list(rings), ring_clock=sorted(map(str, rck)), writer_flops=len(writers),
                          writer_groups=dict(sorted(groups.items())), sampler_flops=sp,
                          sampler_clock=(str(_ckpin(next(iter(samplers)))) if samplers else None))
        if face_copies:
            record["face_copies"] = face_copies
        if writer_stages:
            record["writer_stages"] = writer_stages
        if origin_removed is not None:
            record["origin_removed_unloaded"] = origin_removed
        return None, record

    def replica_slot(b, r, D):
        """S81-GUNIT-FORM-1 11-07 form "replica": (None, flops) = OK, else (failure text, None).  From the port net,
        every path through BUF / INV / HB cells only (any fanout: the resizer may buffer the D loads after synthesis)
        ends at the D pin of a flop, with even inversion parity, exactly D distinct flops, all on ONE clock net, no
        port or other cell reached (no logic, no leak); each flop is then this bit's face register."""
        ffs, ck, seen, stack = [], set(), {r}, [(r, 0)]
        while stack:
            n_, par = stack.pop()
            if n_ != r and n_ in roots_ports:
                return f"buffer tree reaches port {roots_ports[n_][0]}", None
            if n_ != r and len(drv[n_]) != 1:
                return f"{len(drv[n_])} drivers on replica tree net {n_}", None
            for ci, pin in loads[n_]:
                m, path, pp = F.cells[ci]
                if is_ff(m):
                    if pin != "D" or par:
                        return f"replica load {path}.{pin} is not a D pin at even inversion", None
                    c_ = [v for k, (dd_, v) in pp.items() if k in ("CLK", "C", "CK") and len(v) == 1]
                    if len(c_) != 1:
                        return f"replica flop {path} clock pin not found", None
                    ffs.append(ci); ck.add(F.find(c_[0][0]))
                    continue
                if not is_buf(m):
                    return f"replica tree loads {m} {path}", None
                outs = [v for k, (dd_, v) in pp.items() if dd_ == "out"]
                if len(outs) != 1 or len(outs[0]) != 1:
                    return f"replica tree cell {path} has {len(outs)} outputs", None
                o_ = F.find(outs[0][0])
                if o_ in seen:
                    return "buffer/inverter cycle in replica tree", None
                seen.add(o_)
                stack.append((o_, par ^ (1 if m.upper().startswith(("INV", "$_NOT_")) else 0)))
        if len(ffs) != D or len(set(ffs)) != D:
            return f"{len(set(ffs))} distinct replica flops ({len(ffs)} D pins), declared D {D}", None
        if len(ck) != 1:
            return f"replica flops on {len(ck)} clock nets (want one)", None
        return None, ffs

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

    # Explicit PHY clock pads are proved clock-only through the actual netlist,
    # not exempted by their spelling. Opaque native endpoints require typed pins.
    res_pad = {}
    for pad in pad_clocks or ():
        if pad.get('dir') != 'in':
            continue
        name = pad['name']
        if T.dirs.get(name) != 'input' or len(_bits_of(T, name)) != 1 or not re.match(skip_re, name):
            fail('pad_clock', name, 'want one input bit with an actual SDC create_clock')
            continue
        allowed = {(x['module'], x['pin']) for x in pad.get('sink_pins', [])}
        if allowed - set(native_clock_pins):
            fail('pad_clock', name, f'declared native clock pins lack actual Liberty clock:true input roles: {sorted(allowed - set(native_clock_pins))}')
            continue
        root = port_root[_bits_of(T, name)[0]]
        stack, visited, terminals, why = [(root, None)], set(), 0, None
        while stack and why is None:
            net, parent = stack.pop()
            if net in visited:
                continue
            visited.add(net)
            if len(drv[net]) != (0 if parent is None else 1):
                why = 'clock net has an unexpected driver'; break
            for ci, pin in loads[net]:
                master, path, pp = F.cells[ci]
                if (is_ff(master) and pin in ('CLK', 'C', 'CK')) or (master, pin) in allowed:
                    terminals += 1; continue
                if is_buf(master) or (master.upper().startswith('ICG') and pin == 'CLK'):
                    ins = [(p, v) for p, (d, v) in pp.items() if d == 'in']
                    outs = [v for p, (d, v) in pp.items() if d == 'out']
                    if is_buf(master) and (len(ins) != 1 or len(ins[0][1]) != 1):
                        why = f'non-scalar clock buffer {path}'; break
                    if len(outs) != 1 or len(outs[0]) != 1:
                        why = f'non-scalar clock output {path}'; break
                    child = F.find(outs[0][0])
                    if child in visited:
                        why = f'clock buffer cycle at {path}'; break
                    stack.append((child, ci)); continue
                why = f'data/untyped load {master} {path}/{pin}'; break
        if why is None and not terminals:
            why = 'no sequential or typed native clock load'
        if why:
            fail('pad_clock', name, why)
        else:
            res_pad[name] = dict(clock_loads=terminals, nets=len(visited))
    if pad_clocks:
        res['pad_clock_inputs'] = res_pad

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
            if b in spare and d == "output" and all(x in spare for x in others) and _spare_tie(F, drv, r) is not None:
                res["spare_declared"].append(b)       # DIE-S81-46: declared spare-out bit, tied constant
                res["ok"] += 1
                continue
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
            if d == "input" and _reset_spine_landing(F, loads[r]):
                # DIE-KV-57 10-31: a reset-spine landing (ot_dp_rsync, asbuilt.reset_spines: asserted asynchronously,
                # released after S clocks) loads ONLY the asynchronous set/reset pins of its own synchroniser flops --
                # the same class as arst_n into the root synchroniser (SKIP_RE): no face register by design.  Any D,
                # logic or second-instance load still takes the ordinary input check below.
                res.setdefault("reset_spine", []).append(b)
                res["ok"] += 1
                continue
            # S81-SVCRS-3 11-10: an unlisted bit of a per-bit replica bus skips every land branch below and takes the
            # ordinary input check (the final else)
            lp = p in land and _land_bit(p, b)
            if d == "output":
                cur, chain, ff = r, [], None
                ok = True
                seen = set()
                lat = None
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
                        if lat is not None:
                            why = face_lockup_why(lat[0], ci)
                            if why:
                                fail("unregistered", b, f"face latch {lat[1]}: {why}")
                                ok = False
                                break
                            res.setdefault("face_lockup", []).append(b)
                        break
                    if lat is None and latch_level(m) and pin == "Q" and pp.get("D", ("", []))[0] == "in" \
                            and len(pp["D"][1]) == 1:
                        lat = (ci, path)               # the one face lockup latch: trace on through its D
                        chain.append(path)
                        cur = F.find(pp["D"][1][0])
                        if cur in roots_ports:
                            fail("feedthrough", b, f"latched from port {roots_ports[cur][0]}")
                            ok = False
                            break
                        continue
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
            elif lp and land_form[p] == 'hard_child':
                why = hard_child(p, b, r)
                if why:
                    fail('land_slot', b, why)
                    continue
                res['ok'] += 1
                res['hard_landing_bits'] = res.get('hard_landing_bits', 0) + 1
                continue
            elif lp and land_form[p] in ("ring_start", "origin_start"):
                origin = origin_spec(land_raw[p]) if land_form[p] == "origin_start" else None
                copies = land_raw[p].get("copies", ()) if origin is not None else ()
                stages = land_raw[p].get("stages", ()) if origin is not None else ()
                why, rec = ring_start(b, r, [] if origin else ring_spec(land_raw[p]), origin, copies, stages)
                if why:
                    fail("land_slot", b, why)
                    continue
                res.setdefault("ring_start", {})[b] = rec
                res["ring_start_bits"] = res.get("ring_start_bits", 0) + 1
                res["ok"] += 1
                continue
            elif lp and land_form[p] == "replica":
                why, rffs = replica_slot(b, r, int(land[p]) if rep_bits.get(p) is None
                                         else rep_bits[p][int(b[len(p) + 1:-1])])
                if why:
                    fail("land_slot", b, why)
                    continue
                for ci in rffs:
                    claimed[ci].append(b)
                res["flops"][b] = F.cells[rffs[0]][1]
                res["land_replica_bits"] = res.get("land_replica_bits", 0) + 1
                res["ok"] += 1
                continue
            elif lp and land_form[p] == "hold_mux":
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
            elif lp:
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
        sb = [b for b in bs if "merged" in seam_cls(b)]
        if len(bs) > 1 and sb and len(bs) - len(sb) <= 1:
            # HBM-Q2NF-RF 11-10: one flop registers at most ONE non-seam bit plus its declared seam copies; the
            # non-seam (die-facing) bit still has a flop of its own among die bits, so it keeps the full guard.
            for b in bs:
                res["seam_declared"].append(f"{b}: merged flop {F.cells[ci][1]} with {[x for x in bs if x != b][:3]}")
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
        # Use the same data-port census on both sides: clock/reset pins in
        # pins.json do not require a data face register.
        want = {x['bus'] if x.get('bit') is None else f"{x['bus']}[{x['bit']}]"
                for x in pins if not re.match(skip_re, x['bus'])}
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
                                   "{bus: D} (ICG form) or {bus: {D, form: hold_mux}} or {bus: {form: ring_start, ring: R}}")
    ap.add_argument("--types-from", help="hierarchical netlist (kit 1_2_yosys.v) giving instance-path module types "
                                         "for a flat ODB-written netlist (typed status-copy / origin proofs)")
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
    dl = kit_dead_list(Path(a.pins).parent) if a.pins else []
    spl = kit_spare_list(Path(a.pins).parent) if a.pins else []
    tml = kit_timed_list(Path(a.pins).parent) if a.pins else []
    sml = kit_seam_map(Path(a.pins).parent) if a.pins else {}
    pad_clocks, native_clock_pins = kit_pad_clocks(bd) if bd else ([], set())
    r = guard(Path(a.netlist).read_text(), a.top, pins=pins, ft1=ft1, straps=sl, bumps=bl, clocks=ck, land=land, dead=dl, exports=ex, pad_clocks=pad_clocks, native_clock_pins=native_clock_pins, spare=spl, timed=tml, seam=sml,
              types=hier_module_types(Path(a.types_from).read_text(), a.top) if a.types_from else None)
    r["netlist"] = a.netlist
    if a.types_from:
        r["types_from"] = a.types_from
    if a.out:
        Path(a.out).write_text(json.dumps(r, indent=1) + "\n")
    print(f"FACE_GUARD {r['verdict']} top {r['top']} bits {r['checked']} ok {r['ok']} fails {r['fail_counts']}")
    return 0 if r["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
