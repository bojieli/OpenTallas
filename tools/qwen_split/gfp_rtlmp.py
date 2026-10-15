#!/usr/bin/env python3
"""GLOBAL-FP-Q candidate (a): OpenROAD RTL-MP (hierarchical, dataflow-aware macro placer) at die block level.

Every die instance becomes a hard macro (real outline, per-port pins at the assigned per-bit pin centroids, real
master symmetry); every data bus becomes k parallel nets with k ~ bits x activations/token / (217 x 64) (net weight
= width x traffic, as the brief asks).  Hierarchy given to RTL-MP: one module per 4x4 reduction block (tiles + its
stations), W/E head columns, hub, three band port groups, KV link group, IO band.  The S-edge IO band and the N-edge
KV PHY are pre-placed FIXED.  The macro placement written by RTL-MP is read back into the gfp model and scored by
gfp_core.score exactly like every other candidate.
"""
import collections, math, os, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gfp_core as C  # noqa: E402
import gfp_candidates as G  # noqa: E402

PLAT = Path('/home/ubuntu/.local/opentallas-pdk-asap7-platform/asap7/lef')
NET_UNIT = 64 * C.ME_OPS
FIXED = ('io_collective', 'io_ucie', 'io_serdes', 'io_serdes_1', 'io_serdes_2', 'io_xfifo', 'ucie_kv')


def module_of(n, i, B):
    if i['m'] == 'qfd_tile_nk' or i['m'].startswith('qfd_xcst'):
        c, r = map(int, n.split('_')[1:3])
        return f'blk_{c // 4}_{r // 4}'
    if i['m'].startswith('qfd_xcol'): return 'head_w' if i['m'].endswith('_w') else 'head_e'
    if n.startswith('io_'): return 'io'
    if n in G.TOP: return 'kv'
    for b, names in G.BAND.items():
        if n in names: return f'band_{b}'
    return 'hub'


def build(die, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    base = die.base
    B = None
    # nets
    k_of = {}
    for r in die.recs:
        w = r['n'] * max(r['act'], 1)
        k_of[r['b']] = max(1, min(64, round(w / NET_UNIT)))
    # pins needed per (master, port)
    need = collections.defaultdict(int)
    for r in die.recs:
        for (n, _), p in zip(r['ends'], r['port']):
            need[(base[n]['m'], p)] = max(need[(base[n]['m'], p)], k_of[r['b']])
    # LEF
    lef = ['VERSION 5.8 ;', 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;']
    masters = sorted({i['m'] for i in base.values()})
    for m in masters:
        info = die.d['masters'][m]
        w, h = info['w'], info['h']
        lef += [f'MACRO {m}', '  CLASS BLOCK ;', '  ORIGIN 0 0 ;', f'  FOREIGN {m} 0 0 ;', f'  SIZE {w:.3f} BY {h:.3f} ;', '  SYMMETRY X Y ;']
        pins = die.g.pins[m]
        for (mm, p), k in sorted(need.items()):
            if mm != m: continue
            loc = pins[p]
            for j in range(k):
                q = loc[min(len(loc) - 1, int((j + 0.5) * len(loc) / k))]
                x = min(max(q[0], 0.05), w - 0.15); y = min(max(q[1], 0.05), h - 0.15)
                lef += [f'  PIN {p}_{j}', '    DIRECTION INOUT ;', '    USE SIGNAL ;', '    PORT', '      LAYER M4 ;',
                        f'        RECT {x:.3f} {y:.3f} {x + 0.1:.3f} {y + 0.1:.3f} ;', '    END', f'  END {p}_{j}']
        lef += [f'END {m}']
    lef += ['END LIBRARY']
    (out / 'macros.lef').write_text('\n'.join(lef) + '\n')
    # hierarchical verilog
    mod = {n: module_of(n, i, B) for n, i in base.items()}
    nets = []           # (netname, [(inst, pin)])
    for r in die.recs:
        k = k_of[r['b']]
        for j in range(k):
            nets.append((f"{r['b']}_{j}", [(n, f'{p}_{j}') for (n, _), p in zip(r['ends'], r['port'])]))
    users = collections.defaultdict(set)
    for nn, eps in nets:
        for n, _ in eps: users[nn].add(mod[n])
    members = collections.defaultdict(list)
    for n in base: members[mod[n]].append(n)
    conns = collections.defaultdict(lambda: collections.defaultdict(list))
    for nn, eps in nets:
        for n, p in eps: conns[n][p].append(nn)
    v = []
    for md, insts in sorted(members.items()):
        ports = sorted({nn for nn, us in users.items() if md in us and len(us) > 1})
        local = sorted({nn for nn, us in users.items() if us == {md}})
        v.append(f'module {md} (' + ', '.join(['gin'] + ports) + ');')
        v.append('  input gin;')
        for p in ports: v.append(f'  inout {p};')
        # one real std cell per module (RTL-MP soft-macro shaping needs a non-empty std-cell cluster)
        v.append(f'  wire {md}_bo; BUFx2_ASAP7_75t_R {md}_buf (.A(gin), .Y({md}_bo));')
        for p in local: v.append(f'  wire {p};')
        for n in insts:
            pc = [f'.{p}({nl[0]})' for p, nl in sorted(conns[n].items())]
            v.append(f'  {base[n]["m"]} {n} (' + ', '.join(pc) + ');')
        v.append('endmodule')
    top_wires = sorted({nn for nn, us in users.items() if len(us) > 1})
    v.append('module qfd_compute_die (gin);')
    v.append('  input gin;')
    for w_ in top_wires: v.append(f'  wire {w_};')
    for md in sorted(members):
        ports = sorted({nn for nn, us in users.items() if md in us and len(us) > 1})
        v.append(f'  {md} u_{md} (' + ', '.join(['.gin(gin)'] + [f'.{p}({p})' for p in ports]) + ');')
    v.append('endmodule')
    (out / 'die.v').write_text('\n'.join(v) + '\n')
    # fixed placement + tcl
    W, H = die.die['w'], die.die['h']
    fix = []
    for n in FIXED:
        i = base[n]
        fix.append(f'place_macro -macro_name u_{mod[n]}/{n} -location {{{i["x"]:.3f} {i["y"]:.3f}}} -orientation {i["o"]}')
    tcl = f"""
read_lef {PLAT}/asap7_tech_1x_201209.lef
read_lef {PLAT}/asap7sc7p5t_28_R_1x_220121a.lef
read_lef {out}/macros.lef
read_verilog {out}/die.v
link_design qfd_compute_die
initialize_floorplan -die_area "0 0 {W:.3f} {H:.3f}" -core_area "0 0 {W:.3f} {H:.3f}" -site asap7sc7p5t
make_tracks M1 -x_offset 0 -x_pitch 0.036 -y_offset 0 -y_pitch 0.036
make_tracks M2 -x_offset 0 -x_pitch 0.036 -y_offset 0 -y_pitch 0.036
make_tracks M3 -x_offset 0 -x_pitch 0.036 -y_offset 0 -y_pitch 0.036
make_tracks M4 -x_offset 0 -x_pitch 0.048 -y_offset 0 -y_pitch 0.048
make_tracks M5 -x_offset 0 -x_pitch 0.048 -y_offset 0 -y_pitch 0.048
make_tracks M6 -x_offset 0 -x_pitch 0.064 -y_offset 0 -y_pitch 0.064
make_tracks M7 -x_offset 0 -x_pitch 0.064 -y_offset 0 -y_pitch 0.064
make_tracks M8 -x_offset 0 -x_pitch 0.08 -y_offset 0 -y_pitch 0.08
make_tracks M9 -x_offset 0 -x_pitch 0.08 -y_offset 0 -y_pitch 0.08
{chr(10).join(fix)}
foreach n {{{' '.join(f'u_{mod[n]}/{n}' for n in FIXED)}}} {{ [[ord::get_db_block] findInst $n] setPlacementStatus FIRM }}
place_pins -hor_layers M4 -ver_layers M5
rtl_macro_placer -halo_width 21.6 -halo_height 21.6 -target_util 0.95 -report_directory {out}/rpt -write_macro_placement {out}/placement.tcl
write_def {out}/placed.def
"""
    (out / 'run.tcl').write_text(tcl)
    return dict(macros=len(base), nets=len(nets), modules=len(members), k_total=sum(k_of.values()))


def read_back(die, out: Path):
    """Parse placed.def COMPONENTS into a gfp model (instance names without the module prefix)."""
    m = {n: dict(i) for n, i in die.base.items()}
    txt = (out / 'placed.def').read_text()
    units = int(re.search(r'UNITS DISTANCE MICRONS (\d+)', txt).group(1))
    for mo in re.finditer(r'-\s+(\S+)\s+(\S+)\s+\+\s+(PLACED|FIXED|FIRM)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\S+)', txt):
        full, master, _, x, y, o = mo.groups()
        n = full.split('/')[-1].replace('\\', '')
        if n in m:
            m[n]['x'] = int(x) / units; m[n]['y'] = int(y) / units
            m[n]['o'] = {'N': 'R0', 'FN': 'MY', 'FS': 'MX', 'S': 'R180'}.get(o, 'R0')
    return m


if __name__ == '__main__':
    die = C.Die(); C.attach_ports(die)
    out = Path(sys.argv[1])
    print(build(die, out))
