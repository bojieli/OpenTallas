# S81-COLLECT/RG3 10-21: wide-outline pin plans for s81ctrl_rg3w / s81ctrl_rg3sw (structural re-floorplan after the
# rg3/rg3s regate CTS FAIL: N/S faces 98% spanned at 388.8 um, hold repair stuck at the PHY face, GPL overflow 36.7%).
# Outline 561.6 x 324; the 4 SRAM FIFOs as two abutted N-S stacks (one per PC; lower R0 pins S, upper MX pins N) so the
# S (PHY, 64.8 um) and N (stream+reader, 57.7 um) full-width std-cell bands are macro-free, plus a 144.7 um centre column.
#  mode w : N face per PC half (as gen_pins.py mode n) PC0 rq rd rrq rrd | clk ck_o | PC1 rq rd rrq rrd over 4.5..557.1;
#           S face = the n32s S pins in their n32s order re-spread over 4.5..557.1 (same layer per pin); rst_n W mid.
#  mode sw: N face = the n32s N pins in n32s order re-spread; S as w; rrq (92) on W, rrd (544) on E (M4).
import re, sys
src, mode, out = sys.argv[1], sys.argv[2], sys.argv[3]
W, H = 561.6, 324.0
OH = 324.0  # n32s outline height
pins = [l for l in open(src).read().splitlines() if l.startswith('place_pin')]
def nm(l): return re.search(r'-pin_name \{([^}]*)\}', l).group(1)
def loc(l): return tuple(float(v) for v in re.search(r'-location \{([\d.]+) ([\d.]+)\}', l).groups())
def lay(l): return re.search(r'-layer (\S+)', l).group(1)
L = {'M3': ('M3', 0.009, 0.036, '{0.018 0.144}'), 'M5': ('M5', 0.012, 0.048, '{0.024 0.192}'),
     'M4': ('M4', 0.012, 0.048, '{0.192 0.024}')}
def snap(T, v, lo):
    k = max(0, round((v - T[1]) / T[2]))
    x = T[1] + k * T[2]
    while x < lo: k += 1; x = T[1] + k * T[2]
    return round(x, 3)
X0, X1 = 4.545, W - 4.5
res = ['# S81-COLLECT/RG3 10-21: dsfd_ctrl_rg3 wide pin plan mode %s (561.6 x 324), gen_pins_w.py from dsfd_ctrl_rg2_n32s_pins.tcl' % mode]
def horiz(seq, y, layers=None):
    st = (X1 - X0) / (len(seq) - 1)
    last = {'M3': -1.0, 'M5': -1.0}
    for i, p in enumerate(seq):
        T = L[layers[i]] if layers else (L['M3'] if i % 2 == 0 else L['M5'])
        x = snap(T, X0 + i * st, last[T[0]] + 0.3)
        last[T[0]] = x
        res.append(f'place_pin -pin_name {{{p}}} -layer {T[0]} -location {{{x:.3f} {y:.3f}}} -pin_size {T[3]} -force_to_die_boundary')
    assert max(last.values()) < W - 1, last
def vert(seq, xx):
    y0, y1 = 6.0, H - 6.0
    st = (y1 - y0) / (len(seq) - 1)
    prev = -1.0
    for i, p in enumerate(seq):
        y = snap(L['M4'], y0 + i * st, prev + 0.3)
        if xx == 0.0 and abs(y - H / 2) < 0.5: y = snap(L['M4'], H / 2 + 0.6, prev + 0.3)
        prev = y
        res.append(f'place_pin -pin_name {{{p}}} -layer M4 -location {{{xx:.3f} {y:.3f}}} -pin_size {L["M4"][3]} -force_to_die_boundary')
    assert prev < H - 1
south = sorted([l for l in pins if loc(l)[1] == 0.0], key=lambda l: loc(l)[0])
north = sorted([l for l in pins if loc(l)[1] == OH], key=lambda l: loc(l)[0])
west = [l for l in pins if loc(l)[0] == 0.0 and 0 < loc(l)[1] < OH]
assert [nm(l) for l in west] == ['rst_n'] and len(pins) == len(south) + len(north) + 1
if mode == 'w':
    seq = ([f'rq[{i}]' for i in range(341)] + [f'rd[{i}]' for i in range(280)] + [f'rrq[{i}]' for i in range(46)] + [f'rrd[{i}]' for i in range(272)]
           + ['clk', 'ck_o'] + [f'rq[{i}]' for i in range(341, 682)] + [f'rd[{i}]' for i in range(280, 562)]
           + [f'rrq[{i}]' for i in range(46, 92)] + [f'rrd[{i}]' for i in range(272, 544)])
    horiz(seq, H)
elif mode == 'sw':
    horiz([nm(l) for l in north], H, [lay(l) for l in north])
    vert([f'rrq[{i}]' for i in range(92)], 0.0)
    vert([f'rrd[{i}]' for i in range(544)], W)
else:
    sys.exit('mode w|sw')
horiz([nm(l) for l in south], 0.0, [lay(l) for l in south])
ry = snap(L['M4'], H / 2, 0)
res.append(f'place_pin -pin_name {{rst_n}} -layer M4 -location {{0.000 {ry:.3f}}} -pin_size {L["M4"][3]} -force_to_die_boundary')
open(out, 'w').write('\n'.join(res) + '\n')
print(mode, len(res) - 1, 'pins')
