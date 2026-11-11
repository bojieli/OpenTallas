"""KIT-ISTATIONS 11-11 (TOOLS-2, DIE-HBM-100 class item): per-bit-group sites for a bus's ONE station chain.

kit_istations.bus_entries merges the per-core station rows of a bus (one row per capture / launch core group) into one
chain at the bits-weighted centroid of the deepest rows.  On a multi-core bank bus that parks every flop of a stage in
one pile and leaves each other core 1-2 mm from its stage.  Here the chain stays ONE RTL chain (same depth, same
registers, 0 cycles, EQ by construction); only the SITES differ: bit b of stage j goes to the site of the core that
captures (in bus) or launches (out bus) bit b, taken from that core's own planned route resampled to the chain depth.

bit -> core comes from the bound RTL: an in bus's last-stage q[hi:lo] readers (instance block name or a flattened
g_/w_<core>_ identifier), an out bus's u_bout .d concatenation.  Bits with no resolvable owner keep the merged site.
A bit read by several cores sits at the mean of their sites.  Pure functions; no file is written here."""
import re

REACH_UM = 405.0
ID = r"[A-Za-z_][A-Za-z0-9_$]*"
INST_START = re.compile(rf"^(\s*)({ID})\s+(?:#\(.*\)\s+)?(u_\w+)\s*\(\s*$")
ITEM = re.compile(rf"^({ID})(?:\[(\d+)(?::(\d+))?\])?$")
DECL = re.compile(r"^\s*(?:wire|logic|reg|input\s+wire|output\s+wire|input|output)\s*(?:\[(\d+):(\d+)\])?\s*(" + ID + r")\s*[;,]",
                  re.M)

BITS_TCL = r"""# KIT-ISTATIONS 11-11 per-bit-group sites of one bus station (plan internal_stations rows per core, one RTL chain):
# bit b of the instance sits at its owner core's stage site; bits without a range (epoch flop, unresolved) at the default.
proc is_place_bits {pat default tag ranges} {
  global ff_blk ff_dbu is_n is_miss is_fh
  set bx [dict create]
  foreach r $ranges { lassign $r lo hi x y; for {set b $lo} {$b <= $hi} {incr b} { dict set bx $b [list $x $y] } }
  set hit 0
  foreach i [$ff_blk getInsts] {
    set nm [$i getName]
    set nn [string map {\\ {}} $nm]
    if {![string match $pat $nn]} continue
    if {![string match "*DFF*" [[$i getMaster] getName]]} continue
    set xy $default
    if {[regexp {q\[([0-9]+)\]} $nn -> b] && [dict exists $bx $b]} { set xy [dict get $bx $b] }
    lassign $xy x y
    set got [ff_put_near $i [expr {round($x * $ff_dbu)}] [expr {round($y * $ff_dbu)}]]
    if {$got eq ""} { lappend is_miss $nm; continue }
    puts $is_fh "$nm\t$tag\t[expr {[lindex $got 0] / double($ff_dbu)}]\t[expr {[lindex $got 1] / double($ff_dbu)}]\t-"
    incr is_n; incr hit
  }
  if {!$hit} { lappend is_miss $pat }
}
"""


def _dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def spread(path, n):
    """n points at arclength (j + 1) / (n + 1) along a Manhattan polyline (kit_hbm_cstations._spread)"""
    legs = [_dist(a, b) for a, b in zip(path, path[1:])]
    out = []
    for j in range(n):
        s, k = sum(legs) * (j + 1) / (n + 1), 0
        while k < len(legs) - 1 and s > legs[k]:
            s -= legs[k]
            k += 1
        a, b = path[k], path[k + 1]
        f = s / legs[k] if legs[k] else 0.0
        out.append((round(a[0] + f * (b[0] - a[0]), 3), round(a[1] + f * (b[1] - a[1]), 3)))
    return out


def split_concat(expr):
    e = expr.strip()
    if not (e.startswith("{") and e.endswith("}")):
        return [e]
    inner, depth, cur, out = e[1:-1], 0, "", []
    for ch in inner:
        if ch in "{(":
            depth += 1
        elif ch in "})":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    out.append(cur.strip())
    return None if depth or any(not x for x in out) else out


def core_of_entry(e, hard=()):
    """hard-core instance of a per-core station row: capture / launch (the end that is not the face bus) without its
    pin component; with the plan's hard_cores names the longest one that prefixes it"""
    for k in ("capture", "launch"):
        v = str(e.get(k, ""))
        if v and not v.startswith("face bus"):
            for h in sorted(hard, key=len, reverse=True):
                if v == h or v.startswith(h + "."):
                    return h
            return v.rsplit(".", 1)[0] if "." in v else v
    return None


def flat_of(core):
    return core.replace(".", "_")


def match_core(text, cores):
    """core whose flattened name prefixes a wire / reg identifier (w_<flat>_<port>); longest wins"""
    best = None
    for c in cores:
        f = flat_of(c)
        if re.match(rf"^(?:w_|g_)?{re.escape(f)}(?:_|$)", text) and (best is None or len(f) > len(flat_of(best))):
            best = c
    return best


ASSIGN = re.compile(rf"^\s*assign\s+({ID})\s*=\s*(.+?);", re.M)
NBA = re.compile(rf"\b({ID})\s*<=\s*([^;]+);")
PORT = re.compile(rf"^\s*\.({ID})\((.*)\),?\s*(?://.*)?$")


def _items(expr):
    """expr -> [(ident, hi, lo)] MSB first of a flat concatenation of ident[hi:lo] / ident[i] / ident; None if not flat"""
    its = split_concat(expr)
    if its is None:
        return None
    out = []
    for it in its:
        m = ITEM.match(it.strip())
        if not m:
            return None
        hi = int(m.group(2)) if m.group(2) is not None else None
        lo = int(m.group(3)) if m.group(3) is not None else hi
        out.append((m.group(1), hi, lo))
    return out


class Netlist:
    """pass-through structure of the bound text: wire = reg aliases and reg <= concat sources (one text pass)"""

    def __init__(self, txt):
        self.width = {d.group(3): (int(d.group(1)) - int(d.group(2)) + 1) if d.group(1) else 1 for d in DECL.finditer(txt)}
        self.alias = {m.group(1): m.group(2).strip() for m in ASSIGN.finditer(txt) if re.fullmatch(ID, m.group(2).strip())}
        self.src = {}
        for ln in txt.split("\n"):
            dm = re.match(r"^\s*ot_dp_dly\s+#\(.*?\)\s+u_\w+\s+\(.*?\.d\(([^()]*)\),\s*\.q\(([^()]*)\)\)\s*;", ln)
            if dm:      # landing-pad delay: a pass-through (same bits, D cycles later), one bit per cell in the bound RTL
                its = _items(dm.group(1).strip())
                q = ITEM.match(dm.group(2).strip())
                if its is not None and q and q.group(1) not in self.src:
                    self.src[q.group(1)] = its
                continue
            if re.match(r"^\s*ot_dp_\w+", ln):
                continue
            for m in NBA.finditer(ln.split("//")[0]):
                its = _items(m.group(2).strip())
                if its is not None and m.group(1) not in self.src:
                    self.src[m.group(1)] = its
        self.txt = txt

    def bits(self, ident, hi, lo):
        w = self.width.get(ident)
        if hi is None:
            if not w:
                return []
            hi, lo = w - 1, 0
        return list(range(min(hi, lo), max(hi, lo) + 1))

    def back(self, ident, bit, stop, depth=4):
        """pass-through trace of ident[bit] to a stop(ident, bit) -> value hit; None when it does not resolve"""
        r = stop(ident, bit)
        if r is not None:
            return r
        if depth == 0:
            return None
        ident = self.alias.get(ident, ident)
        its = self.src.get(ident)
        if its is None:
            return None
        pos = sum(self._w(i) or 0 for i in its)
        for (nm, hi, lo) in its:
            w = self._w((nm, hi, lo))
            if not w:
                return None
            pos -= w
            if pos <= bit < pos + w:
                off = min(hi, lo) if hi is not None else 0
                return self.back(nm, off + bit - pos, stop, depth - 1)
        return None

    def _w(self, it):
        nm, hi, lo = it
        return (abs(hi - lo) + 1) if hi is not None else self.width.get(nm)


def in_bit_owners(txt, n, cores, nl=None):
    """{bus bit: set(core)}: each core's instance port bits traced back through pass-through regs to the in bus last stage"""
    nl = nl or Netlist(txt)
    qre = re.compile(rf"^{re.escape(n)}(?:_p\d+|_is\d+)?_q$")
    owners, lines = {}, txt.split("\n")
    for c in cores:
        inst = "u_" + flat_of(c)
        for i, ln in enumerate(lines):
            m = INST_START.match(ln)
            if not (m and m.group(3) == inst):
                continue
            j = i + 1
            while j < len(lines) and not re.match(r"^\s*\);", lines[j]):
                pm = PORT.match(lines[j])
                its = _items(pm.group(2)) if pm else None
                for (nm, hi, lo) in (its or []):
                    for b in nl.bits(nm, hi, lo):
                        r = nl.back(nm, b, lambda a, k: k if qre.match(a) else None)
                        if r is not None:
                            owners.setdefault(r, set()).add(c)
                j += 1
    return owners


def out_bit_owners(txt, n, W, cores, nl=None):
    """{bus bit: set(core)} of an out bus: each u_bout .d bit traced back through pass-through regs to a core output wire"""
    nl = nl or Netlist(txt)
    m = re.search(rf"^\s*ot_dp_ste?\s+#\(\.W\({W}\)\)\s+u_bout_{re.escape(n)}\s*\(.*?\.d\(([^)]*)\),\s*\.ea\(", txt, re.M)
    if not m:
        return None
    its = _items(m.group(1))
    if its is None:
        return None
    pos, owners = W, {}
    for (nm, hi, lo) in its:
        w = nl._w((nm, hi, lo))
        if not w:
            return None
        pos -= w
        off = min(hi, lo) if hi is not None else 0
        for k in range(w):
            c = nl.back(nm, off + k, lambda a, bit: match_core(a, cores) if match_core(a, cores) else None)
            if c is not None:
                owners.setdefault(pos + k, set()).add(c)
    return owners if pos == 0 else None


def _runs(site_of_bit, W):
    """[(lo, hi, x, y)] runs of consecutive bits at one site"""
    out = []
    for b in range(W):
        s = site_of_bit.get(b)
        if s is None:
            continue
        if out and out[-1][1] == b - 1 and out[-1][2:] == s:
            out[-1] = (out[-1][0], b, s[0], s[1])
        else:
            out.append((b, b, s[0], s[1]))
    return out


def chain_order(path, in_bus, face_first):
    """station 0 is at the face side of an in bus and at the leaf (core) side of an out bus"""
    return path if (face_first == in_bus) else path[::-1]


def plan_groups(es, in_bus, n, W, owners, hard=()):
    """-> dict(stages=[[(lo,hi,x,y)]]*n, groups={core: dict(bits, hop_um)}, unresolved_bits) or None (no owners).
    es: the bus's per-core plan rows (each row's regs_um runs from_um -> to_um)."""
    cores = sorted({core_of_entry(e, hard) for e in es} - {None})
    if not owners or not cores:
        return None
    site, worst = {}, {}
    for c in cores:
        rows = [e for e in es if core_of_entry(e, hard) == c and e.get("regs_um") and e.get("from_um") and e.get("to_um")]
        if not rows:
            continue
        w = sum(int(r.get("bits", 1)) for r in rows)
        acc = [[0.0, 0.0] for _ in range(n)]
        hop = 0.0
        for r in rows:
            ff = in_bus or str(r.get("launch", "")).startswith("face bus")
            path = [tuple(r["from_um"])] + [tuple(p) for p in r["regs_um"]] + [tuple(r["to_um"])]
            ordered = chain_order(path, in_bus, ff if not in_bus else True)
            st = ordered[1:-1] if len(r["regs_um"]) == n else spread(ordered, n)
            for j, p in enumerate(st):
                acc[j][0] += p[0] * int(r.get("bits", 1))
                acc[j][1] += p[1] * int(r.get("bits", 1))
            full = [ordered[0]] + list(st) + [ordered[-1]]
            hop = max(hop, max(_dist(a, b) for a, b in zip(full, full[1:])))
        site[c] = [(round(a[0] / w, 3), round(a[1] / w, 3)) for a in acc]
        worst[c] = hop
    stages = []
    for j in range(n):
        per_bit = {}
        for b, cs in owners.items():
            pts = [site[c][j] for c in cs if c in site]
            if pts and b < W:
                per_bit[b] = (round(sum(p[0] for p in pts) / len(pts), 3), round(sum(p[1] for p in pts) / len(pts), 3))
        stages.append(_runs(per_bit, W))
    bits = {c: sum(1 for b, cs in owners.items() if c in cs and b < W) for c in cores}
    return dict(stages=stages, groups={c: dict(bits=bits[c], hop_um=round(worst.get(c, 0.0), 3)) for c in cores},
                unresolved_bits=W - sum(1 for b in range(W) if b in owners))


def merged_violates(es, merged_regs, in_bus, reach=REACH_UM):
    """True when some per-core group's core end is farther than reach from BOTH end stages of the merged chain (the
    failure DIE-LAYOUT-HBM measured: a merged pile leaves other cores 1-3 mm from their stage)"""
    for e in es:
        if not (e.get("from_um") and e.get("to_um")):
            continue
        ff = in_bus or str(e.get("launch", "")).startswith("face bus")
        core_end = e["to_um"] if ff else e["from_um"]
        if min(_dist(core_end, merged_regs[0]), _dist(core_end, merged_regs[-1])) > reach:
            return True
    return False


def tcl_lines(stage_names, groups, default_sites, bus):
    """istations.tcl lines: one is_place_bits per chain stage instance (stage_names[j] has default_sites[j])"""
    out = []
    for nm, ranges, (x, y) in zip(stage_names, groups["stages"], default_sites):
        rs = " ".join("{%d %d %0.9g %0.9g}" % r for r in ranges)
        out.append(f"is_place_bits {{*{nm}[./]*}} {{{x} {y}}} ist:{bus} {{{rs}}}")
    return out
