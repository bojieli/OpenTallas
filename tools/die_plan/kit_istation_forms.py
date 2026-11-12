#!/usr/bin/env python3
"""HBM-KITIST-1 11-12 (DIE-HBM-100): two OPT-IN station forms for kit_istations.py (default off: a plan without the keys
below, or --no-station-forms, leaves kit_istations byte-identical).

Both forms keep the lane's cycles per bus bit and every register-to-register hop of the plan; they change WHERE the
registers are and HOW MANY of them each bus bit carries inside one partition type.  Registers are emitted as exact-width
ot_dp_st stages (W = bits present in that stage), so nothing relies on synthesis dropping constant flops behind the
keep_hierarchy boundary of ot_dp_st.

(1) pad_landing -- per-bit station depth (q_b001 / q_b002 cell cut; DIE-LAYOUT-HBM qb001_padspec)
    partition_types[T].pad_landing = [ {bus, bit_depth:[[lo,hi,d],...], stage_sites_um?} ]
    kit_istations merges the capture-group rows of a bus into ONE chain of K stations (K = len of the deepest
    regs_um, bind pads included) that all W bits traverse.  bit_depth gives each payload bit b its own station count d_b:
      out bus  bit b enters the chain at stage S-d_b (S = max(K, max d_b)) and leaves through the last stage; the epoch
               flop chain is K deep (stages S-K..S-1; earlier stages carry a dead 1-bit epoch flop);
      in bus   bit b is read at stage d_b-1 (d_b = 0: the face register); the reader epoch is the one of stage K-1;
               stages beyond K carry only the bits with larger d_b.
    d_b < K removes K-d_b registers of bit b here; the neighbour type of the lane carries d'_b = K' + (K - d_b), so
    d_src(b) + d_dst(b) = K_src + K_dst for every bit (check_pair): per-bit cycles and the seam bit order are unchanged.
    The L71 hoist-before-fanout is the in-bus case: q_b001 L71_i d_b = K - h(b), q_b002 L71_o d_b = K' + h(b).
    Sites: bit b's stations sit at the spread of its owner core's row path (rows + bit->core owner from the bound RTL,
    kit_bus_bitgroups), or `stage_sites_um` when given; a stage with no site floats to GPL.
    bit_depth_from_rows() is the legal maximum (d_b = max reach_need over the owner rows) -- the plan side bakes the
    two tables (both sides must agree).

(2) station_trees -- shared registered trunk + per-core branches (q_b000 L65_i / L14_o)
    partition_types[T].station_trees = [ {bus, nodes:[{id,parent,site_um}], readers:[{node,core?,prefix?,bits?}]  (in)
                                              / sources:[{node,core?,prefix?,bits?}]  (out)} ]
    A node is ONE ot_dp_st stage (exact width = bits of the readers below it / sources at or below it).  In bus: the root
    (parent null) is fed by the face register (or the last bind pad); a reader reads its node's q.  Out bus: a source
    enters its bits at a node, a node merges its children and own sources, the root feeds u_bout.  Every reader / source
    is exactly K stations from the face (K = len(deepest regs_um) incl. bind pads): one bus = one latency.
    A bit shared by several cores is one flop on the trunk, not one flop at the mean site of all cores; a core near the
    face reads a branch that carries the K-depth delay registers beside the core.
    Attribution of a read to a reader: instance block `u_<core flat>` ports, else an identifier prefix (w_/g_<core
    flat>_..., or the entry's explicit `prefix` list); a read no reader owns fails closed.
Report rows (kit_rtl.json kit_istations[]) carry stage widths and flops before / after."""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_rtl  # noqa: E402
import kit_bus_bitgroups as BG  # noqa: E402

REACH_UM = 360.0


class FormError(SystemExit):
    pass


def _fail(tn, bus, msg):
    raise FormError(f"kit_istations: {tn} {bus}: {msg}")


# ---------------------------------------------------------------- run tables / pure helpers
def expand_runs(runs, W, what="bit_depth"):
    """[[lo,hi,v],...] -> list of W values; fail closed on overlap, range, gaps"""
    out = [None] * W
    for r in runs:
        lo, hi, v = int(r[0]), int(r[1]), r[2]
        if not 0 <= lo <= hi < W:
            raise ValueError(f"{what}: run [{lo},{hi}] outside 0..{W - 1}")
        for b in range(lo, hi + 1):
            if out[b] is not None:
                raise ValueError(f"{what}: bit {b} in two runs")
            out[b] = v
    miss = [b for b in range(W) if out[b] is None]
    if miss:
        raise ValueError(f"{what}: bits {miss[:8]}{'...' if len(miss) > 8 else ''} not covered")
    return out


def compress_runs(vals):
    out = []
    for b, v in enumerate(vals):
        if v is None:
            continue
        if out and out[-1][1] == b - 1 and out[-1][2] == v:
            out[-1][1] = b
        else:
            out.append([b, b, v])
    return out


def check_pair(k_src, d_src, k_dst, d_dst):
    """bits whose cycles change across a seam: d_src(b) + d_dst(b) != k_src + k_dst (empty list = preserved)"""
    if len(d_src) != len(d_dst):
        return list(range(min(len(d_src), len(d_dst)), max(len(d_src), len(d_dst))))
    return [b for b, (a, c) in enumerate(zip(d_src, d_dst)) if a + c != k_src + k_dst]


def peer_depth(k, d, k_peer):
    """neighbour-type depths that keep the lane's cycles when this side carries d of its k"""
    return [k_peer + (k - x) for x in d]


def reach_need(frm, to, reach=REACH_UM):
    """registers a row needs for hops <= reach: ceil(manhattan / reach) - 1"""
    d = abs(frm[0] - to[0]) + abs(frm[1] - to[1])
    return max(0, int(-(-d // reach)) - 1) if d > 0 else 0


def bit_depth_from_rows(rows, owners, W, k, hard=(), reach=REACH_UM):
    """legal maximum landing: d_b = max over owner rows of reach_need, clipped to <= k; unresolved bits keep k"""
    need = {}
    for e in rows:
        c = BG.core_of_entry(e, hard)
        if c is None or not e.get("from_um") or not e.get("to_um"):
            continue
        need[c] = max(need.get(c, 0), reach_need(e["from_um"], e["to_um"], reach))
    out = []
    for b in range(W):
        cs = [c for c in owners.get(b, ()) if c in need]
        out.append(min(k, max(need[c] for c in cs)) if cs else k)
    return out


def cat(refs):
    """MSB-first [(name, idx|None)] -> RTL expression; consecutive descending bits of one name fold to name[hi:lo]"""
    parts, i = [], 0
    while i < len(refs):
        nm, ix = refs[i]
        if ix is None:
            parts.append(nm)
            i += 1
            continue
        j = i
        while (j + 1 < len(refs) and refs[j + 1][0] == nm and refs[j + 1][1] is not None
               and refs[j + 1][1] == refs[j][1] - 1):
            j += 1
        parts.append(f"{nm}[{ix}]" if j == i else f"{nm}[{ix}:{refs[j][1]}]")
        i = j + 1
    return parts[0] if len(parts) == 1 and not parts[0].startswith("{") else "{" + ", ".join(parts) + "}"


def _is_decl(ln):
    return re.match(r"^\s*(wire|reg|logic)\b", ln) is not None


def _bout_line(txt, n, W):
    return re.search(rf"^(\s*ot_dp_ste?\s+#\(\.W\({W}\)\)\s+u_bout_{re.escape(n)}\s*\(.*?\.d\()(\{{[^}}]*\}}|[^)]*)"
                     rf"(\),\s*\.ea\()([^)]*)(\).*)$", txt, re.M)


def out_refs(txt, d0, W, tn, bus):
    """u_bout .d expression -> LSB-first [(name, idx|None)] for each of the W bits"""
    width = BG.Netlist(txt).width
    els = BG.split_concat(d0.strip())
    if els is None:
        _fail(tn, bus, "u_bout d not a flat concatenation")
    msb = []
    for el in els:
        ps = re.fullmatch(r"([\w$]+)\s*\[(\d+):(\d+)\]", el)
        sb = re.fullmatch(r"([\w$]+)\s*\[(\d+)\]", el)
        if ps:
            msb += [(ps.group(1), x) for x in range(int(ps.group(2)), int(ps.group(3)) - 1, -1)]
        elif sb:
            msb.append((sb.group(1), int(sb.group(2))))
        elif re.fullmatch(r"[\w$]+", el) and width.get(el):
            w = width[el]
            msb += [(el, x if w > 1 else None) for x in range(w - 1, -1, -1)]
        else:
            msb.append((el, None))              # literal such as 1'b0
    if len(msb) != W:
        _fail(tn, bus, f"u_bout d has {len(msb)} bits != {W} (unresolvable whole-wire reference)")
    return msb[::-1]


def _station(tag, w, d, ea, qn, eqn, note="kit_istations: FIRM plan station"):
    return (f"    ot_dp_st #(.W({w})) u_ist_{tag} (.clk(clk), .rst_n(rst_n), .d({d}), .ea({ea}), "
            f".q({qn}), .eq({eqn}));  // {note}")


def _decl(qn, eqn, w):
    return f"    wire [{w - 1}:0] {qn};\n    wire {eqn};  // kit_istations"


def _bus_rows(t, bus):
    return [e for e in t.get("internal_stations", []) if e.get("conn") == "bus:" + bus]


def _planned_k(t, bus, tn):
    rows = _bus_rows(t, bus)
    if not rows:
        _fail(tn, bus, "no internal_stations rows (planned station count unknown)")
    return max(len(e["regs_um"]) for e in rows)


def _row_regs(e, in_bus):
    """(path, regs) of a plan row ordered face->core (in bus) / core->face (out bus)"""
    p = [tuple(e["from_um"])] + [tuple(r) for r in e["regs_um"]] + [tuple(e["to_um"])]
    regs = [tuple(r) for r in e["regs_um"]]
    face_first = str(e.get("launch", "")).startswith("face bus")
    if face_first != in_bus:
        p, regs = p[::-1], regs[::-1]
    return p, regs


def pad_stage_plan(W, k, d, in_bus, have=0):
    """-> dict(S, sets=[sorted bits per stage], pos=[{bit: idx}]).  out: bit b in stages S-d_b..S-1; in: stages 0..d_b-1
    (stages < have are the full-width bind pads)."""
    S = max([k] + list(d))
    sets = []
    for j in range(S):
        if in_bus and j < have:
            sets.append(list(range(W)))
        elif in_bus:
            sets.append([b for b in range(W) if d[b] > j])
        else:
            sets.append([b for b in range(W) if S - d[b] <= j])
    return dict(S=S, sets=sets, pos=[{b: i for i, b in enumerate(s)} for s in sets])


# ---------------------------------------------------------------- pad_landing
def pad_landing(tn, t, bus_name, entry, txt, man, tcl, rep, bound_bus_width):
    b = next((x for x in t["buses"] if x["name"] == bus_name), None)
    if b is None:
        _fail(tn, bus_name, "pad_landing on unknown bus")
    in_bus = b["dir"] == "in"
    n = gen_rtl.sv_id(bus_name)
    W = bound_bus_width(tn, b, txt, man)
    try:
        dl = expand_runs(entry["bit_depth"], W)
    except ValueError as ex:
        _fail(tn, bus_name, str(ex))
    if any(not isinstance(x, int) or x < 0 for x in dl):
        _fail(tn, bus_name, "bit_depth must be non-negative integers")
    k = _planned_k(t, bus_name, tn)
    if re.search(rf"\bu_ist_{re.escape(n)}_(\d+)\b", txt) or re.search(rf"\bu_ist_{re.escape(n)}_t", txt):
        _fail(tn, bus_name, "stations already inserted (run on a fresh kit-rtl copy)")
    pads = sorted(int(m) for m in re.findall(rf"\bu_b(?:in|out)_{re.escape(n)}_pad(\d+)\b", txt))
    have = len(pads)
    if have and not in_bus:
        _fail(tn, bus_name, "pad_landing on an out bus with bind pads is not supported (fail closed)")
    if have > k:
        _fail(tn, bus_name, f"bound module has {have} pad stages > {k} planned")
    sp = pad_stage_plan(W, k, dl, in_bus, have)
    S, sets, pos = sp["S"], sp["sets"], sp["pos"]
    hard = [h["inst"] for h in t.get("hard_cores", [])]
    rows = _bus_rows(t, bus_name)
    cores = sorted({BG.core_of_entry(e, hard) for e in rows} - {None})
    owners = (BG.in_bit_owners(txt, n, cores) if in_bus else BG.out_bit_owners(txt, n, W, cores)) if cores else None
    owner_row = {}
    for e in rows:
        c = BG.core_of_entry(e, hard)
        if c and c not in owner_row and e.get("from_um") and e.get("to_um"):
            owner_row[c] = _row_regs(e, in_bus)
    deep = next((e for e in rows if len(e["regs_um"]) == k and e.get("from_um") and e.get("to_um")), None)
    merged = _row_regs(deep, in_bus) if deep else None
    explicit = entry.get("stage_sites_um")
    if explicit is not None and len(explicit) not in (S, S - have):
        _fail(tn, bus_name, f"stage_sites_um has {len(explicit)} entries, chain has {S} stages ({have} bind pads)")

    def site_of(j, bit):
        if explicit is not None:
            jj = j - (S - len(explicit))
            return tuple(explicit[jj]) if 0 <= jj < len(explicit) else None
        d = dl[bit]
        cs = sorted(c for c in (owners or {}).get(bit, ()) if c in owner_row)
        pr = owner_row[cs[0]] if cs else merged
        if pr is None or d <= 0:
            return None
        idx = j if in_bus else j - (S - d)
        path, regs = pr
        return regs[idx] if len(regs) == d else BG.spread(path, d)[idx]

    decl, body, names = [], [], []
    if in_bus:
        face = (f"{n}_q", f"{n}_eq")
        pq = [(f"{n}_p{p}_q", f"{n}_p{p}_eq") for p in pads]
        last_q, last_eq = pq[-1] if pq else face
        qname, eqname = {j: pq[j][0] for j in range(have)}, {j: pq[j][1] for j in range(have)}
        for j in range(have, S):
            w = len(sets[j])
            qn, eqn = f"{n}_is{j}_q", f"{n}_is{j}_eq"
            if w == 0:
                _fail(tn, bus_name, f"stage {j} carries no bit (bit_depth leaves a gap)")
            if j == have:
                src = [(last_q, bit) for bit in reversed(sets[j])]
                ea = last_eq
            else:
                src = [(qname[j - 1], pos[j - 1][bit]) for bit in reversed(sets[j])]
                ea = eqname[j - 1]
            decl.append(_decl(qn, eqn, w))
            body.append(_station(f"{n}_{j}", w, cat(src), ea, qn, eqn))
            names.append(f"u_ist_{n}_{j}")
            qname[j], eqname[j] = qn, eqn

        def read_ref(bit):
            dd = dl[bit]
            if dd == 0:
                return (face[0], bit)
            j = dd - 1
            return (qname[j], bit if j < have else pos[j][bit])
        eq_new = eqname[k - 1] if k >= 1 else face[1]
        qre = re.compile(rf"\b{re.escape(last_q)}(?:\[(\d+)(?::(\d+))?\])?(?![\w$\[])")
        out = []
        for ln in txt.splitlines(keepends=True):
            if re.search(rf"\bu_bin_{re.escape(n)}(_pad\d+)?\s*\(", ln) or _is_decl(ln):
                out.append(ln)
                continue

            def sub(m):
                if m.group(1) is None:
                    lo, hi = 0, W - 1
                elif m.group(2) is None:
                    lo = hi = int(m.group(1))
                else:
                    hi, lo = max(int(m.group(1)), int(m.group(2))), min(int(m.group(1)), int(m.group(2)))
                return cat([read_ref(bit) for bit in range(hi, lo - 1, -1)])
            ln = qre.sub(sub, ln)
            ln = re.sub(rf"\b{re.escape(last_eq)}\b", eq_new, ln)
            out.append(ln)
        txt = "".join(out)
        txt = re.sub(r"(\n\s*endmodule\b)", "\n" + "\n".join(decl + body) + r"\1", txt, count=1)
    else:
        m = _bout_line(txt, n, W)
        if not m:
            _fail(tn, bus_name, f"no u_bout_{n} face register line to feed")
        raw = out_refs(txt, m.group(2), W, tn, bus_name)
        ea0 = m.group(4)
        cur = {}
        for j in range(S):
            w = len(sets[j])
            qn, eqn = f"{n}_is{j}_q", f"{n}_is{j}_eq"
            if w == 0:                          # epoch-only stage: one dead data flop keeps the K-deep epoch chain
                src, w = [("1'b0", None)], 1
            else:
                src = [cur[bit] if bit in cur else raw[bit] for bit in reversed(sets[j])]
            ea = "1'b0" if j < S - k else (ea0 if j == S - k else f"{n}_is{j - 1}_eq")
            decl.append(_decl(qn, eqn, w))
            body.append(_station(f"{n}_{j}", w, cat(src), ea, qn, eqn))
            names.append(f"u_ist_{n}_{j}")
            for bit in sets[j]:
                cur[bit] = (qn, pos[j][bit])
        eq_final = ea0 if k == 0 else f"{n}_is{S - 1}_eq"
        dfin = cat([cur.get(bit, raw[bit]) for bit in range(W - 1, -1, -1)])
        line = re.sub(r"^(\s*)ot_dp_ste\b", r"\1ot_dp_st", m.group(1) + dfin + m.group(3) + eq_final + m.group(5))
        txt = txt[:m.start()] + line + txt[m.end():]
        txt = re.sub(r"(\n\s*endmodule\b)", "\n" + "\n".join(decl + body) + r"\1", txt, count=1)
    # --- sites: per stage per narrow index
    if BG.BITS_TCL not in tcl:
        tcl.append(BG.BITS_TCL)
    for j in range(have if in_bus else 0, S):
        per = {}
        for bit in sets[j]:
            xy = site_of(j, bit)
            if xy is not None:
                per[pos[j][bit]] = (round(xy[0], 3), round(xy[1], 3))
        rs = " ".join("{%d %d %0.9g %0.9g}" % r for r in BG._runs(per, len(sets[j])))
        if rs:
            tcl.append(f"is_place_bits {{*u_ist_{n}_{j}[./]*}} {{0 0}} ist:{bus_name} {{{rs}}}")
    rep.append(dict(conn="bus:" + bus_name, planned=k, bound_pads=have, inserted=len(names), stations=names,
                    plan_width=b["width"], bound_width=W,
                    pad_landing=dict(dir=b["dir"], stages=S, stage_widths=[len(s) for s in sets],
                                     bit_depth=compress_runs(dl), data_flops_single_chain=W * k,
                                     data_flops=sum(len(s) for s in sets[have:]) + W * have if in_bus else sum(dl),
                                     owners_resolved=sum(1 for bit in range(W) if (owners or {}).get(bit)),
                                     sites="explicit" if explicit is not None else ("owner-row" if owners else "merged"))))
    return txt


# ---------------------------------------------------------------- station_trees
def tree_check(tn, bus, nodes, k, have, leaf_nodes):
    ids = [x["id"] for x in nodes]
    if not ids or len(set(ids)) != len(ids):
        _fail(tn, bus, "tree nodes: empty or duplicate ids")
    par = {x["id"]: x.get("parent") for x in nodes}
    roots = [i for i, p in par.items() if p is None]
    if len(roots) != 1:
        _fail(tn, bus, f"tree must have exactly one root (got {roots})")
    if any(p is not None and p not in par for p in par.values()):
        _fail(tn, bus, "tree node with unknown parent")
    depth = {}

    def dep(i, seen=()):
        if i in depth:
            return depth[i]
        if i in seen:
            _fail(tn, bus, "tree has a cycle")
        depth[i] = 1 + (dep(par[i], seen + (i,)) if par[i] is not None else 0)
        return depth[i]
    for i in ids:
        dep(i)
    for lf in leaf_nodes:
        if lf not in par:
            _fail(tn, bus, f"reader/source on unknown node {lf}")
        if depth[lf] + have != k:
            _fail(tn, bus, f"node {lf} is {depth[lf] + have} stations from the face, bus latency is {k} "
                           "(one bus = one latency)")
    return par, depth


def _bits_of(spec, W):
    out = set()
    for r in spec:
        lo, hi = (int(r[0]), int(r[1])) if isinstance(r, (list, tuple)) else (int(r), int(r))
        if not 0 <= lo <= hi < W:
            raise ValueError(f"bits [{lo},{hi}] outside 0..{W - 1}")
        out.update(range(lo, hi + 1))
    return out


def _inst_reader(inst, atts):
    for a in atts:
        c = a.get("core")
        if c and inst in ("u_" + BG.flat_of(c), BG.flat_of(c), c):
            return a["name"]
        if any(inst.startswith(p) for p in a.get("prefix", [])):
            return a["name"]
    return None


def _ident_readers(ln, atts):
    hits = set()
    cores = [a["core"] for a in atts if a.get("core")]
    for ident in re.findall(r"[A-Za-z_][\w$]*", ln):
        for a in atts:
            if any(ident.startswith(p) for p in a.get("prefix", [])):
                hits.add(a["name"])
        c = BG.match_core(ident, cores) if cores else None
        if c:
            hits.add(next(a["name"] for a in atts if a.get("core") == c))
    return hits


def station_tree(tn, t, entry, txt, man, tcl, rep, bound_bus_width):
    bus_name = entry["bus"]
    b = next((x for x in t["buses"] if x["name"] == bus_name), None)
    if b is None:
        _fail(tn, bus_name, "station_tree on unknown bus")
    in_bus = b["dir"] == "in"
    n = gen_rtl.sv_id(bus_name)
    W = bound_bus_width(tn, b, txt, man)
    k = _planned_k(t, bus_name, tn)
    if re.search(rf"\bu_ist_{re.escape(n)}_(\d+)\b", txt) or re.search(rf"\bu_ist_{re.escape(n)}_t", txt):
        _fail(tn, bus_name, "stations already inserted (run on a fresh kit-rtl copy)")
    pads = sorted(int(m) for m in re.findall(rf"\bu_b(?:in|out)_{re.escape(n)}_pad(\d+)\b", txt))
    have = len(pads)
    if have and not in_bus:
        _fail(tn, bus_name, "station tree on an out bus with bind pads is not supported (fail closed)")
    nodes = entry["nodes"]
    key = "readers" if in_bus else "sources"
    atts = [dict(a) for a in entry.get(key, [])]
    if not atts:
        _fail(tn, bus_name, f"tree without {key}")
    for a in atts:
        a.setdefault("name", a.get("core") or a["node"])
    if len({a["name"] for a in atts}) != len(atts):
        _fail(tn, bus_name, f"duplicate {key} names")
    par, depth = tree_check(tn, bus_name, nodes, k, have, [a["node"] for a in atts])
    cores = [a["core"] for a in atts if a.get("core")]
    owners = None
    for a in atts:
        if a.get("bits") is not None:
            try:
                a["_bits"] = _bits_of(a["bits"], W)
            except ValueError as ex:
                _fail(tn, bus_name, str(ex))
    if any("_bits" not in a for a in atts):
        owners = (BG.in_bit_owners(txt, n, cores) if in_bus else BG.out_bit_owners(txt, n, W, cores)) if cores else None
        for a in atts:
            if "_bits" in a:
                continue
            if not owners or not a.get("core"):
                _fail(tn, bus_name, f"{a['name']}: no explicit bits and no RTL owner mapping")
            a["_bits"] = {bit for bit, cs in owners.items() if a["core"] in cs and bit < W}
            if not a["_bits"]:
                _fail(tn, bus_name, f"{a['name']}: core owns no bit of the bus")
    nb = {x["id"]: set() for x in nodes}
    for a in atts:
        i = a["node"]
        while i is not None:
            nb[i] |= a["_bits"]
            i = par[i]
    dead = [i for i, s in nb.items() if not s]
    if dead:
        _fail(tn, bus_name, f"tree node(s) {dead} carry no bit (dead branch)")
    idorder = [x["id"] for x in nodes]
    order = sorted(nb, key=lambda i: (depth[i], idorder.index(i)))
    S = {i: sorted(nb[i]) for i in nb}
    P = {i: {bit: x for x, bit in enumerate(S[i])} for i in nb}
    qn = {i: f"{n}_t{gen_rtl.sv_id(i)}_q" for i in nb}
    eqn = {i: f"{n}_t{gen_rtl.sv_id(i)}_eq" for i in nb}
    inst = {i: f"{n}_t{gen_rtl.sv_id(i)}" for i in nb}
    decl, body, names = [], [], []
    site = {x["id"]: x.get("site_um") for x in nodes}
    if in_bus:
        last_q, last_eq = ((f"{n}_p{pads[-1]}_q", f"{n}_p{pads[-1]}_eq") if pads else (f"{n}_q", f"{n}_eq"))
        for i in order:
            w = len(S[i])
            if par[i] is None:
                d, ea = cat([(last_q, bit) for bit in reversed(S[i])]), last_eq
            else:
                d, ea = cat([(qn[par[i]], P[par[i]][bit]) for bit in reversed(S[i])]), eqn[par[i]]
            decl.append(_decl(qn[i], eqn[i], w))
            body.append(_station(inst[i], w, d, ea, qn[i], eqn[i], "kit_istations: FIRM plan tree station"))
            names.append(f"u_ist_{inst[i]}")
        by_name = {a["name"]: a for a in atts}
        qre = re.compile(rf"\b{re.escape(last_q)}(?:\[(\d+)(?::(\d+))?\])?(?![\w$\[])")
        eqre = re.compile(rf"\b{re.escape(last_eq)}\b")
        out, ctx = [], None
        for ln in txt.split("\n"):
            ms = BG.INST_START.match(ln)
            if ms:
                ctx = ("inst", _inst_reader(ms.group(3), atts))
            elif re.match(r"^\s*\);", ln):
                ctx = None
            reads = qre.search(ln) or eqre.search(ln)
            if (not reads or _is_decl(ln) or re.search(rf"\bu_bin_{re.escape(n)}(_pad\d+)?\s*\(", ln)):
                out.append(ln)
                continue
            who = {ctx[1]} - {None} if ctx else _ident_readers(ln, atts)
            if len(who) != 1:
                raise FormError(f"kit_istations: {tn} {bus_name}: read of {last_q} not owned by exactly one tree reader "
                                f"(owners {sorted(who)}): {ln.strip()[:120]}")
            a = by_name[next(iter(who))]
            nd = a["node"]

            def sub(m, a=a, nd=nd):
                if m.group(1) is None:
                    lo, hi = 0, W - 1
                elif m.group(2) is None:
                    lo = hi = int(m.group(1))
                else:
                    hi, lo = max(int(m.group(1)), int(m.group(2))), min(int(m.group(1)), int(m.group(2)))
                bad = [bit for bit in range(lo, hi + 1) if bit not in a["_bits"]]
                if bad:
                    raise FormError(f"kit_istations: {tn} {bus_name}: reader {a['name']} reads bit(s) {bad[:6]} "
                                    "outside its declared bits")
                return cat([(qn[nd], P[nd][bit]) for bit in range(hi, lo - 1, -1)])
            out.append(eqre.sub(eqn[nd], qre.sub(sub, ln)))
        txt = "\n".join(out)
        txt = re.sub(r"(\n\s*endmodule\b)", "\n" + "\n".join(decl + body) + r"\1", txt, count=1)
    else:
        m = _bout_line(txt, n, W)
        if not m:
            _fail(tn, bus_name, f"no u_bout_{n} face register line to feed")
        raw = out_refs(txt, m.group(2), W, tn, bus_name)
        ea0 = m.group(4)
        kids = {i: [c for c in idorder if par[c] == i] for i in nb}
        src_at = {i: set().union(*[a["_bits"] for a in atts if a["node"] == i]) for i in nb}
        seen = set()
        for i in nb:
            if src_at[i] & seen:
                _fail(tn, bus_name, f"bit(s) {sorted(src_at[i] & seen)[:6]} enter the tree at two nodes")
            seen |= src_at[i]
        miss = sorted(set(range(W)) - seen)
        if miss:
            _fail(tn, bus_name, f"u_bout d bits {miss[:8]} belong to no tree source")
        for i in sorted(nb, key=lambda x: -depth[x]):          # leaves first
            parts = []
            for bit in reversed(S[i]):
                if bit in src_at[i]:
                    parts.append(raw[bit])
                else:
                    c = next(c for c in kids[i] if bit in nb[c])
                    parts.append((qn[c], P[c][bit]))
            ea = eqn[kids[i][0]] if kids[i] else ea0
            decl.append(_decl(qn[i], eqn[i], len(S[i])))
            body.append(_station(inst[i], len(S[i]), cat(parts), ea, qn[i], eqn[i], "kit_istations: FIRM plan tree station"))
            names.append(f"u_ist_{inst[i]}")
        root = next(i for i in nb if par[i] is None)
        dfin = cat([(qn[root], P[root][bit]) for bit in range(W - 1, -1, -1)])
        line = re.sub(r"^(\s*)ot_dp_ste\b", r"\1ot_dp_st", m.group(1) + dfin + m.group(3) + eqn[root] + m.group(5))
        txt = txt[:m.start()] + line + txt[m.end():]
        txt = re.sub(r"(\n\s*endmodule\b)", "\n" + "\n".join(decl + body) + r"\1", txt, count=1)
    for i in nb:
        if site[i] is not None:
            tcl.append(f"is_place {{*u_ist_{inst[i]}[./]*}} {site[i][0]} {site[i][1]} ist:{bus_name}")
    rep.append(dict(conn="bus:" + bus_name, planned=k, bound_pads=have, inserted=len(names), stations=names,
                    plan_width=b["width"], bound_width=W,
                    station_tree=dict(dir=b["dir"], nodes=len(nb), node_widths={i: len(S[i]) for i in order},
                                      data_flops=sum(len(S[i]) for i in nb), data_flops_single_chain=W * (k - have),
                                      readers=[a["name"] for a in atts])))
    return txt


# ---------------------------------------------------------------- entry point used by kit_istations.main
def claimed_conns(t):
    return {"bus:" + e["bus"] for e in t.get("pad_landing", [])} | {"bus:" + e["bus"] for e in t.get("station_trees", [])}


def apply_forms(tn, t, txt, man, tcl, rep, bound_bus_width):
    """-> (txt, claimed conns).  Default off: no keys -> (txt, set())."""
    claimed = claimed_conns(t)
    if not claimed:
        return txt, set()
    dup = [e["bus"] for e in t.get("pad_landing", [])]
    dup += [e["bus"] for e in t.get("station_trees", [])]
    if len(set(dup)) != len(dup):
        raise FormError(f"kit_istations: {tn}: a bus is claimed twice by pad_landing / station_trees ({sorted(dup)})")
    for e in t.get("pad_landing", []):
        txt = pad_landing(tn, t, e["bus"], e, txt, man, tcl, rep, bound_bus_width)
    for e in t.get("station_trees", []):
        txt = station_tree(tn, t, e, txt, man, tcl, rep, bound_bus_width)
    return txt, claimed


def derive_cli(plan_path, tn, bus_name, kit_dir):
    """print the legal-maximum pad_landing entry for one bus (reach floor of every owner row); the plan side bakes the
    two sides of a seam from this table (check_pair verifies they agree)."""
    import json
    raw = json.load(open(plan_path))
    t = raw["partition_types"][tn]
    man = json.loads((Path(kit_dir) / "kit_rtl.json").read_text())
    bfile = next(Path(f) for f in man["files"] if Path(f).stem == man["bound_module"])
    txt = bfile.read_text()
    n = gen_rtl.sv_id(bus_name)
    m = re.search(rf"\bot_dp_ste?\s+#\(\.W\((\d+)\)\)\s+u_b(in|out)_{re.escape(n)}\s*\(", txt)
    if not m:
        raise SystemExit(f"kit_istation_forms: no face register of {bus_name} in {bfile}")
    W, in_bus = int(m.group(1)), m.group(2) == "in"
    hard = [h["inst"] for h in t.get("hard_cores", [])]
    rows = _bus_rows(t, bus_name)
    k = _planned_k(t, bus_name, tn)
    cores = sorted({BG.core_of_entry(e, hard) for e in rows} - {None})
    owners = (BG.in_bit_owners(txt, n, cores) if in_bus else BG.out_bit_owners(txt, n, W, cores)) or {}
    d = bit_depth_from_rows(rows, owners, W, k, hard)
    print(json.dumps(dict(bus=bus_name, bit_depth=compress_runs(d), planned_k=k, width=W,
                          owners_resolved=sum(1 for b in range(W) if owners.get(b)),
                          data_flops_single_chain=W * k, data_flops=sum(d))))


if __name__ == "__main__":
    if len(sys.argv) == 6 and sys.argv[1] == "derive":
        derive_cli(*sys.argv[2:])
    else:
        raise SystemExit("usage: kit_istation_forms.py derive PLAN.json TYPE BUS KIT_RTL_DIR")
