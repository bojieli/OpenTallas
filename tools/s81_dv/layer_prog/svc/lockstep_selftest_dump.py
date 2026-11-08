"""self-test: a dump synthesised from the compiler's own model of the image (NOT an RTL result)"""
import json, sys
from pathlib import Path
repo, img, H, out = sys.argv[1], Path(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
sys.path.insert(0, repo + '/tools/s81_dv/layer_prog')
import lower_svc as L
rec = json.loads((img / 'image.json').read_text())
meta = [int(x, 16) for x in (img / 'meta.hex').read_text().split()]
T = meta[1]; sc = [int(x, 16) for x in (img / 'sc.hex').read_text().split()][:T]
pv = [int(x, 16) for x in (img / 'pv.hex').read_text().split()]
oexp = [int(x, 16) for x in (img / 'oexp.hex').read_text().split()]
passes = rec.get('passes') or [dict(k=0, heads=list(range(16)), pv_first=rec['pv_first'])]
LW = H * 132 + 20; nsb = (T + 3) // 4
L_ = []
c = 100
for p in passes:
    for j in range(nsb):
        b = (4 * j) << (LW - 16)
        for rr in range(4):
            b |= 1 << (LW - 20 + rr)
            for h, g in enumerate(p['heads']):
                r = 4 * j + rr
                if r < T:
                    e = sc[r] >> (33 * g)
                    b |= (e & 0xFFFFFFFF) << (4 * H + (rr * H + h) * 32)
                    b |= (e >> 32 & 1) << (rr * H + h)
        L_.append(f'RT {c} {b:x}'); c += 1
    for j in range(nsb):
        L_.append(f'RT {c} 0'); c += 1
for s in range(16):
    t = L.tile_of(s)
    for n in range((T + 15) // 16):
        d = sum(((sc[16 * n + rr] >> (33 * t)) & 0xFFFFFFFF) << (32 * rr) for rr in range(16) if 16 * n + rr < T)
        L_.append(f'SE {s} 500 {d:0128x}')
        L_.append(f'W {s} 501 210 0000 ffff {0:0128x}')
    g = t
    for k in range(32):
        d = oexp[32 * g + k] << (256 if g % 2 else 0)
        L_.append(f'W {s} 900 220 {0x200 + 8 * k + g // 2:04x} {0xff00 if g % 2 else 0x00ff:04x} {d:0128x}')
for p in passes:
    for e, sid in (('u_rsv_11', 11), ('u_rsv_05', 5)):
        ent = 'u_rsv_05' if sid == 5 else 'u_rsv_11'
        for i in range(320):
            t0 = 0 if sid == 11 else 8
            t, b, wi = t0 + i // 40, (i % 40) // 5, i % 5
            if wi == 0:
                d = (1 << 512) | (b << 64) | ((p['k'] << 32) if H == 8 else 0)
                fl = 0
                for w in range(1, 5):
                    for h, g in enumerate(p['heads']):
                        dm = 32 * t + 8 * (w - 1) + b
                        fl |= (pv[dm] >> (33 * g + 32) & 1) << (H * (w - 1) + h)
                d |= fl
            else:
                dm = 32 * t + 8 * (wi - 1) + b
                d = sum(((pv[dm] >> (33 * g)) & 0xFFFFFFFF) << (32 * h) for h, g in enumerate(p['heads']))
            L_.append(f'PV {sid} {p["pv_first"] + i} 0 {d:0129x}')
for g in range(16):
    sid = 5 if g >= 8 else 11
    for bt in range(8):
        rows = [oexp[32 * g + 4 * bt + r] for r in range(4)]
        L_.append(f'PV {sid} 950 800000000000 {rows[0] | rows[1] << 256:0129x}')
        L_.append(f'PV {sid} 951 800000000000 {rows[2] | rows[3] << 256:0129x}')
        L_.append(f'PV {sid} 952 800000000000 {(1 << 512) | (g << 8) | bt:0129x}')
L_.append(f'JD 0 {rec["done_w"]} 1'); L_.append(f'JD 1 {rec["done_e"]} 1')
L_.append('END 9999 qi 1 nq 1 late 0 slice_faults 0000 rfx 0 cred 0')
Path(out).write_text('\n'.join(L_) + '\n')
