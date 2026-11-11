"""p2o_probe SRC GEOM PINS BASE TYPE BUS PREFIX OUT: for every face_out flop of BUS, the launching flop matching PREFIX
(geometry connectivity), its planned relay site in BASE and the L1 hop site -> pin.  Writes JSON."""
import json, re, sys, collections
SRC, GEOM, PINS, BASE, TN, BUS, PREFIX, OUT = sys.argv[1:9]
sys.path.insert(0, SRC + "/tools/autopilot")
import geom_rules as G
D = G.Design(GEOM)
name = {cid: c[6].replace("\\", "") for cid, c in D.cells.items()}
seq = {cid for cid, c in D.cells.items() if c[0] == "S"}
comb = {cid for cid, c in D.cells.items() if c[0] in "BLK"}
drv_of = {}
for cid, nets in D.drives.items():
    for n in nets:
        drv_of[n] = cid
sink_nets = collections.defaultdict(list)
for n, v in enumerate(D.nets):
    for s in v[2]:
        if s[0] == "i" and not s[2]:
            sink_nets[s[1]].append(n)
def launches(cid, limit=64):
    out, seen, front = set(), set(), [cid]
    while front and len(seen) < 4096:
        nf = []
        for c in front:
            for n in sink_nets.get(c, []):
                d = drv_of.get(n)
                if d is None or d in seen:
                    continue
                seen.add(d)
                if d in seq:
                    out.add(d)
                elif d in comb:
                    nf.append(d)
        front = nf
    return out
pins = json.load(open(PINS)); pins = pins["pins"] if isinstance(pins, dict) else pins
PIN = {int(p["bit"]): (float(p["x"]), float(p["y"])) for p in pins if p["bus"] == BUS}
RX = re.compile(r"^u_bound\.u_bout_" + re.escape(BUS) + r"/q\[(\d+)\]\$")
base = json.load(open(BASE)); rs = base["partition_types"][TN].get("relay_sites", {})
key = lambda nm: re.sub(r"^[^./]*[./]", "", re.sub(r"\$_[A-Za-z0-9_]*$", "", nm))
rows = []
for cid in seq:
    m = RX.match(name[cid])
    if not m:
        continue
    bit = int(m.group(1))
    for l in launches(cid):
        k = key(name[l])
        if not k.startswith(PREFIX):
            continue
        site = rs.get(k)
        pin = PIN.get(bit)
        c = G.ctr(D.cells[l])
        rows.append(dict(bit=bit, launch=k, site=site, placed=[round(c[0], 1), round(c[1], 1)], pin=pin,
                         hop_planned=round(abs(site[0] - pin[0]) + abs(site[1] - pin[1]), 1) if site and pin else None,
                         hop_placed=round(abs(c[0] - pin[0]) + abs(c[1] - pin[1]), 1) if pin else None))
hp = [r["hop_planned"] for r in rows if r["hop_planned"] is not None]
print(json.dumps(dict(bits=len({r["bit"] for r in rows}), launches=len(rows), no_site=sum(r["site"] is None for r in rows),
                      planned_max=max(hp) if hp else None, planned_gt403=sum(h > 403 for h in hp),
                      placed_max=max(r["hop_placed"] for r in rows) if rows else None)))
json.dump(rows, open(OUT, "w"))
