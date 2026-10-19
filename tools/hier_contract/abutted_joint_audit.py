#!/usr/bin/env python3
"""DIE-LEVEL abutted-joint bit-order audit (ROOT-PINORDER-AUDIT 2026-10-19; generalises
tools/ref_tile/specs_hbm_b_rtl2_1017/hc_ring_joints.py from the HC ring to every hard child pair of a die case).

Why: HBM-HCRING found that abutted tile faces had NO defined bit order.  A route without route.pin_balance runs PPL with
OT_PIN_GROUP_MAX 32: a wide bus becomes ordered 32-bit chunks that PPL scatters independently over the face, so two
abutted tiles meet chunk-scrambled; and a tile placed mirrored across the joint (R180 / MX / MY against an R0
neighbour) meets the neighbour's bus fully REVERSED unless one side lays its bits out high bit first over the mirrored
range (spec key pin_order_desc -> run_abi3_physical OT_PIN_ORDER_DESC, needs route.pin_balance).

Inputs (one die case, as the die generators write it):
  --verilog die.v           structural die netlist (top-level nets between hard children; std cells ignored)
  --place F                 placement: OpenROAD `place_inst -name I -location {x y} -orientation O` lines and/or
                            `ot_mts::place [$_blk findInst I] x y O` lines (location = lower-left of the placed bbox)
  --lef F|DIR               the LEF abstracts the die binds (files, directories of *.lef, .gz ok)
  --status KIND:PATH        which masters are ROUTED (closed view: the LEF pin centres ARE the order):
                              s81_case:case.json      (closed_views {master: rev:physical/ref_tile/<kit>/views/..})
                              hbm_manifest:manifest.json  (views {master: ROUTED_* / BOUND_ROUTED / SYNTH ..})
                              lane_views:lane_views.tsv   (KV: master<TAB>closure ref)
                              lef_comments            (generator comment above each MACRO: 'closed view
                                                       physical/ref_tile/<kit>/views' or '(CLOSED <job>' = routed;
                                                       ', re-pin' = die re-pinned a closed view -> not routed)
  --orig-netlist die.v      optional: the bind netlist whose instance masters name the real module of per-instance
                            stand-in cells (S81 rv_*), for the kit lookup
  --kit-root DIR            worktree with physical/ref_tile/*/spec.json (+ git ls-tree for views/<master> names)

Pin model per side of a joint (hc_ring_joints.py 'plan' mode, generalised):
  routed_lef   a closed view: the routed LEF pin centres (order measured, order_defined = true)
  kit_plan     not routed, kit found, port has a face in the kit: the kit's route pin plan (ref_tile pin_regions):
               one region per ranged port (pin_ranges), one per face for the unranged ports (full face minus
               OT_PIN_CORNER_UM 1.0); bits in `lsort -dictionary` name order, reversed for pin_order_desc;
               pin k of n at lo + (hi - lo)(k + .5)/n.  order_defined = route.pin_balance present.  Without it the
               route really scatters 32-b chunks: the IDEAL ordered plan is reported and flagged order_defined=false.
  standin_lef  not routed and no kit / port not in the kit (or io_tcl / ANY face): the die's stand-in LEF centres,
               order_defined = false (fail closed: listed in missing.no_kit / missing.port_not_in_kit).

Joint = two placed hard children whose bboxes face each other across a gap <= --gap-um (default 5 um; abutted = 0)
with an overlap along the joint line, and at least one net bit whose two pins both sit on the facing faces
(<= --face-tol-um of the joint line).  Pins of the pair's nets that are not on the facing faces are counted
(off_face_bits) but not judged.  Joint wiring = what abutted (or crossing-free channel) faces give: the two face pin
rows paired by RANK along the joint line.  Per joint: bits, identity (every net pairs rank to rank), moved bits,
name-wired crossings (inversions), max offset along the joint line, reversed (crossings = n(n-1)/2), mirrored
(the two masters' face axes run opposite in the die), order_defined, and for a joint that needs work: the side to
re-kit (the master with fewer die instances, then the non-routed one) with per port the range in THAT master's
face coordinates that lands each bit on its partner (mirrored range) and whether it must run high bit first.
Verdicts (judged for joints > --min-bits - 1 bits, default > 32):
  ok             identity, 0 crossings, offset <= --tol-um, both sides order_defined
  undefined      geometry fine under the ideal plan but a side has no defined order (add route.pin_balance)
  reversed       full reversal (mirrored joint without pin_order_desc + mirrored range)
  scrambled      crossings > 0, not a full reversal
  misaligned     crossing-free but offset > --tol-um (ranges do not face each other)
Fail-closed: instances without placement, masters without LEF (other than ASAP7 std cells) and port width mismatches
  -> listed in `missing`, `complete` = false, exit 3 (a 1-bit pin missing from a LEF is listed but does not block);
  non-routed masters without a kit -> missing.no_kit and order_defined = false on every joint they touch.

CLI: abutted_joint_audit.py --die NAME --verilog die.v --place place.tcl --lef DIR [--status KIND:PATH]
       [--orig-netlist bind.v] [--kit-root WT] --out DIE.json [--handoff handoff_DIE.md --lead LANE]
exit 0 = complete audit (whatever the verdicts; this is an audit, not a gate), 3 = incomplete (missing data).
"""
from __future__ import annotations

import argparse
import collections
import gzip
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from pin_align import inversions  # noqa: E402

SCHEMA = "opentallas.abutted_joint_audit.v1"
STD_RE = re.compile(r"_ASAP7_|^(TIEHI|TIELO|BUF|INV|ICG|DFF|SDF|NAND|NOR|AND|OR|XOR|XNOR|AO|OA|HB|DECAP|FILLER|TAP)",
                    re.I)
CORNER_UM = 1.0          # run_abi3_physical OT_PIN_CORNER_UM default (full-face balanced regions)
ROT = ("R90", "R270", "MXR90", "MYR90")


# ------------------------------------------------------------------------------------------------------------ input
def _open(p):
    p = Path(p)
    return gzip.open(p, "rt") if p.suffix == ".gz" else open(p)


def lef_files(specs):
    out = []
    for s in specs:
        p = Path(s)
        if p.is_dir():
            out += sorted(x for x in p.iterdir() if x.name.endswith((".lef", ".lef.gz")))
        else:
            out.append(p)
    return out


def read_lef(paths):
    """{macro: {w, h, pins: {pin: (cx, cy, dir)}, comment}}: first RECT of each signal pin; '#' lines before MACRO"""
    out = {}
    for path in paths:
        m = pin = None
        pend = []
        use = dirn = None
        first = None
        with _open(path) as fh:
            for line in fh:
                s = line.split()
                if not s:
                    continue
                k = s[0]
                if k.startswith("#"):
                    if m is None:
                        pend.append(line.strip())
                    continue
                if k == "MACRO":
                    m = s[1]
                    out[m] = {"w": 0.0, "h": 0.0, "pins": {}, "comment": " ".join(pend), "file": str(path)}
                    pend = []
                    pin = None
                elif m is None:
                    continue
                elif k == "SIZE":
                    out[m]["w"], out[m]["h"] = float(s[1]), float(s[3])
                elif k == "PIN":
                    pin, use, dirn, first = s[1], None, None, None
                elif k == "OBS":
                    pin = None
                elif pin is not None and k == "DIRECTION":
                    dirn = s[1]
                elif pin is not None and k == "USE":
                    use = s[1]
                elif pin is not None and k == "RECT" and first is None:
                    v = [x for x in s[1:] if x not in ("MASK", ";")]
                    try:
                        x0, y0, x1, y1 = map(float, v[-4:])
                        first = ((x0 + x1) / 2, (y0 + y1) / 2)
                    except ValueError:
                        pass
                elif k == "END" and len(s) > 1:
                    if pin is not None and s[1] == pin:
                        if first is not None and use not in ("POWER", "GROUND"):
                            out[m]["pins"][pin] = (first[0], first[1], dirn)
                        pin = None
                    elif s[1] == m:
                        m = None
    return out


_PLI = re.compile(r"place_inst\s+-name\s+(\S+)\s+-location\s+\{\s*([-\d.]+)\s+([-\d.]+)\s*\}\s+-orientation\s+(\S+)")
_MTS = re.compile(r"ot_mts::place\s+\[\s*\$\w+\s+findInst\s+(\S+?)\s*\]\s+([-\d.]+)\s+([-\d.]+)\s+(\S+)")


def read_place(paths):
    out = {}
    for p in paths:
        with _open(p) as fh:
            for line in fh:
                if "place" not in line:
                    continue
                for rx in (_PLI, _MTS):
                    for mm in rx.finditer(line):
                        name = mm.group(1).strip("{}").replace("\\", "")
                        out[name] = (float(mm.group(2)), float(mm.group(3)), mm.group(4))
    return out


# ------------------------------------------------------------------------------------------------- verilog netlist
_TOK = re.compile(r"\\\S+|[A-Za-z_][A-Za-z0-9_$]*|\d+'[sS]?[bBoOdDhH][0-9a-fA-FxXzZ_?]+|'[01xXzZ]|\d+|\[[^\]]*\]|[{}(),.#]")
_DECL = re.compile(r"^(wire|input|output|inout|reg|tri|supply0|supply1)\b\s*(?:wire\b|reg\b|signed\b|\s)*"
                   r"(\[\s*(-?\d+)\s*:\s*(-?\d+)\s*\])?\s*(.*)$", re.S)


def _clean(text):
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return re.sub(r"//[^\n]*", " ", text)


def _name(tok):
    return tok[1:] if tok.startswith("\\") else tok


class Netlist:
    """top module of a structural die netlist: instances {inst: (master, {port: [bit keys MSB first]})}"""

    def __init__(self, text, want_masters=None):
        text = _clean(text)
        self.width = {}
        self.instances = {}
        self.assigns = []
        mm = re.search(r"\bmodule\s+(\\?\S+?)\s*(#\s*\(.*?\)\s*)?\(", text, re.S)
        if not mm:
            raise ValueError("no module in netlist")
        self.top = _name(mm.group(1))
        # header: up to the matching ')' then ';'
        i, depth = mm.end(), 1
        while depth and i < len(text):
            c = text[i]
            depth += (c == "(") - (c == ")")
            i += 1
        self._decl_list(text[mm.end():i - 1].split(","))
        end = text.find("endmodule", i)
        body = text[i:end if end >= 0 else len(text)]
        for st in body.split(";"):
            st = st.strip()
            if not st:
                continue
            d = _DECL.match(st)
            if d:
                self._decl(d)
                continue
            if st.startswith("assign"):
                self.assigns.append(st[6:])
                continue
            self._inst(st, want_masters)

    def _decl_list(self, items):
        cur = None
        for it in items:
            it = it.strip()
            d = _DECL.match(it)
            if d:
                cur = (d.group(3), d.group(4))
                self._set(d.group(5), cur)
            elif it and cur is not None:
                self._set(it, cur)

    def _decl(self, d):
        self._set(d.group(5), (d.group(3), d.group(4)))

    def _set(self, names, rng):
        for n in names.split(","):
            n = n.strip().split("=")[0].strip()
            if not n:
                continue
            n = _name(n.split()[0]) if n.split() else n
            if rng[0] is not None:
                self.width[n] = (int(rng[0]), int(rng[1]))
            else:
                self.width.setdefault(n, None)

    def _inst(self, st, want):
        toks = _TOK.findall(st)
        if len(toks) < 3:
            return
        master = _name(toks[0])
        if want is not None and master not in want:
            return
        k = 1
        if toks[k] == "#":                       # parameter override: skip balanced parens
            depth, k = 0, k + 1
            while k < len(toks):
                depth += (toks[k] == "(") - (toks[k] == ")")
                k += 1
                if depth == 0:
                    break
        inst = _name(toks[k])
        k += 1
        if k < len(toks) and toks[k].startswith("["):      # instance array: not used by die generators
            inst += toks[k]
            k += 1
        ports = {}
        # .port ( expr )
        while k < len(toks):
            if toks[k] == "." and k + 2 < len(toks) and toks[k + 2] == "(":
                port = _name(toks[k + 1])
                j, depth = k + 3, 1
                while j < len(toks) and depth:
                    depth += (toks[j] == "(") - (toks[j] == ")")
                    j += 1
                ports[port] = self.bits(toks[k + 3:j - 1])
                k = j
            else:
                k += 1
        self.instances[inst] = (master, ports)

    def bits(self, toks):
        """expression tokens -> bit keys MSB first (None = constant / unconnected bit)"""
        out, i = [], 0
        while i < len(toks):
            if toks[i] == ",":
                i += 1
                continue
            e, i = self._expr(toks, i)
            out += e
        return [self._canon(x) for x in out]

    def _expr(self, toks, i):
        t = toks[i]
        if t == "{":
            if i + 2 < len(toks) and toks[i + 1].isdigit() and toks[i + 2] == "{":      # {N{...}}
                inner, j = self._expr(toks, i + 2)
                return inner * int(toks[i + 1]), j + 1                                 # skip the outer '}'
            items, j = [], i + 1
            while j < len(toks) and toks[j] != "}":
                if toks[j] == ",":
                    j += 1
                    continue
                e, j = self._expr(toks, j)
                items += e
            return items, j + 1
        if "'" in t:
            mm = re.match(r"(\d*)'", t)
            return [None] * (int(mm.group(1)) if mm and mm.group(1) else 1), i + 1
        if t[0].isdigit():
            return [None], i + 1
        if t in ("(", ")", ".", "#", "}"):
            return [], i + 1
        name = _name(t)
        if t.startswith("\\") and name.endswith("]") and "[" in name:
            return [(name, None)], i + 1                                   # escaped bit name: one scalar net
        sel = toks[i + 1] if i + 1 < len(toks) and toks[i + 1].startswith("[") else None
        if sel:
            inner = sel[1:-1].strip()
            if ":" in inner:
                a, b = (int(x) for x in inner.split(":"))
                step = -1 if a >= b else 1
                return [(name, j) for j in range(a, b + step, step)], i + 2
            return [(name, int(inner))], i + 2
        w = self.width.get(name)
        if w is None:
            return [(name, None)], i + 1
        a, b = w
        step = -1 if a >= b else 1
        return [(name, j) for j in range(a, b + step, step)], i + 1

    def _canon(self, key):
        if key is None:
            return None
        n, j = key
        if j is None and self.width.get(n) is not None:
            a, b = self.width[n]
            if a == b:
                return (n, a)
        return key


class UF:
    def __init__(self):
        self.p = {}

    def find(self, x):
        p = self.p
        while p.get(x, x) != x:
            p[x] = p.get(p[x], p[x])
            x = p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def _dict_key(s):
    """Tcl lsort -dictionary: digit runs compare as integers, case-insensitive first"""
    parts = re.split(r"(\d+)", s)
    return [(0, int(x), "") if x.isdigit() else (1, 0, x.lower()) for x in parts if x != ""], s


def port_bits(pins, port):
    """LEF pin names of a port, descending bit index (MSB first) or [port] for a scalar"""
    if port in pins:
        return [port]
    rx = re.compile(re.escape(port) + r"\[(\d+)\]$")
    got = []
    for p in pins:
        mm = rx.match(p)
        if mm:
            got.append((int(mm.group(1)), p))
    return [p for _, p in sorted(got, reverse=True)]


def port_index(pins):
    """{port base: [pin names MSB first]} for a macro's pins"""
    by = collections.defaultdict(list)
    for p in pins:
        mm = re.match(r"(.+)\[(\d+)\]$", p)
        if mm:
            by[mm.group(1)].append((int(mm.group(2)), p))
        else:
            by[p].append((None, p))
    return {k: [p for _, p in sorted(v, key=lambda t: -1 if t[0] is None else t[0], reverse=True)]
            for k, v in by.items()}


# ---------------------------------------------------------------------------------------------------- geometry
def xform(x, y, w, h, o):
    """master point -> offset inside the placed bbox (location = bbox lower-left, odb setLocation)"""
    if o in ("R0", "N"):
        return x, y
    if o in ("R180", "S"):
        return w - x, h - y
    if o in ("MX", "FS"):
        return x, h - y
    if o in ("MY", "FN"):
        return w - x, y
    if o in ("R90", "W"):
        return h - y, x
    if o in ("R270", "E"):
        return y, w - x
    if o in ("MXR90", "FW"):
        return y, x
    if o in ("MYR90", "FE"):
        return h - y, w - x
    raise ValueError(f"orientation {o}")


def placed_wh(w, h, o):
    return (h, w) if o in ROT or o in ("W", "E", "FW", "FE") else (w, h)


def master_face(x, y, w, h):
    d = {"S": y, "N": h - y, "W": x, "E": w - x}
    f = min(d, key=d.get)
    return f, d[f]


# --------------------------------------------------------------------------------------------------------- kits
class Kits:
    def __init__(self, root):
        self.root = Path(root) if root else None
        self.spec = {}
        self.by_top = collections.defaultdict(list)
        self.by_view = collections.defaultdict(list)
        self.rev = None
        if not self.root:
            return
        for p in sorted((self.root / "physical/ref_tile").glob("*/spec.json")):
            try:
                s = json.loads(p.read_text())
            except Exception:
                continue
            k = p.parent.name
            self.spec[k] = s
            if s.get("top"):
                self.by_top[s["top"]].append(k)
        try:
            self.rev = subprocess.check_output(["git", "-C", str(self.root), "rev-parse", "HEAD"], text=True).strip()
            ls = subprocess.check_output(["git", "-C", str(self.root), "ls-tree", "-r", "--name-only", "HEAD",
                                          "physical/ref_tile"], text=True, timeout=120)
            for line in ls.splitlines():
                mm = re.match(r"physical/ref_tile/([^/]+)/views/([^/]+?)(?:\.lef|/[^/]+\.lef)$", line)
                if mm and mm.group(1) not in self.by_view[mm.group(2)]:
                    self.by_view[mm.group(2)].append(mm.group(1))
        except Exception:
            pass

    def lookup(self, master, hint=None):
        """(kit, candidates)"""
        if hint and hint in self.spec:
            return hint, [hint]
        base = re.sub(r"__pv\d+$", "", master)
        cands = []
        for m in (master, base):
            for k in self.by_view.get(m, []) + self.by_top.get(m, []):
                if k in self.spec and k not in cands:
                    cands.append(k)
        if not cands:
            return None, []
        # prefer a kit that both has the view and names the module; then the most recent-looking name
        both = [k for k in cands if self.spec[k].get("top") in (master, base) and k in self.by_view.get(master, [])]
        pick = sorted(both or cands, key=lambda k: (not (self.spec[k].get("route") or {}).get("pin_balance"), k))[0]
        return pick, cands


def kit_plan(spec, w, h):
    """{pin name: (x, y)} master coordinates of every planned bit (ref_tile pin_regions + run_abi3_physical
    balanced placer), plus {port: face}; ports on ANY / io_tcl kits are not modelled"""
    if spec.get("io_tcl"):
        return None, {}
    rng = spec.get("pin_ranges") or {}
    desc = set(spec.get("pin_order_desc") or [])
    faces = {}
    regions = []
    for f, v in (spec.get("pins") or {}).items():
        if not v or f not in "NSEW" or len(f) != 1:
            continue
        plain = [n for n in v if n not in rng]
        for n in v:
            faces[n] = f
        if plain:
            regions.append((plain, f, None))
        for n in v:
            if n in rng:
                regions.append(([n], f, (float(rng[n][0]), float(rng[n][1]))))
    return regions, faces, desc


def plan_positions(spec, w, h, pins):
    """{lef pin name: (x, y)} for the kit's planned pins present in the LEF"""
    r = kit_plan(spec, w, h)
    if r[0] is None:
        return {}, {}
    regions, faces, desc = r
    idx = port_index(pins)
    out = {}
    for names, f, rg in regions:
        bits = []
        for n in names:
            bits += idx.get(n, [])
        if not bits:
            continue
        bits = sorted(bits, key=_dict_key)
        if rg is not None and names[0] in desc:
            bits = bits[::-1]
        L = w if f in "NS" else h
        if rg is None:
            lo, hi = (CORNER_UM, L - CORNER_UM) if L > 2 * CORNER_UM else (0.0, L)
        else:
            lo, hi = rg
        n = len(bits)
        for k, b in enumerate(bits):
            t = lo + (hi - lo) * (k + 0.5) / n
            out[b] = {"N": (t, h), "S": (t, 0.0), "W": (0.0, t), "E": (w, t)}[f]
    return out, faces


# ---------------------------------------------------------------------------------------------------- status
def load_status(spec):
    """{master: {'routed': bool, 'kit': str|None, 'note': str}} and a mode tag"""
    if not spec:
        return {}, None
    kind, _, path = spec.partition(":")
    st = {}
    if kind == "s81_case":
        d = json.loads(Path(path).read_text())
        for m, ref in (d.get("closed_views") or {}).items():
            mm = re.search(r"physical/ref_tile/([^/]+)/views", ref)
            st[m] = {"routed": True, "kit": mm.group(1) if mm else None, "note": ref}
    elif kind == "hbm_manifest":
        d = json.loads(_open(path).read())
        for m, s in (d.get("views") or {}).items():
            st[m] = {"routed": "ROUTED" in str(s), "kit": None, "note": str(s)}
    elif kind == "lane_views":
        for line in Path(path).read_text().splitlines():
            p = line.split("\t")
            if len(p) >= 2 and p[0]:
                st[p[0]] = {"routed": True, "kit": None, "note": p[1]}
    elif kind == "lef_comments":
        pass
    else:
        raise ValueError(f"--status kind {kind}")
    return st, kind


def lef_comment_status(macros):
    st = {}
    for m, rec in macros.items():
        c = rec.get("comment") or ""
        mm = re.search(r"closed view physical/ref_tile/([^/\s]+)/views", c)
        if mm:
            st[m] = {"routed": True, "kit": mm.group(1), "note": "lef comment: closed view"}
        elif re.search(r"\(CLOSED\s+\S+", c):
            rep = "re-pin" in c
            st[m] = {"routed": not rep, "kit": None,
                     "note": "lef comment: CLOSED" + (" but RE-PINNED by the die (abstract != routed view)" if rep else "")}
    return st


# ------------------------------------------------------------------------------------------------------ audit
class Side:
    __slots__ = ("inst", "master", "x", "y", "o", "w", "h", "pw", "ph", "kit", "source_mode", "routed", "pos",
                 "plan_faces", "spec", "nmaster", "lookup_master", "kit_cands", "status_note")


def build_sides(net, place, macros, status, kits, orig_master, missing):
    sides = {}
    for inst, (master, _) in net.instances.items():
        if master not in macros:
            if not STD_RE.search(master):
                missing["no_lef"].setdefault(master, inst)
            continue
        if inst not in place:
            missing["no_place"].append(inst)
            continue
        m = macros[master]
        x, y, o = place[inst]
        s = Side()
        s.inst, s.master, s.x, s.y, s.o, s.w, s.h = inst, master, x, y, o, m["w"], m["h"]
        s.pw, s.ph = placed_wh(m["w"], m["h"], o)
        st = status.get(master) or {}
        s.routed = bool(st.get("routed"))
        s.status_note = st.get("note")
        s.lookup_master = orig_master.get(inst, master)
        s.kit, s.kit_cands = kits.lookup(s.lookup_master, st.get("kit"))
        if not s.kit and s.lookup_master != master:
            s.kit, s.kit_cands = kits.lookup(master, st.get("kit"))
        s.spec = kits.spec.get(s.kit) if s.kit else None
        s.pos, s.plan_faces = None, {}
        sides[inst] = s
    return sides


_plan_cache = {}


def side_pin(s, pin, macros):
    """(die x, die y, source, order_defined, master face, master t)"""
    m = macros[s.master]
    lx, ly, _ = m["pins"][pin]
    src, od = "standin_lef", False
    if s.routed:
        src, od = "routed_lef", True
    elif s.spec is not None:
        key = (s.kit, s.master)
        if key not in _plan_cache:
            _plan_cache[key] = plan_positions(s.spec, m["w"], m["h"], m["pins"])
        plan, _ = _plan_cache[key]
        if pin in plan:
            lx, ly = plan[pin]
            src = "kit_plan"
            od = bool((s.spec.get("route") or {}).get("pin_balance"))
    f, _ = master_face(lx, ly, m["w"], m["h"])
    t = lx if f in "NS" else ly
    dx, dy = xform(lx, ly, m["w"], m["h"], s.o)
    return s.x + dx, s.y + dy, src, od, f, t


def facing(a, b, gap_um):
    """(axis along the joint 0 = x / 1 = y, line coordinate, a's die face, b's die face, gap) or None"""
    ax0, ay0, ax1, ay1 = a.x, a.y, a.x + a.pw, a.y + a.ph
    bx0, by0, bx1, by1 = b.x, b.y, b.x + b.pw, b.y + b.ph
    oy = min(ay1, by1) - max(ay0, by0)
    ox = min(ax1, bx1) - max(ax0, bx0)
    best = None
    if oy > 0:
        g = bx0 - ax1
        if -0.01 <= g <= gap_um:
            best = (1, (ax1 + bx0) / 2, "E", "W", g)
        g = ax0 - bx1
        if -0.01 <= g <= gap_um and (best is None or g < best[4]):
            best = (1, (bx1 + ax0) / 2, "W", "E", g)
    if ox > 0:
        g = by0 - ay1
        if -0.01 <= g <= gap_um and (best is None or g < best[4]):
            best = (0, (ay1 + by0) / 2, "N", "S", g)
        g = ay0 - by1
        if -0.01 <= g <= gap_um and (best is None or g < best[4]):
            best = (0, (by1 + ay0) / 2, "S", "N", g)
    return best


def die_face(s, x, y):
    """the placed bbox edge nearest to a die point"""
    d = {"W": x - s.x, "E": s.x + s.pw - x, "S": y - s.y, "N": s.y + s.ph - y}
    return min(d, key=d.get)


def axis_map(s, mface, axis):
    """die axis coordinate = a0 + sign * t for master face coordinate t on master face mface"""
    pts = {"N": lambda t: (t, s.h), "S": lambda t: (t, 0.0), "W": lambda t: (0.0, t), "E": lambda t: (s.w, t)}[mface]
    p0 = xform(*pts(0.0), s.w, s.h, s.o)
    p1 = xform(*pts(1.0), s.w, s.h, s.o)
    sign = (p1[axis] - p0[axis])
    return (s.x, s.y)[axis] + p0[axis], (1 if sign > 0 else -1)


def audit(net, place, macros, status, kits, orig_master=None, gap_um=5.0, face_tol_um=3.0, tol_um=2.0, min_bits=33,
          max_fanout=8):
    missing = {"no_lef": {}, "no_place": [], "width_mismatch": [], "no_kit": {}, "port_not_in_kit": {}}
    _plan_cache.clear()                                 # kit specs may differ between audits in one process
    sides = build_sides(net, place, macros, status, kits, orig_master or {}, missing)
    nmaster = collections.Counter(s.master for s in sides.values())
    # net bit -> endpoints on hard children
    uf = UF()
    for a in net.assigns:
        lhs, _, rhs = a.partition("=")
        lb, rb = net.bits(_TOK.findall(lhs)), net.bits(_TOK.findall(rhs))
        if len(lb) == len(rb):
            for x, y in zip(lb, rb):
                if x is not None and y is not None:
                    uf.union(x, y)
    ends = collections.defaultdict(list)
    for inst, (master, ports) in net.instances.items():
        if inst not in sides:
            continue
        pins = macros[master]["pins"]
        idx = None
        for port, bits in ports.items():
            pb = port_bits(pins, port)
            if not pb:
                if idx is None:
                    idx = port_index(pins)
                pb = idx.get(port, [])
            if len(pb) != len(bits):
                missing["width_mismatch"].append([inst, port, len(pb), len(bits)])
                n = min(len(pb), len(bits))
                pb, bits = pb[len(pb) - n:], bits[len(bits) - n:]       # LSB-aligned (Verilog)
            for pin, key in zip(pb, bits):
                if key is not None:
                    ends[uf.find(key)].append((inst, pin))
    pair_nets = collections.defaultdict(list)
    for key, e in ends.items():
        insts = {i for i, _ in e}
        if len(insts) < 2 or len(e) > max_fanout:
            continue
        for i in range(len(e)):
            for j in range(i + 1, len(e)):
                a, b = e[i], e[j]
                if a[0] == b[0]:
                    continue
                if a[0] > b[0]:
                    a, b = b, a
                pair_nets[(a[0], b[0])].append((key, a[1], b[1]))
    joints = []
    for (ia, ib), nets in pair_nets.items():
        A, B = sides[ia], sides[ib]
        fc = facing(A, B, gap_um)
        if fc is None:
            continue
        axis, line, fa, fb, gap = fc
        rows, off_face = [], 0
        for key, pa, pb in nets:
            xa, ya, sa, oa, mfa, ta = side_pin(A, pa, macros)
            xb, yb, sb, ob, mfb, tb = side_pin(B, pb, macros)
            perp_a = (xa, ya)[1 - axis]
            perp_b = (xb, yb)[1 - axis]
            if (abs(perp_a - line) > face_tol_um + gap / 2 or abs(perp_b - line) > face_tol_um + gap / 2
                    or die_face(A, xa, ya) != fa or die_face(B, xb, yb) != fb):    # corner pins of a side face
                off_face += 1
                continue
            rows.append(dict(pa=pa, pb=pb, a=(xa, ya)[axis], b=(xb, yb)[axis], sa=sa, sb=sb, oa=oa, ob=ob,
                             mfa=mfa, mfb=mfb, ta=ta, tb=tb))
        if not rows:
            continue
        joints.append(judge_joint(A, B, axis, fa, fb, gap, rows, off_face, nmaster, tol_um, min_bits))
    for s in sides.values():
        if not s.routed and s.spec is None:
            missing["no_kit"].setdefault(s.lookup_master, s.inst)
    return joints, missing, sides


def _bits_desc_range(ts):
    ts = sorted(ts)
    n = len(ts)
    step = (ts[-1] - ts[0]) / (n - 1) if n > 1 else 1.0
    return [round(ts[0] - step / 2, 3), round(ts[-1] + step / 2, 3)]


def judge_joint(A, B, axis, fa, fb, gap, rows, off_face, nmaster, tol_um, min_bits):
    n = len(rows)
    ra = sorted(range(n), key=lambda i: (rows[i]["a"], i))
    rb = sorted(range(n), key=lambda i: (rows[i]["b"], i))
    rank_b = {i: k for k, i in enumerate(rb)}
    seq = [rank_b[i] for i in ra]
    moved = sum(1 for k, i in enumerate(ra) if rank_b[i] != k)
    cross = inversions([rows[i]["b"] for i in ra])
    maxc = n * (n - 1) // 2
    rev = n > 1 and all(seq[k] == n - 1 - k for k in range(n))
    off = max(abs(r["a"] - r["b"]) for r in rows)
    od_a = all(r["oa"] for r in rows)
    od_b = all(r["ob"] for r in rows)
    src_a = sorted({r["sa"] for r in rows})
    src_b = sorted({r["sb"] for r in rows})
    mfa = collections.Counter(r["mfa"] for r in rows).most_common(1)[0][0]
    mfb = collections.Counter(r["mfb"] for r in rows).most_common(1)[0][0]
    a0a, sga = axis_map(A, mfa, axis)
    a0b, sgb = axis_map(B, mfb, axis)
    mirrored = sga != sgb
    ports = collections.Counter((re.sub(r"\[\d+\]$", "", r["pa"]), re.sub(r"\[\d+\]$", "", r["pb"])) for r in rows)
    ident = moved == 0 and cross == 0
    if n < min_bits:
        verdict = "small"
    elif cross == 0 and moved == 0 and off <= tol_um:
        verdict = "ok" if od_a and od_b else "undefined"
    elif rev:
        verdict = "reversed"
    elif cross > 0:
        verdict = "scrambled"
    else:
        verdict = "misaligned"
    j = dict(a=side_rec(A, mfa, fa, src_a, od_a, nmaster), b=side_rec(B, mfb, fb, src_b, od_b, nmaster),
             axis="x" if axis == 0 else "y", gap_um=round(gap, 3), bits=n, off_face_bits=off_face,
             ports=[[pa, pb, c] for (pa, pb), c in sorted(ports.items())],
             identity=ident, moved_bits=moved, name_wired_crossings=cross, max_crossings=maxc,
             reversed=rev, max_offset_um=round(off, 3), mirrored=mirrored, order_defined=od_a and od_b,
             verdict=verdict)
    if verdict not in ("ok", "small"):
        j["fix"] = prescribe(A, B, rows, axis, (a0a, sga), (a0b, sgb), mirrored, verdict, od_a, od_b, nmaster)
    return j


def side_rec(s, mface, dface, src, od, nmaster):
    return dict(inst=s.inst, master=s.master, module=s.lookup_master, kit=s.kit, kit_candidates=len(s.kit_cands or []), orient=s.o,
                master_face=mface, die_face=dface, source=src, routed=s.routed, order_defined=od,
                pin_balance=bool(s.spec and (s.spec.get("route") or {}).get("pin_balance")),
                master_instances=nmaster[s.master])


def _bitkey(pin):
    mm = re.match(r"(.+)\[(\d+)\]$", pin)
    return (mm.group(1), int(mm.group(2))) if mm else (pin, 0)


def _mono(v):
    return all(v[i] < v[i + 1] for i in range(len(v) - 1)) or all(v[i] > v[i + 1] for i in range(len(v) - 1))


def own_order(rows, tag):
    """{port: True if the side's own bits run monotonically along the joint} (PPL chunk scatter -> False)"""
    by = collections.defaultdict(list)
    for r in rows:
        port, bit = _bitkey(r["p" + tag])
        by[port].append((bit, r[tag]))
    return {p: _mono([x for _, x in sorted(v)]) for p, v in by.items()}


def side_prescription(who, rows, a0, sg):
    """per port of side `who`: the range (its own master face coordinates) and bit direction that land every bit on
    its partner pin; monotonic = expressible as pin_ranges (+ pin_order_desc)"""
    other = "b" if who == "a" else "a"
    ports = collections.defaultdict(list)
    for r in rows:
        port, bit = _bitkey(r["p" + who])
        ports[port].append((bit, (r[other] - a0) / sg))
    pp = {}
    for port, lst in sorted(ports.items()):
        tv = [t for _, t in sorted(lst)]
        pp[port] = {"bits": len(tv), "pin_range": _bits_desc_range(tv),
                    "pin_order_desc": len(tv) > 1 and tv[0] > tv[-1], "monotonic": _mono(tv)}
    return pp


def prescribe(A, B, rows, axis, ma, mb, mirrored, verdict, od_a, od_b, nmaster):
    """which kit to change and how.  Each side's prescription = the partner's pin positions in its own face
    coordinates (per port range + high-bit-first flag).  The re-kit side: a side whose prescription is expressible
    (every port monotonic, i.e. the partner's own order is monotonic), then fewer die instances, then not CLOSED,
    then b.  A side whose OWN bits are not monotonic (PPL chunk scatter in a closed view, or an unordered stand-in)
    must itself be re-kitted with route.pin_balance (and re-routed when closed) before any range can match it."""
    own = {"a": own_order(rows, "a"), "b": own_order(rows, "b")}
    pres = {"a": side_prescription("a", rows, *ma), "b": side_prescription("b", rows, *mb)}
    sd = {"a": A, "b": B}
    od = {"a": od_a, "b": od_b}
    # a side's prescription is usable only if its PARTNER has a defined, monotonic order to copy
    # (a kit-planned partner counts as defined: the actions add its route.pin_balance; a stand-in LEF or a scrambled
    # routed view does not)
    src = {"a": {r["sa"] for r in rows}, "b": {r["sb"] for r in rows}}
    usable = {}
    for t in "ab":
        o = "b" if t == "a" else "a"
        usable[t] = "standin_lef" not in src[o] and all(own[o].values())
    cand = sorted("ab", key=lambda t: (not usable[t], nmaster[sd[t].master], sd[t].routed, t == "a"))
    who = cand[0]
    S = sd[who]
    pp = pres[who]
    acts = []
    for tag in "ab":
        s = sd[tag]
        bad = sorted(p for p, m in own[tag].items() if not m)
        if s.routed and bad:
            acts.append(f"{tag}: CLOSED {s.master} (kit {s.kit}) own bit order scrambled on {', '.join(bad[:6])}"
                        f"{' ...' if len(bad) > 6 else ''} -> re-kit with route.pin_balance + re-route")
        elif not od[tag] and not s.routed:
            acts.append(f"{tag}: kit {s.kit or '<no kit: ' + (s.lookup_master or s.master) + '>'} add route.pin_balance "
                        f"(order undefined)")
    if verdict in ("reversed", "scrambled", "misaligned") and A.master == B.master and not mirrored:
        acts.append(f"same master {A.master} on both sides, same orientation sense: the crossing is the die netlist's "
                    f"bit mapping across the joint (not a kit order) -> die generator: wire bit k to the facing bit k "
                    f"(or a variant master); a kit range cannot fix it for every instance")
    if verdict in ("reversed", "scrambled", "misaligned"):
        if usable[who]:
            nd = sorted(p for p, r in pp.items() if r["pin_order_desc"])
            acts.append(f"{who}: kit {S.kit or S.lookup_master or S.master} pin_ranges as prescribed on "
                        f"{', '.join(sorted(pp)[:8])}{' ...' if len(pp) > 8 else ''}"
                        + (f" + pin_order_desc {', '.join(nd[:8])}" if nd else "")
                        + (" (mirrored joint)" if mirrored else ""))
            if S.routed:
                acts.append(f"{who}: {S.master} is a CLOSED view -> the change needs a re-route of that kit")
        else:
            pp = {}
            acts.append("no range prescription yet: neither side has a defined monotonic order to copy; define the "
                        "orders above, then re-run this audit for the ranges")
    return dict(side=who, inst=S.inst, master=S.master, module=S.lookup_master, kit=S.kit,
                master_instances=nmaster[S.master], prescription_usable=usable[who],
                routed=S.routed, ports=pp, own_order_monotonic={t: all(v.values()) for t, v in own.items()},
                actions=acts)


# ------------------------------------------------------------------------------------------------------- report
def summarise(joints, min_bits):
    big = [j for j in joints if j["bits"] >= min_bits]
    v = collections.Counter(j["verdict"] for j in big)
    return dict(joints=len(joints), joints_gt32=len(big), verdicts=dict(sorted(v.items())),
                order_undefined=sum(1 for j in big if not j["order_defined"]),
                reversed=sum(1 for j in big if j["reversed"]),
                mirrored=sum(1 for j in big if j["mirrored"]),
                needs_work=sum(1 for j in big if j["verdict"] != "ok"),
                bits_gt32=sum(j["bits"] for j in big))


def joint_class(j):
    a, b = j["a"], j["b"]
    return (a["kit"] or a["module"], a["orient"], a["master_face"], b["kit"] or b["module"], b["orient"],
            b["master_face"], j["verdict"])


def handoff_md(die, lead, rep):
    s = rep["summary"]
    L = [f"# Abutted-joint hand-off: {die} ({rep['source']['label']})",
         "",
         f"Owner lane: **{lead}** (die lead).  Generated by `tools/hier_contract/abutted_joint_audit.py` "
         f"(ROOT-PINORDER-AUDIT 10-19); data `{die}.json`.  Do not regen kits from here: the die lead assigns.",
         "",
         f"Joints {s['joints']}, > 32 b {s['joints_gt32']} ({s['bits_gt32']} bits), order-undefined "
         f"{s['order_undefined']}, reversed {s['reversed']}, mirrored {s['mirrored']}, needing work {s['needs_work']}; "
         f"verdicts {s['verdicts']}.  Complete: {rep['complete']}.",
         ""]
    if not rep["complete"]:
        L += ["**INCOMPLETE INPUT (fail closed):** " + "; ".join(f"{k} {v}" for k, v in rep["missing_counts"].items()
                                                                  if v), ""]
    work = [j for j in rep["joints"] if j["bits"] >= rep["params"]["min_bits"] and j["verdict"] != "ok"]
    if not work:
        L.append("No > 32 b joint needs work.")
        return "\n".join(L) + "\n"
    groups = collections.OrderedDict()
    for j in sorted(work, key=lambda j: (-j["bits"], j["a"]["inst"])):
        groups.setdefault(joint_class(j), []).append(j)
    L += ["| # | joints | bits (max) | A kit / view (orient, face) | B kit / view (orient, face) | verdict | crossings | "
          "max offset um | re-kit (side) | action |", "|---|---|---|---|---|---|---|---|---|---|"]
    for n, (cls, js) in enumerate(groups.items(), 1):
        j = js[0]
        fx = j.get("fix") or {}
        a, b = j["a"], j["b"]
        def lab(x):
            return (f"{x['kit'] or '(no kit) ' + x['module']}{' [CLOSED]' if x['routed'] else ''}"
                    f"{'' if x['order_defined'] else ' [no order]'} ({x['orient']}, {x['master_face']})")
        L.append(f"| {n} | {len(js)} | {max(x['bits'] for x in js)} | {lab(a)} | {lab(b)} | {j['verdict']}"
                 f"{' mirrored' if j['mirrored'] else ''} | {j['name_wired_crossings']} / {j['max_crossings']} | "
                 f"{j['max_offset_um']} | {fx.get('kit') or fx.get('module')} ({fx.get('side')}) | "
                 f"{'; '.join(fx.get('actions', []))} |")
    L += ["", "## Per-class prescription (first joint of each class; ports of the re-kit side)", ""]
    for n, (cls, js) in enumerate(groups.items(), 1):
        j = js[0]
        fx = j.get("fix") or {}
        insts = ", ".join(f"{x['a']['inst']}|{x['b']['inst']}" for x in js[:6]) + (" ..." if len(js) > 6 else "")
        L.append(f"{n}. `{fx.get('kit') or fx.get('module')}` ({fx.get('master_instances')} die instances"
                 f"{', CLOSED' if fx.get('routed') else ''}) joints: {insts}")
        for p, r in list((fx.get("ports") or {}).items())[:12]:
            L.append(f"   - `{p}` {r['bits']} b: pin_range {r['pin_range']}"
                     f"{', pin_order_desc' if r['pin_order_desc'] else ''}{'' if r['monotonic'] else ' (NOT monotonic)'}")
    conf = rep.get("conflicts") or []
    if conf:
        L += ["", "## Conflicts (same kit port prescribed differently: needs a mirrored variant master)", ""]
        for c in conf[:40]:
            L.append(f"- `{c['kit']}` `{c['port']}`: {c['variants']}")
    return "\n".join(L) + "\n"


def conflicts(joints):
    seen = collections.defaultdict(set)
    for j in joints:
        fx = j.get("fix")
        if not fx or not fx.get("kit"):
            continue
        for p, r in fx["ports"].items():
            seen[(fx["kit"], p)].add((tuple(round(x, 1) for x in r["pin_range"]), r["pin_order_desc"]))
    return [dict(kit=k, port=p, variants=sorted(v)) for (k, p), v in sorted(seen.items()) if len(v) > 1]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--die", required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--verilog", required=True)
    ap.add_argument("--place", action="append", required=True)
    ap.add_argument("--lef", action="append", required=True)
    ap.add_argument("--status", default="")
    ap.add_argument("--lef-comment-status", action="store_true", help="also read routed status from LEF comments")
    ap.add_argument("--orig-netlist", default="")
    ap.add_argument("--kit-root", default=str(HERE.parents[1]))
    ap.add_argument("--gap-um", type=float, default=5.0)
    ap.add_argument("--face-tol-um", type=float, default=3.0)
    ap.add_argument("--tol-um", type=float, default=2.0)
    ap.add_argument("--min-bits", type=int, default=33)
    ap.add_argument("--source-note", action="append", default=[])
    ap.add_argument("--out", required=True)
    ap.add_argument("--handoff", default="")
    ap.add_argument("--lead", default="die lead")
    a = ap.parse_args(argv)
    macros = read_lef(lef_files(a.lef))
    net = Netlist(_open(a.verilog).read())
    place = read_place(a.place)
    status, kind = load_status(a.status)
    if a.lef_comment_status or kind in (None, "lef_comments"):
        for m, v in lef_comment_status(macros).items():
            status.setdefault(m, v)
    orig = {}
    if a.orig_netlist:
        on = Netlist(_open(a.orig_netlist).read())
        orig = {i: m for i, (m, _) in on.instances.items()}
    kits = Kits(a.kit_root)
    joints, missing, sides = audit(net, place, macros, status, kits, orig, a.gap_um, a.face_tol_um, a.tol_um,
                                   a.min_bits)
    for j in joints:
        for t in ("a", "b"):
            x = j[t]
            if x["source"] == ["standin_lef"] and x["kit"]:
                missing["port_not_in_kit"].setdefault(x["kit"], sorted({p[0 if t == 'a' else 1] for p in j["ports"]}))
    mc = {k: len(v) for k, v in missing.items()}
    # a port the die connects but the LEF lacks / sizes differently fails the audit closed, except a 1-bit pin
    # (clock / reset / strap: never part of a > 32 b joint), which is listed but does not block
    complete = not (missing["no_lef"] or missing["no_place"]
                    or any(max(w[2], w[3]) > 1 for w in missing["width_mismatch"]))
    rep = dict(schema=SCHEMA, tool="tools/hier_contract/abutted_joint_audit.py", die=a.die,
               source=dict(label=a.label, verilog=a.verilog, place=a.place, lef=a.lef, status=a.status,
                           orig_netlist=a.orig_netlist, kit_rev=kits.rev, notes=a.source_note),
               params=dict(gap_um=a.gap_um, face_tol_um=a.face_tol_um, tol_um=a.tol_um, min_bits=a.min_bits),
               counts=dict(instances=len(net.instances), hard_children=len(sides), macros=len(macros),
                           placed=len(place), routed_masters=sum(1 for v in status.values() if v.get("routed")),
                           kits=len(kits.spec)),
               complete=complete, missing_counts=mc,
               missing={k: (dict(list(v.items())[:200]) if isinstance(v, dict) else v[:200]) for k, v in missing.items()},
               summary=summarise(joints, a.min_bits),
               conflicts=conflicts([j for j in joints if j["bits"] >= a.min_bits]),
               joints=sorted(joints, key=lambda j: (-j["bits"], j["a"]["inst"], j["b"]["inst"])))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rep, indent=1) + "\n")
    if a.handoff:
        Path(a.handoff).write_text(handoff_md(a.die, a.lead, rep))
    s = rep["summary"]
    print(f"ABUTTED_JOINTS {a.die} joints {s['joints']} gt32 {s['joints_gt32']} order_undefined {s['order_undefined']} "
          f"reversed {s['reversed']} mirrored {s['mirrored']} needs_work {s['needs_work']} verdicts {s['verdicts']} "
          f"complete {complete} missing {mc}")
    return 0 if complete else 3


if __name__ == "__main__":
    sys.exit(main())
