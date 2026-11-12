"""DIE-LAYOUT-HBM ladder fit: per bank type, new outline in a 2x4 ladder over the NE bank block width 4493.44 um
(hub|io edges unchanged, total height 4320), row heights chosen so both rows fit with no growth; then a shelf pack of the
type's hard cores (orient free: R0/R90 not allowed for SRAM -> keep orientation, MX/MY only) into the new outline with
34.56-um gaps, to test the SRAM/hcol aspect fit."""
import json, sys, math
P = json.load(open(sys.argv[1])); T = P['partition_types']
parts = {p['name']: p for p in P['partitions']}
top = ['NE_b000', 'NE_b001', 'NE_b002', 'NE_b003']; bot = ['NE_b010', 'NE_b011', 'NE_b012', 'NE_b013']
WB = parts['NE_io']['origin_um'][0] - parts['NE_b000']['origin_um'][0]
LAT = 4.32; G = 34.56
def info(n):
    t = T[parts[n]['type']]; w, h = t['outline_um']
    cores = [(c['outline_um'][0], c['outline_um'][1], c['inst']) for c in t['hard_cores']]
    return dict(n=n, type=parts[n]['type'], w=w, h=h, area=w*h, cells=t.get('cells'), cores=cores,
                carea=sum(a*b for a, b, _ in cores), ft=len(t.get('ft_slots', [])), ftb=sum(s['width'] for s in t.get('ft_slots', [])))
I = {n: info(n) for n in top + bot}
At = sum(I[n]['area'] for n in top); Ab = sum(I[n]['area'] for n in bot)
print(f'bank block width {WB:.2f}; top area {At/1e6:.3f} mm2, bottom {Ab/1e6:.3f} mm2, total height 4320')
best = None
for kt in range(300, 700):
    ht = kt * LAT; hb = 4320 - ht
    wt = sum(math.ceil(I[n]['area'] / ht / LAT) * LAT for n in top); wb = sum(math.ceil(I[n]['area'] / hb / LAT) * LAT for n in bot)
    m = WB - max(wt, wb)
    if best is None or m > best[0]: best = (m, ht, hb, wt, wb)
m, ht, hb, wt, wb = best
print(f'best rows: top h {ht:.2f} (width {wt:.2f}), bottom h {hb:.2f} (width {wb:.2f}), slack {m:.2f} um')
def shelf(cores, W, H):
    cs = sorted(cores, key=lambda c: -c[1]); x = y = rowh = 0; rows = 1
    for w, h, n in cs:
        if w > W or h > H: return False, f'{n} {w:.0f}x{h:.0f} > outline'
        if x + w > W: y += rowh + G; x = 0; rowh = 0; rows += 1
        if y + h > H: return False, f'overflow at row {rows}'
        x += w + G; rowh = max(rowh, h)
    return True, f'{rows} shelves, top {y+rowh:.0f}/{H:.0f}'
for n in top + bot:
    i = I[n]; H = ht if n in top else hb; Wn = math.ceil(i['area'] / H / LAT) * LAT
    ok, why = shelf(i['cores'], Wn, H)
    hmax = max((c[1] for c in i['cores']), default=0); wmax = max((c[0] for c in i['cores']), default=0)
    print(f"{n:8s} {i['type']:22s} now {i['w']:.0f}x{i['h']:.0f} -> {Wn:.0f}x{H:.0f}  cores {len(i['cores'])} core% {100*i['carea']/i['area']:.0f}  max core {wmax:.0f}x{hmax:.0f}  cells {i['cells']}  ft {i['ft']} slots {i['ftb']} b  shelf {'FIT' if ok else 'NO'} ({why})")
