"""PATH-S81-PD: region-lattice phase sweep for the S81 G=2 landed fallback.
For each block-lattice phase (ox, oy) in units of the col-partition pitch, rebuild the regions exactly as
fallback_regions.regions (same keys, same port-connected components, same merge_hard), then count landed ports/bits
and test every landed sink bus with the branch's clock_landing_plan._storage_band (face strip -> compact bank ->
grid scan), accumulating used bands per sink PARTITION (compose splits types per landing set).
usage: region_phase.py PLAN LAT OUT.json [phases like 0,0 1,0 0,1 1,1]"""
import json, sys, copy, collections, math
sys.path.insert(0, 'tools/die_plan')
import fallback_regions as FR, clock_landing_plan as CLP
FR.CORE_MODE = 'tap'
plan, latp, outp = sys.argv[1:4]
phases = [tuple(int(v) for v in a.split(',')) for a in (sys.argv[4:] or ['0,0', '1,0', '0,1', '1,1'])]
raw = json.load(open(plan))
CLP._fill_ft_windows(raw, plan)
T = raw['partition_types']; parts = {p['name']: p for p in raw['partitions']}
cw = min(T[p['type']]['outline_um'][0] for p in parts.values() if FR.legacy_cores(T[p['type']]))
ch = min(T[p['type']]['outline_um'][1] for p in parts.values() if FR.legacy_cores(T[p['type']]))
block = 2
import os
GROUPS = json.load(open(os.environ['GROUPS']))['groups'] if os.environ.get('GROUPS') else []


def regions(ox, oy):
    rect = {}
    for n, p in parts.items():
        w, h = T[p['type']]['outline_um']; x, y = p['origin_um']; rect[n] = (x, y, x+w, y+h)
    def blk(n):
        x0, y0, x1, y1 = rect[n]
        return (int(((x0+x1)/2 + ox*cw) // (block*cw)), int(((y0+y1)/2 + oy*ch) // (block*ch)))
    key = {n: ('std', blk(n)) for n in parts}
    for i, grp in enumerate(GROUPS):
        for n in grp:
            if n in key: key[n] = ('std', ('g', i))
    par = {n: n for n in parts}
    def find(a):
        while par[a] != a: par[a] = par[par[a]]; a = par[a]
        return a
    for pr in raw['ports']:
        a, b = pr['src']['part'], pr['dst']['part']
        if a in parts and b in parts and key[a] == key[b]: par[find(a)] = find(b)
    reg = {n: str(find(n)) for n in parts}
    return FR.merge_hard(raw, reg)


res = []
for ox, oy in phases:
    reg = regions(ox, oy)
    land = [pr for pr in raw['ports'] if pr['src']['part'] in reg and pr['dst']['part'] in reg and reg[pr['src']['part']] != reg[pr['dst']['part']]]
    used = collections.defaultdict(list); fails = []
    for pr in sorted(land, key=lambda p: (-int(p['width']), p['id'])):
        dp = pr['dst']['part']; t = T[parts[dp]['type']]; bus = pr['dst']['bus']
        try:
            b = CLP._bus_geom(t, bus); wd = int(b.get('width') or pr['width'] or 2)
            band = CLP._storage_band(t, bus, wd, used[dp]); used[dp].append(band['rect_um'])
        except Exception as e:
            fails.append(dict(part=dp, type=parts[dp]['type'], bus=bus, width=int(pr['width']), err=str(e)[-60:]))
    sizes = collections.Counter(reg.values())
    r = dict(phase=[ox, oy], regions=len(sizes), largest=max(sizes.values()), landed_ports=len(land),
             landed_bits=sum(int(p['width']) for p in land), band_fails=len(fails),
             fail_types=dict(collections.Counter(f['type'].split('__')[0] for f in fails)), fails=fails)
    res.append(r)
    print(json.dumps({k: v for k, v in r.items() if k != 'fails'}), flush=True)
json.dump(res, open(outp, 'w'), indent=1)
if os.environ.get('DUMPREG'):
    reg = regions(0, 0); sz = collections.Counter(reg.values())
    for tag, n in sz.most_common(6):
        ms = [m for m in reg if reg[m] == tag]
        xs = [parts[m]['origin_um'][0] for m in ms] + [parts[m]['origin_um'][0] + T[parts[m]['type']]['outline_um'][0] for m in ms]
        ys = [parts[m]['origin_um'][1] for m in ms] + [parts[m]['origin_um'][1] + T[parts[m]['type']]['outline_um'][1] for m in ms]
        print(tag, n, 'bbox mm %.2f x %.2f' % ((max(xs)-min(xs))/1e3, (max(ys)-min(ys))/1e3), sorted(ms)[:20])
