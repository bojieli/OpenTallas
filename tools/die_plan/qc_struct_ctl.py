#!/usr/bin/env python3
"""STRUCT-CTL-1 (DIE-QC-97 11-09): structural data-path form for one landed soft QC type (sle_ctl__cl67434795).

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

  struct_ctl.py SRC KIT GEOM BASE_PLAN TYPE OUT_PLAN REPORT_JSON [--reach 350]
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


RX_BIN = re.compile(r"^u_bound\.u_bin_(\w+?)/(q\[(\d+)\]|eq)\$")
RX_PD = re.compile(r"^u_bound\.u_pd(\d+)_(\w+)_(\d+)\.(r\[(\d+)\]|q)\$")
RX_LPAD = re.compile(r"^u_bound\.u_lpad_(\w+?)\.q\[(\d+)\]\$")
RX_BOUT = re.compile(r"^u_bound\.u_bout_(\w+?)/(q\[(\d+)\]|eq)\$")


def owner(nm):
    if nm.startswith("u_bound.u_u_ctl."):
        return "ctl"
    if nm.startswith("u_bound.u_u_tap."):
        return "tap"
    return None


bins, pds, lpads, bouts, content_ff = {}, {}, {}, {}, collections.defaultdict(list)
for cid in seq:
    nm = name[cid]
    m = RX_BIN.match(nm)
    if m:
        bus = m.group(1)
        bit = INW[bus] if m.group(2) == "eq" else int(m.group(3))
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
        bouts[cid] = (bus, OUTW[bus] if m.group(2) == "eq" else int(m.group(3)))
        continue
    o = owner(nm)
    if o:
        content_ff[o].append(cid)
print(f"bins {len(bins)} pd {len(pds)} lpad {len(lpads)} bout {len(bouts)} ctl {len(content_ff['ctl'])} tap {len(content_ff['tap'])}")

# ---- which content drives which output bus, which input bus feeds which content directly
drive = collections.defaultdict(lambda: collections.Counter())      # content -> out bus -> bits
for o, ffs in content_ff.items():
    for cid in ffs:
        for t in captures(cid, 64):
            if t in bouts:
                drive[o][bouts[t][0]] += 1
bin_caps = {cid: captures(cid, 512) for cid in bins}
feed = collections.defaultdict(lambda: collections.Counter())       # content -> in bus -> bits
for cid, caps in bin_caps.items():
    for o in {owner(name[t]) for t in caps} - {None}:
        feed[o][bins[cid][0]] += 1
pd_dest = {}                                                        # (bus, k) -> capture cids of the chain's last flop
for cid, (bus, k, j, d) in pds.items():
    if j == d - 1:
        pd_dest[(bus, k)] = captures(cid, 64)
lpad_caps = {cid: captures(cid, 64) for cid in lpads}
for cid, caps in lpad_caps.items():
    for o in {owner(name[t]) for t in caps} - {None}:
        feed[o][lpads[cid][0]] += 1
mixed_out = collections.Counter()                                   # out bus bits NOT driven by a content (pass-through)
for cid, (bus, k) in bouts.items():
    mixed_out[bus] += 1
print("drive", {o: dict(v) for o, v in drive.items()})
print("feed", {o: dict(v) for o, v in feed.items()})

L1 = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
w_out, h_out = 1226.88, 1339.2


def ring_bit(bus, bit):
    r = LC.get(bus, {}).get("rect_um")
    p = PIN.get((bus, bit)) or PC.get(bus)
    if not r:
        return p
    x0, y0, x1, y1 = r
    return (min(max(p[0], x0), x1), min(max(p[1], y0), y1))


def ring_centre(bus):
    r = LC.get(bus, {}).get("rect_um")
    if not r:
        return PC[bus]
    return ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)


raw_bytes = Path(BASE).read_bytes()
raw = json.loads(raw_bytes)
t = raw["partition_types"][TN]
assert "internal_stations" not in t and "relay_sites" not in t, "type already carries stations / relay sites"
# KNEE-1 11-10: a per_bit chain is placed by the kit's knee rule (istation_knee mirrors kit_istations
# is_knee_site: bbox of ALL the bus's pins, one shared integer stage split, leaf offset); the straight L1/(n+1) estimate
# left 10 chains of sle_ctl__cl67434795 over the kit's 403 um stop (x_hc1_i 924 um with 1 station).
BUSREC = {b["name"]: b for b in t["buses"]}
CORNERS = {b: [(min(x for x, _ in v), min(y for _, y in v)), (max(x for x, _ in v), max(y for _, y in v))]
           for b, v in byb.items()}           # legs() reads only the bbox of the pins


def knee_n(n, c, bus, direction):
    if n <= 0 or bus not in BUSREC:
        return n
    rec = BUSREC[bus]
    return KN.stations_needed(rec["face"], direction, c, CORNERS[bus], n, KN.PLAN_MARGIN_UM, KN.leaf_offset(t, rec))


def n_out(c, bus):
    return knee_n(max(0, math.ceil(L1(c, PC[bus]) / REACH) - 1), c, bus, "out")


def n_in(c, bus):
    free = 2 + LPAD.get(bus, 0)
    return knee_n(max(0, math.ceil(L1(c, ring_centre(bus)) / REACH) - free), c, bus, "in")


def cost(o, c):
    s = 0.0
    for bus in drive[o]:
        s += (OUTW[bus] + 1) * n_out(c, bus)
    for bus in feed[o]:
        s += (INW[bus] + 1) * n_in(c, bus)
    return s


best = {}
for o in ("ctl", "tap"):
    if o not in drive and o not in feed:
        continue
    cand = [(cost(o, (x, y)), x, y) for x in range(60, 1180, 20) for y in range(60, 1290, 20)]
    cmin = min(cand)[0]
    # among the cheapest, the one nearest the outline centre of its connections (ties: deterministic)
    pts = [PC[b] for b in drive[o]] + [ring_centre(b) for b in feed[o]]
    mc = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
    c = min((L1((x, y), mc), x, y) for v, x, y in cand if v == cmin)
    best[o] = (float(c[1]), float(c[2]))
    print(f"box {o}: centre {best[o]} added station flops {cmin:g}")

stations, report = [], dict(reach_um=REACH, boxes=best, out=[], inn=[], hops={})


def line(a, b, f):
    return (round(a[0] + (b[0] - a[0]) * f, 3), round(a[1] + (b[1] - a[1]) * f, 3))


face_of = {b["name"]: b.get("face") for b in t["buses"]}
st_out, st_in = {}, {}
for o, c in best.items():
    for bus in sorted(drive[o]):
        n = n_out(c, bus)
        if n <= 0:
            continue
        if bus in st_out:
            n = max(n, len(st_out[bus]["regs_um"]))
        regs = [line(c, PC[bus], (j + 1) / (n + 1)) for j in range(n)]
        st_out[bus] = dict(conn=f"bus:{bus}", from_um=[c[0], c[1]], to_um=[round(PC[bus][0], 3), round(PC[bus][1], 3)],
                           regs_um=[list(r) for r in regs], bits=OUTW[bus] + 1, launch=f"u_{o}",
                           capture=f"face {bus}", bit_route="per_bit", leaf_um=[c[0], c[1]],
                           note=f"STRUCT-CTL-1 DIE-QC-97 11-09: +{n} pin cycles, {o} box -> {bus} pins "
                                f"{L1(c, PC[bus]):.0f} um")
        report["out"].append(dict(bus=bus, content=o, stations=n, dist_um=round(L1(c, PC[bus]), 1),
                                  content_bits=drive[o][bus], bus_bits=OUTW[bus] + 1))
    for bus in sorted(feed[o]):
        n = n_in(c, bus)
        if n <= 0 or bus in LPAD:
            continue
        if bus in st_in:
            n = max(n, len(st_in[bus]["regs_um"]))
        rc = ring_centre(bus)
        tot = n + 2
        regs = [line(rc, c, (j + 2) / (tot)) for j in range(n)]
        st_in[bus] = dict(conn=f"bus:{bus}", from_um=[round(rc[0], 3), round(rc[1], 3)], to_um=[c[0], c[1]],
                          regs_um=[list(r) for r in regs], bits=INW[bus] + 1, launch=f"face {bus}",
                          capture=f"u_{o}", bit_route="per_bit", leaf_um=[c[0], c[1]],
                          note=f"STRUCT-CTL-1 DIE-QC-97 11-09: +{n} pin cycles, {bus} ring -> {o} box "
                               f"{L1(rc, c):.0f} um")
        report["inn"].append(dict(bus=bus, content=o, stations=n, dist_um=round(L1(rc, c), 1)))
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
    o = owner(nm)
    if o in best:
        return best[o]
    return ctr(cid)


relay = {}


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
            tg.append(line(rb, best.get("ctl", rb), 0.5))
            continue
        o = owner(name[t_])
        if o in best and bus in st_in:
            tg.append(first_in_station_site(bus, bit, best[o]))
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
    o = next((owner(name[t_]) for t_ in lpad_caps[cid] if owner(name[t_])), None)
    if start is None or o not in best:
        continue
    p = line(start, best[o], 0.5)
    relay[key(cid)] = [p[0], p[1]]
    hop["lpad"] = max(hop["lpad"], L1(start, p), L1(p, best[o]))

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
