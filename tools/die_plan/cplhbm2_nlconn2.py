#!/usr/bin/env python3
"""CPL-HBM-2 (DO_NOT_COUNT): real core<->face / core<->core links of a partition type from its kit synth netlist
(flat 1_synth_odb.v). The plan core_conns.json is stale for the HBM SU types (face bus names are not type buses).
Directed cone walk from every hard-core signal pin (clock/reset/strap/scan skipped):
  output pin -> forward through comb cells to sinks; input pin -> backward through comb cells to the driver.
  At most FLOPS sequential cells crossed (D<->Q), at most DEPTH comb cells, nets with > FCAP sinks not crossed
  (but a hit on such a net still counts). Hits: top port bit (type bus) or another hard-core pin.
Per core port bus the targets are recorded; bits = pins of that core reaching that target.
Output: {"core_conns": {type: {inst: {core_bus: [targets]}}}, "bits": {type: {inst: {target: bits}}},
         "hyper": [[bus, [cores], bits]] (face buses: which cores each type bus bit reaches)}
usage: nlconn2.py PLAN TYPE NETLIST.v OUT.json [--depth 10] [--flops 1] [--fanout 32]"""
import collections
import json
import re
import sys

plan, tn, nlf, out = sys.argv[1:5]
arg = lambda k, d: type(d)(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d
DEPTH, FLOPS, FCAP = arg("--depth", 10), arg("--flops", 1), arg("--fanout", 32)
P = json.load(open(plan))
T = P["partition_types"][tn]
mods = {h["module"] for h in T["hard_cores"]}
san = lambda s: re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")
plan_key = {san(h.get("physical_inst") or h["inst"]): h["inst"] for h in T["hard_cores"]}
txt = open(nlf).read()
body = txt[txt.index(";") + 1:]
ports = {}
for m in re.finditer(r"^\s*(input|output|inout)\s+(?:\[(\d+):(\d+)\]\s+)?(\S+?)\s*;", body, re.M):
    ports[m.group(4)] = m.group(1)
inst_re = re.compile(r"^\s*([A-Za-z_][\w$]*)\s+(\\\S+|[A-Za-z_][\w$.\[\]]*)\s*\((.*?)\)\s*;", re.M | re.S)
pin_re = re.compile(r"\.([\w$]+)\s*\(\s*(\{[^}]*\}|[^(){}]*?)\s*\)\s*(?=,|$)", re.S)
OUTP = {"Y", "Q", "QN", "CON", "SN", "Z", "ZN", "CO", "S"}
SEQ = re.compile(r"^(DFF|DHL|DLL|SDF|ICG|DFFH|DFFL|SDFH|SDFL)", re.I)
cells = []
for m in inst_re.finditer(body):
    ct, nm, conn = m.group(1), m.group(2), m.group(3)
    if ct in ("module", "input", "output", "wire", "assign", "inout", "reg"):
        continue
    pins = []
    for pm in pin_re.finditer(conn):
        pn, ex = pm.group(1), pm.group(2).strip()
        if not ex:
            continue
        parts = [x.strip() for x in ex[1:-1].split(",")] if ex.startswith("{") else [ex]
        for q, net in enumerate(parts):
            net = net.replace(" ", "")
            if not net or "'" in net:
                continue
            mm = re.match(r"^([A-Za-z_][\w$]*)\[(\d+):(\d+)\]$", net)
            if mm:
                a, b = int(mm.group(2)), int(mm.group(3))
                for x in range(min(a, b), max(a, b) + 1):
                    pins.append(("%s[%d]" % (pn, x), "%s[%d]" % (mm.group(1), x)))
                continue
            pins.append((pn + ("[%d]" % q if len(parts) > 1 else ""), net))
    cells.append((ct, nm, pins))
ismac = [c[0] in mods for c in cells]
isseq = [bool(SEQ.match(c[0])) for c in cells]
drv = {}
sinks = collections.defaultdict(list)
for k, (ct, nm, pins) in enumerate(cells):
    if ismac[k]:
        continue
    for p, n in pins:
        if p in OUTP:
            drv[n] = (k, p)
        else:
            sinks[n].append((k, p))
# macro pins: a net with no std-cell driver and not a top input is driven by the macro on it
mac_on = collections.defaultdict(list)
for k, (ct, nm, pins) in enumerate(cells):
    if ismac[k]:
        for p, n in pins:
            mac_on[n].append((k, p))


def port_of(net):
    base = re.sub(r"\[\d+\]$", "", net.lstrip("\\"))
    return base if base in ports else None


assigns = collections.defaultdict(set)
for m in re.finditer(r"^\s*assign\s+(\S+)\s*=\s*(\S+?)\s*;", body, re.M):
    assigns[m.group(1)].add(m.group(2)); assigns[m.group(2)].add(m.group(1))


_pc = {}


def pinst(k):
    if k in _pc:
        return _pc[k]
    k2 = san(cells[k][1])
    m = [kk for kk in plan_key if k2.endswith(kk)] or [kk for kk in plan_key if ("_" + kk + "_") in ("_" + k2 + "_")]
    _pc[k] = plan_key[max(m, key=len)] if m else None
    return _pc[k]


SKIP = re.compile(r"(clk|rst|strap_|scan|test|tie|_id\b|lane_id)", re.I)


def walk(k0, n0, out_dir):
    hits = set()
    # state: (net, direction fwd?, flops crossed, depth)
    st = [(n0, out_dir, 0, 0)]
    seen = set()
    while st:
        n, fwd, fl, d = st.pop()
        if (n, fwd, fl) in seen:
            continue
        seen.add((n, fwd, fl))
        for a in [n] + list(assigns.get(n, ())):
            po = port_of(a)
            if po:
                hits.add("bus:" + po)
        macdrv = n not in drv and not (port_of(n) and ports.get(port_of(n)) == "input")
        for (j, pj) in mac_on.get(n, []):
            if j != k0 and (fwd or macdrv):
                pi = pinst(j)
                if pi:
                    hits.add("core:" + pi)
        if fwd:
            sk = sinks.get(n, [])
            if len(sk) > FCAP:
                continue
            for (j, pj) in sk:
                if SKIP.search(pj):
                    continue
                if isseq[j]:
                    if fl >= FLOPS or not pj.startswith("D"):
                        continue
                    for (p2, n2) in cells[j][2]:
                        if p2 in OUTP:
                            st.append((n2, True, fl + 1, d))
                elif d < DEPTH:
                    for (p2, n2) in cells[j][2]:
                        if p2 in OUTP:
                            st.append((n2, True, fl, d + 1))
        else:
            dv = drv.get(n)
            if dv is None:
                continue
            j, pj = dv
            if isseq[j]:
                if fl >= FLOPS:
                    continue
                for (p2, n2) in cells[j][2]:
                    if p2.startswith("D") and not SKIP.search(p2):
                        st.append((n2, False, fl + 1, d))
            elif d < DEPTH:
                for (p2, n2) in cells[j][2]:
                    if p2 not in OUTP and not SKIP.search(p2):
                        st.append((n2, False, fl, d + 1))
    return hits


res_bits, conns = {}, {}
hyper = collections.defaultdict(lambda: collections.defaultdict(int))
for k, c in enumerate(cells):
    if not ismac[k]:
        continue
    pi = pinst(k)
    if pi is None:
        print("unmapped macro", c[1], file=sys.stderr)
        continue
    tb = collections.Counter()
    cb = collections.defaultdict(collections.Counter)
    for p, n in c[2]:
        if SKIP.search(p):
            continue
        out_pin = n not in drv and not (port_of(n) and ports.get(port_of(n)) == "input")
        h = walk(k, n, out_pin)
        bus = re.sub(r"\[\d+\]$", "", p)
        for x in h:
            tb[x] += 1
            cb[bus][x] += 1
            if x.startswith("bus:"):
                hyper[x[4:]][pi] += 1
    res_bits[pi] = dict(tb)
    conns[pi] = {b: [t for t, v in cnt.items() if v >= max(1, 0.1 * max(cnt.values()))] for b, cnt in cb.items()}
H = [[b, sorted(cs), int(max(cs.values()))] for b, cs in hyper.items()]
json.dump(dict(type=tn, netlist=nlf, depth=DEPTH, flops=FLOPS, fanout_cap=FCAP, core_conns={tn: conns},
               bits={tn: res_bits}, hyper=H), open(out, "w"), indent=1)
agg = collections.Counter()
for pi, tb in res_bits.items():
    for t_, b in tb.items():
        agg["face" if t_.startswith("bus:") else "core"] += b
print(tn, "macros", len(res_bits), "pin-bits to faces", agg["face"], "to cores", agg["core"])
for pi, tb in list(res_bits.items())[:6]:
    print(" ", pi, sorted(tb.items(), key=lambda x: -x[1])[:8])
for b, cs, w in sorted(H, key=lambda x: -x[2])[:10]:
    print("  bus", b, "cores", len(cs), "max bits/core", w)
