#!/usr/bin/env python3
"""STRUCT-FWV3-1 (DIE-QC-97 11-09): structural data-path form of a landed soft QC type with one flattened content u_core\n(STRUCT-CTL-1 pattern, qc_struct_ctl.py; launch/consumer distances measured bit by bit instead of content boxes).

Plan-only form, built from the existing plan machinery (no generator change):
  * relay_sites (DIE-KV-59): FIRM sites for EXISTING flops, 0 added cycles:
      - every bus-in register u_bin_<bus> bit at the L1 minimax point of its landing-ring bit and its first consumers
        (so ring -> bin and bin -> consumer are each one hop <= reach),
      - every landing-pad relay chain u_pd<D>_<bus>_<k> (D stages, reset-less) spread evenly on the line from its
        bin bit to its consumer (the chains GPL collapsed, relay_collapse 1540),
      - packed receiver pads u_lpad_<bus> at the midpoint of their bin and consumer.
  * internal_stations conn bus:<out> (bit_route per_bit, leaf_um = the driving content's box): PIN CYCLES on every
    output a content (u_ctl / u_tap) drives farther than reach from its box; qc_struct_ctl_lanes.py then sets
    lane fixed_cycles = source + destination station count (native_istations convention) so lane_latency counts them.
  * internal_stations conn bus:<in> (per_bit) on a direct content input whose ring -> box distance needs more than
    the two free hops (ring -> bin -> content).
Content boxes (u_ctl, u_tap) are chosen to minimise added station flops (bits x stations).  Connectivity is read from a
placed geometry dump of the same kit RTL (geom.tsv) and the bound RTL; pin positions from the kit pins.json, ring bands
from the kit landing_contract.json.

  qc_struct_core.py SRC KIT GEOM BASE_PLAN TYPE OUT_PLAN REPORT_JSON [--reach 350]
Then tools/die_plan/qc_struct_ctl_lanes.py (lane fixed_cycles); a type without a reader START tree also needs
qc_start_1108/plan_start.py (the START broadcast, sle_fw_v3 a37 TT -334).
"""
import json, math, re, sys, collections
from pathlib import Path

SRC, KIT, GEOM, BASE, TN, OUT, REP = sys.argv[1:8]
REACH = float(sys.argv[sys.argv.index("--reach") + 1]) if "--reach" in sys.argv else 350.0
sys.path.insert(0, SRC + "/tools/autopilot")
sys.path.insert(0, SRC + "/tools/die_plan")
import geom_rules as G  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
import istation_knee as KN  # noqa: E402

K = Path(KIT)
pins = json.loads((K / "pins.json").read_text())
pins = pins["pins"] if isinstance(pins, dict) else pins
PIN = {(p["bus"], int(p["bit"])): (float(p["x"]), float(p["y"])) for p in pins}
byb = collections.defaultdict(list)
for (b, k), xy in PIN.items():
    byb[b].append(xy)
PC = {b: (sum(x for x, _ in v) / len(v), sum(y for _, y in v) / len(v)) for b, v in byb.items()}
LC = json.loads((K / "landing_contract.json").read_text())["bands"]
BOUND = next((K / "rtl").glob("*_bound.sv")).read_text()
W_OF = {}
for m in re.finditer(r"ot_dp_ste?\s+#\(\.W\((\d+)\)\)\s+u_(bin|bout)_(\w+)\s*\(", BOUND):
    W_OF[m.group(3)] = int(m.group(1))
OUTW, INW = {}, {}
for m in re.finditer(r"ot_dp_ste?\s+#\(\.W\((\d+)\)\)\s+u_(bin|bout)_(\w+)\s*\(", BOUND):
    (OUTW if m.group(2) == "bout" else INW)[m.group(3)] = int(m.group(1))
LPAD = {m.group(2): int(m.group(1)) for m in re.finditer(r"ot_dp_dly\s+#\(\.W\(\d+\),\s*\.D\((\d+)\)\)\s+u_lpad_(\w+)\s*\(", BOUND)}

D = G.Design(GEOM)
name = {cid: c[6].replace("\\", "") for cid, c in D.cells.items()}
ctr = lambda cid: G.ctr(D.cells[cid])
seq = {cid for cid, c in D.cells.items() if c[0] == "S"}
comb = {cid for cid, c in D.cells.items() if c[0] in "BLK"}


def captures(cid, limit=4096):
    """capture flops reached from flop cid through combinational cells (data pins only)"""
    out, seen, front = set(), set(), [cid]
    while front and len(out) < limit:
        nf = []
        for c in front:
            for n in D.drives.get(c, []):
                for s in D.nets[n][2]:
                    if s[0] != "i" or s[2]:
                        continue
                    t = s[1]
                    if t in seq:
                        out.add(t)
                    elif t in comb and t not in seen:
                        seen.add(t)
                        nf.append(t)
        front = nf
    return out


RX_BIN = re.compile(r"^u_bound\.u_bin_(\w+?)/(q(?:\[(\d+)\])?|eq)\$")
RX_PD = re.compile(r"^u_bound\.u_pd(\d+)_(\w+)_(\d+)\.(r\[(\d+)\]|q)\$")
RX_LPAD = re.compile(r"^u_bound\.u_lpad_(\w+?)\.q\[(\d+)\]\$")
RX_BOUT = re.compile(r"^u_bound\.u_bout_(\w+?)/(q(?:\[(\d+)\])?|eq)\$")


def owner(nm):
    return "core" if nm.startswith("u_bound.u_core.") else None


bins, pds, lpads, bouts, content_ff = {}, {}, {}, {}, collections.defaultdict(list)
for cid in seq:
    nm = name[cid]
    m = RX_BIN.match(nm)
    if m:
        bus = m.group(1)
        bit = INW[bus] if m.group(2) == "eq" else int(m.group(3) or 0)
        bins[cid] = (bus, bit)
        continue
    m = RX_PD.match(nm)
    if m:
        d, bus, k = int(m.group(1)), m.group(2), int(m.group(3))
        j = d - 1 if m.group(4) == "q" else int(m.group(5))
        pds[cid] = (bus, k, j, d)
        continue
    m = RX_LPAD.match(nm)
    if m:
        lpads[cid] = (m.group(1), int(m.group(2)))
        continue
    m = RX_BOUT.match(nm)
    if m:
        bus = m.group(1)
        bouts[cid] = (bus, OUTW[bus] if m.group(2) == "eq" else int(m.group(3) or 0))
        continue
    o = owner(nm)
    if o:
        content_ff[o].append(cid)
print(f"bins {len(bins)} pd {len(pds)} lpad {len(lpads)} bout {len(bouts)} core {len(content_ff['core'])}")

L1 = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])


def ring_bit(bus, bit):
    r = LC.get(bus, {}).get("rect_um")
    p = PIN.get((bus, bit)) or PC.get(bus)
    if not r:
        return p
    x0, y0, x1, y1 = r
    return (min(max(p[0], x0), x1), min(max(p[1], y0), y1))


def family(bus):
    """buses of one bundle carry one latency (same station count), so a bundle never skews"""
    if re.match(r"^(ag|ar[dlmtv])_eo$", bus):
        return "ar_eo"
    if re.match(r"^r[delrv]_ei$", bus):
        return "r_ei"
    m = re.match(r"^(x_\w+?)(_p\d+)?_([io])$", bus)
    return f"{m.group(1)}_{m.group(3)}" if m else bus


def pct(v, q=0.99):
    v = sorted(v)
    return v[min(len(v) - 1, int(q * len(v)))]


bin_caps = {cid: captures(cid, 4096) for cid in bins}
lpad_caps = {cid: captures(cid, 64) for cid in lpads}
pd_dest = {}
for cid, (bus, k, j, d) in pds.items():
    if j == d - 1:
        pd_dest[(bus, k)] = captures(cid, 64)

# ---- out buses: every launch of every face-out bit, measured (bin launches sit at their ring bit / pin after siting)
launches = collections.defaultdict(list)                            # (bus, bit) -> launch points
for cid in content_ff["core"]:
    p = ctr(cid)
    for t in captures(cid, 4096):
        if t in bouts:
            launches[bouts[t]].append(p)
for cid, (bus, bit) in bins.items():
    p = ring_bit(bus, bit)
    for t in bin_caps[cid]:
        if t in bouts:
            launches[bouts[t]].append(p)
for cid, (bus, bit) in lpads.items():
    for t in lpad_caps[cid]:
        if t in bouts:
            launches[bouts[t]].append(ctr(cid))
for (bus, k), caps in pd_dest.items():
    for t in caps:
        if t in bouts:
            launches[bouts[t]].append(ctr(next(c for c, v in pds.items() if v[:3] == (bus, k, v[3] - 1))))

out_d, out_leaf = {}, {}
for bus in OUTW:
    dist, far = [], []
    for bit in range(OUTW[bus] + 1):
        ls = launches.get((bus, bit), [])
        pin = PIN.get((bus, bit)) or PC[bus]
        if ls:
            dist.append(max(L1(p, pin) for p in ls))
            far.extend((L1(p, pin), p) for p in ls)
    if not dist:
        continue
    out_d[bus] = pct(dist)
    cut = 0.85 * max(d for d, _ in far)
    pts = [p for d, p in far if d >= cut]
    out_leaf[bus] = (round(sum(p[0] for p in pts) / len(pts), 3), round(sum(p[1] for p in pts) / len(pts), 3))

# ---- in buses: distance ring bit -> consumers; two free hops (ring -> bin -> consumer) + pad/chain depth
in_d, in_need, in_leaf = {}, {}, {}
for cid, (bus, bit) in bins.items():
    rb = ring_bit(bus, bit)
    free, cons = 2, []
    for t in bin_caps[cid]:
        if t in pds:
            cb, ck, cj, cd = pds[t]
            end = [ctr(c) for c in pd_dest.get((cb, ck), []) if owner(name[c])]
            free = 2 + cd
            cons.extend(end)
        elif t in lpads:
            free = 2 + LPAD.get(bus, 1)
            cons.extend(ctr(c) for c in lpad_caps[t] if owner(name[c]))
        elif owner(name[t]):
            cons.append(ctr(t))
    if not cons:
        continue
    dmax = max(L1(rb, p) for p in cons)
    in_d.setdefault(bus, []).append(dmax)
    in_need.setdefault(bus, []).append(max(0, math.ceil(dmax / REACH) - free))
    in_leaf.setdefault(bus, []).extend(cons)

n_out = {b: max(0, math.ceil(d / REACH) - 1) for b, d in out_d.items()}
n_in = {b: pct(v) for b, v in in_need.items() if b not in LPAD}
fam = collections.defaultdict(int)
for b, n in list(n_out.items()) + list(n_in.items()):
    fam[family(b)] = max(fam[family(b)], n)
n_out = {b: fam[family(b)] for b in n_out}
n_in = {b: fam[family(b)] for b in n_in}

raw_bytes = Path(BASE).read_bytes()
raw = json.loads(raw_bytes)
t = raw["partition_types"][TN]
assert "internal_stations" not in t and "relay_sites" not in t, "type already carries stations / relay sites"

# KNEE-1 11-10: size every per_bit chain with the kit's own knee rule (istation_knee mirrors kit_istations
# is_knee_site: pin bbox of the whole bus, one shared integer stage split, leaf offset), out AND in buses.  The old
# straight L1/(n+1) per-bit estimate passed sle_fw_v3 st_eo at 355 um; the kit measured 442.99 and stopped GPL.
BUSREC = {b["name"]: b for b in t["buses"]}


def in_leaf_pt(bus):
    pts = in_leaf[bus]
    return (round(sum(p[0] for p in pts) / len(pts), 3), round(sum(p[1] for p in pts) / len(pts), 3))


def knee_size(n, bus, direction, leaf, width):
    rec = BUSREC[bus]
    pts = [PIN.get((bus, k)) or PC[bus] for k in range(width + 1)]
    return KN.stations_needed(rec["face"], direction, leaf, pts, n, KN.PLAN_MARGIN_UM, KN.leaf_offset(t, rec))


for _ in range(4):                       # knee depth, then one latency per bundle, until both hold
    n_out = {b: knee_size(n, b, "out", out_leaf[b], OUTW[b]) if n else 0 for b, n in n_out.items()}
    n_in = {b: knee_size(n, b, "in", in_leaf_pt(b), INW[b]) if n else 0 for b, n in n_in.items()}
    fam = collections.defaultdict(int)
    for b, n in list(n_out.items()) + list(n_in.items()):
        fam[family(b)] = max(fam[family(b)], n)
    stable = all(n_out[b] == fam[family(b)] for b in n_out) and all(n_in[b] == fam[family(b)] for b in n_in)
    n_out = {b: fam[family(b)] for b in n_out}
    n_in = {b: fam[family(b)] for b in n_in}
    if stable:
        break
print("n_out", {b: n for b, n in n_out.items() if n}, "n_in", {b: n for b, n in n_in.items() if n})
stations, report = [], dict(reach_um=REACH, out=[], inn=[], hops={})


def line(a, b, f):
    return (round(a[0] + (b[0] - a[0]) * f, 3), round(a[1] + (b[1] - a[1]) * f, 3))


st_out, st_in = {}, {}
for bus, n in sorted(n_out.items()):
    if n <= 0:
        continue
    c = out_leaf[bus]
    st_out[bus] = dict(conn=f"bus:{bus}", from_um=list(c), to_um=[round(PC[bus][0], 3), round(PC[bus][1], 3)],
                       regs_um=[list(line(c, PC[bus], (j + 1) / (n + 1))) for j in range(n)], bits=OUTW[bus] + 1,
                       launch="u_core", capture=f"face {bus}", bit_route="per_bit", leaf_um=list(c),
                       note=f"STRUCT-FWV3-1 DIE-QC-97 11-09: +{n} pin cycles, launch -> {bus} pins p99 {out_d[bus]:.0f} um")
    report["out"].append(dict(bus=bus, stations=n, p99_um=round(out_d[bus], 1), leaf=c))
for bus, n in sorted(n_in.items()):
    if n <= 0:
        continue
    c = in_leaf_pt(bus)
    rc = PC[bus]
    tot = n + 2
    st_in[bus] = dict(conn=f"bus:{bus}", from_um=[round(rc[0], 3), round(rc[1], 3)], to_um=list(c),
                      regs_um=[list(line(rc, c, (j + 2) / tot)) for j in range(n)], bits=INW[bus] + 1,
                      launch=f"face {bus}", capture="u_core", bit_route="per_bit", leaf_um=list(c),
                      note=f"STRUCT-FWV3-1 DIE-QC-97 11-09: +{n} pin cycles, {bus} ring -> consumers p99 "
                           f"{pct(in_d[bus]):.0f} um")
    report["inn"].append(dict(bus=bus, stations=n, p99_um=round(pct(in_d[bus]), 1), leaf=c))
stations = list(st_out.values()) + list(st_in.values())


def first_in_station_site(bus, bit, c):
    """per_bit knee site of station 0 of an in bus (approx: straight line pin -> leaf at 1/(n+1))"""
    e = st_in[bus]
    n = len(e["regs_um"])
    return line(PIN.get((bus, bit)) or PC[bus], c, 1.0 / (n + 1))


def target_of(cid):
    """planned point of a capture flop"""
    nm = name[cid]
    if cid in bouts:
        bus, bit = bouts[cid]
        pin = PIN.get((bus, bit)) or PC[bus]
        if bus in st_out:                     # the bout is fed by the station chain: this flop drives station 0
            e = st_out[bus]
            return line(tuple(e["leaf_um"]), pin, 1.0 / (len(e["regs_um"]) + 1))
        return pin
    return ctr(cid)


relay = {}


def lpad_end(cid):
    pts = [target_of(t) for t in lpad_caps[cid]] or [ctr(cid)]
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def key(cid):
    k = re.sub(r"\$_[A-Za-z0-9_]*$", "", name[cid])
    return re.sub(r"^[^./]*[./]", "", k)


# chain destinations
chain_end = {}
for (bus, k), caps in pd_dest.items():
    pts = [p for p in (target_of(t) for t in caps) if p]
    if not pts:
        pts = [ctr(next(iter(caps)))] if caps else []
    if pts:
        chain_end[(bus, k)] = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
pd_by_chain = collections.defaultdict(dict)
for cid, (bus, k, j, d) in pds.items():
    pd_by_chain[(bus, k)][j] = cid


def minimax(points):
    """L1 minimax centre (rotate 45 deg: Chebyshev centre of u = x + y, v = x - y)"""
    us = [p[0] + p[1] for p in points]
    vs = [p[0] - p[1] for p in points]
    u = (min(us) + max(us)) / 2
    v = (min(vs) + max(vs)) / 2
    return ((u + v) / 2, (u - v) / 2)


hop = collections.defaultdict(float)
far_bins = []
for cid, (bus, bit) in list(bins.items()):
    rb = ring_bit(bus, bit)
    tg = []
    if bus in st_in:                          # kit_istations re-points every reader to the station chain
        tg.append(first_in_station_site(bus, bit, tuple(st_in[bus]["leaf_um"])))
    for t_ in ([] if bus in st_in else bin_caps[cid]):
        if t_ in pds:
            cb, ck, cj, cd = pds[t_]
            end = chain_end.get((cb, ck))
            if end is not None:
                tg.append(line(rb, end, 1.0 / (cd + 1)))        # provisional first chain site
            continue
        if t_ in lpads:
            tg.append(line(rb, lpad_end(t_), 0.5))
            continue
        p = target_of(t_)
        if p is not None:
            tg.append(p)
    if not tg:
        continue
    site = minimax([rb] + tg)
    worst = max(L1(site, p) for p in [rb] + tg)
    if worst > 400:
        far_bins.append((round(worst), bus, bit, [round(v) for v in rb], [[round(v) for v in p] for p in tg][:4]))
    # never farther than reach from the ring bit when the targets allow it
    relay[key(cid)] = [round(site[0], 3), round(site[1], 3)]
    hop["ring->bin"] = max(hop["ring->bin"], L1(rb, site))
    for p in tg:
        hop["bin->first"] = max(hop["bin->first"], L1(site, p))
    bins[cid] = (bus, bit, site)

bin_site = {(v[0], v[1]): v[2] for v in bins.values() if len(v) == 3}
for (bus, k), stages in pd_by_chain.items():
    end = chain_end.get((bus, k))
    start = bin_site.get((bus, k))
    if end is None or start is None:
        continue
    d = max(stages) + 1
    prev = start
    for j in range(d):
        p = line(start, end, (j + 1) / (d + 1))
        if j in stages:
            relay[key(stages[j])] = [p[0], p[1]]
        hop["chain"] = max(hop["chain"], L1(prev, p))
        prev = p
    hop["chain_last->dest"] = max(hop["chain_last->dest"], L1(prev, end))
for cid, (bus, bit) in lpads.items():
    start = bin_site.get((bus, bit))
    if start is None:
        continue
    end = lpad_end(cid)
    p = line(start, end, 0.5)
    relay[key(cid)] = [p[0], p[1]]
    hop["lpad"] = max(hop["lpad"], L1(start, p), L1(p, end))

report["hops"] = {k: round(v, 1) for k, v in hop.items()}
fb = collections.Counter(b for _, b, _, _, _ in far_bins)
report["far_bins"] = dict(fb)
for row in sorted(far_bins, reverse=True)[:3] + [r for b in fb for r in [max(x for x in far_bins if x[1] == b)]]:
    print("FAR", row)
report["relay_sites"] = len(relay)
report["stations"] = [dict(conn=e["conn"], n=len(e["regs_um"])) for e in stations]
report["pin_cycles"] = {e["conn"][4:]: len(e["regs_um"]) for e in stations}
t2 = dict(t)
if stations:
    t2["internal_stations"] = stations
t2["relay_sites"] = dict(sorted(relay.items()))
raw["partition_types"][TN] = t2
style = None
for f in (lambda p: json.dumps(p, separators=(",", ":")) + "\n", lambda p: json.dumps(p) + "\n",
          lambda p: json.dumps(p, indent=1) + "\n", lambda p: json.dumps(p, indent=2) + "\n",
          lambda p: json.dumps(p, separators=(",", ":")), lambda p: json.dumps(p)):
    if f(json.loads(raw_bytes)).encode() == raw_bytes:
        style = f
        break
assert style, "base plan JSON style not recognised"
Path(OUT).write_text(style(raw))
Path(REP).write_text(json.dumps(report, indent=1) + "\n")
print(json.dumps({k: v for k, v in report.items() if k not in ("out", "inn")}))
for r in report["out"] + report["inn"]:
    print(r)
