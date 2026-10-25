#!/usr/bin/env python3
"""lane_clock_audit: clock-domain audit of a BOUND die (bind.py output: partition modules + <die>_bound_top.sv) (TOK-QK/D 10-24).

    lane_clock_audit.py BIND_RTL_DIR --pd PORT_DOMAINS.json [--pd ...] [--src FILES.f] [--json OUT.json]

For every register the binder emitted (ot_dp_st boundary / ft station, ot_dp_dly lane pad / landing pad / kept as-built
stage) and every leaf input, the launch points of its D cone (registers, leaf outputs; through assigns, comb cells and
the bound top's lane wires) are found and their clock domains compared with the capturing clock.  Domains are die-level
clock roles (core, hbm, phy, host, ingest, fwd: the bound top's clk_* ports; clk_clk_hbm_<Q> -> hbm), so one partition
TYPE is analysed once for all its instances (a type whose instances map one clock port to different roles is reported).

Leaf port domains: a leaf with one clock pin is in that domain; a multi-clock leaf needs its per-port (per-bit) domains
from tools/die_plan/port_domains.py (--pd); a multi-clock leaf without them is reported (UNKNOWN), never assumed.

Report (per lane bus = partition type + bus name, instances aggregated):
  WRONG_CLOCK  every leaf launching into the lane and every leaf capturing from it is in ONE domain X, but the lane's
               registers are on another clock Y: two bare crossings that need not exist (bind the lane on X).
  CROSS_BARE   launch and capture leaf domains differ and the lane carries them through plain registers: an
               unsynchronised crossing (needs ONE CDC: async FIFO for multi-bit, 2-flop for a single-bit level).
  CROSS_SYNC   launch and capture differ, the capture is a synchroniser (ot_dp_rsync / ot_reset_sync / 2-flop leaf input
               / CDC cell): OK.
  OK           one domain end to end.
Also: INTRA arcs (as-built leaf->leaf wiring or kept ot_dp_dly inside a partition) whose launch and capture differ.
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

BIND_REG = {"ot_dp_st", "ot_dp_dly"}
SYNC_CELLS = {"ot_dp_rsync": ("a", "clk"), "ot_reset_sync": ("async_rst_n", "clk")}
# CDC cells (multi-clock by design): their ports' domains come from --pd like any leaf; listed here as "a synchroniser"
CDC_CELLS = re.compile(r"^(ot_fdi_phy_cdc|ot_async_fifo\w*|ot_cdc\w*|ot_sync\w*)$")


def strip_comments(t):
    t = re.sub(r"/\*.*?\*/", " ", t, flags=re.S)
    return re.sub(r"//[^\n]*", "", t)


def split_top(s, sep):
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


def match_paren(s, i):
    d = 0
    for j in range(i, len(s)):
        if s[j] == "(":
            d += 1
        elif s[j] == ")":
            d -= 1
            if d == 0:
                return j
    raise ValueError("unbalanced")


class Mod:
    """one generated partition module: ports, wires (widths), statements"""

    def __init__(self, text):
        t = strip_comments(text)
        m = re.search(r"\bmodule\s+(\w+)", t)
        self.name = m.group(1)
        i = m.end()
        j = i
        while t[j].isspace():
            j += 1
        if t[j] == "#":
            k = t.index("(", j)
            j = match_paren(t, k) + 1
        k = t.index("(", j)
        e = match_paren(t, k)
        self.ports, self.width = {}, {}
        for p in split_top(t[k + 1:e], ","):
            p = p.strip()
            mm = re.match(r"(input|output|inout)\s+(?:wire|reg|logic)?\s*(?:\[(\d+):(\d+)\])?\s*(\w+)", p)
            if mm:
                self.ports[mm.group(4)] = mm.group(1)
                self.width[mm.group(4)] = (int(mm.group(2)) - int(mm.group(3)) + 1) if mm.group(2) else 1
        body = t[t.index(";", e) + 1:t.rindex("endmodule")]
        self.stmts = []
        for st in split_top(body, ";"):
            st = st.strip()
            if not st:
                continue
            mm = re.match(r"wire\s*(?:\[(\d+):(\d+)\])?\s*(\w+)(?:\s*=\s*(.*))?$", st, re.S)
            if mm:
                self.width[mm.group(3)] = (int(mm.group(1)) - int(mm.group(2)) + 1) if mm.group(1) else 1
                if mm.group(4):
                    self.stmts.append(("assign", mm.group(3), mm.group(4)))
                continue
            mm = re.match(r"assign\s+(.*?)\s*=\s*(.*)$", st, re.S)
            if mm:
                self.stmts.append(("assign", mm.group(1), mm.group(2)))
                continue
            mm = re.match(r"(\w+)\s*(#\s*\(.*\))?\s*(\w+)\s*\((.*)\)$", st, re.S)
            if mm and mm.group(1) not in ("module", "parameter", "localparam"):
                conns = {}
                for c in split_top(mm.group(4), ","):
                    c = c.strip()
                    cm = re.match(r"\.(\w+)\s*\((.*)\)$", c, re.S)
                    if cm:
                        conns[cm.group(1)] = cm.group(2).strip()
                params = {}
                if mm.group(2):
                    ps = mm.group(2).strip()[1:].strip()[1:-1]
                    for c in split_top(ps, ","):
                        cm = re.match(r"\s*\.(\w+)\s*\((.*)\)\s*$", c, re.S)
                        if cm:
                            params[cm.group(1)] = cm.group(2).strip()
                self.stmts.append(("inst", mm.group(1), mm.group(3), conns, params))

    def bits(self, e):
        """expression -> (list of bit refs LSB first, simple?) ; ref = (sig, i) | ('const', v)"""
        e = e.strip()
        if not e:
            return [], True
        if e.startswith("{") and e.endswith("}") and match_brace(e, 0) == len(e) - 1:
            inner = e[1:-1].strip()
            rm = re.match(r"(\d+)\s*\{(.*)\}$", inner, re.S)
            if rm and match_brace(inner, inner.index("{")) == len(inner) - 1:
                b, s = self.bits("{" + rm.group(2) + "}")
                return b * int(rm.group(1)), s
            out, simple = [], True
            for part in split_top(inner, ","):
                b, s = self.bits(part)
                out = b + out          # MSB first in source
                simple &= s
            return out, simple
        mm = re.fullmatch(r"(\w+)\s*(?:\[\s*(\d+)\s*(?::\s*(\d+))?\s*\])?", e)
        if mm and not re.fullmatch(r"\d+", e):
            n = mm.group(1)
            if mm.group(2) is None:
                return [(n, i) for i in range(self.width.get(n, 1))], True
            hi = int(mm.group(2))
            lo = int(mm.group(3)) if mm.group(3) is not None else hi
            return [(n, i) for i in range(lo, hi + 1)], True
        mm = re.fullmatch(r"(\d+)'[sS]?([bdhBDH])([0-9a-fA-FxXzZ_]+)", e)
        if mm:
            w = int(mm.group(1))
            return [("const", 0)] * w, True
        if re.fullmatch(r"\d+", e):
            return [("const", 0)] * 32, True
        # complex expression: every referenced bit feeds every result bit
        refs = []
        for mm in re.finditer(r"([A-Za-z_]\w*)\s*(?:\[\s*(\d+)\s*(?::\s*(\d+))?\s*\])?", e):
            n = mm.group(1)
            if n not in self.width:
                continue
            if mm.group(2) is None:
                refs += [(n, i) for i in range(self.width.get(n, 1))]
            else:
                hi = int(mm.group(2))
                lo = int(mm.group(3)) if mm.group(3) is not None else hi
                refs += [(n, i) for i in range(lo, hi + 1)]
        return refs, False


def match_brace(s, i):
    d = 0
    for j in range(i, len(s)):
        if s[j] == "{":
            d += 1
        elif s[j] == "}":
            d -= 1
            if d == 0:
                return j
    return -1


def role_of(net):
    n = re.sub(r"^clk_", "", net)
    n = re.sub(r"^clk_", "", n)
    if n.startswith("hbm"):
        return "hbm"
    return n


class Audit:
    def __init__(self, rtl_dir, pds, src_files):
        self.dir = Path(rtl_dir)
        self.pd = {}
        for f in pds:
            self.pd.update(json.loads(Path(f).read_text()))
        self.mods = {}
        top = None
        for f in sorted(self.dir.glob("*.sv")):
            t = f.read_text(errors="replace")
            if "_bound_top" in f.name:
                top = Mod(t)
                continue
            if not re.search(r"^module\s+kv\w*|GENERATED by tools/die_plan/bind.py", t, re.M):
                continue
            if "GENERATED by tools/die_plan/bind.py" not in t[:400]:
                continue
            m = Mod(t)
            self.mods[m.name] = m
        self.top = top
        self.leaf_dirs = self._leaf_dirs(src_files)
        self.findings = []

    def _leaf_dirs(self, src_files):
        """module -> {port: dir} from the source files (ANSI headers) + the --pd records"""
        d = defaultdict(dict)
        for m, r in self.pd.items():
            for p, x in r["ports"].items():
                d[m][p] = x["dir"]
        files = []
        for sf in src_files or []:
            files += [x for x in Path(sf).read_text().split() if x.endswith((".sv", ".v")) and Path(x).exists()]
        for f in [str(x) for x in self.dir.glob("*.sv")] + files:
            t = strip_comments(Path(f).read_text(errors="replace"))
            for mm in re.finditer(r"\bmodule\s+(\w+)", t):
                name = mm.group(1)
                if name in d and name not in self.pd:
                    continue
                try:
                    j = mm.end()
                    while t[j].isspace():
                        j += 1
                    if t[j] == "#":
                        k = t.index("(", j)
                        j = match_paren(t, k) + 1
                    k = t.index("(", j)
                    e = match_paren(t, k)
                except (ValueError, IndexError):
                    continue
                hdr = t[k + 1:e]
                cur = None
                for tok in split_top(hdr, ","):
                    mm2 = re.match(r"\s*(input|output|inout)\b(.*)", tok, re.S)
                    if mm2:
                        cur = mm2.group(1)
                        nm = re.findall(r"(\w+)\s*$", mm2.group(2).strip())
                    else:
                        nm = re.findall(r"^\s*(\w+)\s*$", tok)
                    if cur and nm:
                        d[name].setdefault(nm[0], cur)
                if not re.search(r"\b(input|output)\b", hdr):      # non-ANSI
                    body = t[e:]
                    body = body[:body.find("endmodule")]
                    for mm3 in re.finditer(r"\b(input|output|inout)\b[^;]*?(\w+(?:\s*,\s*\w+)*)\s*;", body):
                        for n in re.split(r"\s*,\s*", mm3.group(2)):
                            d[name].setdefault(n, mm3.group(1))
        return d

    # ---------------------------------------------------------------- per type
    def clock_roles(self):
        """type -> {clock port: role}, from the top's instances (inconsistent roles reported)"""
        r = defaultdict(dict)
        self.inst_type = {}
        self.inst_conn = {}
        for st in self.top.stmts:
            if st[0] != "inst" or st[1] not in self.mods:
                continue
            _, mt, inst, conns, _ = st
            self.inst_type[inst] = mt
            self.inst_conn[inst] = conns
            for p, e in conns.items():
                if p == "clk" or p.startswith("clk_"):
                    ro = role_of(e)
                    if p in r[mt] and r[mt][p] != ro:
                        self.findings.append(dict(kind="TYPE_ROLE_SPLIT", type=mt, port=p, roles=[r[mt][p], ro]))
                    r[mt].setdefault(p, ro)
        return r

    def analyse(self):
        roles = self.clock_roles()
        self.roles = roles
        self.inst_by_type = defaultdict(list)
        for inst, mt in self.inst_type.items():
            self.inst_by_type[mt].append(inst)
        # out-port driver role per type (the register / ft station / pass-through driving each output bit)
        self.T = {}
        for mt, m in self.mods.items():
            if mt in roles:
                self.T[mt] = self.type_graph(m, roles[mt])
        # external launch of each in-port bit: from the top's wiring
        self.ext = defaultdict(set)          # (type, port, bit) -> {(role, desc)}
        self.leaf_up = {}
        net_drv = {}
        for inst, conns in self.inst_conn.items():
            mt = self.inst_type[inst]
            m = self.mods[mt]
            for p, e in conns.items():
                if m.ports.get(p) == "output":
                    bl, _ = self.top.bits(e)
                    for i, b in enumerate(bl):
                        net_drv[b] = (inst, p, i)
        self.net_drv = net_drv
        for inst, conns in self.inst_conn.items():
            mt = self.inst_type[inst]
            m = self.mods[mt]
            for p, e in conns.items():
                if m.ports.get(p) != "input" or p == "clk" or p.startswith("clk_") or p == "arst_n":
                    continue
                bl, _ = self.top.bits(e)
                for i, b in enumerate(bl):
                    d = net_drv.get(b)
                    if d is None:
                        self.ext[(mt, p, i)].add(("top-input", "die IO / top port"))
                        continue
                    for x in self.out_launch(*d):
                        self.ext[(mt, p, i)].add(x)

    def out_launch(self, inst, port, i, depth=0):
        """launch points (role, desc) driving output bit `port[i]` of instance inst (through pass-through ft assigns)"""
        mt = self.inst_type[inst]
        G = self.T[mt]
        res = set()
        for kind, x in G["launch"][(port, i)]:
            if kind == "inport":
                if depth > 50:
                    continue
                d = self.inst_conn[inst].get(x[0])
                bl, _ = self.top.bits(d)
                b = bl[x[1]]
                dd = self.net_drv.get(b)
                if dd:
                    res |= self.out_launch(*dd, depth=depth + 1)
            else:
                res.add(x)
        return res

    def type_graph(self, m, croles):
        """within type m: drivers of every bit, register elements, leaf ports with domains"""
        clkports = {p for p in m.ports if p == "clk" or p.startswith("clk_")}
        drv = {}                  # bit -> ("reg", elem) | ("leaf", (inst, port, i, role)) | ("comb", [bits]) | ("in", (p,i))
        regs = []                 # (elem name, kind, role, d bits, q bits, cell)
        caps = []                 # leaf input capture points: (inst, module, port, i, role|None, src bits, sync)
        unknown = set()
        for p, d in m.ports.items():
            if d == "input" and p not in clkports:
                for i in range(m.width.get(p, 1)):
                    drv[(p, i)] = ("in", (p, i))
        for st in m.stmts:
            if st[0] == "assign":
                lb, ls = m.bits(st[1])
                rb, rs = m.bits(st[2])
                if rs and len(rb) == len(lb):
                    for a, b in zip(lb, rb):
                        drv[a] = ("comb", [b])
                else:
                    for a in lb:
                        drv[a] = ("comb", rb)
                continue
            _, mod, inst, conns, params = st
            ckp = conns.get("clk", "")
            if mod in BIND_REG:
                role = croles.get(ckp.strip(), "?")
                for dn, qn in (("d", "q"), ("ea", "eq")):
                    if dn not in conns:
                        continue
                    db, _ = m.bits(conns[dn])
                    qb, _ = m.bits(conns[qn])
                    if mod == "ot_dp_dly" and dn == "d":
                        pass
                    for k, q in enumerate(qb):
                        e = (inst, mod, role, qn, k)
                        drv[q] = ("reg", e)
                        regs.append((e, [db[k]] if k < len(db) else []))
                continue
            if mod in SYNC_CELLS:
                ip, cp = SYNC_CELLS[mod]
                role = croles.get(conns.get(cp, "").strip(), "?")
                outs = [p for p in conns if p not in (ip, cp)]
                for o in outs:
                    for k, q in enumerate(m.bits(conns[o])[0]):
                        drv[q] = ("reg", (inst, mod, role, o, k))
                for k, b in enumerate(m.bits(conns.get(ip, ""))[0]):
                    caps.append((inst, mod, ip, k, role, [b], "synchroniser"))
                continue
            # a leaf / plan cell / CDC cell
            dirs = self.leaf_dirs.get(mod, {})
            pins = {}
            for p, e in conns.items():
                if e.strip().strip("{}") and all(x.strip() in clkports for x in e.strip().strip("{}").split(",")):
                    pins[p] = croles.get(e.strip().strip("{}").split(",")[0].strip(), "?")
            pdm = self.pd.get(mod)
            for p, e in conns.items():
                if p in pins:
                    continue
                dr = dirs.get(p)
                if dr is None:
                    dr = "output" if re.fullmatch(r"w_\w+", e.strip()) else "input"
                bl, simple = m.bits(e)
                for k, b in enumerate(bl):
                    role, sync = self.port_role(mod, p, k, pins, pdm, unknown)
                    if dr == "output":
                        drv[b] = ("leaf", (inst, mod, p, k, role))
                    else:
                        caps.append((inst, mod, p, k, role, [b], sync))
        # launch sets per bit
        memo = {}

        def launch(b, depth=0):
            if b in memo:
                return memo[b]
            memo[b] = frozenset()
            if b[0] == "const":
                return memo[b]
            d = drv.get(b)
            if d is None:
                r = frozenset()
            elif d[0] == "reg":
                e = d[1]
                r = frozenset({("reg", (e[2], f"{e[1]} {e[0]}"))})
            elif d[0] == "leaf":
                x = d[1]
                r = frozenset({("leaf", (x[4], f"leaf {x[1]} {x[0]}.{x[2]}"))})
            elif d[0] == "in":
                r = frozenset({("inport", d[1])})
            else:
                s = set()
                if depth < 2000:
                    for y in d[1]:
                        s |= launch(y, depth + 1)
                r = frozenset(s)
            memo[b] = r
            return r
        out_launch = {}
        for p, d in m.ports.items():
            if d == "output":
                for i in range(m.width.get(p, 1)):
                    out_launch[(p, i)] = launch((p, i))
        return dict(m=m, drv=drv, regs=regs, regd=dict(regs), caps=caps, launch=out_launch, lf=launch, unknown=unknown)

    def port_role(self, mod, p, k, pins, pdm, unknown):
        """(role, sync) of leaf port bit p[k]: --pd per-bit clock pins, else the leaf's only clock"""
        if CDC_CELLS.match(mod) and pdm is None:
            unknown.add(f"{mod}.{p}")
            return None, "cdc-cell"
        if pdm is not None and p in pdm["ports"]:
            x = pdm["ports"][p]
            cl = (x["bits"][k] if x.get("bits") and k < len(x["bits"]) else list(x["clocks"]))
            cl = [c for c in cl if c != "const"]
            rs = {pins.get(c, "?") for c in cl if not c.startswith("derived:")}
            sync = None
            if x.get("sync") and "sync2" in x["sync"]:
                sync = "sync2"
            if "reset" in x.get("kind", []) and not cl:
                return None, "reset"
            if len(rs) == 1:
                return rs.pop(), sync
            if not rs:
                return None, sync
            return "mixed:" + "+".join(sorted(rs)), sync
        rs = set(pins.values())
        if len(rs) == 1:
            return next(iter(rs)), None
        if not rs:
            return None, None       # combinational cell (no clock): transparent
        unknown.add(f"{mod}.{p}")
        return "?", None

    # ---------------------------------------------------------------- arcs
    def resolve(self, mt, L):
        """launch set of a type-local bit set -> {(role, desc)} (in-ports resolved through the top, all instances)"""
        out = set()
        for kind, x in L:
            if kind == "inport":
                out |= self.ext.get((mt, x[0], x[1]), set())
            else:
                out.add(x)
        return out

    def arcs(self):
        """every capture point (bind register bit, leaf input bit) vs the roles launching into it"""
        rows = defaultdict(lambda: dict(bits=0, launch=set(), example=None))
        for mt, G in self.T.items():
            lf = G["lf"]
            for e, db in G["regs"]:
                inst, mod, role, qn, k = e
                L = set()
                for b in db:
                    L |= lf(b)
                Ls = self.resolve(mt, L)
                lr = {r for r, _ in Ls}
                if not lr or lr == {role}:
                    continue
                key = (mt, inst, mod, role, qn == "eq")
                rows[key]["bits"] += 1
                rows[key]["launch"] |= lr
                rows[key]["example"] = rows[key]["example"] or sorted(Ls)[0][1]
            for inst, mod, p, k, role, src, sync in G["caps"]:
                if role is None or (role or "").startswith("mixed") and False:
                    pass
                L = set()
                for b in src:
                    L |= lf(b)
                Ls = self.resolve(mt, L)
                lr = {r for r, _ in Ls}
                if role is None or not lr or lr == {role}:
                    continue
                key = (mt, inst, f"{mod}.{p}", role, sync or "")
                rows[key]["bits"] += 1
                rows[key]["launch"] |= lr
                rows[key]["example"] = rows[key]["example"] or sorted(Ls)[0][1]
        return rows

    # ---------------------------------------------------------------- lanes (end to end)
    def lane_ends(self):
        """per in-bus of each type (u_bin_<n>): the leaf domains launching into it (through every register upstream,
        across partitions) and the leaf domains capturing from it (through pads / forwards downstream), plus the clock
        roles of the registers between."""
        # downstream: from each in-port bit, forward through comb/regs (not leaves) to leaf captures / out-ports
        res = {}
        for mt, G in self.T.items():
            m = G["m"]
            fwd = defaultdict(list)       # bit -> [next bits] through comb and bind registers
            regrole = {}
            for b, d in G["drv"].items():
                if d[0] == "comb":
                    for y in d[1]:
                        fwd[y].append(b)
            for e, db in G["regs"]:
                q = (e[0], e[3], e[4])
                for b in db:
                    fwd[b].append(("__reg",) + q)
                regrole[q] = e[2]
            # map reg q tuple -> q bit
            qbit = {}
            for b, d in G["drv"].items():
                if d[0] == "reg":
                    e = d[1]
                    qbit[(e[0], e[3], e[4])] = b
            capby = defaultdict(list)
            for inst, mod, p, k, role, src, sync in G["caps"]:
                for b in src:
                    capby[b].append((inst, mod, p, role, sync))
            G["fwd"], G["qbit"], G["regrole"], G["capby"] = fwd, qbit, regrole, capby
        for mt, G in self.T.items():
            m = G["m"]
            for p, d in m.ports.items():
                if d != "input" or p == "clk" or p.startswith("clk_") or p == "arst_n":
                    continue
                for i in range(m.width.get(p, 1)):
                    up = self.leaf_launch_through(mt, p, i)
                    down, regs = self.leaf_capture_through(mt, (p, i))
                    key = (mt, p)
                    r = res.setdefault(key, dict(up=defaultdict(int), down=defaultdict(int), regs=set(), bits=0,
                                                 ex_up=None, ex_down=None, sync=set()))
                    r["bits"] += 1
                    for x in up[0]:
                        r["up"][x] += 1
                    r["ex_up"] = r["ex_up"] or (sorted(up[1])[0] if up[1] else None)
                    r["regs"] |= up[2] | regs
                    for (ro, sy), ex in down.items():
                        r["down"][ro] += 1
                        if sy:
                            r["sync"].add(sy)
                        r["ex_down"] = r["ex_down"] or ex
        return res

    def leaf_launch_through(self, mt, p, i, depth=0, seen=None):
        """leaf roles launching into in-port bit p[i] of type mt, through every bind register upstream"""
        seen = seen if seen is not None else set()
        roles, descs, regs = set(), set(), set()
        # follow the top: every instance of mt -> driver out-port -> back through the source type
        for inst in self.inst_by_type[mt]:
            e = self.inst_conn[inst].get(p)
            if e is None:
                continue
            bl, _ = self.top.bits(e)
            if i >= len(bl):
                continue
            dd = self.net_drv.get(bl[i])
            if dd is None:
                continue
            key = (dd[0], dd[1], dd[2])
            if key in seen or depth > 60:
                continue
            seen.add(key)
            r2, d2, g2 = self.back_through(self.inst_type[dd[0]], (dd[1], dd[2]), depth, seen)
            roles |= r2
            descs |= d2
            regs |= g2
        return roles, descs, regs

    def back_through(self, mt, b, depth, seen):
        G = self.T[mt]
        roles, descs, regs, stack, vis = set(), set(), set(), [b], set()
        while stack:
            x = stack.pop()
            if x in vis:
                continue
            vis.add(x)
            d = G["drv"].get(x)
            if d is None:
                continue
            if d[0] == "comb":
                stack.extend(d[1])
            elif d[0] == "reg":
                e = d[1]
                if e[1] in BIND_REG:
                    regs.add((mt, e[0].split("_")[0] + "_" + e[1], e[2]))
                    stack.extend(G["regd"].get(e, []))
                else:
                    roles.add(e[2])
                    descs.add(f"{mt}:{e[1]} {e[0]}")
            elif d[0] == "leaf":
                roles.add(d[1][4])
                descs.add(f"{mt}:{d[1][1]} {d[1][0]}.{d[1][2]}")
            elif d[0] == "in":
                r2, d2, g2 = self.leaf_launch_through(mt, d[1][0], d[1][1], depth + 1, seen)
                roles |= r2
                descs |= d2
                regs |= g2
        return roles, descs, regs

    def leaf_capture_through(self, mt, b):
        G = self.T[mt]
        out, regs, stack, vis = {}, set(), [b], set()
        while stack:
            x = stack.pop()
            if x in vis:
                continue
            vis.add(x)
            for cap in G["capby"].get(x, []):
                inst, mod, p, role, sync = cap
                out.setdefault((role, sync), f"{mt}:{mod} {inst}.{p}")
            for y in G["fwd"].get(x, []):
                if y[0] == "__reg":
                    q = y[1:]
                    regs.add((mt, q[0].split("_")[0] + "_" + "reg", G["regrole"][q]))
                    qb = G["qbit"].get(q)
                    if qb is not None:
                        stack.append(qb)
                else:
                    stack.append(y)
        return out, regs


def classify(r):
    up = {x for x in r["up"] if x}
    down = {x for x in r["down"] if x}
    regroles = {g[2] for g in r["regs"]}
    if not r["down"]:
        return "FT_ONLY"            # forwarded to another partition only: judged at its final in-bus
    if not up or not down:
        return "UNRESOLVED"
    if len(up) == 1 and up == down:
        d = next(iter(up))
        return "OK" if regroles <= {d} else "WRONG_CLOCK"
    if r["sync"] and r["sync"] <= {"synchroniser", "sync2", "reset"}:
        return "CROSS_SYNC"
    return "CROSS_BARE"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rtl")
    ap.add_argument("--pd", action="append", default=[])
    ap.add_argument("--src", action="append", default=[])
    ap.add_argument("--json")
    ap.add_argument("--show", type=int, default=400)
    a = ap.parse_args(argv)
    A = Audit(a.rtl, a.pd, a.src)
    A.analyse()
    lanes = A.lane_ends()
    by = defaultdict(list)
    for (mt, p), r in sorted(lanes.items()):
        c = classify(r)
        by[c].append(dict(type=mt, port=p, bits=r["bits"], launch=dict(r["up"]), capture=dict(r["down"]),
                          reg_clocks=sorted({g[2] for g in r["regs"]}), sync=sorted(r["sync"]),
                          ex_launch=r["ex_up"], ex_capture=r["ex_down"],
                          instances=sum(1 for t in A.inst_type.values() if t == mt)))
    arcs = A.arcs()
    arcrows = [dict(type=k[0], elem=k[1], cell=k[2], capture_role=k[3], tag=k[4], bits=v["bits"],
                    launch=sorted(v["launch"]), example=v["example"],
                    instances=sum(1 for t in A.inst_type.values() if t == k[0])) for k, v in sorted(arcs.items())]
    unknown = sorted({u for G in A.T.values() for u in G["unknown"]})
    print(f"lane_clock_audit {a.rtl}: {len(A.mods)} partition types, {len(A.inst_type)} instances")
    for c in ("WRONG_CLOCK", "CROSS_BARE", "CROSS_SYNC", "UNRESOLVED", "FT_ONLY", "OK"):
        rows = by.get(c, [])
        nb = sum(x["bits"] * x["instances"] for x in rows)
        print(f"== {c}: {len(rows)} in-bus ports (type level), {nb} die bits")
        if c in ("OK", "FT_ONLY"):
            continue
        for x in rows[:a.show]:
            print(f"   {x['type']}.{x['port']} w{x['bits']} x{x['instances']}: launch {x['launch']} regs {x['reg_clocks']} "
                  f"capture {x['capture']} sync {x['sync']} | {x['ex_launch']} -> {x['ex_capture']}")
    print(f"== ARCS with launch role != capture clock (type level): {len(arcrows)}")
    for x in arcrows[:a.show]:
        print(f"   {x['type']} {x['elem']} ({x['cell']}) capture {x['capture_role']} {x['tag']} <- {x['launch']} "
              f"bits {x['bits']} x{x['instances']} e.g. {x['example']}")
    print(f"== UNKNOWN multi-clock leaf ports (no --pd): {len(unknown)} {unknown[:40]}")
    for f in A.findings:
        print("   FINDING", f)
    if a.json:
        Path(a.json).write_text(json.dumps(dict(lanes=by, arcs=arcrows, unknown=unknown, findings=A.findings),
                                           indent=1, sort_keys=True, default=str) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
