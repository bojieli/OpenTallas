import json, re, sys, time
sys.path.insert(0, sys.argv[1]); sys.path.insert(0, sys.argv[2])
import die_clock as DC, die_clock_128 as C128, die_clock_mesh as DM, branch_sizing as BS
B, C, kr, kc, smax = sys.argv[3], sys.argv[4], float(sys.argv[5]), float(sys.argv[6]), float(sys.argv[7])
cells = json.load(open(f'{B}/place.json'))
for l in open(f'{B}/ctree.v'):
    m = re.match(r'\s*(BUFx\w+)\s+(\S+)\s*\(', l)
    if m and m.group(2) in cells: cells[m.group(2)]['lib'] = m.group(1)
nets = json.load(open(f'{B}/nets.json'))['nets']
libs = C128.lib_cells(C, DM.Path('~/.cache/opentallas/asap7_nldm').expanduser(), BS.SIZES + ('BUFx4_ASAP7_75t_R',))
r0, c0 = C128.wire_rc(DM.NDR['4w'], DC.LAYER_RC)
t = time.time()
rec = BS.size_branches(cells, nets, libs, r0 * kr, c0 * kc, DM.BUF, DM.BUF_W, DM.ROW_Y, DM.BUF_WIDTHS, slew_max=smax, max_level=int(sys.argv[9]) if len(sys.argv) > 9 else 11)
rec['sec'] = round(time.time() - t, 1)
print(json.dumps(rec, indent=1))
if len(sys.argv) > 8:
    json.dump({c: v['lib'] for c, v in cells.items() if v.get('lib') and v['lib'] != DM.BUF and c.startswith('ckm_r')}, open(sys.argv[8], 'w'))
