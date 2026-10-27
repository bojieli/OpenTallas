"""PD10 calibration: plan model (all BUFx24) vs PD9 me1 RCX tree arrivals; global wire R/C scale fit."""
import json, re, sys, statistics as st
sys.path.insert(0, sys.argv[1]); sys.path.insert(0, sys.argv[2])
import die_clock as DC, die_clock_128 as C128, die_clock_mesh as DM, branch_sizing as BS
B, C = sys.argv[3], sys.argv[4]
cells = json.load(open(f'{B}/place.json'))
for l in open(f'{B}/ctree.v'):
    m = re.match(r'\s*(BUFx\w+)\s+(\S+)\s*\(', l)
    if m and m.group(2) in cells: cells[m.group(2)]['lib'] = m.group(1)
nets = json.load(open(f'{B}/nets.json'))['nets']
libs = C128.lib_cells(C, DM.Path('~/.cache/opentallas/asap7_nldm').expanduser(), BS.SIZES + ('BUFx4_ASAP7_75t_R',))
r0, c0 = C128.wire_rc(DM.NDR['4w'], DC.LAYER_RC)
rcx = {}
for l in open(f'{B}/tree_{C}.txt'):
    f = l.split(); rcx[f[1]] = (f[0], float(f[2]), float(f[4]))
best = None
for kr in [float(x) for x in sys.argv[5].split(',')]:
  for kc in [float(x) for x in sys.argv[6].split(',')]:
    M = BS.Model(cells, nets, libs, r0 * kr, c0 * kc, DM.BUF, DM.BUF_W, DM.ROW_Y, DM.BUF_WIDTHS)
    a_in, a_out, sl = M.forward()
    off = rcx['ckm_n0'][1] - a_out['ckm_n0']
    d = []
    for k, (t, v, s) in rcx.items():
        mv = a_out.get(k) if t == 'N' else a_in.get(k)
        if mv is not None: d.append((v - off - mv, k, t))
    D = [x[0] for x in d if x[2] == 'D']
    mean = st.mean(D); sd = st.pstdev(D)
    # spread agreement
    mD = [a_in[k] for k, (t, v, s) in rcx.items() if t == 'D' and k in a_in]
    print(f'kr {kr} kc {kc} D resid mean {mean:7.1f} sd {sd:6.2f} model D spread {max(mD)-min(mD):6.1f}  rcx D spread {max(v for t,v,s in rcx.values() if t=="D")-min(v for t,v,s in rcx.values() if t=="D"):6.1f} slewmax model {max(sl.values()):.0f}', flush=True)
    if best is None or sd < best[0]: best = (sd, kr, kc)
print('BEST', best, 'r0', r0, 'c0', c0)
