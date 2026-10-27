import json, re, sys, statistics as st, collections
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
node_of = {h['tag']: h['node'] for h in M['htree'] if h.get('node')}; node_of['h'] = 'ckm_n0'
dsite = {(round(d['site'][0], 2), round(d['site'][1], 2)): d for d in M['drivers'].values()}
# arrival at each level node (input), per level: spread of arrivals at that level's node inputs
by = collections.defaultdict(list)
for h in M['htree']:
    if h.get('leaf'):
        d = dsite.get((round(h['b'][0], 2), round(h['b'][1], 2)))
        if d is None: continue
        e = d['cells'][0]
    else:
        e = h.get('node')
    if e in a_in: by[h['level']].append((a_in[e], h['tag'], h['len_um'], h.get('node_move_um')))
mv = collections.defaultdict(list)
for r in M.get('mirror_resites', []):
    mv[r.get('level', 12)].append(r['d_um'])
for L in sorted(by):
    v = [x[0] for x in by[L]]
    m = mv.get(L, [])
    print(f"L{L:2d} n={len(v):4d} arr spread {max(v)-min(v):6.1f} sd {st.pstdev(v):5.1f} | mirror moves {len(m):4d} med {st.median(m) if m else 0:6.1f} max {max(m) if m else 0:6.1f}")
