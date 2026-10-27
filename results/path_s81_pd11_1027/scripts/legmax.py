import json, re, sys, collections
sys.path.insert(0, sys.argv[1]); sys.path.insert(0, sys.argv[2])
import die_clock as DC, die_clock_128 as C128, die_clock_mesh as DM, branch_sizing as BS
B = sys.argv[3]
cells = json.load(open(f'{B}/place.json'))
for l in open(f'{B}/ctree.v'):
    m = re.match(r'\s*(BUFx\w+)\s+(\S+)\s*\(', l)
    if m and m.group(2) in cells: cells[m.group(2)]['lib'] = m.group(1)
nets = json.load(open(f'{B}/nets.json'))['nets']
libs = C128.lib_cells('TT', DM.Path('~/.cache/opentallas/asap7_nldm').expanduser(), BS.SIZES + ('BUFx4_ASAP7_75t_R',))
r0, c0 = C128.wire_rc(DM.NDR['4w'], DC.LAYER_RC)
Mo = BS.Model(cells, nets, libs, r0, c0*1.4, DM.BUF, DM.BUF_W, DM.ROW_Y, DM.BUF_WIDTHS)
a_in, a_out, sl = Mo.forward()
M = json.load(open(f'{B}/mesh.json'))
# max per-hop (repeated segment) length per level = len/n_seg; leaf/unbuffered legs = len
hop = collections.defaultdict(float); n405 = collections.Counter()
for h in M['htree']:
    seg = h['len_um'] / max(1, len(h['reps']) + 1)
    hop[h['level']] = max(hop[h['level']], seg)
    if seg > 405: n405[h['level']] += 1
# tree net pin-to-pin max Manhattan driver->load (actual stage wire) and slew
mx, ms = 0, 0
for n in nets:
    if n.get('level') is None or n['level'] == 99 or isinstance(n['drv'], list) or n['drv'] not in cells: continue
    d = Mo.centre(n['drv'])
    for ld in n['loads']:
        if ld in cells:
            p = Mo.centre(ld); mx = max(mx, abs(p[0]-d[0]) + abs(p[1]-d[1]))
            ms = max(ms, sl.get(ld, 0))
print(B, 'max hop per level', {k: round(v, 1) for k, v in sorted(hop.items())}, 'hops>405', dict(n405), 'total', sum(n405.values()),
      '| max stage pin-pin', round(mx, 1), 'model slew max', round(ms, 1))
