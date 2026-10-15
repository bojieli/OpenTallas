#!/usr/bin/env python3
"""GLOBAL-FP-Q candidate (a'): OpenROAD RTL-MP on a CLUSTERED die (the flat 1637-macro run did not finish in 2 h).

Clusters: 48 rigid 4x4 reduction-block macros (tiles + stations keep their relative placement, so every in-block
tree is preserved); the 48 head columns and every hub/band/KV/IO instance are free macros (a first try with 36
row-band field macros failed MPL-0040 at the root cluster: rigid 12-mm macros at 79% utilisation).  Every inter-cluster bus becomes
k parallel nets, k = bits x activations/token / (217 x 64), clipped to 1..64 (net weight = width x traffic).  Pins sit
at the member's real assigned pin centroids.  IO band + KV PHY fixed.  No flips (macros keep their current
orientation).  The placement is expanded back to instances and scored by gfp_core.score like every candidate.
"""
import collections, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gfp_core as C  # noqa: E402

PLAT = Path('/home/ubuntu/.local/opentallas-pdk-asap7-platform/asap7')
NET_UNIT = 64 * C.ME_OPS
FIXED = ('io_collective', 'io_ucie', 'io_serdes', 'io_serdes_1', 'io_serdes_2', 'io_xfifo', 'ucie_kv')


def cluster_of(n, i):
    """48 rigid 4x4 reduction-block macros (tiles + their stations); head columns and hub instances are free macros."""
    if i['m'] in C.FIELD_MASTERS and not n.startswith('h_'):
        c, r = int(n.split('_')[1]), int(n.split('_')[2])
        return f'F{c // 4}_{r // 4}'
    return n


def region_of(cl):
    if cl.startswith('F'): return 'field_w' if int(cl[1:].split('_')[0]) < 6 else 'field_e'
    if cl.startswith('h_'): return 'field_w' if int(cl[2:]) < 24 else 'field_e'
    if cl.startswith('io_'): return 'io'
    m = re.search(r'_(\d)(_f1)?$', cl)
    if cl.startswith(('sp_port_tiles', 'sp_res_ser', 'sp_band_lanes')) and m: return 'band_' + m.group(1)
    return 'hub'


def build(die, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    base = die.base
    cl = {n: cluster_of(n, i) for n, i in base.items()}
    mem = collections.defaultdict(list)
    for n, c in cl.items(): mem[c].append(n)
    box = {}
    for c, ns in mem.items():
        x0 = min(base[n]['x'] for n in ns); y0 = min(base[n]['y'] for n in ns)
        x1 = max(base[n]['x'] + base[n]['w'] for n in ns); y1 = max(base[n]['y'] + base[n]['h'] for n in ns)
        box[c] = (x0, y0, x1, y1)
    pins = collections.defaultdict(list)      # cluster -> [(pin, x, y)]
    nets = []
    for r in die.recs:
        cs = [cl[n] for n, _ in r['ends']]
        if len(set(cs)) < 2: continue
        k = max(1, min(64, round(r['n'] * max(r['act'], 1) / NET_UNIT)))
        P = [C.place(e, base) for e in r['ends']]
        for j in range(k):
            eps = []
            for e, (n, _) in enumerate(r['ends']):
                pts = P[e]; q = pts[min(len(pts) - 1, int((j + 0.5) * len(pts) / k))]
                c = cl[n]; x0, y0, x1, y1 = box[c]
                px = min(max(q[0] - x0, 0.05), x1 - x0 - 0.15); py = min(max(q[1] - y0, 0.05), y1 - y0 - 0.15)
                pn = f'p{len(pins[c])}'; pins[c].append((pn, px, py)); eps.append((c, pn))
            nets.append((f"{r['b']}__{j}", eps))
    lef = ['VERSION 5.8 ;', 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;']
    for c, (x0, y0, x1, y1) in box.items():
        lef += [f'MACRO CL_{c}', '  CLASS BLOCK ;', '  ORIGIN 0 0 ;', f'  FOREIGN CL_{c} 0 0 ;', f'  SIZE {x1 - x0:.3f} BY {y1 - y0:.3f} ;']
        for pn, px, py in pins[c]:
            lef += [f'  PIN {pn}', '    DIRECTION INOUT ;', '    USE SIGNAL ;', '    PORT', '      LAYER M4 ;',
                    f'        RECT {px:.3f} {py:.3f} {px + 0.1:.3f} {py + 0.1:.3f} ;', '    END', f'  END {pn}']
        lef += [f'END CL_{c}']
    lef += ['END LIBRARY']
    (out / 'macros.lef').write_text('\n'.join(lef) + '\n')
    reg = {c: region_of(c) for c in box}
    users = collections.defaultdict(set)
    conn = collections.defaultdict(dict)
    for nn, eps in nets:
        for c, pn in eps: users[nn].add(reg[c]); conn[c][pn] = nn
    by_reg = collections.defaultdict(list)
    for c, g in reg.items(): by_reg[g].append(c)
    v = []
    for g, cs in sorted(by_reg.items()):
        ports = sorted(nn for nn, us in users.items() if g in us and len(us) > 1)
        local = sorted(nn for nn, us in users.items() if us == {g})
        v.append(f'module {g} (' + ', '.join(['gin'] + ports) + ');'); v.append('  input gin;')
        for p in ports: v.append(f'  inout {p};')
        v.append(f'  wire {g}_bo; BUFx2_ASAP7_75t_R {g}_buf (.A(gin), .Y({g}_bo));')
        for p in local: v.append(f'  wire {p};')
        for c in cs:
            v.append(f'  CL_{c} {c} (' + ', '.join(f'.{pn}({nn})' for pn, nn in sorted(conn[c].items())) + ');')
        v.append('endmodule')
    v.append('module qfd_compute_die (gin);'); v.append('  input gin;')
    for w_ in sorted(nn for nn, us in users.items() if len(us) > 1): v.append(f'  wire {w_};')
    for g in sorted(by_reg):
        ports = sorted(nn for nn, us in users.items() if g in us and len(us) > 1)
        v.append(f'  {g} u_{g} (' + ', '.join(['.gin(gin)'] + [f'.{p}({p})' for p in ports]) + ');')
    v.append('endmodule')
    (out / 'die.v').write_text('\n'.join(v) + '\n')
    W, H = die.die['w'], die.die['h']
    fix = [f'place_macro -macro_name u_{reg[n]}/{n} -location {{{box[n][0]:.3f} {box[n][1]:.3f}}} -orientation R0' for n in FIXED]
    tcl = f"""
read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef {out}/macros.lef
read_liberty {PLAT}/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
read_verilog {out}/die.v
link_design qfd_compute_die
initialize_floorplan -die_area "0 0 {W:.3f} {H:.3f}" -core_area "0 0 {W:.3f} {H:.3f}" -site asap7sc7p5t
""" + '\n'.join(f'make_tracks M{l} -x_offset 0 -x_pitch {p} -y_offset 0 -y_pitch {p}' for l, p in
                ((1, .036), (2, .036), (3, .036), (4, .048), (5, .048), (6, .064), (7, .064), (8, .08), (9, .08))) + f"""
{chr(10).join(fix)}
foreach n {{{' '.join(f'u_{reg[n]}/{n}' for n in FIXED)}}} {{ [[ord::get_db_block] findInst $n] setPlacementStatus FIRM }}
place_pins -hor_layers M4 -ver_layers M5
rtl_macro_placer -halo_width 5.4 -halo_height 5.4 -target_util 0.95 -report_directory {out}/rpt -write_macro_placement {out}/placement.tcl
write_def {out}/placed.def
"""
    (out / 'run.tcl').write_text(tcl)
    return dict(clusters=len(box), nets=len(nets), pins=sum(len(p) for p in pins.values()))


def read_back(die, out: Path):
    base = die.base
    cl = {n: cluster_of(n, i) for n, i in base.items()}
    mem = collections.defaultdict(list)
    for n, c in cl.items(): mem[c].append(n)
    org = {c: (min(base[n]['x'] for n in ns), min(base[n]['y'] for n in ns)) for c, ns in mem.items()}
    txt = (out / 'placed.def').read_text()
    units = int(re.search(r'UNITS DISTANCE MICRONS (\d+)', txt).group(1))
    m = {n: dict(i) for n, i in base.items()}
    seen = 0
    for mo in re.finditer(r'-\s+(\S+)\s+CL_(\S+)\s+\+\s+(PLACED|FIXED|FIRM)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\S+)', txt):
        full, c, _, x, y, o = mo.groups()
        X, Y = int(x) / units, int(y) / units
        dx, dy = X - org[c][0], Y - org[c][1]
        for n in mem[c]:
            m[n]['x'] = round(base[n]['x'] + dx, 3); m[n]['y'] = round(base[n]['y'] + dy, 3)
        seen += 1
    assert seen == len(mem), f'placed {seen} of {len(mem)} clusters'
    return m


if __name__ == '__main__':
    die = C.Die(); C.attach_ports(die)
    print(build(die, Path(sys.argv[1])))
