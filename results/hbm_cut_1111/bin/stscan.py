"""VIS-TRIAGE-HBM stscan (DIE-HBM-98 class check, 2026-11-11): plan internal_stations vs the bound netlist, per type.

VIASOFT: no direct wire, but the pair connects through soft (non-plan-core) logic within --depth graph hops: the
plan models a soft-mediated path (e.g. a reduction) as a direct core-core station.
MISATTRIBUTED: a face-bus station whose named core is not a direct driver/load of that face in the netlist; 'actual'
lists the cores that are (or soft-only / none).  PHANTOM / VIASOFT below are core<->core stations only.
PHANTOM: a plan internal station whose endpoint pair {A, B} (core or face bus) has no bound connection in the type
netlist (no wire from a bind instance of A into a pin of a bind instance of B, or the reverse; face bus = the type port
L*_i / L*_o, input side through its bin/lpad/pd registers, output side through u_bout_<bus>).
MISSING: a bound core<->core or face<->core connection between plan hard cores with no plan station for the pair,
reported with bits and the plan pin/origin distance (only pairs > --reach um centre distance are 'unbudgeted').
UNMAPPED: plan station endpoints with no bind instance (names drift); counted, not judged.

usage: stscan.py PLAN_DIR BIND_RTL_DIR [--types a,b] [--reach 405] [--out tsv] [--detail json]
"""
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path

INST_RE = re.compile(r"^    (\w+)\s+(?:#\(.*?\)\s+)?(u_\w+)\s*\(\s*\n(.*?)\n    \);", re.S | re.M)
INST1_RE = re.compile(r"^    (\w+)\s+(?:#\([^\n]*?\)\s+)?(u_\w+)\s*\((\.[^\n]*)\);\s*(?://.*)?$", re.M)
PORT1_RE = re.compile(r"\.(\w+)\(((?:[^()]|\([^()]*\))*)\)")
PORT_RE = re.compile(r"^\s*\.(\w+)\((.*)\),?\s*$", re.M)
WIRE_RE = re.compile(r"\b(w_\w+?)(?:\[(\d+)(?::(\d+))?\])?(?=[\s,}\)\]]|$)")
FACE_IN_RE = re.compile(r"\b(?:pd\d+_)?(L\w+?_i)(?:_q|_b|_\d+)?\b(?:\[(\d+)(?::(\d+))?\])?")


def width(hi, lo):
    if hi is None:
        return 1
    return abs(int(hi) - int(lo if lo is not None else hi)) + 1


def bind_norm(plan_inst):
    return "u_" + plan_inst.replace("__", "_")


def parse_netlist(path):
    s = path.read_text(errors="replace")
    insts = {}
    for m in INST_RE.finditer(s):
        mod, name, body = m.groups()
        insts[name] = (mod, {p: e for p, e in PORT_RE.findall(body)})
    for m in INST1_RE.finditer(s):
        mod, name, body = m.groups()
        if name not in insts:
            insts[name] = (mod, {p: e for p, e in PORT1_RE.findall(body)})
    names = sorted(insts, key=len, reverse=True)
    # wire w_<X>_<port> is driven by instance u_<X>... (bind convention: inst u_u_A -> wire w_u_A_port)
    drv_cache = {}

    def driver(w):
        if w in drv_cache:
            return drv_cache[w]
        cand = "u_" + w[2:]
        d = next((n for n in names if cand.startswith(n + "_")), None)
        drv_cache[w] = d
        return d
    edges = defaultdict(int)       # (frozenset{a,b}) -> bits
    for name, (mod, ports) in insts.items():
        if name.startswith("u_bout_"):
            bus = name[len("u_bout_"):]
            e = ports.get("d", "")
            for w, hi, lo in WIRE_RE.findall(e):
                d = driver(w)
                if d:
                    edges[("F:" + bus, d)] += width(hi or None, lo or None)
            continue
        if name.startswith(("u_bin_", "u_lpad_")):
            continue
        for p, e in ports.items():
            for w, hi, lo in WIRE_RE.findall(e):
                d = driver(w)
                if d and d != name:
                    edges[(d, name)] += width(hi or None, lo or None)
            for bus, hi, lo in FACE_IN_RE.findall(e):
                edges[("F:" + bus, name)] += width(hi or None, lo or None)
    und = defaultdict(int)
    for (a, b), n in edges.items():
        und[frozenset((a, b))] += n
    return insts, und


IDENT_RE = re.compile(r"\b([A-Za-z_]\w*)\b")
ASSIGN_RE = re.compile(r"^\s*assign\s+([A-Za-z_]\w*)[^=]*=\s*(.*?);", re.M)
ALWAYS_RE = re.compile(r"^\s*always\s*@\([^)]*\)\s*(?:if\s*\(.*?\)\s*)?([A-Za-z_]\w*)[^<]*<=\s*(.*?);", re.M)
SKIP_NET = re.compile(r"(^|_)(clk|rst|rst_n|rn)\w*$|^clk|^rst|^\d")


def soft_graph(path, insts, hard_names):
    """DIRECTED net graph through soft logic: assign rhs->lhs, always d->q, soft instance inputs->outputs (outputs =
    nets named w_<inst>_*; ot_dp_st/dly d,ea -> q,eq; u_bout_<bus> d -> 'F:<bus>'), hard core inputs -> 'H:<inst>' ->
    its output nets.  Concatenations make it bit-blind (conservative: may call a phantom 'via soft', never the reverse)."""
    s = path.read_text(errors="replace")
    adj = defaultdict(set)

    def link(a, b):
        if a != b:
            adj[a].add(b)

    def nets(e):
        return [n for n in IDENT_RE.findall(e) if not (n[0].isdigit() or SKIP_NET.search(n) or n in ("b0", "b1"))]
    for m in ASSIGN_RE.finditer(s):
        for n in nets(m.group(2)):
            link(n, m.group(1))
    for m in ALWAYS_RE.finditer(s):
        for n in nets(m.group(2)):
            link(n, m.group(1))
    for name, (mod, ports) in insts.items():
        outp = "w_" + name[2:] + "_"
        if name.startswith("u_bout_"):
            for n in nets(ports.get("d", "")):
                link(n, "F:" + name[len("u_bout_"):])
            continue
        if mod.startswith(("ot_dp_st", "ot_dp_dly")) or set(ports) >= {"d", "q"}:
            ins = nets(ports.get("d", "")) + nets(ports.get("ea", ""))
            outs = nets(ports.get("q", "")) + nets(ports.get("eq", ""))
        else:
            ins, outs = [], []
            for pn, e in ports.items():
                if SKIP_NET.search(pn):
                    continue
                for n in nets(e):
                    (outs if n.startswith(outp) else ins).append(n)
        node = ("H:" + name) if name in hard_names else ("S:" + name)
        for n in ins:
            link(n, node)
        for n in outs:
            link(node, n)
    return adj


def reach(adj, start, targets, depth):
    """directed BFS from start through soft nodes; never passes through another H:/F: node."""
    seen = {start}; front = [start]
    for _ in range(depth):
        nxt = []
        for u in front:
            for v in adj.get(u, ()):
                if v in seen:
                    continue
                seen.add(v)
                if v in targets:
                    return v
                if v.startswith(("H:", "F:")):
                    continue
                nxt.append(v)
        front = nxt
        if not front:
            break
    return None


def endpoint(x):
    """plan station endpoint -> ('F', bus) | ('C', inst) | None"""
    if not x:
        return None
    x = x.strip()
    if x.startswith("face bus "):
        return ("F", x[len("face bus "):].strip())
    if x.startswith("face flop") or x.startswith("face"):
        return None
    return ("C", x.split(".")[0])


def bind_set(ep, insts):
    if ep[0] == "F":
        b = ep[1]
        alts = {b, b.replace("s_i", "_i")} | ({b[:-2] + "s_i"} if b.endswith("_i") else set())
        return {"F:" + a for a in alts}
    parts = ep[1].split("__")
    for k in range(len(parts), 0, -1):           # split pieces of one bound content (u_lk_N0__rx__rest -> u_u_lk_N0)
        n = bind_norm("__".join(parts[:k]))
        hit = {i for i in insts if (i == n or i.startswith(n + "_")) and not i.startswith(("u_bout_", "u_bin_", "u_lpad_"))}
        if hit:
            return hit
    return set()


def scan_type(tn, t, insts, und, reach_um, adj=None, depth=24):
    st = t.get("internal_stations", []) or []
    phantom, mapped_pairs, unmapped, soft, misatt = [], set(), [], [], []
    face_cores = defaultdict(set)
    for pair in und:
        xs = sorted(pair)
        if len(xs) == 2 and xs[0].startswith("F:") != xs[1].startswith("F:"):
            f_, c_ = (xs[0], xs[1]) if xs[0].startswith("F:") else (xs[1], xs[0])
            face_cores[f_].add(c_)
    if adj is not None:
        # through register-only chains (u_ist_* plan stations, u_pd*/u_bin_/u_lpad_ pads): face <-> hard core
        radj = defaultdict(set)
        for u, vs in adj.items():
            for v in vs:
                radj[v].add(u)
        REG = ("S:u_ist_", "S:u_pd", "S:u_bin_", "S:u_lpad_", "S:u_bout_")

        def chain(start, g, bus):
            seen, front, hits = {start}, [start], set()
            depth = 0
            while front and depth < 12:
                depth += 1
                nxt = []
                for u in front:
                    for v in g.get(u, ()):
                        if v in seen:
                            continue
                        seen.add(v)
                        if v.startswith("H:"):
                            hits.add(v[2:]); continue
                        if v.startswith("S:") and not v.startswith(REG):
                            continue
                        if v.startswith("F:"):
                            continue
                        if not v.startswith("S:"):
                            # a net: only follow nets that touch a register-chain instance or a hard core
                            if bus not in v and not any(w.startswith(REG + ("H:",)) for w in list(g.get(v, ())) + list(adj.get(v, ())) + list(radj.get(v, ()))):
                                continue
                        nxt.append(v)
                front = nxt
            return hits
        buses = {x[2:] for x in face_cores} | {b["name"] for b in t.get("buses", [])}
        for bname in buses:
            if bname.endswith("_o"):
                face_cores["F:" + bname] |= chain("F:" + bname, radj, bname)
            else:
                face_cores["F:" + bname] |= chain(bname, adj, bname)
    for i, s in enumerate(st):
        a, b = endpoint(s.get("launch")), endpoint(s.get("capture"))
        if a is None or b is None:
            continue
        A, B = bind_set(a, insts), bind_set(b, insts)
        if (a[0] == "C" and not A) or (b[0] == "C" and not B):
            unmapped.append((i, s.get("conn"), s.get("launch"), s.get("capture")))
            continue
        hit = any(frozenset((x, y)) in und for x in A for y in B)
        if hit:
            for x in A:
                for y in B:
                    mapped_pairs.add(frozenset((x, y)))
        else:
            rec = dict(idx=i, conn=s.get("conn"), launch=s.get("launch"), capture=s.get("capture"),
                       bits=int(s.get("bits", 0) or 0), regs=len(s.get("regs_um") or []))
            via = None
            if adj is not None:
                def src(x):
                    return x[2:] if x.startswith("F:") else "H:" + x       # input face: its port net
                def dst(x):
                    return x if x.startswith("F:") else "H:" + x           # output face: F:<bus>
                for x in A:
                    for y in B:
                        via = reach(adj, src(x), {dst(y)}, depth) or reach(adj, src(y), {dst(x)}, depth)
                        if via:
                            break
                    if via:
                        break
            faces = [x for x in (A | B) if x.startswith("F:")]
            if faces:
                # face station whose named core is not the face's direct driver/load: MISATTRIBUTED
                act = sorted({c for f_ in faces for c in face_cores.get(f_, ())})
                rec["actual"] = act or (["soft-only"] if via else ["none"])
                rec["via_soft"] = bool(via)
                named = {x for x in (A | B) if not x.startswith("F:")}
                if named & set(act):
                    rec["note"] = "named core is the face driver/load (path through registers/soft)"
                    soft.append(rec)      # correctly attributed; counted with viasoft
                else:
                    misatt.append(rec)
            else:
                (soft if via else phantom).append(rec)
    # missing: bound pairs between plan hard cores (or face<->hard core) with no station
    hard, hardall = {}, defaultdict(list)
    for c in t.get("hard_cores", []):
        for bi in bind_set(("C", c["inst"]), insts):
            hard.setdefault(bi, c)
            hardall[bi].append(c)
    missing = []
    for pair, bits in und.items():
        if pair in mapped_pairs or len(pair) != 2:
            continue
        a, b = sorted(pair)
        fa, fb = a.startswith("F:"), b.startswith("F:")
        if fa and fb:
            continue
        if not ((fa or a in hard) and (fb or b in hard)):
            continue
        if fa or fb:
            continue      # face<->core links: plan models many as bus pins, report core<->core only (conservative)
        ca, cb = hard[a], hard[b]
        if ca is cb:
            continue
        cx = lambda c: (c["origin_um"][0] + c["outline_um"][0] / 2, c["origin_um"][1] + c["outline_um"][1] / 2)
        best = None
        for pa in hardall[a]:
            for pb in hardall[b]:
                (x0, y0), (x1, y1) = cx(pa), cx(pb)
                dd = abs(x0 - x1) + abs(y0 - y1)
                if best is None or dd < best[0]:
                    best = (dd, pa, pb)
        d, ca, cb = best      # nearest plan pieces of split bound contents (optimistic distance)
        missing.append(dict(a=a, b=b, plan_a=ca["inst"], plan_b=cb["inst"], bits=bits, dist_um=round(d, 1),
                            unbudgeted=d > reach_um))
    return phantom, missing, unmapped, soft, misatt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan_dir"); ap.add_argument("rtl_dir")
    ap.add_argument("--types"); ap.add_argument("--reach", type=float, default=405.0)
    ap.add_argument("--out"); ap.add_argument("--detail")
    a = ap.parse_args()
    P = json.loads((Path(a.plan_dir) / "die_plan.json").read_text())
    rtl = Path(a.rtl_dir)
    types = a.types.split(",") if a.types else sorted(P["partition_types"])
    rows, detail = [], {}
    for tn in types:
        t = P["partition_types"][tn]
        mod = t.get("module", tn)
        m2 = mod if mod.startswith("hbm_arch_") else "hbm_arch_" + mod
        cands = [rtl / f"{m2}__{tn}.sv", rtl / f"hbm_arch_{tn}.sv", rtl / f"{m2}.sv"]
        f = next((c for c in cands if c.is_file()), None)
        nst = len(t.get("internal_stations", []) or [])
        if f is None:
            rows.append([tn, nst, "NO_NETLIST"] + [""] * 14)
            continue
        insts, und = parse_netlist(f)
        hard_names = set()
        for c in t.get("hard_cores", []):
            hard_names |= bind_set(("C", c["inst"]), insts)
        adj = soft_graph(f, insts, hard_names)
        ph, mi, um, so, ma = scan_type(tn, t, insts, und, a.reach, adj)
        mu = [m for m in mi if m["unbudgeted"]]
        rows.append([tn, nst, f.name, len(ph), sum(p["bits"] for p in ph), sum(p["regs"] for p in ph),
                     len(so), sum(p["bits"] for p in so), sum(p["regs"] for p in so),
                     len(ma), sum(p["bits"] for p in ma), sum(p["regs"] for p in ma),
                     len(mi), sum(m["bits"] for m in mi), len(mu), sum(m["bits"] for m in mu), len(um)])
        detail[tn] = dict(netlist=f.name, phantom=ph, soft=so, misattributed=ma, missing=mi, unmapped=um)
        print("\t".join(map(str, rows[-1])), flush=True)
    hdr = ["type", "plan_stations", "netlist", "phantom_n", "phantom_bits", "phantom_regs", "viasoft_n", "viasoft_bits",
           "viasoft_regs", "misattr_n", "misattr_bits", "misattr_regs", "missing_n", "missing_bits",
           "missing_gt_reach_n", "missing_gt_reach_bits", "unmapped_n"]
    if a.out:
        Path(a.out).write_text("\t".join(hdr) + "\n" + "\n".join("\t".join(map(str, r)) for r in rows) + "\n")
    if a.detail:
        Path(a.detail).write_text(json.dumps(detail, indent=1))


if __name__ == "__main__":
    main()
