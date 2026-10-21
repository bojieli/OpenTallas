#!/usr/bin/env python3
"""QKO-HROOT3-P11 10-21: relay stations for the qkd_hr_cluster p11 parent.

    relay_plan.py VAR.json OUT.json [REACH_um]

For every child->child (driver -> reader) lane of a placement whose pin-to-pin manhattan length exceeds REACH (405 um,
owner reach rule), the bits of that (driver, reader) pair are grouped and get ceil(len / REACH) - 1 relay stations
(qkd_hr_rly hard children: one register stage each, own ck_core__rly_<k> clock entry), spaced evenly along the
L-shaped lane, each at the nearest LEGAL lattice spot (no overlap, 21.6 um gaps).  Async reset nets (*rst_n, por_n)
get reset relays (async assert, release one edge later).  Every relayed reader sees its bits +stages edges later
than in the flat parent: a COMPILER RE-SCHEDULE (listed in OUT.json "reschedule"), priced in the static calendar.
Broadcast nets (>= 4 readers) are relayed per far reader the same way.  Lanes to / from parent ports are not relayed
(their parent pin sits at the projection of the child pin; reported).
"""
import collections
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hr_parent as HP  # noqa: E402

LAT = 43.2
GAP = 21.6


def driver_of(n, mem, dirs):
    outs = [(i, nm, p) for (i, nm, p) in mem if i != 'PORT' and dirs[i].get(p) == 'output']
    if outs:
        return outs[0]
    ins = [(i, nm, p) for (i, nm, p) in mem if i == 'PORT']
    return ins[0] if ins else None


def main():
    var, out = sys.argv[1], sys.argv[2]
    reach = float(sys.argv[3]) if len(sys.argv) > 3 else 405.0
    V, blocks = HP.load(var)
    nets = HP.net_members(blocks)
    HP.assign_standins(V, blocks, nets)
    PW, PH = V['outline']
    dirs = {}
    for inst, b in blocks.items():
        if b['standin']:
            dirs[inst] = HP.rtl_dirs(b['rtl'])
        else:
            lef = HP.gshow(f"{b['view']}/{b['cell']}.lef")
            d = {}
            for pm in re.finditer(r'^  PIN (\S+)\s+DIRECTION (\w+)', lef, re.M):
                d[pm.group(1).split('[')[0]] = 'output' if pm.group(2) == 'OUTPUT' else 'input'
            dirs[inst] = d
    groups = collections.defaultdict(list)     # (drv, rdr) -> [(net bit, drv xy, rdr xy, reader pin bit)]
    port_long = collections.Counter()
    for n, mem in nets.items():
        mem = [m for m in mem if m[2] not in HP.CLOCKS]
        if len(mem) < 2:
            continue
        drv = driver_of(n, mem, dirs)
        if drv is None or drv[0] == 'PORT':
            for (i, nm, p) in mem:
                if i != 'PORT' and drv is not None:
                    xy = HP.gxy(blocks[i], nm)
                    if xy and min(xy[0], PW - xy[0], xy[1], PH - xy[1]) > reach:
                        port_long[(drv[2], i)] += 1
            continue
        dxy = HP.gxy(blocks[drv[0]], drv[1])
        if dxy is None:
            continue
        for (i, nm, p) in mem:
            if i == 'PORT':
                if min(dxy[0], PW - dxy[0], dxy[1], PH - dxy[1]) > reach:
                    port_long[(drv[0], p)] += 1
                continue
            if i == drv[0]:
                continue
            rxy = HP.gxy(blocks[i], nm)
            if rxy is None:
                continue
            d = abs(dxy[0] - rxy[0]) + abs(dxy[1] - rxy[1])
            if d > reach:
                groups[(drv[0], i)].append((n, dxy, rxy, d))
    # occupancy for legal relay spots
    rects = [(b['x'], b['y'], b['w'], b['h']) for b in blocks.values()]

    def free(x, y, w, h):
        if x < GAP or y < GAP or x + w > PW - GAP or y + h > PH - GAP:
            return False
        for (a, b2, c, e) in rects:
            if min(x + w + GAP, a + c + GAP) - max(x, a) > 1e-6 and min(y + h + GAP, b2 + e + GAP) - max(y, b2) > 1e-6:
                return False
        return True

    def spot(tx, ty, w, h):
        best = None
        for r in range(0, 30):
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    if max(abs(dx), abs(dy)) != r:
                        continue
                    x = round(round((tx - w / 2) / LAT + dx) * LAT, 3)
                    y = round(round((ty - h / 2) / LAT + dy) * LAT, 3)
                    if free(x, y, w, h):
                        c = abs(x + w / 2 - tx) + abs(y + h / 2 - ty)
                        if best is None or c < best[0]:
                            best = (c, x, y)
            if best:
                return best[1], best[2]
        return None

    relays, resched = [], []
    k = 0
    for (dv, rd), bits in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        rst = [b for b in bits if re.search(r'(rst_n|por_n)', b[0])]
        dat = [b for b in bits if b not in rst]
        for kind, bl in (('rst', rst), ('data', dat)):
            if not bl:
                continue
            L = max(b[3] for b in bl)
            nst = max(1, math.ceil(L / reach) - 1)
            sx = sum(b[1][0] for b in bl) / len(bl); sy = sum(b[1][1] for b in bl) / len(bl)
            tx = sum(b[2][0] for b in bl) / len(bl); ty = sum(b[2][1] for b in bl) / len(bl)
            w = len(bl)
            h = max(LAT, math.ceil(w / 3.0 / 0.8 / LAT) * LAT)
            rw = LAT
            chain = []
            for s in range(1, nst + 1):
                f = s / (nst + 1)
                # L-shaped lane: x first then y (station on the path)
                tot = abs(tx - sx) + abs(ty - sy)
                a = f * tot
                if a <= abs(tx - sx):
                    px, py = sx + math.copysign(a, tx - sx), sy
                else:
                    px, py = tx, sy + math.copysign(a - abs(tx - sx), ty - sy)
                sp = spot(px, py, rw, h)
                if sp is None:
                    raise SystemExit(f'no legal relay spot for {dv}->{rd} ({w} b) near {px:.0f},{py:.0f}')
                rects.append((sp[0], sp[1], rw, h))
                orient = 'R0' if tx >= sx else 'MY'      # d on the W face toward the driver
                name = f'u_rly{k}'
                k += 1
                chain.append({'inst': name, 'at': list(sp), 'orient': orient, 'w': rw, 'h': h})
            relays.append({'driver': dv, 'reader': rd, 'kind': kind, 'width': w, 'stages': nst, 'max_um': round(L, 1),
                           'bits': sorted({b[0] for b in bl}), 'chain': chain})
            resched.append({'reader': rd, 'driver': dv, 'bits': w, 'added_edges': nst, 'kind': kind})
    json.dump({'reach_um': reach, 'relays': relays, 'reschedule': resched,
               'port_lanes_over_reach': {f'{a}->{b}': n for (a, b), n in port_long.items()}}, open(out, 'w'), indent=1)
    print(f'{len(relays)} relay groups, {sum(len(r["chain"]) for r in relays)} stations, '
          f'{sum(r["width"] * r["stages"] for r in relays)} relay flops; port lanes > reach: {sum(port_long.values())} bits')
    for r in relays[:40]:
        print(f"  {r['driver']} -> {r['reader']}: {r['width']} b {r['kind']} {r['max_um']} um x{r['stages']}")


if __name__ == '__main__':
    main()
