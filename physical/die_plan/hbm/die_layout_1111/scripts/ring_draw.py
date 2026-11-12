"""DIE-LAYOUT-HBM: NE bank ring, current fold vs proposed 2x4 ladder (REDESIGN drawing)."""
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
cols = [('b000',458),('b010',829),('b001',786),('b011',380),('b002',380),('b012',553),('b003',553),('b013',553)]
ring = [('hub','b000',4986),('b000','b001',6904),('b001','b002',4128),('b002','b003',4401),('b003','b013',4127),
        ('b013','b012',4127),('b012','b011',4128),('b011','b010',4401),('b010','b000',4097),('b000','b010',4512),('b000','hub',4098)]
extra = [('b001','b011',3332),('b010','b001',1756),('b011','b002',1747)]
fig, ax = plt.subplots(1, 2, figsize=(20, 9), facecolor='white')
def arrow(a, p, q, bits, col):
    a.add_patch(FancyArrowPatch(p, q, arrowstyle='-|>', mutation_scale=14, lw=0.6 + bits / 1200, color=col, connectionstyle='arc3,rad=0.25'))
    a.text((p[0]+q[0])/2, (p[1]+q[1])/2 + 120, f'{bits}', fontsize=8, ha='center', color=col)
# current
a = ax[0]; x = 0; pos = {}
a.add_patch(Rectangle((-700, 0), 650, 4320, fc='#ddd', ec='k')); a.text(-375, 2160, 'NE_hub', ha='center'); pos['hub'] = (-50, 2160)
for n, w in cols:
    a.add_patch(Rectangle((x, 0), w, 4320, fc='#cfe3ff', ec='k')); a.text(x + w/2, 4200, n, ha='center', fontsize=10); pos[n] = (x + w/2, 2160); x += w
a.add_patch(Rectangle((x, 0), 648, 4320, fc='#eee', ec='k')); a.text(x + 324, 2160, 'NE_io', ha='center')
ys = {}
for i, (s, d, b) in enumerate(ring):
    y = 600 + (i % 6) * 520
    p, q = (pos[s][0], y), (pos[d][0], y)
    skip = abs([c for c, _ in cols].index(d) - [c for c, _ in cols].index(s)) if s != 'hub' and d != 'hub' else 0
    arrow(a, p, q, b, 'red' if skip > 1 else 'green')
a.set_xlim(-800, x + 750); a.set_ylim(-300, 4600); a.set_aspect('equal')
a.set_title('NOW (main cd03a1f3, NE side; NW mirrors): ring hub->b000->b001->b002->b003->b013->b012->b011->b010->b000->hub\n'
            'folded onto one row: every ring hop (red, 4.1-6.9 kb) passes THROUGH the neighbour column\n'
            'ring station flops 133k / side; L14m+L167m+L168m 6.9 kb through b010 (535k cells > 400k cap)', fontsize=9)
# proposed
a = ax[1]; pos = {}
a.add_patch(Rectangle((-700, 0), 650, 4320, fc='#ddd', ec='k')); a.text(-375, 2160, 'NE_hub', ha='center'); pos['hub'] = (-50, 2160)
HT, HB = 2095.2, 2224.8
top = [('b000',946.08),('b001',1624.32),('b002',786.24),('b003',1136.16)]; bot = [('b010',1611.36),('b011',738.72),('b012',1075.68),('b013',1067.04)]
x = 0
for n, w in top:
    a.add_patch(Rectangle((x, HB), w, HT, fc='#cfe3ff', ec='k')); a.text(x + w/2, 4150, n + f' {w:.0f}x{HT:.0f}', ha='center', fontsize=8); pos[n] = (x + w/2, HB + HT/2); x += w
x = 0
for n, w in bot:
    a.add_patch(Rectangle((x, 0), w, HB, fc='#cfe3ff', ec='k')); a.text(x + w/2, HB - 160, n + f' {w:.0f}x{HB:.0f}', ha='center', fontsize=8); pos[n] = (x + w/2, HB/2); x += w
a.add_patch(Rectangle((4492.8, 0), 648, 4320, fc='#eee', ec='k')); a.text(4817, 2160, 'NE_io', ha='center')
a.add_patch(Rectangle((946.08, HB - 60), 4492.8 - 946.08, 120, fc='orange', alpha=0.35, ec='none'))
a.text(2700, HB - 330, 'N-S transit band x 946-4493 (b001..b003 / b010..b013 seam): NE 21.0 kb + ladder links 10.9 kb\n= 31.9 kb / 43.6-65.6k tracks -> 0.49-0.73 (NW 0.51-0.77); b000|b010 seam 8.6 kb / 946 um -> 0.51', fontsize=7, ha='center', color='darkorange')
a.text(2246, -230, 'no growth: rows h 2095.20 / 2224.80 (sum 4320), widths area-preserving on 4.32 lattice, b003 -4.32 / b013 -8.64 um (22% core); all 8 shelf-pack FIT', color='m', fontsize=7, ha='center')
for s, d, b in ring + extra:
    arrow(a, pos[s], pos[d], b, 'green' if (s, d, b) in ring else 'gray')
a.set_xlim(-800, 5300); a.set_ylim(-300, 4600); a.set_aspect('equal')
a.set_title('PROPOSED (REDESIGN, S1/S0): 2x4 ladder, same areas (w x2, h /2)\n'
            'every ring hop abuts (0 pass-through, ring stations -> 0, latency kept as lat pads)\n'
            'b010: 0 ring pass-through, N-S transits moved to the x>946 band -> ~257k cells (< 400k); fallback split A/B 15/26 cores', fontsize=9)
plt.tight_layout(); plt.savefig('ring_redesign.png', dpi=110); plt.savefig('ring_redesign.svg')
