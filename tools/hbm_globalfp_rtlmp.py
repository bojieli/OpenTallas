#!/usr/bin/env python3
"""GLOBAL-FP-H candidate (a): OpenROAD RTL-MP (rtl_macro_placer) at die block level.

Every graph node becomes a LEF CLASS BLOCK macro (its outline, pins on M4 at the outline centre per bundle);
every link becomes round(bits/32 * weight) two-pin nets (weight 1 = width only; 'traffic' mode multiplies by
1 + normalised traffic share), instantiated in a hierarchical Verilog netlist (one module per quadrant
cluster, ATT, IDX, IO) so RTL-MP's dataflow clustering sees the real groups.  PHYs and SerDes are FIRM.
Reads back the placed DEF COMPONENTS -> placement json (lower-left, um).

  python3 tools/hbm_globalfp_rtlmp.py --graph graph.json --tech asap7/ --mode width|traffic --work DIR [--run]
"""
import argparse, collections, json, math, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hbm_globalfp as F

DBU = 1000


def mod_of(n):
    i = n['id']
    if i.startswith('att_'):
        return 'm_att'
    if i.startswith('idx_'):
        return 'm_idx'
    if i.startswith(('lk_', 'ep_')):
        return 'm_io'
    if i.startswith('phy_'):
        return 'TOP'
    if i == 'hc_eng' or i.startswith('hc_eng'):
        return 'm_hc'
    return f"m_q{n['quadrant']}"


def gen(G, work, mode, fixed_pos):
    N, L = G['nodes'], G['links']
    os.makedirs(work, exist_ok=True)
    tq = sum(l['bytes_per_token']['qwen'] for l in L) or 1; td = sum(l['bytes_per_token']['ds'] for l in L) or 1
    tb = sum(l['bits'] for l in L)
    nets = []          # (net, src, dst)
    pins = {i: [] for i in N}
    for k, l in enumerate(L):
        w = 1.0
        if mode == 'traffic':
            share = 0.5 * (l['bytes_per_token']['qwen'] / tq + l['bytes_per_token']['ds'] / td)
            w = 1.0 + share / (l['bits'] / tb)
        n = max(1, round(l['bits'] / 32 * min(w, 20.0)))
        for b in range(n):
            nm = f'n{k}_{b}'
            nets.append((nm, l['src'], l['dst']))
            pins[l['src']].append(nm + 'a'); pins[l['dst']].append(nm + 'b')
    # LEF
    with open(f'{work}/blocks.lef', 'w') as f:
        f.write('VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\nUNITS\n  DATABASE MICRONS 1000 ;\nEND UNITS\n')
        for i, n in N.items():
            w, h = round(n['w'] / 0.054) * 0.054, round(n['h'] / 0.270) * 0.270
            f.write(f'MACRO B_{i}\n  CLASS BLOCK ;\n  ORIGIN 0 0 ;\n  SIZE {w:.3f} BY {h:.3f} ;\n  SYMMETRY X Y ;\n')
            f.write(f'  PIN p\n    DIRECTION INOUT ;\n    USE SIGNAL ;\n    PORT\n      LAYER M4 ;\n        RECT {w/2-0.5:.3f} {h/2-0.5:.3f} {w/2+0.5:.3f} {h/2+0.5:.3f} ;\n    END\n  END p\n')
            f.write(f'  OBS\n    LAYER M1 ;\n      RECT 0 0 {w:.3f} {h:.3f} ;\n    LAYER M2 ;\n      RECT 0 0 {w:.3f} {h:.3f} ;\n    LAYER M3 ;\n      RECT 0 0 {w:.3f} {h:.3f} ;\n  END\nEND B_{i}\n\n')
        f.write('END LIBRARY\n')
    # one pin per macro, bus width = number of nets: use a vector port p[k] would need k pins in LEF; instead each net
    # bundle attaches to the single pin 'p' through a per-instance port bus -> use separate pins: regenerate with N pins
    with open(f'{work}/blocks.lef', 'w') as f:
        f.write('VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\nUNITS\n  DATABASE MICRONS 1000 ;\nEND UNITS\n')
        for i, n in N.items():
            w, h = round(n['w'] / 0.054) * 0.054, round(n['h'] / 0.270) * 0.270
            k = max(1, len(pins[i]))
            sym = '' if i.startswith(('phy_', 'lk_')) else '  SYMMETRY X Y ;\n'
            f.write(f'MACRO B_{i}\n  CLASS BLOCK ;\n  ORIGIN 0 0 ;\n  SIZE {w:.3f} BY {h:.3f} ;\n{sym}')
            for b in range(k):
                x = w / 2 + ((b % 40) - 20) * 0.096; y = h / 2 + ((b // 40) % 40 - 20) * 0.096
                f.write(f'  PIN p[{b}]\n    DIRECTION INOUT ;\n    USE SIGNAL ;\n    PORT\n      LAYER M4 ;\n        RECT {x:.3f} {y:.3f} {x+0.024:.3f} {y+0.024:.3f} ;\n    END\n  END p[{b}]\n')
            f.write(f'  OBS\n    LAYER M1 ;\n      RECT 0 0 {w:.3f} {h:.3f} ;\n    LAYER M2 ;\n      RECT 0 0 {w:.3f} {h:.3f} ;\n    LAYER M3 ;\n      RECT 0 0 {w:.3f} {h:.3f} ;\n  END\nEND B_{i}\n\n')
        f.write('END LIBRARY\n')
    # Verilog: blackbox macros + hierarchical modules
    mods = {}
    for i, n in N.items():
        mods.setdefault(mod_of(dict(n, id=i)), []).append(i)
    conn = {i: list(pins[i]) for i in N}
    bufs = collections.defaultdict(list)      # module -> [(a, b)]
    use = collections.defaultdict(set)         # net -> modules using it
    for i in N:
        for nm in conn[i]:
            use[nm].add(mod_of(dict(N[i], id=i)))
    for nm, sname, dname in nets:
        ms = mod_of(dict(N[sname], id=sname)); md = mod_of(dict(N[dname], id=dname))
        m = ms if ms != 'TOP' else md
        bufs[m].append((nm + 'a', nm + 'b'))
        use[nm + 'a'].add(m); use[nm + 'b'].add(m)
    allm = set(mods) | set(bufs)
    def ports(m):
        return sorted(nm for nm, ms in use.items() if m in ms and (len(ms) > 1 or m == 'TOP'))
    with open(f'{work}/top.v', 'w') as f:
        for m in sorted(allm):
            if m == 'TOP':
                continue
            pp = ports(m)
            loc = sorted(nm for nm, ms in use.items() if ms == {m})
            f.write(f'module {m}(' + ', '.join(pp) + ');\n')
            for nm in pp:
                f.write(f'  inout {nm};\n')
            for nm in loc:
                f.write(f'  wire {nm};\n')
            for i in mods.get(m, []):
                cs = list(reversed(conn[i])) or ["1'bz"]
                f.write(f'  B_{i} u_{i}(.p({{' + ', '.join(cs) + '}));\n')
            for k2, (x, y) in enumerate(bufs[m]):
                f.write(f'  BUFx2_ASAP7_75t_R b{k2}(.A({x}), .Y({y}));\n')
            f.write('endmodule\n')
        top_ports = sorted(nm for nm, ms in use.items() if 'TOP' in ms)
        f.write('module hbm_die(' + ', '.join(top_ports) + ');\n')
        for nm in top_ports:
            f.write(f'  inout {nm};\n')
        cross = sorted(nm for nm, ms in use.items() if len(ms - {'TOP'}) > 1 and nm not in set(top_ports))
        for nm in cross:
            f.write(f'  wire {nm};\n')
        for m in sorted(allm):
            if m == 'TOP':
                continue
            f.write(f'  {m} u_{m}(' + ', '.join(f'.{x}({x})' for x in ports(m)) + ');\n')
        f.write('endmodule\n')
    W, H = F.W_DIE, F.H_DIE
    fix = []
    for i, (x, y) in fixed_pos.items():
        n = N[i]
        fix.append(f'odb::dbBlockage_create [ord::get_db_block] {int(x*DBU)} {int(y*DBU)} {int((x+n["w"])*DBU)} {int((y+n["h"])*DBU)}')
        ps = pins[i]
        for b, nm in enumerate(ps):
            px = x + 10 + (n['w'] - 20) * (b + 0.5) / len(ps)
            py = 0.0 if y < H / 2 else H
            fix.append(f'place_pin -pin_name {nm} -layer M5 -location {{{px:.3f} {py:.3f}}} -pin_size {{0.024 0.048}}')
    tcl = f"""
read_lef {{TECH}}/asap7_tech_1x_201209.lef
read_lef {{TECH}}/asap7sc7p5t_28_R_1x_220121a.lef
read_lef {work}/blocks.lef
read_verilog {work}/top.v
link_design hbm_die -hier
initialize_floorplan -die_area {{0 0 {W:.3f} {H:.3f}}} -core_area {{0 0 {W:.3f} {H:.3f}}} -site asap7sc7p5t
make_tracks M1 -x_offset 0.018 -x_pitch 0.036 -y_offset 0.018 -y_pitch 0.036
make_tracks M2 -x_offset 0.018 -x_pitch 0.036 -y_offset 0.018 -y_pitch 0.036
make_tracks M3 -x_offset 0.018 -x_pitch 0.036 -y_offset 0.018 -y_pitch 0.036
make_tracks M4 -x_offset 0.024 -x_pitch 0.048 -y_offset 0.024 -y_pitch 0.048
make_tracks M5 -x_offset 0.024 -x_pitch 0.048 -y_offset 0.024 -y_pitch 0.048
make_tracks M6 -x_offset 0.032 -x_pitch 0.064 -y_offset 0.032 -y_pitch 0.064
make_tracks M7 -x_offset 0.032 -x_pitch 0.064 -y_offset 0.032 -y_pitch 0.064
{chr(10).join(fix)}
set_thread_count 8
rtl_macro_placer -halo_width 20 -halo_height 20 -target_util 0.6 -report_directory {work}/rtlmp_rpt
write_def {work}/placed.def
"""
    open(f'{work}/run.tcl', 'w').write(tcl)
    return f'{work}/run.tcl'


def readback(G, deff):
    s = open(deff).read()
    comp = s[s.index('COMPONENTS'):s.index('END COMPONENTS')]
    P = {}
    dbu = int(re.search(r'UNITS DISTANCE MICRONS (\d+)', s).group(1))
    for m in re.finditer(r'-\s+(\S+)\s+B_(\S+)\s+\+\s+(?:PLACED|FIXED|FIRM)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\S+)', comp):
        i = m.group(2)
        n = G['nodes'][i]
        P[i] = dict(x=int(m.group(3)) / dbu, y=int(m.group(4)) / dbu, w=n['w'], h=n['h'], orient=m.group(5))
    return P


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--graph', required=True); ap.add_argument('--tech', required=True)
    ap.add_argument('--mode', default='width'); ap.add_argument('--work', required=True)
    ap.add_argument('--fixed-from', required=True, help='placement json for PHY + SerDes')
    ap.add_argument('--run', action='store_true'); ap.add_argument('--readback', action='store_true')
    a = ap.parse_args()
    G = json.load(open(a.graph))
    Pf = json.load(open(a.fixed_from))
    fixed = {i: (Pf[i]['x'], Pf[i]['y']) for i in G['nodes'] if i.startswith(('phy_',))}
    tcl = gen(G, a.work, a.mode, fixed)
    txt = open(tcl).read().replace('{TECH}', os.path.abspath(a.tech))
    open(tcl, 'w').write(txt)
    if a.run:
        r = subprocess.run(['openroad', '-no_init', '-exit', tcl], capture_output=True, text=True)
        open(f'{a.work}/openroad.log', 'w').write(r.stdout + r.stderr)
        print('openroad rc', r.returncode)
    if a.readback or a.run:
        P = readback(G, f'{a.work}/placed.def')
        json.dump(P, open(f'{a.work}/placement.json', 'w'))
        print('placed', len(P))
