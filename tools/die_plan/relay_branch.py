#!/usr/bin/env python3
"""S81-RLYBR-1 11-19 (COORD family class: one relay feeds sinks more than 2 x 405 um apart -- bs0 on col_h9_r0_p3..p6, the
t2 -> t3 relays y_xa / xb / cc_3_0 feeding bs3 and t3 on col_h10_r0, bn3 -> frame_int_o0 station 0 on col_h10_r0).

Two generator rules, fixed once for every type instead of hand rows per type:

1. RELAY BRANCH COPIES (plan partition_types[T].relay_branch, realised by bind.py through apply()).
   A relay leaf (ot_s81_rly / ot_s81_rly_k / dsfd_rly_<W>_<F>) whose hard-core sinks cannot all be reached from one site
   (no point within LIMIT of the source pin centroid AND of every sink pin centroid; flight = Manhattan) is split: the sinks are
   clustered so that each cluster plus the source fits one reach box, and every cluster but the one the relay keeps gets a COPY
   of the relay (same module, same input, same reset; the as-built bs4 branch relay u_y_xa_3_bs4_0 is the precedent form).
   Each copy is one stage like the original: 0 added cycles.  A cluster that does not fit with its source even alone (the
   source -> sink flight is over 2 x LIMIT) still gets its copy and D = ceil(L / LIMIT) - 2 relay_depth sink rows in front of
   its sink ports (bind's declared stages, bind_core_input_pipe.json: the +cycle form).  Sinks without a plan position (soft
   leaves) stay on the original relay.  Rows: {"inst": <relay leaf>, "copies": [{"name": <copy leaf>, "sinks": [<sink leaf>],
   "D": 0, "span_um": .., "path_um": ..}], "note": ..}; leaf names are bind rel names (bound instance minus its u_).
   Flattened synthesis merges flops with identical inputs (Yosys opt_merge, keep does not stop it): bind therefore requires
   the copy's reset to differ from the original's after reset_replicate (per-instance regions on every col type).

2. STATION CHAIN JOIN (plan internal_stations[].join, realised by kit_istations.py through join_stations()).
   An out-bus chain u_ist_<bus>_0..n-1 takes its whole bus at station 0.  A slice whose source pin is far from station 0
   (> LIMIT) but nearest to station k > 0 (col_h10_r0 frame_int_o0: bn3.d_st sits 1448 um from station 0, 220 um from
   station 4) joins the chain AT station k through k local flops (ot_dp_st, u_isj_<bus>_<g>_<s>): every bit still sees n
   stages, 0 added cycles; stations 0..k-1 carry zeros in those bits.  Rows: {"bits": [lo, hi], "stage": k, "src": ..,
   "src_um": [x, y], "stage0_um": .., "stage_um": ..}.

3. IN-BUS TRUNK AIM (FABLE-FIX-S81-COLH9R1 11-19 pattern, col_h9_r1 / col_h10_r1 / col_h10_r2 / col_h9_r2): a lane-pad chain
   u_lpad_<bus> (ot_dp_dly, D = planned stations) whose last station is over LIMIT from where most bits end (aimed at a 1-bit
   reset capture) is re-sited on the L path from_um -> bit-weighted centroid of the majority sink cluster; the minority bits keep
   the old sites through per-flop relay_sites (u_lpad_<bus>.r[j][b], last stage .q[b]).  0 cycles, no RTL (trunk_rows()).

usage: relay_branch.py PLAN.json TYPE_RE BOUND_DIR [--plan-dir DIR] [--limit 405] [--out-plan OUT.json] [--report REP.json]
       BOUND_DIR holds <TYPE>_bound.sv or <TYPE>.sv (a bind out/rtl).  Without --out-plan nothing is written.
"""
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

LIMIT = 405.0
TAG = "S81-RLYBR-1"
RELAY_MOD = re.compile(r"^(ot_s81_rly|ot_s81_rly_k|dsfd_rly_\d+_[A-Z]+)$")
_PAR = r"#\((?:[^()]|\((?:[^()]|\([^()]*\))*\))*\)"
HDR = re.compile(r"^(?P<ind>\s*)(?P<mod>[A-Za-z_]\w*)\s*(?P<par>" + _PAR + r")?\s+(?P<inst>[A-Za-z_][\w$]*)\s*\(\s*$")
ONE = re.compile(r"^(?P<ind>\s*)(?P<mod>[A-Za-z_]\w*)\s*(?P<par>" + _PAR + r")?\s+(?P<inst>[A-Za-z_][\w$]*)\s*"
                 r"\((?P<body>\s*\..*)\)\s*;(?P<tail>.*)$")
PORT = re.compile(r"^\s*\.(?P<p>\w+)\((?P<e>.*)\)\s*,?\s*(?://.*)?$")
ASSIGN = re.compile(r"^\s*assign\s+(?P<lhs>[A-Za-z_]\w*)\s*(?:\[[^\]]*\])?\s*=\s*(?P<rhs>.*?)\s*;\s*(?://.*)?$")
DECL = re.compile(r"^\s*(?:wire|reg|logic)\s*(?:\[\s*(?P<h>\d+)\s*:\s*(?P<l>\d+)\s*\])?\s*(?P<names>[^;]*);")
IDENT = re.compile(r"[A-Za-z_][\w$]*")
ATTR = re.compile(r"^(\s*)\(\*.*?\*\)\s*")
KEYWORDS = {"module", "assign", "wire", "reg", "logic", "input", "output", "always", "if", "else", "begin", "end",
            "endmodule", "generate", "localparam", "parameter", "initial"}
OUT_PORTS = ("q", "o", "Y", "y", "eq", "qx")
PASS_IN = ("i", "d", "a")


class BranchError(Exception):
    pass


def sid(s):
    return re.sub(r"_+", "_", re.sub(r"[^A-Za-z0-9_]", "_", str(s))).strip("_")


def _ports_one(body):
    out, i = [], 0
    pat = re.compile(r"\.(\w+)\s*\(")
    while True:
        m = pat.search(body, i)
        if not m:
            return out
        depth, j = 1, m.end()
        while j < len(body) and depth:
            depth += {"(": 1, ")": -1}.get(body[j], 0)
            j += 1
        out.append((m.group(1), body[m.end():j - 1].strip()))
        i = j


class Netlist:
    """the statements of one bound module: multi-line instance blocks, one-line instances, assigns, declarations"""

    def __init__(self, text):
        self.lines = text.split("\n")
        self.st, self.decl = [], {}
        i, L = 0, self.lines
        while i < len(L):
            ln = ATTR.sub(r"\1", L[i])
            m = HDR.match(ln)
            if m and m["mod"] not in KEYWORDS:
                ports, pl, j = {}, {}, i + 1
                while j < len(L):
                    for p_, e_ in _ports_one(re.sub(r"//.*$", "", L[j])):
                        ports[p_] = e_
                        pl[p_] = j
                    if re.search(r"\)\s*;\s*(?://.*)?$", L[j]):
                        break
                    j += 1
                self.st.append(dict(kind="inst", lines=list(range(i, j + 1)), mod=m["mod"], par=m["par"] or "",
                                    ind=m["ind"], inst=m["inst"], ports=ports, port_line=pl))
                i = j + 1
                continue
            m = ONE.match(ln)
            if m and m["mod"] not in KEYWORDS:
                ports = dict(_ports_one(m["body"]))
                self.st.append(dict(kind="one", lines=[i], mod=m["mod"], par=m["par"] or "", ind=m["ind"], inst=m["inst"],
                                    ports=ports, port_line={p: i for p in ports}))
            else:
                m = ASSIGN.match(ln)
                if m:
                    self.st.append(dict(kind="assign", lines=[i], lhs=m["lhs"], rhs=m["rhs"]))
                else:
                    m = DECL.match(ln)
                    if m:
                        w = None if m["h"] is None else (int(m["h"]), int(m["l"]))
                        for nm in m["names"].split(","):
                            nm = nm.strip().split("=")[0].strip()
                            if IDENT.fullmatch(nm or "-"):
                                self.decl[nm] = (i, w)
            i += 1
        self.by_inst = {s["inst"]: k for k, s in enumerate(self.st) if s["kind"] != "assign"}
        self.refs = defaultdict(set)
        for k, s in enumerate(self.st):
            txt = " ".join(re.sub(r"//.*$", "", self.lines[j]) for j in s["lines"])
            if s["kind"] != "assign":
                txt = " ".join(s["ports"].values())
            else:
                txt = s["rhs"]
            for nm in set(IDENT.findall(txt)):
                self.refs[nm].add(k)
        self.drv = {}
        for k, s in enumerate(self.st):
            if s["kind"] == "assign":
                self.drv.setdefault(s["lhs"], (k, None))
                continue
            for p, e in s["ports"].items():
                if IDENT.fullmatch(e) and (p in OUT_PORTS or e == f"w_{s['inst'][2:]}_{p}"):
                    self.drv.setdefault(e, (k, p))

    def width(self, name):
        d = self.decl.get(name)
        return None if d is None or d[1] is None else d[1][0] - d[1][1] + 1

    def consumers(self, w):
        """statements reading w (its driver excluded)"""
        dk = self.drv.get(w, (None,))[0]
        out = []
        for k in sorted(self.refs.get(w, ())):
            if k == dk:
                s = self.st[k]
                if s["kind"] == "assign" or all(e != w for e in s["ports"].values()) or \
                        any(re.search(rf"\b{re.escape(w)}\b", e) and e != w for e in s["ports"].values()):
                    pass
                else:
                    continue
            out.append(k)
        return out

    def owners(self, k, w, depth=0):
        """terminal readers [(instance, port)] of wire w through statement k: assigns and one-line stages with an output
        (relay_depth u_y_xd_*, ot_dp_st, ...) are followed, a multi-line instance block is a terminal"""
        s = self.st[k]
        if depth > 12:
            raise BranchError(f"reader chain of {w} deeper than 12")
        if s["kind"] == "assign":
            return [o for c in self.consumers(s["lhs"]) for o in self.owners(c, s["lhs"], depth + 1)]
        ports = [p for p, e in s["ports"].items() if re.search(rf"\b{re.escape(w)}\b", e) and p not in OUT_PORTS]
        if s["kind"] == "one":
            outs = [e for p, e in s["ports"].items() if p in OUT_PORTS and IDENT.fullmatch(e)]
            if outs:
                return [o for q in outs for c in self.consumers(q) for o in self.owners(c, q, depth + 1)]
        return [(s["inst"], p) for p in ports]


def _bump_id(par, used):
    m = re.search(r"\.ID\((\d+)\)", par)
    if not m:
        return par
    n = max(used) + 1 if used else int(m.group(1)) + 1
    used.add(n)
    return par[:m.start()] + f".ID({n})" + par[m.end():]


def apply(text, rows):
    """bind post-pass: emit the relay copies of `rows` (plan relay_branch) into the bound module text.
    -> (text, report rows).  Raises BranchError on a stale row (no such relay, a copy sink the relay does not feed, a
    reader that feeds sinks of two branches)."""
    if not rows:
        return text, []
    N = Netlist(text)
    edits, inserts, rep = {}, [], []
    used_ids = {int(x) for s in N.st if s["kind"] != "assign" and s["mod"] == "ot_s81_rly_k"
                for x in re.findall(r"\.ID\((\d+)\)", s["par"])}
    for row in rows:
        inst = "u_" + sid(row["inst"])
        k = N.by_inst.get(inst)
        if k is None:
            if row.get("optional"):
                continue
            raise BranchError(f"relay {row['inst']} not in the bound module")
        S = N.st[k]
        if not RELAY_MOD.match(S["mod"]) or S["kind"] != "inst":
            raise BranchError(f"{inst} is {S['mod']}, not a relay leaf")
        W = S["ports"].get("o", "")
        if not IDENT.fullmatch(W) or W not in N.decl:
            raise BranchError(f"{inst}: output {W!r} is not a declared wire")
        readers = {c: N.owners(c, W) for c in N.consumers(W) if c != k}
        seen = set()
        for c in row.get("copies") or []:
            cname = "u_" + sid(c["name"])
            if cname in N.by_inst:
                raise BranchError(f"copy name {cname} already used in the bound module")
            sinks = {"u_" + sid(x) for x in c["sinks"]}
            hit = [r for r, os in readers.items() if os and all(o[0] in sinks for o in os)]
            mixed = [r for r, os in readers.items() if any(o[0] in sinks for o in os) and not all(o[0] in sinks for o in os)]
            if mixed:
                raise BranchError(f"{inst}: a reader feeds copy {cname} sinks and other sinks "
                                  f"({sorted({o[0] for r in mixed for o in readers[r]})[:6]})")
            got = {o[0] for r in hit for o in readers[r]}
            if sinks - got:
                raise BranchError(f"{inst}: copy {cname} sink(s) {sorted(sinks - got)} not fed by the relay")
            if seen & set(hit):
                raise BranchError(f"{inst}: a reader is claimed by two copies")
            seen |= set(hit)
            WC = f"w_{cname[2:]}_o"
            for r in hit:
                for j in N.st[r]["lines"]:
                    edits[j] = re.sub(rf"\b{re.escape(W)}\b", WC, edits.get(j, N.lines[j]))
            par = _bump_id(S["par"], used_ids) if S["mod"] == "ot_s81_rly_k" else S["par"]
            ind = S["ind"]
            ps = ",\n".join(f"{ind}    .{p}({WC if p == 'o' else e})" for p, e in S["ports"].items())
            block = [f"{ind}// {TAG}: relay branch copy of {inst} for {', '.join(sorted(sinks))} "
                     f"(1 stage like the original, {int(c.get('D', 0))} declared stage(s) in front of its sinks)",
                     f"{ind}{S['mod']}{(' ' + par) if par else ''} {cname} (", ps, f"{ind});"]
            inserts.append((S["lines"][-1] + 1, block))
            dl, wd = N.decl[W]
            rng = f"[{wd[0]}:{wd[1]}] " if wd else ""
            inserts.append((dl + 1, [f"    wire {rng}{WC};  // {TAG}"]))
            rep.append(dict(relay=inst, copy=cname, sinks=sorted(sinks), readers=len(hit), D=int(c.get("D", 0))))
    lines = [edits.get(j, ln) for j, ln in enumerate(N.lines)]
    for pos, block in sorted(inserts, key=lambda x: -x[0]):
        lines[pos:pos] = block
    return "\n".join(lines), rep


def copies_distinct(text, rep):
    """after reset_replicate: [(relay, copy)] whose inputs are all identical to the original's (flattened synthesis would
    merge the copy back into the relay)"""
    N = Netlist(text)
    bad = []
    for r in rep:
        a, b = N.st[N.by_inst[r["relay"]]]["ports"], N.st[N.by_inst[r["copy"]]]["ports"]
        if all(a.get(p) == e for p, e in b.items() if p != "o"):
            bad.append((r["relay"], r["copy"]))
    return bad


# ---------------------------------------------------------------- generator (plan rows from the bound module + geometry)

def _box_ok(pts, r):
    u = [x + y for x, y in pts]
    v = [x - y for x, y in pts]
    return max(u) - min(u) <= 2 * r + 1e-6 and max(v) - min(v) <= 2 * r + 1e-6


def _flight(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def cluster(src, sinks, limit=LIMIT):
    """sinks {name: (x, y)} -> [[names]]: agglomerative, a cluster is 'near' when it fits one reach box with the source;
    two clusters merge when the union stays near (or, for two far clusters, fits a box by itself), smallest union first"""
    cl = [[n] for n in sorted(sinks)]

    def near(c):
        return src is not None and _box_ok([src] + [sinks[n] for n in c], limit)

    while len(cl) > 1:
        best = None
        for i in range(len(cl)):
            for j in range(i + 1, len(cl)):
                u = cl[i] + cl[j]
                ok = near(u) or (not near(cl[i]) and not near(cl[j]) and _box_ok([sinks[n] for n in u], limit))
                if not ok:
                    continue
                pts = [sinks[n] for n in u]
                span = max(_flight(p, q) for p in pts for q in pts)
                if best is None or span < best[0]:
                    best = (span, i, j)
        if best is None:
            break
        _, i, j = best
        cl[i] = sorted(cl[i] + cl[j])
        del cl[j]
    return cl


class Geometry:
    def __init__(self, plan, tn, N, plan_dir=None):
        self.t = plan["partition_types"][tn]
        self.N = N
        self.plan_dir = plan_dir
        self.hc = {}
        for h in self.t.get("hard_cores", []):
            if "origin_um" not in h:
                continue
            for c in [h["inst"]] + ([h["inst"].split(".", 1)[1]] if "." in h["inst"] else []):
                if "u_" + sid(c) in N.by_inst:
                    self.hc["u_" + sid(c)] = h
                    break
        self._pins = {}

    def pin(self, inst, port):
        """pin centroid of hard-core instance `inst` port (type frame), the core centre without pins, None if not a core"""
        h = self.hc.get(inst)
        if h is None:
            return None
        if inst not in self._pins:
            import relay_depth as RD
            try:
                self._pins[inst] = RD._pin_table(h, self.plan_dir)
            except (OSError, ValueError, KeyError):
                self._pins[inst] = None
        tab = self._pins[inst]
        if tab and port in tab and tab[port]:
            pts = list(tab[port].values())
            return (sum(x for x, _ in pts) / len(pts), sum(y for _, y in pts) / len(pts))
        dx, dy = h.get("track_offset_um", [0.0, 0.0])
        return (h["origin_um"][0] + dx + h["outline_um"][0] / 2, h["origin_um"][1] + dy + h["outline_um"][1] / 2)

    def source(self, expr, depth=0):
        """(label, (x, y)) of the hard-core output driving expr (through assigns and pass-through soft leaves), else None"""
        ids = [i for i in IDENT.findall(re.sub(r"\[[^\]]*\]", "", expr)) if not re.fullmatch(r"\d+'?\w*", i)]
        if len(set(ids)) != 1 or depth > 8:
            return None
        d = self.N.drv.get(ids[0])
        if d is None:
            return None
        s = self.N.st[d[0]]
        if s["kind"] == "assign":
            return self.source(s["rhs"], depth + 1)
        if s["inst"] in self.hc:
            return (f"{s['inst']}.{d[1]}", self.pin(s["inst"], d[1]))
        ins = [s["ports"][p] for p in PASS_IN if p in s["ports"]]
        return self.source(ins[0], depth + 1) if len(ins) == 1 else None


def _copy_name(rel, tag, taken):
    m = re.match(r"^(.*?)((?:_\d+|_sk)?)$", rel)
    base, suf = m.group(1), m.group(2)
    name = f"{base}_{tag}{suf}"
    while name in taken:
        name = f"{base}_{tag}b{suf}"
        tag += "b"
    taken.add(name)
    return name


def branch_rows(plan, tn, text, plan_dir=None, limit=LIMIT):
    """-> (relay_branch rows, relay_depth sink rows for far copies, report) of one type"""
    N = Netlist(text)
    G = Geometry(plan, tn, N, plan_dir)
    rows, drows, rep = [], [], []
    taken = {s["inst"][2:] for s in N.st if s["kind"] != "assign"}
    have_rd = {(sid(r["inst"]), r.get("port", "o")): int(r["D"]) for r in G.t.get("relay_depth") or [] if r.get("side") != "sink"}
    for k, S in enumerate(N.st):
        if S["kind"] != "inst" or not RELAY_MOD.match(S["mod"]):
            continue
        W = S["ports"].get("o", "")
        if not IDENT.fullmatch(W):
            continue
        sinks, ports, soft = {}, defaultdict(set), set()
        for c in N.consumers(W):
            if c == k:
                continue
            for inst, port in N.owners(c, W):
                p = G.pin(inst, port)
                if p is None:
                    soft.add(inst)
                    continue
                ports[inst].add((port, c))
                sinks.setdefault(inst, []).append(p)
        pts = {i: (sum(x for x, _ in v) / len(v), sum(y for _, y in v) / len(v)) for i, v in sinks.items()}
        if len(pts) < 2:
            continue
        src = G.source(S["ports"].get("i", ""))
        sp = src[1] if src else None
        allp = list(pts.values()) + ([sp] if sp else [])
        if _box_ok(allp, limit):
            continue
        cl = cluster(sp, pts, limit)
        if len(cl) < 2:
            rep.append(dict(relay=S["inst"], unfixed="sinks fit no common box but do not split", sinks=sorted(pts)))
            continue
        # the relay keeps the cluster with the most sinks (ties: nearest the source); soft sinks always stay on it
        def key(c):
            return (-len(c), min(_flight(sp, pts[n]) for n in c) if sp else 0.0, c)
        cl.sort(key=key)
        rel = S["inst"][2:]
        copies = []
        for c in cl[1:]:
            tag = sid(re.split(r"_u_|^u_", c[0][2:])[-1]) or "br"
            name = _copy_name(rel, tag, taken)
            L = max(_flight(sp, pts[n]) for n in c) if sp else 0.0
            near = sp is not None and _box_ok([sp] + [pts[n] for n in c], limit)
            # a relay_depth row on the relay (its stages follow the copy's readers) already pays part of the way
            D = 0 if near or sp is None else max(0, max(1, math.ceil(L / limit) - 2) - have_rd.get((sid(rel), "o"), 0))
            span = max(_flight(pts[a], pts[b]) for a in c for b in c)
            copies.append(dict(name=name, sinks=sorted(n[2:] for n in c), D=D, span_um=round(span, 1), path_um=round(L, 1)))
            if D:
                if (sid(rel), "o") in have_rd:     # relay and sink depth rows exclude each other in bind
                    rep.append(dict(relay=S["inst"], copy=name, unfixed=f"D={D} needed but the relay has a relay_depth row"))
                    continue
                for n in c:
                    for port, ck in sorted(ports[n]):
                        e = N.st[ck]["ports"].get(port, "") if N.st[ck]["kind"] != "assign" else ""
                        if N.st[ck]["kind"] == "assign" or not re.fullmatch(re.escape(W) + r"(\[[^\]]*\])?", e):
                            rep.append(dict(relay=S["inst"], copy=name, unfixed=f"D={D}: {n}.{port} is not a whole-port read"))
                            continue
                        drows.append(dict(inst=n[2:], port=port, side="sink", D=min(D, 4), path_um=round(L, 1),
                                          note=f"{TAG}: far branch of {rel} via copy {name}"))
        far = max(_flight(pts[a], pts[b]) for a in pts for b in pts)
        rows.append(dict(inst=rel, copies=copies,
                         note=f"{TAG}: sinks span {far:.0f} um (> one {limit:.0f}-um reach box with the source "
                              f"{src[0] if src else '?'}); kept {sorted(n[2:] for n in cl[0])}"
                              + (f" + soft {sorted(x[2:] for x in soft)}" if soft else "")))
        rep.append(dict(relay=S["inst"], module=S["mod"], source=src[0] if src else None, kept=sorted(cl[0]),
                        copies=[(c["name"], c["sinks"], c["D"], c["span_um"]) for c in copies], soft=sorted(soft)))
    return rows, drows, rep


def _concat_items(expr):
    e = expr.strip()
    if not (e.startswith("{") and e.endswith("}")):
        return [e]
    e, out, depth, cur = e[1:-1], [], 0, ""
    for ch in e:
        if ch in "{(":
            depth += 1
        elif ch in "})":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def _item_width(N, it):
    m = re.fullmatch(r"([A-Za-z_][\w$]*)\s*\[\s*(\d+)\s*(?::\s*(\d+)\s*)?\]", it)
    if m:
        return int(m.group(2)) - int(m.group(3) if m.group(3) is not None else m.group(2)) + 1
    m = re.fullmatch(r"(\d+)'[bdh]\w+", it)
    if m:
        return int(m.group(1))
    if IDENT.fullmatch(it):
        return N.width(it) or 1
    return None


def join_rows(plan, tn, text, plan_dir=None, limit=LIMIT):
    """-> ({conn: [join rows]}, report) for the out-bus station chains of one type"""
    N = Netlist(text)
    G = Geometry(plan, tn, N, plan_dir)
    t = G.t
    out, rep = {}, []
    for e in t.get("internal_stations", []):
        conn = e.get("conn", "")
        if not conn.startswith("bus:") or e.get("core") or len(e.get("regs_um") or []) < 2:
            continue
        bus = conn[4:]
        b = next((x for x in t.get("buses", []) if x["name"] == bus), None)
        if b is None or b.get("dir") != "out" or e.get("bit_route") or "bit_sites_um" in e or "face_bit_sites_um" in e:
            continue
        n = sid(bus)
        if any(re.fullmatch(rf"u_bout_{re.escape(n)}_pad\d+", i) for i in N.by_inst):
            continue
        regs = e["regs_um"][::-1] if str(e.get("launch", "")).startswith("face bus") else e["regs_um"]
        s0 = N.by_inst.get(f"u_ist_{n}_0", N.by_inst.get(f"u_bout_{n}"))
        if s0 is None:
            continue
        items = _concat_items(N.st[s0]["ports"].get("d", ""))
        widths = [_item_width(N, it) for it in items]
        if None in widths:
            rep.append(dict(conn=conn, unfixed="station 0 input has an item of unknown width"))
            continue
        pos, lo = [], 0
        for it, w in reversed(list(zip(items, widths))):
            pos.append((lo, lo + w - 1, it))
            lo += w
        rows = []
        for lo, hi, it in sorted(pos):
            src = G.source(it)
            if not src or src[1] is None:
                continue
            d = [_flight(src[1], r) for r in regs]
            kk = min(range(len(d)), key=d.__getitem__)
            if kk == 0 or d[0] <= limit:
                continue
            if rows and rows[-1]["stage"] == kk and rows[-1]["src"] == src[0] and rows[-1]["bits"][1] == lo - 1:
                rows[-1]["bits"][1] = hi
                continue
            rows.append(dict(bits=[lo, hi], stage=kk, src=src[0], src_um=[round(src[1][0], 3), round(src[1][1], 3)],
                             stage0_um=round(d[0], 1), stage_um=round(d[kk], 1)))
        if rows:
            out[conn] = rows
            rep.append(dict(conn=conn, joins=rows))
    return out, rep


# ---------------------------------------------------------------- 3. in-bus trunk aim (FABLE-FIX-S81-COLH9R1 11-19 pattern)

def deep_pins(N, G, k, w, depth=0, seen=None):
    """hard-core sink pin points reached from statement k reading w (through assigns, one-line stages and soft multi-line
    leaves such as relays and seams, <= 4 leaves deep)"""
    seen = set() if seen is None else seen
    pts = []
    for inst, port in N.owners(k, w):
        if inst in seen:
            continue
        seen.add(inst)
        p = G.pin(inst, port)
        if p is not None:
            pts.append(p)
            continue
        if depth >= 4 or inst not in N.by_inst:
            continue
        si = N.by_inst[inst]
        for _op, e in N.st[si]["ports"].items():
            if IDENT.fullmatch(e) and N.drv.get(e, (None,))[0] == si:
                for c in N.consumers(e):
                    pts += deep_pins(N, G, c, e, depth + 1, seen)
    return pts


def _boxes(t, halo):
    return [(h["origin_um"][0] - halo, h["origin_um"][1] - halo, h["origin_um"][0] + h["outline_um"][0] + halo,
             h["origin_um"][1] + h["outline_um"][1] + halo) for h in t.get("hard_cores", []) if "origin_um" in h]


def _inside(boxes, p):
    return any(x0 < p[0] < x1 and y0 < p[1] < y1 for x0, y0, x1, y1 in boxes)


def _free(t, boxes, p, grid=4.32):
    w, h = t.get("outline_um", [1e9, 1e9])
    snap = (round(p[0] / grid) * grid, round(p[1] / grid) * grid)
    for r in range(0, 40):
        for dx, dy in ((0, 0),) if r == 0 else ((r, 0), (-r, 0), (0, r), (0, -r), (r, r), (-r, -r), (r, -r), (-r, r)):
            q = (round(snap[0] + dx * grid, 3), round(snap[1] + dy * grid, 3))
            if 0 <= q[0] <= w and 0 <= q[1] <= h and not _inside(boxes, q):
                return [q[0], q[1]]
    return None


def _lpath(a, b, boxes, n):
    """n points at j / (n + 1) of the Manhattan L path a -> b, the leg order with fewer points inside a hard core"""
    best = None
    for corner in ((b[0], a[1]), (a[0], b[1])):
        legs = [(a, corner), (corner, b)]
        tot = sum(_flight(p, q) for p, q in legs)
        pts = []
        for j in range(1, n + 1):
            d = tot * j / (n + 1)
            for p, q in legs:
                L = _flight(p, q)
                if d <= L or (p, q) == legs[-1]:
                    f = d / L if L else 0.0
                    pts.append((p[0] + (q[0] - p[0]) * f, p[1] + (q[1] - p[1]) * f))
                    break
                d -= L
        hits = sum(_inside(boxes, p) for p in pts)
        if best is None or hits < best[0]:
            best = (hits, pts)
    return best[1]


def trunk_rows(plan, tn, text, plan_dir=None, limit=LIMIT, halo=5.0):
    """in-bus lane-pad chains (u_lpad_<bus>, ot_dp_dly D = number of planned stations) whose stations head away from where
    most bits end: the stations are re-sited on the L path from_um -> bit-weighted centroid of the majority sink cluster;
    the minority bits (a 1-bit reset capture, small slices) keep the OLD sites through per-flop relay_sites
    (u_lpad_<bus>.r[j][b], last stage .q[b]).  0 added cycles, no RTL.  -> ({conn: row}, report)"""
    N = Netlist(text)
    G = Geometry(plan, tn, N, plan_dir)
    t = G.t
    boxes = _boxes(t, halo)
    out, rep = {}, []
    for e in t.get("internal_stations", []):
        conn = e.get("conn", "")
        if not conn.startswith("bus:") or e.get("core") or e.get("bit_route") or "bit_sites_um" in e:
            continue
        b = next((x for x in t.get("buses", []) if x["name"] == conn[4:]), None)
        if b is None or b.get("dir") != "in":
            continue
        n = sid(conn[4:])
        k = N.by_inst.get(f"u_lpad_{n}")
        if k is None or N.st[k]["mod"] != "ot_dp_dly":
            continue
        m = re.search(r"\.D\((\d+)\)", N.st[k]["par"])
        D, regs, Q = int(m.group(1)) if m else 0, e.get("regs_um") or [], f"{n}_q"
        if D != len(regs) or Q not in N.decl or "from_um" not in e:
            rep.append(dict(conn=conn, unfixed=f"lane pad D {D} vs {len(regs)} planned stations"))
            continue
        W = N.width(Q) or 1
        sl = []
        for c in N.consumers(Q):
            if c == k:
                continue                                    # the lane pad itself drives Q inside its .q concat
            s = N.st[c]
            exprs = [s["rhs"]] if s["kind"] == "assign" else [v for p_, v in s["ports"].items() if p_ not in OUT_PORTS]
            pts = None
            for ex in exprs:
                for mm in re.finditer(rf"\b{re.escape(Q)}\b\s*(?:\[\s*(\d+)\s*(?::\s*(\d+)\s*)?\])?", ex):
                    hi = int(mm.group(1)) if mm.group(1) else W - 1
                    lo = int(mm.group(2)) if mm.group(2) else (hi if mm.group(1) else 0)
                    pts = deep_pins(N, G, c, Q) if pts is None else pts
                    sl.append((lo, hi, pts))
        cen = {i: (sum(x for x, _ in p) / len(p), sum(y for _, y in p) / len(p)) for i, (_lo, _hi, p) in enumerate(sl) if p}
        if not cen:
            continue
        cl = cluster(None, cen, limit)
        bits = [sum(sl[i][1] - sl[i][0] + 1 for i in c) for c in cl]
        M = cl[max(range(len(cl)), key=bits.__getitem__)]
        wsum = sum(sl[i][1] - sl[i][0] + 1 for i in M)
        C = (sum(cen[i][0] * (sl[i][1] - sl[i][0] + 1) for i in M) / wsum,
             sum(cen[i][1] * (sl[i][1] - sl[i][0] + 1) for i in M) / wsum)
        if _flight(regs[-1], C) <= limit:
            continue
        new = [_free(t, boxes, p) for p in _lpath(tuple(e["from_um"]), C, boxes, D)]
        if None in new:
            rep.append(dict(conn=conn, unfixed="no free site for a re-aimed station"))
            continue
        if _flight(new[-1], C) > limit:
            rep.append(dict(conn=conn, unfixed=f"re-aimed last station still {_flight(new[-1], C):.0f} um from the majority sinks"))
            continue
        minor = sorted((sl[i][0], sl[i][1]) for i in range(len(sl)) if i not in M)
        have = set(t.get("relay_sites") or {})
        sites = {}
        for lo, hi in minor:
            for bit in range(lo, hi + 1):
                for j in range(D):
                    key = f"u_lpad_{n}.r[{j}][{bit}]" if j < D - 1 else f"u_lpad_{n}.q[{bit}]"
                    if key not in have:
                        sites[key] = list(regs[j])
        row = dict(regs_um=new, to_um=[round(C[0], 3), round(C[1], 3)], old_regs_um=regs, majority_bits=wsum,
                   minority=[list(x) for x in minor], relay_sites=sites,
                   old_last_um=round(_flight(regs[-1], C), 1), new_last_um=round(_flight(new[-1], C), 1))
        out[conn] = row
        rep.append(dict(conn=conn, trunk=dict((k_, v) for k_, v in row.items() if k_ != "relay_sites"), sites=len(sites)))
    return out, rep


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan")
    ap.add_argument("type_re")
    ap.add_argument("bound_dir")
    ap.add_argument("--plan-dir")
    ap.add_argument("--limit", type=float, default=LIMIT)
    ap.add_argument("--out-plan")
    ap.add_argument("--report")
    a = ap.parse_args(argv[1:])
    plan = json.loads(Path(a.plan).read_text())
    plan_dir = Path(a.plan_dir or Path(a.plan).resolve().parent)
    reports = []
    for tn in sorted(plan["partition_types"]):
        if not re.search(a.type_re, tn):
            continue
        f = next((q for q in (Path(a.bound_dir) / f"{tn}_bound.sv", Path(a.bound_dir) / f"{tn}.sv") if q.is_file()), None)
        if f is None:
            reports.append(dict(type=tn, error="no bound module"))
            continue
        text = f.read_text()
        t = plan["partition_types"][tn]
        rows, drows, rep = branch_rows(plan, tn, text, plan_dir, a.limit)
        joins, jrep = join_rows(plan, tn, text, plan_dir, a.limit)
        trunks, trep = trunk_rows(plan, tn, text, plan_dir, a.limit)
        if a.out_plan:
            if rows:
                t["relay_branch"] = rows
            else:
                t.pop("relay_branch", None)
            if drows:
                cur = t.setdefault("relay_depth", [])
                keys = {(sid(r["inst"]), r.get("port"), r.get("side")) for r in cur}
                cur += [r for r in drows if (sid(r["inst"]), r["port"], "sink") not in keys]
            for e in t.get("internal_stations", []):
                if e.get("conn") in joins:
                    e["join"] = joins[e["conn"]]
                tr = trunks.get(e.get("conn"))
                if tr and e["regs_um"] == tr["old_regs_um"]:
                    e["regs_um"], e["to_um"] = tr["regs_um"], tr["to_um"]
                    e["note"] = e.get("note", "") + (f" | {TAG} trunk: stations re-aimed at the bit-weighted sink centroid of "
                                                     f"{tr['majority_bits']} bits (0 cycles); minority bits {tr['minority']} keep "
                                                     "the old sites by relay_sites")
                    t.setdefault("relay_sites", {}).update(tr["relay_sites"])
        reports.append(dict(type=tn, relay_branch=rows, relay_depth_sink=drows, joins=joins,
                            trunks={c: dict((k, v) for k, v in r.items() if k != "relay_sites") for c, r in trunks.items()},
                            detail=rep + jrep + trep))
        nc = sum(len(r["copies"]) for r in rows)
        print(f"{tn}: {len(rows)} relay(s) split, {nc} cop(ies) ({sum(1 for r in rows for c in r['copies'] if c['D'])} far, "
              f"+cycles), {sum(len(v) for v in joins.values())} station join(s)")
        for r in rows:
            for c in r["copies"]:
                print(f"    {r['inst']} -> {c['name']} sinks {c['sinks']} D={c['D']} span {c['span_um']} path {c['path_um']}")
        for conn, tr in trunks.items():
            print(f"    {conn} trunk -> {tr['to_um']} ({tr['majority_bits']} bits; last station {tr['old_last_um']} -> "
                  f"{tr['new_last_um']} um), minority {tr['minority']} keep old sites ({len(tr['relay_sites'])} relay_sites)")
        for conn, js in joins.items():
            for j in js:
                print(f"    {conn} bits {j['bits']} from {j['src']} -> stage {j['stage']} ({j['stage0_um']} -> {j['stage_um']} um)")
    if a.out_plan:
        Path(a.out_plan).write_text(json.dumps(plan, indent=1))
    if a.report:
        Path(a.report).write_text(json.dumps(reports, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
