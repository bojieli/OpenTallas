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
    planned = planned_ends(t)
    for fp in files:
        try:
            with open(fp, errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        insts, assigns = parse_wrapper(text)
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

        def sources(expr, depth=0, seen=None):
            seen = set() if seen is None else seen
            out = []
            for nm, lo, hi in _idents(expr):
                if SKIP_NET.match(nm) or nm in seen:
                    continue
                if nm in drv:
                    out.extend(drv[nm])
                elif nm in alias and depth < TRACE_DEPTH:
                    seen.add(nm)
                    for r in alias[nm]:
                        out.extend(sources(r, depth + 1, seen))
            return out

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
                    if a and not b and _is_soft(insts, name, hard, nested):
                        soft.setdefault(name, []).append((a, al, nb, "in", p))
                    if b and not a and _is_soft(insts, sn, hard, nested):
                        soft.setdefault(sn, []).append((b, bl, nb, "out", sp))
                    if not a or not b:
                        continue
                    stats["judged"] += 1
                    d = _man(a, b)
                    if d > reach and not _is_planned(planned, al, bl):
                        k = (al, bl)
                        if k not in hops or hops[k][0] < d:
                            hops[k] = (d, a, b)
        # SOFT: a soft leaf with no plan seat sits (placer-like) at the bit-weighted centroid of its judged register ends
        seated = {k.split(".", 1)[0] for k in rs if "." in k.split("/", 1)[0]} if rs else set()
        for sn, ends in soft.items():
            if sn in seated:                       # the plan seats this soft core's registers (relay_sites): not estimated
                continue
            agg = {}
            for pos, lab, nb, dr, port in ends:
                r = agg.setdefault((lab, dr, port), [pos, 0])
                r[1] += nb
            tot = sum(v[1] for v in agg.values())
            if len(agg) < 2 or not tot:
                continue
            cx = sum(v[0][0] * v[1] for v in agg.values()) / tot
            cy = sum(v[0][1] * v[1] for v in agg.values()) / tot
            sp_ = insts[sn][1] or sn
            for (lab, dr, port), (pos, nb) in agg.items():
                d = _man((cx, cy), pos)
                if d > reach and "." in lab:      # legs to hard-core pins only (a face leg is the leaf's own I/O flop)
                    sl = f"{sp_}.{port} (soft, est. seat ({_f(cx)},{_f(cy)}) = centroid of {len(agg)} ends)"
                    k = (lab, sl) if dr == "in" else (sl, lab)
                    if k not in softhops or softhops[k][0] < d:
                        softhops[k] = (d, nb)
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
    for (al, bl), (d, a, b) in hops.items():
        rows.append(dict(type=tn, family=family(tn), kind="HOP", src=al, dst=bl, len_um=round(d, 1),
                         stations=int(math.ceil(d / reach)) - 1, over_ps=round((d - reach) * PS_PER_UM),
                         a=a, b=b))
    for (al, bl), (d, nb) in softhops.items():
        rows.append(dict(type=tn, family=family(tn), kind="SOFT", src=al, dst=bl, len_um=round(d, 1),
                         stations=int(math.ceil(d / reach)) - 1, over_ps=round((d - reach) * PS_PER_UM), a=None, b=None))
    for (ca, cb), (d, n, ex) in dups.items():
        rows.append(dict(type=tn, family=family(tn), kind="DUPSTN", src=f"{ca} (e.g. {ex[0]}_*)",
                         dst=f"{cb} (e.g. {ex[1]}_*; {n} duplicate stations on shared d)", len_um=round(d, 1),
                         stations=0, over_ps=round(d * PS_PER_UM), a=None, b=None))
    return rows


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
        rr, st = rows(raw, plan_path, tree, bind_out, **kw)
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
            elif r["kind"] == "SOFT":
                out.append(f"WARN {CHECK} {r['type']}: SOFT {r['src']} -> {r['dst']} is one cycle with no station (estimate: "
                           f"the soft leaf has no plan seat): {_f(r['len_um'])} um > reach {reach:g} (~{r['over_ps']} ps over); "
                           f"fix: +{r['stations']} station(s) on the leg, or a place_region / relay seat for the leaf near this end")
            else:
                out.append(f"WARN {CHECK} {r['type']}: DUPSTN {r['src']} / {r['dst']}: duplicate ot_dp_dly stations "
                           f"on the same source bits, sinks {_f(r['len_um'])} um apart (~{r['over_ps']} ps of wire added to the far sink if merged); synthesis merges them unless kept, "
                           f"then one station drives both sinks; fix: OT_KEEP_WIRES += ot_dp_dly:r for the type, or one station per sink side "
                           f"with distinct d")
        if rr:
            nh = sum(1 for r in rr if r["kind"] == "HOP")
            ns = sum(1 for r in rr if r["kind"] == "SOFT")
            out.append(f"WARN {CHECK} summary: {nh} direct one-cycle hop(s) > {reach:g} um in "
                       f"{len({r['type'] for r in rr if r['kind'] == 'HOP'})} type(s) / "
                       f"{len({r['family'] for r in rr if r['kind'] == 'HOP'})} families, {ns} SOFT estimate(s) in "
                       f"{len({r['type'] for r in rr if r['kind'] == 'SOFT'})} type(s), "
                       f"{len(rr) - nh - ns} DUPSTN group(s); {st['judged']} hop(s) judged over {st['bound']}/{st['types']} bound types "
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
                f.write(f"{sha}\t{r['type']}\t{r['family']}\t{src}\t{r['dst']}\t{r['len_um']}\t{r['stations']}\t{r['over_ps']}\n")
        print(f"# {len(rr or [])} rows -> {opts['tsv']} ({st})")
    for ln in findings(raw, a[0], tree, opts.get("bind_out"), max_lines=100000 if "--all" in sys.argv else None, **kw):
        print(ln)
    print(f"# load {t1 - t0:.1f} s, check {time.time() - t1:.2f} s")
