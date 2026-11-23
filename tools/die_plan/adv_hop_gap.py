#!/usr/bin/env python3
"""adv_hop_gap.py -- PRECHECK-R2 static advisory ADV-HOP-GAP (COORD 11-23 from FABLE-RC-S81 RC-GAP; an estimator, never a gate).

An internal ONE-CYCLE hop with no station on it: the bound wrapper RTL connects a register end (hard-core pin, seated
ot_dp_* stage / face register) to another register end directly (only wires / assign logic between, no ot_dp_* stage),
and the two ends sit more than the reach (cbc_rules.REACH_GATE_UM, 405 um) apart in the plan.  Reach is checked on
station chains (precheck REACH) and ports, not on these direct internal nets.  FABLE-RC-S81 (11-23 01:00) cross-type
setup cases: S81 gunit__t1 -2168 (u_l1 -> g_l1f[k].u_f, no stations), bk_sel__t2 -604 (u_core.lp_q -> u_vm.r 584 um),
seqhost__t1 -480 (u_l2.vlg -> cw_d, 1476 um), slice *_C xg/xf legs -495..-1304, col_h10 station merge.

Inputs (read only):
  - strict bind OUT (adv_port_pin.find_bind_out: kw bind_out, beside the plan, or the tree's plan_of_record native_bind):
    bind_report.json types.<T>.module, rtl/<module>.sv + rtl/<module>__pv*.sv (param variants of the type).
    Parsed by regex: "// as-built <path>" + instance blocks (.port(expr)), single-line ot_dp_* instances, assign A = B.
  - plan partition_types.<T>: hard_cores[] (inst, module, origin_um, outline_um, orient, pins_file -> core pin json
    {pins: [{name, x, y}]} in the core frame), relay_sites {"<inst>/<pin>": [x, y]} (seated stage / face registers),
    buses[] (face windows: u_bin_<bus> / u_bout_<bus> face registers default to the window centre on the face).
Register ends:
  HARD    a hard-core pin (as-built instance matched to hard_cores by module + inst suffix), position = pin-bit centroid;
  NESTED  a soft as-built leaf whose plan hard cores sit inside it (gunit g_l1f[k].u_l1f -> u_alo/u_f/u_ahi): its port P is
          the nested core pin P (same name);
  STAGE   an ot_dp_st / ot_dp_dly / ot_dp_dly_keep instance with a relay_sites seat, or a u_bin_/u_bout_ face register.
  A net through an unseated ot_dp_* stage (lane pad, relay_depth u_y_xd_*, ft station) or a soft leaf without nested
  cores ends the trace (not judged).  Clock / reset / landing nets are skipped.
Findings:
  HOP     direct hop > reach: len (Manhattan, um), stations needed = ceil(len / reach) - 1, est over = (len - reach) *
          PS_PER_UM (0.6845 ps/um: 833 ps over 1,217 um of repeated wire, the S81 xg/xf 1.2-1.5 ns / ~1 mm legs);
  HOP-SITE a HOP with a seated plan stage (relay_sites) on one end where a seat within reach of every judged end of
          that stage exists (for an unseated u_bin_/u_bout_ face register: a point on its bus window): re-seat / pin it
          there (0 stations) instead of adding stations.
  CDC-SYNC / CLOCK-UNKNOWN  (FABLE-RC-S81 11-23) clock domains come from the wrapper's clock-port connections: clk and
          every clk_t<i> / clk_c<k> tap are one domain, io_pma_rck*, fclk_* and any other clock net are their own.  A HOP
          / SOFT row whose two instances share no clock is CDC-SYNC (a synchroniser arc, 0 stations, kept for review);
          when one instance has several clocks and they overlap, the register's clock is not known from the wrapper:
          CLOCK-UNKNOWN (stations as if same clock).  Reset arcs are never judged here (reset ports are skipped).
  SOFT-GAP / SOFT-SITE  a soft as-built leaf with no plan seat (e.g. col u_y_xa_* / u_y_cc_* relays, slice xg): the
          free placer puts it near the bit-weighted centroid of its judged ends.  A leg from the centroid to a hard pin
          > reach is SOFT-SITE when SOME site is within reach of every end (minimax site in u = x + y, v = x - y; fix =
          pin the leaf there, 0 stations; FAM-S81-COL-H10-R4: 76 col_h10 legs 408-455 um) and SOFT-GAP when none is
          (len = distance from the best seat, real stations needed).
  Bit slices are resolved per bit through wiring assigns (concats, slices, replication, sel ? {..} : {..}), so a sink
          slice of a concat bus is driven only by the cores in its slice (S81 svc hcore -> h4: was ~8x over-counted).
  DUPSTN  two or more ot_dp_dly stations whose d is the same source bits through alias assigns (u_y_xd_u_e11_u_e_* and
          u_y_xd_u_e11_u_w_* both = w_u_e11_0_Y[..]) feeding different sinks: synthesis merges them unless the kit keeps
          them (OT_KEEP_WIRES += ot_dp_dly:r), and then one station drives both sinks (col_h10 FABLE-RC-S81 RC-GAP 1/3).
          len = the sink-to-sink distance the merged station crosses.

    findings(raw, plan_path, tree=None, bind_out=None, **kw) -> ["WARN ADV-HOP-GAP ..."]
    rows(raw, plan_path, tree=None, bind_out=None, **kw) -> (rows, stats); row = dict(type, family, kind, src, dst, len_um,
                                                                                    stations, over_ps, bits)
"""
import glob
import json
import math
import os
import re
import time

CHECK = "ADV-HOP-GAP"
REACH_UM = 405.0
PS_PER_UM = 0.6845
MAX_LINES = 20
DUP_MIN_UM = 20.0           # DUPSTN: sinks closer than this are one place (merge harmless)
TRACE_DEPTH = 8
STAGE_MOD = re.compile(r"ot_dp_(?:st|dly|dly_keep|dly_k|pipe|reg)\b")
SKIP_MOD = re.compile(r"ot_dp_(?:rrelay|landing|clk_landing|rst|cland)|ot_dp_landing|ot_dp_clk")
SKIP_PORT = re.compile(r"^(?:clk\w*|ck|rst\w*|arst\w*|\w*_rst_n|rst_raw_n|scan\w*|se|test\w*)$")
SKIP_NET = re.compile(r"^(?:clk\w*|rst_\w*|arst\w*|cland_\w*|fclk\w*|S_\w+)$")
KEYWORDS = {"wire", "logic", "reg", "assign", "input", "output", "signed"}

_INST = re.compile(r"^[ \t]*([A-Za-z_]\w*)[ \t]*(?:#[ \t]*\((?:[^()]|\([^()]*\))*\))?[ \t]*(\\?[A-Za-z_][\w$.\[\]\\]*)[ \t]*\(", re.M)
_CONN = re.compile(r"\.([A-Za-z_]\w*)\s*\(([^()]*)\)")
_ASSIGN = re.compile(r"^[ \t]*assign[ \t]+([^=;]+?)[ \t]*=[ \t]*([^;]+);", re.M)
_ASBUILT = re.compile(r"^[ \t]*//[ \t]*as-built[ \t]+(\S+)[ \t]*$", re.M)
_IDENT = re.compile(r"(?<![\w'$])([A-Za-z_]\w*)(?:\s*\[\s*(\d+)\s*(?::\s*(\d+)\s*)?\])?")
_PIN = re.compile(r"^(.*?)(?:\[(\d+)\])?$")


def family(t):
    return re.split(r"__(?:t\d+|cl[0-9a-f]{6,}|pv[0-9a-f]{6,})", t)[0]


def _xy(p):
    try:
        return float(p[0]), float(p[1])
    except (TypeError, ValueError, IndexError, KeyError):
        return None


def _man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _f(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


def _orient(o, w, h, x, y):
    return {"MX": (x, h - y), "MY": (w - x, y), "R180": (w - x, h - y)}.get(str(o or "R0"), (x, y))


def pin_xy(face, win, outline):
    try:
        c = (float(win[0]) + float(win[1])) / 2.0
        W, H = float(outline[0]), float(outline[1])
    except (TypeError, ValueError, IndexError):
        return None
    return {"N": (c, H), "S": (c, 0.0), "W": (0.0, c), "E": (W, c)}.get(str(face))


# ----------------------------------------------------------------------------------------------- bind out / rtl
def _find_bind_out(raw, plan_path, tree, bind_out):
    try:
        import importlib
        import sys
        here = os.path.dirname(os.path.abspath(__file__))
        if here not in sys.path:
            sys.path.insert(0, here)
        pp = importlib.import_module("adv_port_pin")
        return pp.find_bind_out(raw, plan_path, tree, bind_out)
    except Exception:  # noqa: BLE001
        pass
    for c in ([bind_out] if bind_out else []) + ([os.path.join(tree, "physical", "die_plan", str(raw.get("die", {}).get("name") if isinstance(raw.get("die"), dict) else raw.get("die")), "plan_of_record", "native_bind", "out")] if tree else []):
        if c and os.path.isfile(os.path.join(c, "bind_report.json")):
            return c
    return None


def parse_wrapper(text):
    """-> (insts {name: (module, path or None, {port: expr})}, assigns [(lhs, rhs)])."""
    asb = {}
    for m in _ASBUILT.finditer(text):
        asb[m.end()] = m.group(1)
    ends = sorted(asb)
    insts = {}
    for m in _INST.finditer(text):
        mod, name = m.group(1), m.group(2).lstrip("\\")
        if mod in KEYWORDS or mod == "module":
            continue
        # body up to the matching ");"
        i, depth, n = m.end(), 1, len(text)
        j = i
        while j < n and depth:
            c = text[j]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            j += 1
        body = text[i:j - 1]
        conns = {p: e.strip() for p, e in _CONN.findall(body)}
        if not conns:
            continue
        path = None
        # an as-built comment ends on the line just before the instance
        k = _bisect_le(ends, m.start())
        if k is not None and m.start() - k <= 2:
            path = asb[k]
        insts[name] = (mod, path, conns)
    assigns = [(a.strip(), b.strip()) for a, b in _ASSIGN.findall(text)]
    return insts, assigns


_DECL = re.compile(r"^[ \t]*(?:input|output|inout|wire|logic|reg)\b(?:[ \t]+(?:wire|logic|reg|signed))*[ \t]*"
                   r"(?:\[\s*(\d+)\s*:\s*(\d+)\s*\])?[ \t]*([A-Za-z_][\w \t,]*?)[ \t]*[;,]?[ \t]*(?://.*)?$", re.M)
_SLICE = re.compile(r"^([A-Za-z_]\w*)\s*(?:\[\s*(\d+)\s*(?::\s*(\d+)\s*)?\])?$")
_LIT = re.compile(r"^(\d+)\s*'\s*[sS]?[bBdDhHoO]\s*[0-9a-fA-FxXzZ_?]+$")
BITS_MAX = 1 << 16
EMPTY = frozenset()
_SIMPLE = re.compile(r"^[A-Za-z_]\w*\s*(?:\[\s*\d+\s*(?::\s*\d+\s*)?\])?$")


def decl_widths(text):
    """{net: (lsb, msb)} of the wrapper's port / wire declarations."""
    out = {}
    for m in _DECL.finditer(text):
        hi, lo = m.group(1), m.group(2)
        rng = (0, 0) if hi is None else (min(int(hi), int(lo)), max(int(hi), int(lo)))
        for nm in m.group(3).split(","):
            nm = nm.strip()
            if re.fullmatch(r"[A-Za-z_]\w*", nm) and nm not in KEYWORDS:
                out[nm] = rng
    return out


def _split_top(s, sep):
    """split s on sep at bracket depth 0."""
    out, d, cur = [], 0, []
    for ch in s:
        if ch in "([{":
            d += 1
        elif ch in ")]}":
            d -= 1
        if ch == sep and d == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    out.append("".join(cur))
    return out


def _closes_at_end(e):
    d = 0
    for i, ch in enumerate(e):
        d += ch in "([{"
        d -= ch in ")]}"
        if d == 0 and i < len(e) - 1:
            return False
    return True


def _split_bitwise(e):
    """operands of top-level binary | & ^ (not || && ^~ reductions), else [e]."""
    out, d, cur, i, n = [], 0, [], 0, len(e)
    while i < n:
        ch = e[i]
        if ch in "([{":
            d += 1
        elif ch in ")]}":
            d -= 1
        if d == 0 and ch in "|&^":
            nxt = e[i + 1] if i + 1 < n else ""
            prev = "".join(cur).strip()
            if nxt == ch or nxt == "~" or not prev or prev[-1] in "~!|&^(":
                return [e]                         # logical || / &&, xnor, or a unary reduction: not bitwise
            out.append(prev)
            cur = []
            i += 1
            continue
        cur.append(ch)
        i += 1
    if not out:
        return [e]
    out.append("".join(cur).strip())
    return out


def _strip_parens(e):
    e = e.strip()
    while e.startswith("(") and e.endswith(")"):
        d = 0
        for i, ch in enumerate(e):
            d += ch == "("
            d -= ch == ")"
            if d == 0 and i < len(e) - 1:
                return e
        e = e[1:-1].strip()
    return e


def _ternary(e):
    """(sel, a, b) of a top-level sel ? a : b, else None."""
    d, q = 0, -1
    for i, ch in enumerate(e):
        if ch in "([{":
            d += 1
        elif ch in ")]}":
            d -= 1
        elif d == 0 and ch == "?" and q < 0:
            q = i
        elif d == 0 and ch == ":" and q >= 0:
            return e[:q], e[q + 1:i], e[i + 1:]
    return None


def _lsb(segs):
    """MSB-first [(w, srcs)] -> LSB-first [(off, w, srcs)]."""
    out, off = [], 0
    for w, srcs in reversed(segs):
        out.append((off, w, srcs))
        off += w
    return out


def _cut(src, k):
    """a source shifted k bits up inside its element (bitwise sources move, whole-range ones do not)."""
    return ("b", src[1], src[2] + k) if src[0] == "b" else src


def _align(parts):
    """bitwise union of MSB-first segment lists (right aligned, the short ones zero-extended)."""
    ls = [_lsb(x) for x in parts]
    n = max((x[-1][0] + x[-1][1]) if x else 0 for x in ls)
    cuts = {0, n}
    for x in ls:
        for off, w, _ in x:
            cuts.add(off)
            cuts.add(off + w)
    cuts = sorted(c for c in cuts if c <= n)
    out = []
    for lo, hi in zip(cuts, cuts[1:]):
        srcs = set()
        for x in ls:
            for off, w, ss in x:
                if off <= lo < off + w:
                    srcs.update(_cut(q, lo - off) for q in ss)
                    break
        out.append((hi - lo, frozenset(srcs)))
    out.reverse()
    return out


def _whole(expr):
    """frozenset of whole-range sources ("a", net, lo, hi) of every ident of a logic expression."""
    return frozenset(("a", nm, lo, hi) for nm, lo, hi in _idents(expr))


def expr_segs(expr, widths, depth=0):
    """MSB-first [(width, frozenset(src))] of a connection / assign expression, or None when it is not a wiring
    expression.  src = ("b", net, lsb): element bit i is net bit lsb + i; ("a", net, lo, hi): every element bit depends
    on the whole range (lo None = the whole net).  Handles idents, [i] / [h:l] slices, {a, b} concats, {N{x}}, sized
    literals, bitwise | & ^ ~ (per bit), and sel ? A : B (per bit of both arms, sel whole)."""
    e = _strip_parens(expr)
    if not e or depth > 8:
        return None
    if e[0] != "{" and _SIMPLE.match(e):           # fast path: a plain ident / slice
        m = _SLICE.match(e)
        nm = m.group(1)
        if nm in KEYWORDS:
            return None
        if m.group(2) is None:
            if nm not in widths:
                return None
            lo, hi = widths[nm]
        else:
            h = int(m.group(2))
            l_ = int(m.group(3)) if m.group(3) is not None else h
            lo, hi = min(h, l_), max(h, l_)
        return [(hi - lo + 1, frozenset((("b", nm, lo),)))]
    t = _ternary(e) if "?" in e else None
    if t:
        x, y = expr_segs(t[1], widths, depth + 1), expr_segs(t[2], widths, depth + 1)
        if x is None or y is None:
            return None
        sel = _whole(t[0])
        return [(w, ss | sel) for w, ss in _align([x, y])]
    ops = _split_bitwise(e) if ("|" in e or "&" in e or "^" in e) else (e,)
    if len(ops) > 1:
        parts = [expr_segs(x, widths, depth + 1) for x in ops]
        if any(x is None for x in parts):
            return None
        return _align(parts)
    if e.startswith("~") and not e.startswith(("~&", "~|", "~^")):
        return expr_segs(e[1:], widths, depth + 1)
    if e.startswith("{") and e.endswith("}") and _closes_at_end(e):
        inner = e[1:-1].strip()
        m = re.match(r"^(\d+)\s*(\{.*\})$", inner, re.S)
        if m:
            x = expr_segs(m.group(2), widths, depth + 1)
            return None if x is None or int(m.group(1)) * len(x) > BITS_MAX else x * int(m.group(1))
        out = []
        for part in _split_top(inner, ","):
            x = expr_segs(part, widths, depth + 1)
            if x is None:
                return None
            out.extend(x)
        return out
    m = _LIT.match(e)
    if m:
        return [(int(m.group(1)), EMPTY)]
    m = _SLICE.match(e)
    if m:
        nm = m.group(1)
        if nm in KEYWORDS:
            return None
        if m.group(2) is None:
            if nm not in widths:
                return None
            lo, hi = widths[nm]
        else:
            h = int(m.group(2))
            l_ = int(m.group(3)) if m.group(3) is not None else h
            lo, hi = min(h, l_), max(h, l_)
        return [(hi - lo + 1, frozenset((("b", nm, lo),)))]
    return None


def expr_bits(expr, widths):
    """MSB-first [frozenset((net, bit or None))] (test / debug view of expr_segs)."""
    sg = expr_segs(expr, widths)
    if sg is None:
        return None
    out = []
    for w, ss in sg:
        for i in range(w - 1, -1, -1):
            out.append(frozenset((q[1], q[2] + i) if q[0] == "b" else (q[1], None) for q in ss))
    return out


class SegResolver:
    """register ends (inst, port) -> bits driving a net range, through wiring assigns, at segment granularity."""

    def __init__(self, assigns, widths, drv, skip):
        self.widths, self.drv, self.skip = widths, drv, skip
        self.by_net, self.maps, self.memo, self.skipc = {}, {}, {}, {}
        for lhs, rhs in assigns:
            m = _SLICE.match(lhs.strip())
            names = [m.group(1)] if m else [nm for nm, lo, hi in _idents(lhs)]
            for nm in names:
                self.by_net.setdefault(nm, []).append((lhs, rhs))

    def _map(self, nm):
        """[(lo, hi, srcs)] of net nm (lo None = whole net) from the assigns that drive it."""
        mp = self.maps.get(nm)
        if mp is not None:
            return mp
        mp = []
        for lhs, rhs in self.by_net.get(nm, ()):
            L = expr_segs(lhs, self.widths)
            R = expr_segs(rhs, self.widths)
            if L is None or any(len(ss) != 1 or next(iter(ss))[0] != "b" for w, ss in L):
                mp.append((None, None, _whole(rhs)))   # LHS not a plain net / slice / concat: whole net, all of RHS
                continue
            if R is None:
                R = [(sum(w for w, _ in L), _whole(rhs))]
            ll, rl = _lsb(L), _lsb(R)
            for off, w, ss in ll:
                q = next(iter(ss))
                if q[1] != nm:
                    continue
                for roff, rw, rss in rl:
                    lo, hi = max(off, roff), min(off + w, roff + rw)
                    if lo < hi:
                        mp.append((q[2] + lo - off, q[2] + hi - 1 - off, frozenset(_cut(x, lo - roff) for x in rss)))
        self.maps[nm] = mp
        return mp

    def _width(self, nm, lo, hi):
        if lo is not None:
            return hi - lo + 1
        w = self.widths.get(nm)
        return (w[1] - w[0] + 1) if w else 1

    def resolve(self, nm, lo, hi, depth=0):
        """{(inst, port): bits} driving nm[lo:hi] (lo None = whole net)."""
        key = (nm, lo, hi)
        r = self.memo.get(key)
        if r is not None:
            return r
        self.memo[key] = {}                            # cycle guard
        res = {}
        if self.skip.match(nm):
            pass
        elif nm in self.drv:
            for dn, dp, dlo, dhi in self.drv[nm]:
                if lo is None or dlo is None:
                    n = self._width(nm, lo, hi) if dlo is None else dhi - dlo + 1
                else:
                    n = min(hi, dhi) - max(lo, dlo) + 1
                if n > 0:
                    res[(dn, dp)] = res.get((dn, dp), 0) + n
        elif depth < 4 * TRACE_DEPTH:
            for mlo, mhi, srcs in self._map(nm):
                if mlo is None or lo is None:
                    olo, ohi = (mlo, mhi) if lo is None else (lo, hi)
                    if olo is None:
                        olo, ohi = 0, self._width(nm, None, None) - 1
                    base = olo if mlo is None else mlo
                else:
                    olo, ohi = max(lo, mlo), min(hi, mhi)
                    base = mlo
                    if olo > ohi:
                        continue
                n = ohi - olo + 1
                for q in srcs:
                    if q[0] == "b":
                        sub = self.resolve(q[1], q[2] + olo - base, q[2] + ohi - base, depth + 1)
                    else:
                        sub = self.resolve(q[1], q[2], q[3], depth + 1)
                    for k, v in sub.items():
                        res[k] = res.get(k, 0) + min(v, n)
        self.memo[key] = res
        return res

    def sources(self, expr):
        """[(inst, port, 0, nbits - 1)] of the register ends driving a sink connection expression."""
        sg = expr_segs(expr, self.widths)
        if sg is None:
            sg = [(1, _whole(expr))]
        cnt = {}
        for w, ss in sg:
            for q in ss:
                sub = self.resolve(q[1], q[2], q[2] + w - 1) if q[0] == "b" else self.resolve(q[1], q[2], q[3])
                for k, v in sub.items():
                    cnt[k] = cnt.get(k, 0) + (min(v, w) if q[0] == "b" else v)
        return [(k[0], k[1], 0, max(1, n) - 1) for k, n in cnt.items()]


def _bisect_le(arr, x):
    import bisect
    i = bisect.bisect_right(arr, x)
    return arr[i - 1] if i else None


def _idents(expr):
    out = []
    for m in _IDENT.finditer(expr):
        nm = m.group(1)
        if nm in KEYWORDS:
            continue
        # skip sized literals like 1'b0 (the ' guard handles b0), and bare numbers are not identifiers
        hi, lo = m.group(2), m.group(3)
        if hi is None:
            out.append((nm, None, None))
        else:
            h = int(hi)
            l_ = int(lo) if lo is not None else h
            out.append((nm, min(h, l_), max(h, l_)))
    return out


# ----------------------------------------------------------------------------------------------- plan geometry
class Pins:
    def __init__(self, plan_path, tree, die):
        self.bases = []
        if tree and die:
            self.bases.append(os.path.join(tree, "physical", "die_plan", str(die)))
        if plan_path:
            pd = os.path.dirname(os.path.abspath(plan_path))
            self.bases += [pd, os.path.dirname(pd), os.path.dirname(os.path.dirname(pd))]
        if tree:
            self.bases.append(tree)
        self.cache = {}

    def get(self, pf):
        if not pf:
            return None
        if pf in self.cache:
            return self.cache[pf]
        d = None
        for b in self.bases:
            p = os.path.join(b, pf)
            if os.path.isfile(p):
                try:
                    with open(p) as f:
                        doc = json.load(f)
                    d = {}
                    for q in doc.get("pins") or []:
                        m = _PIN.match(str(q.get("name", "")))
                        x, y = q.get("x"), q.get("y")
                        if m and x is not None and y is not None:
                            d.setdefault(m.group(1), []).append((float(x), float(y)))
                except (OSError, ValueError, TypeError):
                    d = None
                break
        self.cache[pf] = d
        return d


def core_pin_pos(core, pins, port):
    """centroid of the port's pins in the type frame, or None."""
    if not pins or port not in pins:
        return None
    o, s = _xy(core.get("origin_um")), _xy(core.get("outline_um"))
    if not o or not s:
        return None
    pts = pins[port]
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    x, y = _orient(core.get("orient"), s[0], s[1], cx, cy)
    return (o[0] + x, o[1] + y)


def _norm_path(p):
    return re.sub(r"\[(\d+)\]", r"_\1", p).replace(".", "_")


def match_cores(t, insts):
    """{as-built instance name: plan hard core} by module + the longest inst suffix; plus {soft name: [nested cores]}."""
    cores = [c for c in t.get("hard_cores") or [] if isinstance(c, dict) and c.get("inst")]
    by_mod = {}
    for c in cores:
        by_mod.setdefault(str(c.get("module")), []).append(c)
    hard, used = {}, set()
    paths = {n: (v[0], v[1]) for n, v in insts.items() if v[1]}
    for n, (mod, path) in paths.items():
        cands = by_mod.get(mod) or []
        best, bl = None, -1
        for c in cands:
            ci = str(c["inst"])
            if id(c) in used:
                continue
            if ci == path:
                best, bl = c, 10 ** 6
                break
            tail = ci.split(".", 1)[1] if "." in ci else ci
            if path.endswith("." + tail) or path == tail:
                if len(tail) > bl:
                    best, bl = c, len(tail)
        if best is None and len(cands) == 1 and sum(1 for v in paths.values() if v[0] == mod) == 1:
            best = cands[0]
        if best is not None:
            hard[n] = best
            used.add(id(best))
    nested = {}
    for n, (mod, path) in paths.items():
        if n in hard:
            continue
        tail = path.split(".", 1)[1] if "." in path else path
        kids = []
        for c in cores:
            ci = str(c["inst"])
            ct = ci.split(".", 1)[1] if "." in ci else ci
            if id(c) not in used and (ci.startswith(path + ".") or ct.startswith(tail + ".")):
                kids.append(c)
        if kids:
            nested[n] = kids
    return hard, nested


# ----------------------------------------------------------------------------------------------- the check
def type_rows(tn, t, files, pins, reach, stats):
    ol = t.get("outline_um") or (0, 0)
    rs = t.get("relay_sites") if isinstance(t.get("relay_sites"), dict) else {}
    buses = {b.get("name"): b for b in t.get("buses") or [] if isinstance(b, dict)}
    hops, dups, softhops = {}, {}, {}
    stage_ends = {}                                # seated movable stage -> positions of its judged register ends
    face_seg = {}                                  # unseated face register -> its bus window segment on the face
    planned = planned_ends(t)
    for fp in files:
        try:
            with open(fp, errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        insts, assigns = parse_wrapper(text)
        stats.setdefault("files", 0)
        stats["files"] += 1
        hard, nested = match_cores(t, insts)
        if rs and nested:
            seated = {k.split(".", 1)[0] for k in rs if "." in k.split("/", 1)[0]}
            nested = {k: v for k, v in nested.items() if k not in seated}
        stats["hard"] += len(hard)
        soft = {}                                  # soft leaf -> [(pos, label, bits, dir)] of its judged register ends

        def stage_pos(name):
            for k in (f"{name}/q[0]", f"{name}/q", f"{name}/eq"):
                p = _xy(rs.get(k)) if rs else None
                if p:
                    return p
            m = re.match(r"u_b(?:in|out)_(\w+)$", name)
            if m and m.group(1) in buses:
                b = buses[m.group(1)]
                return pin_xy(b.get("face"), b.get("window_um") or (), ol)
            return None

        # endpoints: (name, port) -> position (or None = unjudged boundary)
        def end_pos(name, port):
            mod, path, conns = insts[name]
            if name in hard:
                c = hard[name]
                return core_pin_pos(c, pins.get(c.get("pins_file")), port), f"{c['inst']}.{port}"
            if name in nested:
                for c in nested[name]:
                    p = core_pin_pos(c, pins.get(c.get("pins_file")), port)
                    if p:
                        return p, f"{c['inst']}.{port}"
                return None, None
            if STAGE_MOD.match(mod):
                p = stage_pos(name)
                return p, (f"{name}" if p else None)
            return None, None

        # drivers: net -> (name, port)
        drv = {}
        for name, (mod, path, conns) in insts.items():
            if SKIP_MOD.match(mod):
                continue
            if STAGE_MOD.match(mod):
                for p in ("q", "eq"):
                    e = conns.get(p)
                    if e:
                        for nm, lo, hi in _idents(e):
                            drv.setdefault(nm, []).append((name, p, lo, hi))
                continue
            flat = "w_" + (name[2:] if name.startswith("u_") else name) + "_"
            for p, e in conns.items():
                if re.fullmatch(r"[A-Za-z_]\w*", e) and e == flat + p:
                    drv.setdefault(e, []).append((name, p, None, None))
        alias = {}
        for lhs, rhs in assigns:
            ids = _idents(lhs)
            if ids:
                alias.setdefault(ids[0][0], []).append(rhs)
        widths = decl_widths(text)
        sources = SegResolver(assigns, widths, drv, SKIP_NET).sources
        cdom = clock_domains(insts, assigns)

        for name, (mod, path, conns) in insts.items():
            if SKIP_MOD.match(mod):
                continue
            stage = bool(STAGE_MOD.match(mod))
            ports = [p for p in conns if (p in ("d", "ea") if stage else not SKIP_PORT.match(p))]
            for p in ports:
                e = conns[p]
                if not stage and e == ("w_" + (name[2:] if name.startswith("u_") else name) + "_" + p):
                    continue                       # this instance's own output
                srcs = sources(e)
                if not srcs:
                    continue
                stats["nets"] += 1
                b, bl = end_pos(name, p)
                for sn, sp, lo, hi in srcs:
                    if sn == name:
                        continue
                    a, al = end_pos(sn, sp)
                    nb = 1 if lo is None else hi - lo + 1
                    cls = clock_class(cdom, sn, name)
                    if a and not b and _is_soft(insts, name, hard, nested):
                        soft.setdefault(name, []).append((a, al, nb, "in", p, cls))
                    if b and not a and _is_soft(insts, sn, hard, nested):
                        soft.setdefault(sn, []).append((b, bl, nb, "out", sp, cls))
                    if not a or not b:
                        continue
                    stats["judged"] += 1
                    d = _man(a, b)
                    for lab_, other in ((al, b), (bl, a)):
                        if lab_ and "." not in lab_ and not cls:
                            stage_ends.setdefault(lab_, []).append(other)
                            fm = re.match(r"u_b(?:in|out)_(\w+)$", lab_)
                            if fm and fm.group(1) in buses and not (rs and any(k.startswith(lab_ + "/") for k in rs)):
                                bb = buses[fm.group(1)]
                                w_ = bb.get("window_um") or ()
                                if len(w_) >= 2:
                                    face_seg[lab_] = (pin_xy(bb.get("face"), (w_[0], w_[0]), ol),
                                                      pin_xy(bb.get("face"), (w_[1], w_[1]), ol))
                    if d > reach and not _is_planned(planned, al, bl):
                        k = (al, bl)
                        if k not in hops or hops[k][0] < d:
                            hops[k] = (d, a, b, cls)
        # SOFT: a soft leaf with no plan seat sits (placer-like) at the bit-weighted centroid of its judged register ends
        seated = {k.split(".", 1)[0] for k in rs if "." in k.split("/", 1)[0]} if rs else set()
        for sn, ends in soft.items():
            if sn in seated:                       # the plan seats this soft core's registers (relay_sites): not estimated
                continue
            agg = {}
            for pos, lab, nb, dr, port, cls in ends:
                r = agg.setdefault((lab, dr, port), [pos, 0, cls])
                r[1] += nb
            tot = sum(v[1] for v in agg.values())
            if len(agg) < 2 or not tot:
                continue
            cx = sum(v[0][0] * v[1] for v in agg.values()) / tot
            cy = sum(v[0][1] * v[1] for v in agg.values()) / tot
            site, rmin = minimax_site([v[0] for v in agg.values()], ol)
            sp_ = insts[sn][1] or sn
            for (lab, dr, port), (pos, nb, cls) in agg.items():
                d = _man((cx, cy), pos)
                if d <= reach or "." not in lab:  # legs to hard-core pins only (a face leg is the leaf's own I/O flop)
                    continue
                if rmin <= reach:
                    # SOFT-SITE: a site within reach of EVERY end exists; the free placer's centroid is not it -> pin it
                    kind, dd = "SOFT-SITE", d
                    sl = (f"{sp_}.{port} (soft, centroid ({_f(cx)},{_f(cy)}) of {len(agg)} ends; feasible site "
                          f"({_f(site[0])},{_f(site[1])}) within {_f(rmin)} um of every end)")
                else:
                    # SOFT-GAP: no site is within reach of every end: a real gap (stations on the far legs)
                    dd = _man(site, pos)
                    if dd <= reach:
                        continue
                    kind = "SOFT-GAP"
                    sl = (f"{sp_}.{port} (soft, no feasible site: best seat ({_f(site[0])},{_f(site[1])}) is "
                          f"{_f(rmin)} um from its farthest end, {len(agg)} ends)")
                k = (kind, lab, sl) if dr == "in" else (kind, sl, lab)
                if k not in softhops or softhops[k][0] < dd:
                    softhops[k] = (dd, nb, cls)
        # DUPSTN: ot_dp_dly stations with identical resolved d bits
        groups = {}
        for name, (mod, path, conns) in insts.items():
            if not mod.startswith("ot_dp_dly") or "d" not in conns:
                continue
            ids = _idents(conns["d"])
            if len(ids) != 1:
                continue
            key = _canon(ids[0], alias)
            if key is None:
                continue
            groups.setdefault(key, []).append(name)
        if any(len(v) > 1 for v in groups.values()):
            q_sink = {}
            for name, (mod, path, conns) in insts.items():
                if SKIP_MOD.match(mod) or name not in hard:
                    continue
                for p, e in conns.items():
                    for nm, lo, hi in _idents(e):
                        q_sink.setdefault(nm, []).append((name, p))
            for key, names in groups.items():
                if len(names) < 2:
                    continue
                ends = []
                for n in names:
                    qn = _idents(insts[n][2].get("q", ""))
                    for nm, lo, hi in qn:
                        for sn, sp in q_sink.get(nm, []):
                            pos, lab = end_pos(sn, sp)
                            if pos:
                                ends.append((n, lab, pos))
                if len({e[1].rsplit(".", 1)[0] for e in ends}) < 2:
                    continue
                best = None
                for i in range(len(ends)):
                    for j in range(i + 1, len(ends)):
                        if ends[i][0] == ends[j][0]:
                            continue
                        dd = _man(ends[i][2], ends[j][2])
                        if best is None or dd > best[0]:
                            best = (dd, ends[i], ends[j])
                if best and best[0] >= DUP_MIN_UM:
                    st = re.sub(r"_\d+_\d+$", "", best[1][0])
                    st2 = re.sub(r"_\d+_\d+$", "", best[2][0])
                    pair = tuple(sorted((best[1][1].rsplit(".", 1)[0], best[2][1].rsplit(".", 1)[0])))
                    r = dups.setdefault(pair, [0.0, 0, None])
                    r[1] += len(names)
                    if best[0] > r[0]:
                        r[0], r[2] = best[0], (st, st2, best[1][1], best[2][1])
    rows = []
    reseat = {}
    for nm, pts in stage_ends.items():
        if nm in face_seg:                         # a face register sits on its window: best point along the window
            p0, p1 = face_seg[nm]
            if p0 and p1:
                best = None
                for i in range(65):
                    q = (p0[0] + (p1[0] - p0[0]) * i / 64.0, p0[1] + (p1[1] - p0[1]) * i / 64.0)
                    r = max(_man(q, x) for x in pts)
                    if best is None or r < best[1]:
                        best = (q, r)
                reseat[nm] = best
        elif not nm.startswith(("u_bin_", "u_bout_")):
            reseat[nm] = minimax_site(pts, ol)
    for (al, bl), (d, a, b, cls) in hops.items():
        if cls:
            sync = cls[0] == "CDC-SYNC"
            rows.append(dict(type=tn, family=family(tn), kind=cls[0], was="HOP", src=al, dst=bl, len_um=round(d, 1),
                             stations=0 if sync else int(math.ceil(d / reach)) - 1,
                             over_ps=0 if sync else round((d - reach) * PS_PER_UM), a=a, b=b, clocks=cls[1]))
            continue
        # a seated plan stage (relay_sites) on one end: if some seat is within reach of ALL its ends, re-seat it (0 stations)
        mv = next((x for x in (al, bl) if x in reseat and reseat[x][1] <= reach), None)
        if mv:
            (sx, sy), r = reseat[mv]
            rows.append(dict(type=tn, family=family(tn), kind="HOP-SITE", src=al, dst=bl, len_um=round(d, 1), stations=0,
                             over_ps=0, a=a, b=b, site=f"{mv} -> ({_f(sx)},{_f(sy)}), {_f(r)} um from its farthest of "
                                                      f"{len(stage_ends[mv])} ends"))
            continue
        rows.append(dict(type=tn, family=family(tn), kind="HOP", src=al, dst=bl, len_um=round(d, 1),
                         stations=int(math.ceil(d / reach)) - 1, over_ps=round((d - reach) * PS_PER_UM),
                         a=a, b=b))
    for (kind, al, bl), (d, nb, cls) in softhops.items():
        if cls:
            sync = cls[0] == "CDC-SYNC"
            rows.append(dict(type=tn, family=family(tn), kind=cls[0], was=kind, src=al, dst=bl, len_um=round(d, 1),
                             stations=0 if sync or kind == "SOFT-SITE" else int(math.ceil(d / reach)) - 1,
                             over_ps=0 if sync or kind == "SOFT-SITE" else round((d - reach) * PS_PER_UM), a=None, b=None,
                             clocks=cls[1]))
            continue
        site = kind == "SOFT-SITE"
        rows.append(dict(type=tn, family=family(tn), kind=kind, src=al, dst=bl, len_um=round(d, 1),
                         stations=0 if site else int(math.ceil(d / reach)) - 1,
                         over_ps=0 if site else round((d - reach) * PS_PER_UM), a=None, b=None))
    for (ca, cb), (d, n, ex) in dups.items():
        rows.append(dict(type=tn, family=family(tn), kind="DUPSTN", src=f"{ca} (e.g. {ex[0]}_*)",
                         dst=f"{cb} (e.g. {ex[1]}_*; {n} duplicate stations on shared d)", len_um=round(d, 1),
                         stations=0, over_ps=round(d * PS_PER_UM), a=None, b=None))
    return rows


CLOCK_PORT = re.compile(r"^(?:\w*clk\w*|ck\w*|\w*_?rck\w*|\w*_?tck\w*)$")
MAIN_CLOCK = re.compile(r"^clk(?:_[tc]\d+)?$")


def clock_domains(insts, assigns):
    """{inst: frozenset(domain)} from the clock-port connections of the wrapper.  clk and every clk_t<i> / clk_c<k> tap
    are ONE domain ("clk"); any other clock root (io_pma_rck*, fclk_*, an instance-driven clock net) is its own."""
    al = {}
    for lhs, rhs in assigns:
        m = _SLICE.match(lhs.strip())
        if m:
            al.setdefault(m.group(1), []).append(rhs)

    def roots(expr, depth=0, seen=None):
        seen = set() if seen is None else seen
        out = set()
        for nm, lo, hi in _idents(expr):
            if nm in seen:
                continue
            seen.add(nm)
            if nm in al and depth < TRACE_DEPTH and not MAIN_CLOCK.match(nm):
                for r in al[nm]:
                    out |= roots(r, depth + 1, seen)
            else:
                out.add("clk" if MAIN_CLOCK.match(nm) else nm)
        return out

    dom = {}
    for name, (mod, path, conns) in insts.items():
        flat = "w_" + (name[2:] if name.startswith("u_") else name) + "_"
        ds = set()
        for p, e in conns.items():
            if CLOCK_PORT.match(p) and e != flat + p:
                ds |= roots(e)
        dom[name] = frozenset(ds)
    return dom


def clock_class(dom, a, b):
    """None (same domain / no information), ("CDC-SYNC", note) when the two instances share no clock, or
    ("CLOCK-UNKNOWN", note) when one has several clocks and the wrapper does not say which one the register uses."""
    da, db = dom.get(a) or EMPTY, dom.get(b) or EMPTY
    if not da or not db or (da == db and len(da) == 1):
        return None
    note = f"clocks {'+'.join(sorted(da))} -> {'+'.join(sorted(db))}"
    return ("CLOCK-UNKNOWN" if da & db else "CDC-SYNC", note)


def minimax_site(pts, outline=None):
    """(site, r): the point whose largest Manhattan distance to pts is smallest (L1 balls are squares in u = x + y,
    v = x - y, so r = max(u range, v range) / 2), clamped into the outline; r is the largest distance from that site."""
    us = [p[0] + p[1] for p in pts]
    vs = [p[0] - p[1] for p in pts]
    u, v = (max(us) + min(us)) / 2.0, (max(vs) + min(vs)) / 2.0
    x, y = (u + v) / 2.0, (u - v) / 2.0
    try:
        x = min(max(x, 0.0), float(outline[0]))
        y = min(max(y, 0.0), float(outline[1]))
    except (TypeError, ValueError, IndexError):
        pass
    return (x, y), max(_man((x, y), p) for p in pts)


def planned_ends(t):
    """[(set of end tokens A, set B)] of planned station rows (internal_stations launch/capture, ft_slots): a hop whose two
    ends match one row is a planned station chain (REACH / PHANTOM-STATION judge it), not a gap."""
    out = []
    for st in t.get("internal_stations") or []:
        if not isinstance(st, dict):
            continue
        conn = str(st.get("conn", ""))
        sides = []
        for k in ("launch", "capture"):
            v = str(st.get(k) or "")
            toks = {x.strip("(),") for x in re.split(r"[\s,]+", v) if "." in x}
            if not toks or v.startswith("face"):
                toks |= {"u_bin_" + conn[4:], "u_bout_" + conn[4:]} if conn.startswith("bus:") else set()
            m = re.match(r"u_b(?:in|out)_(\w+)", v)
            if m:
                toks.add(m.group(0))
            sides.append(toks)
        if len(sides) == 2 and sides[0] and sides[1]:
            out.append((sides[0], sides[1]))
    return out


def _tok_hit(lab, toks):
    if not lab:
        return False
    for x in toks:
        if lab == x or lab.endswith("." + x) or lab.startswith(x + ".") or x.endswith("." + lab.split(".", 1)[-1]):
            return True
    return False


def _is_planned(planned, a, b):
    for A, B in planned:
        if (_tok_hit(a, A) and _tok_hit(b, B)) or (_tok_hit(a, B) and _tok_hit(b, A)):
            return True
    return False


def _is_soft(insts, name, hard, nested):
    mod = insts[name][0]
    return bool(insts[name][1]) and name not in hard and name not in nested and not STAGE_MOD.match(mod) and not SKIP_MOD.match(mod)


def _canon(ident, alias, depth=0):
    """(base, lo, hi) of a single-ident d through pure alias assigns A = B[h:l] / A = B; None if not resolvable."""
    nm, lo, hi = ident
    while depth < TRACE_DEPTH and nm in alias and len(alias[nm]) == 1:
        ids = _idents(alias[nm][0])
        if len(ids) != 1 or not re.fullmatch(r"\s*[A-Za-z_]\w*\s*(\[[^\]]*\])?\s*", alias[nm][0]):
            break
        bn, blo, bhi = ids[0]
        if blo is not None and lo is not None:
            lo, hi = blo + lo, blo + hi
        elif blo is not None:
            lo, hi = blo, bhi
        nm = bn
        depth += 1
    return (nm, lo, hi)


def rows(raw, plan_path, tree=None, bind_out=None, **kw):
    reach = REACH_UM
    try:
        import sys
        here = os.path.dirname(os.path.abspath(__file__))
        if here not in sys.path:
            sys.path.insert(0, here)
        import cbc_rules as C  # noqa: E402
        reach = float(getattr(C, "REACH_GATE_UM", REACH_UM))
    except Exception:  # noqa: BLE001
        pass
    B = _find_bind_out(raw, plan_path, tree, bind_out)
    stats = dict(types=0, bound=0, hard=0, nets=0, judged=0, bind_out=B, reach=reach)
    if not B:
        return None, stats
    with open(os.path.join(B, "bind_report.json")) as f:
        rep = json.load(f)
    rtypes = rep.get("types") or {}
    die = raw.get("die")
    die = die.get("name") if isinstance(die, dict) else die
    pins = Pins(plan_path, tree, die)
    rtl = os.path.join(B, "rtl")
    used = set()
    for p in raw.get("partitions") or []:
        if isinstance(p, dict):
            used.add(p.get("type"))
    only = kw.get("types")
    out = []
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        if not isinstance(t, dict) or t.get("hard") is True or (used and tn not in used) or (only and tn not in only):
            continue
        stats["types"] += 1
        mod = (rtypes.get(tn) or {}).get("module") or t.get("module") or tn
        files = [os.path.join(rtl, mod + ".sv")] + sorted(glob.glob(os.path.join(rtl, glob.escape(mod) + "__pv*.sv")))
        files = [x for x in files if os.path.isfile(x)]
        if not files:
            continue
        stats["bound"] += 1
        out.extend(type_rows(tn, t, files, pins, reach, stats))
    out.sort(key=lambda r: (-r["len_um"], r["type"]))
    return out, stats


def findings(raw, plan_path, tree=None, bind_out=None, **kw):
    """WARN ADV-HOP-GAP lines (capped) + one summary line; never raises."""
    try:
        t0 = time.time()
        if not isinstance(raw, dict) or not raw.get("partition_types"):
            return [f"WARN {CHECK} not checked: plan has no partition_types"]
        pre = kw.pop("_rows", None)
        rr, st = pre if pre else rows(raw, plan_path, tree, bind_out, **kw)
        if rr is None:
            return [f"WARN {CHECK} not checked: no strict bind out (bind_report.json + rtl/) beside the plan or under the tree"]
        reach = st["reach"]
        cap = int(kw.get("max_lines") or MAX_LINES)
        out = []
        for r in rr[:cap]:
            if r["kind"] == "HOP":
                out.append(f"WARN {CHECK} {r['type']}: HOP {r['src']} -> {r['dst']} is one cycle with no station: "
                           f"{_f(r['len_um'])} um > reach {reach:g} (~{r['over_ps']} ps over at {PS_PER_UM} ps/um); "
                           f"fix: +{r['stations']} station(s) on the hop, or seat the two ends <= {reach:g} um apart")
            elif r["kind"] == "CDC-SYNC":
                out.append(f"WARN {CHECK} {r['type']}: CDC-SYNC {r['src']} -> {r['dst']} ({r['clocks']}): launch and capture "
                           f"are on different clocks, not a same-cycle hop ({_f(r['len_um'])} um, was {r['was']}); 0 stations; "
                           f"check the kit SDC bounds it (set_max_delay) and the first sync flop sits near the launch")
            elif r["kind"] == "CLOCK-UNKNOWN":
                out.append(f"WARN {CHECK} {r['type']}: CLOCK-UNKNOWN {r['src']} -> {r['dst']} ({r['clocks']}): one end has several "
                           f"clocks and the wrapper does not say which this register uses; {_f(r['len_um'])} um > reach {reach:g} "
                           f"(was {r['was']}, +{r['stations']} station(s) if same clock; CDC-SYNC if not)")
            elif r["kind"] == "HOP-SITE":
                out.append(f"WARN {CHECK} {r['type']}: HOP-SITE {r['src']} -> {r['dst']} is {_f(r['len_um'])} um > reach "
                           f"{reach:g} at the plan seat, but a seat within reach of every end of the stage exists; fix: re-seat "
                           f"relay_sites {r['site']}, no station needed")
            elif r["kind"] == "SOFT-GAP":
                out.append(f"WARN {CHECK} {r['type']}: SOFT-GAP {r['src']} -> {r['dst']} is one cycle with no station and NO "
                           f"site of the soft leaf is within reach of all its ends (estimate): {_f(r['len_um'])} um from the best seat "
                           f"> reach {reach:g} (~{r['over_ps']} ps over); fix: +{r['stations']} station(s) on the leg")
            elif r["kind"] == "SOFT-SITE":
                out.append(f"WARN {CHECK} {r['type']}: SOFT-SITE {r['src']} -> {r['dst']}: the unplaced leaf's centroid is "
                           f"{_f(r['len_um'])} um from this end (> reach {reach:g}) but a feasible site exists; fix: pin the leaf at "
                           f"that site (relay_sites / place_region row), no station needed")
            else:
                out.append(f"WARN {CHECK} {r['type']}: DUPSTN {r['src']} / {r['dst']}: duplicate ot_dp_dly stations "
                           f"on the same source bits, sinks {_f(r['len_um'])} um apart (~{r['over_ps']} ps of wire added to the far sink if merged); synthesis merges them unless kept, "
                           f"then one station drives both sinks; fix: OT_KEEP_WIRES += ot_dp_dly:r for the type, or one station per sink side "
                           f"with distinct d")
        if rr:
            nh = sum(1 for r in rr if r["kind"] == "HOP")
            nhs = sum(1 for r in rr if r["kind"] == "HOP-SITE")
            ncdc = sum(1 for r in rr if r["kind"] == "CDC-SYNC")
            nunk = sum(1 for r in rr if r["kind"] == "CLOCK-UNKNOWN")
            ng = sum(1 for r in rr if r["kind"] == "SOFT-GAP")
            nsite = sum(1 for r in rr if r["kind"] == "SOFT-SITE")
            ns = ng + nsite
            out.append(f"WARN {CHECK} summary: {nh} direct one-cycle hop(s) > {reach:g} um in "
                       f"{len({r['type'] for r in rr if r['kind'] == 'HOP'})} type(s) / "
                       f"{len({r['family'] for r in rr if r['kind'] == 'HOP'})} families, {nhs} HOP-SITE (re-seat the stage, 0 stations), {ng} SOFT-GAP (no feasible site) in "
                       f"{len({r['type'] for r in rr if r['kind'] == 'SOFT-GAP'})} type(s), {nsite} SOFT-SITE (feasible site, pin it) in "
                       f"{len({r['type'] for r in rr if r['kind'] == 'SOFT-SITE'})} type(s), "
                       f"{len(rr) - nh - nhs - ns - ncdc - nunk} DUPSTN group(s), {ncdc} CDC-SYNC (different clocks, 0 stations), {nunk} CLOCK-UNKNOWN; {st['judged']} hop(s) judged over {st['bound']}/{st['types']} bound types "
                       f"(bind out {st['bind_out']}) in {time.time() - t0:.1f} s"
                       f"{' (first ' + str(cap) + ' listed)' if len(rr) > cap else ''}")
        return out
    except Exception as e:  # noqa: BLE001
        return [f"WARN {CHECK} not checked: {type(e).__name__}: {str(e)[:200]}"]


if __name__ == "__main__":
    import sys
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    opts = dict(x[2:].split("=", 1) for x in sys.argv[1:] if x.startswith("--") and "=" in x)
    t0 = time.time()
    raw = json.load(open(a[0]))
    t1 = time.time()
    tree = a[1] if len(a) > 1 else None
    kw = {}
    if opts.get("types"):
        kw["types"] = set(opts["types"].split(","))
    if opts.get("tsv"):
        import hashlib
        h = hashlib.sha256()
        with open(a[0], "rb") as f:
            for blk in iter(lambda: f.read(1 << 22), b""):
                h.update(blk)
        sha = h.hexdigest()[:12]
        rr, st = rows(raw, a[0], tree, opts.get("bind_out"), **kw)
        new = not os.path.isfile(opts["tsv"])
        with open(opts["tsv"], "a") as f:
            if new:
                f.write("plan_sha\ttype\tfamily\tfrom\tto\tlen_um\tstations_needed\test_over_ps\n")
            for r in rr or []:
                src = r["src"] if r["kind"] == "HOP" else r["kind"] + " " + r["src"]
                if r.get("site"):
                    src += f" [re-seat {r['site']}]"
                if r.get("clocks"):
                    src += f" [{r['clocks']}; was {r['was']}]"
                f.write(f"{sha}\t{r['type']}\t{r['family']}\t{src}\t{r['dst']}\t{r['len_um']}\t{r['stations']}\t{r['over_ps']}\n")
        print(f"# {len(rr or [])} rows -> {opts['tsv']} ({st})")
        kw["_rows"] = (rr, st)
    for ln in findings(raw, a[0], tree, opts.get("bind_out"), max_lines=100000 if "--all" in sys.argv else None, **kw):
        print(ln)
    print(f"# load {t1 - t0:.1f} s, check {time.time() - t1:.2f} s")
