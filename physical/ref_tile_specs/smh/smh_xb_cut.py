#!/usr/bin/env python3
"""SM tile cluster, leaf x-store -> bdc operand relay (xb, 1,064 bits a leaf): wires through the worst vertical cut of the
xs | bdc gap, r15 (relay registers in instance order inside the 100-um station window) vs r16 (register at its bdc pin
column).  Supply = GRT's own capacity in the open gap (22 H tracks a 0.57-um gcell, r15 wg marker at (439.5, 198.9))."""
import sys, json, random, collections
ROOT = sys.argv[1] if len(sys.argv) > 1 else str(__import__("pathlib").Path(__file__).resolve().parents[3])
def pins(view):
    W = H = None; d = {}; pin = None; got = True
    for ln in open(f"{ROOT}/{view}"):
        s = ln.split()
        if not s: continue
        if s[0] == 'SIZE': W, H = float(s[1]), float(s[3])
        elif s[0] == 'PIN': pin = s[1]; got = False
        elif s[0] == 'OBS': pin = None
        elif s[0] == 'RECT' and pin and not got:
            x = (float(s[1]) + float(s[3])) / 2; y = (float(s[2]) + float(s[4])) / 2
            dist = {'W': x, 'E': W - x, 'S': y, 'N': H - y}; d[pin] = (x, y, min(dist, key=dist.get)); got = True
    return W, H, d
V = "physical/ref_tile/{}/views/{}/{}.lef"
xs = pins(V.format("smh_xs_ref_p45m", "ot_hbm_accel_smh_xs", "ot_hbm_accel_smh_xs"))
bdc = pins(V.format("smh_bdc_ref_p50", "ot_hbm_accel_smh_bdc", "ot_hbm_accel_smh_bdc"))
fp = json.load(open(f"{ROOT}/physical/ref_tile/smh_tile_eg_ref/floorplan.json")); B = {b['inst']: b for b in fp['blocks']}
TPU = 22 / 0.57
random.seed(1)
out = {}
for leaf, gap in ((0, 58.32), (1, 30.26)):
    bx = B[f'*g_lf?{leaf}?.u_lh.u_xs']; bb = B[f'*g_lf?{leaf}?.u_lh.u_bdc']; toward = 'S' if leaf else 'N'
    bits = []
    for bs, bd in (('o_ix', 'i_x'), ('o_iw', 'i_w')):
        for k in range(532):
            sp = xs[2].get(f'{bs}[{k}]'); dp = bdc[2].get(f'{bd}[{k}]')
            if not sp or not dp: continue
            sx = bx['x'] + sp[0]; f = sp[2]
            if leaf and f in 'NS': f = {'N': 'S', 'S': 'N'}[f]
            if f == toward: ex = sx
            elif f == 'W': ex = bx['x']
            elif f == 'E': ex = bx['x'] + bx['w']
            else: ex = bx['x'] if sp[0] <= bx['w'] / 2 else bx['x'] + bx['w']
            bits.append((ex, bb['x'] + dp[0]))
    def worst(regx):
        best = (0, 0)
        for c10 in range(int(bx['x'] * 10), int((bx['x'] + bx['w']) * 10), 10):
            c = c10 / 10; n = 0
            for (ex, dx), rx in zip(bits, regx):
                n += (min(ex, rx) < c < max(ex, rx)) + (min(rx, dx) < c < max(rx, dx))
            if n > best[0]: best = (n, c)
        return best
    r15 = worst([random.uniform(137.0, 237.0) for _ in bits]); r16 = worst([dx for _, dx in bits])
    tr = gap * TPU
    out[f"leaf{leaf}"] = dict(gap_um=gap, bits=len(bits), h_tracks=round(tr),
                              r15_instance_order=dict(wires=r15[0], at_x=r15[1], ratio=round(r15[0] / tr, 2)),
                              r16_pin_columns=dict(wires=r16[0], at_x=r16[1], ratio=round(r16[0] / tr, 2)))
print(json.dumps(out, indent=1))
