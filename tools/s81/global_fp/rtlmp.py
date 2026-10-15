#!/usr/bin/env python3
"""Block-level OpenROAD rtl_macro_placer (RTL-MP / mpl) run for the S81 hub region (GLOBAL-FP-S, screen only).

Every die block becomes a hard macro (CLASS BLOCK); frames, PHY/ctrl/svc, links, selector/collector bands and the HCX
homes are pre-placed and LOCKED; the 16 hub blocks are movable inside the hub-region fence.  Data-flow weights:
each graph link becomes round(width x duty / UNIT) parallel nets (trees: one multi-pin net per copy), i.e. net
multiplicity = traffic.  RTL-MP clusters/places the macros on that connectivity (its own wirelength/outline/boundary
objectives), then score.py scores the result with the same objective as every other candidate.
"""
import argparse, json, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import candidates as C

PLAT = '/home/ubuntu/.local/opentallas-pdk-asap7-platform/asap7'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--graph', required=True)
    ap.add_argument('--work', required=True)
    ap.add_argument('--vm-shape', default='2x2')
    ap.add_argument('--unit', type=float, default=40.0)
    ap.add_argument('--out', required=True)
    ap.add_argument('--mpl-args', default='', help='extra rtl_macro_placer weights, e.g. "-boundary_weight 0 -wirelength_weight 1000"')
    ap.add_argument('--tag', default=None)
    a = ap.parse_args()
    g = json.loads(Path(a.graph).read_text())
    w = Path(a.work); w.mkdir(parents=True, exist_ok=True)
    rects = C.base_rects(g)
    rects['sp_vm'] = rects['sp_vm'][:2] + C.VM_SHAPES[a.vm_shape]
    rects['sp_pq'] = rects['sp_pq'][:2] + [1728.0, rects['sp_pq'][3]]
    rects['mix4'] = rects['mix4'][:2] + C.MIX_SHAPES['2x2']
    x0, y0, x1, y1 = C.REGION
    RW, RH = x1 - x0, y1 - y0
    mov = [n for n in C.MOVABLE]
    # sub-die = the hub region; every block outside it is an IO pin on the region boundary at the projection of its
    # anchor (frame street ports grouped per half; IO/fixed blocks at their rectangle centre)
    def anchor(n):
        v = g['nodes'][n]
        if 'port' in v:
            return v['port']
        r = rects[n]
        return [r[0] + r[2] / 2, r[1] + r[3] / 2]
    def project(p):
        px, py = min(max(p[0], x0), x1) - x0, min(max(p[1], y0), y1) - y0
        d = {'W': px, 'E': RW - px, 'S': py, 'N': RH - py}
        side = min(d, key=d.get)
        if side == 'W': px = 0
        elif side == 'E': px = RW
        elif side == 'S': py = 0
        else: py = RH
        return [round(px, 3), round(py, 3)]
    nets, ios = [], []
    for e in g['edges']:
        inside = [b for b in e['ends'] if b in mov]
        if not inside:
            continue
        ext = [b for b in e['ends'] if b not in mov]
        groups = {}
        for b in ext:
            key = ('F' + g['nodes'][b]['half']) if b.startswith('F') else b
            groups.setdefault(key, []).append(anchor(b))
        k = max(1, int(round(e['width'] * e['duty'] / a.unit)))
        for c in range(k):
            nn = 'n_%s_%d' % (e['id'], c)
            pins_here = []
            for key, pts in groups.items():
                cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
                io = 'io_%s_%d_%s' % (e['id'], c, key)
                ios.append((io, nn, project([cx, cy])))
            nets.append((nn, inside))
    pins = {n: [] for n in mov}
    conns = []
    for nn, ends in nets:
        for b in ends:
            p = 'p%d' % len(pins[b]); pins[b].append(p); conns.append((nn, b, p))
    L = ['VERSION 5.8 ;', 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;']
    for n in mov:
        ww, hh = rects[n][2], rects[n][3]
        L.append('MACRO M_%s\n  CLASS BLOCK ;\n  ORIGIN 0 0 ;\n  SIZE %.3f BY %.3f ;' % (n, ww, hh))
        for p in pins[n]:
            L.append('  PIN %s\n    DIRECTION INOUT ;\n    USE SIGNAL ;\n    PORT\n      LAYER M4 ;\n        RECT %.3f %.3f %.3f %.3f ;\n    END\n  END %s'
                     % (p, ww / 2 - 0.05, hh / 2 - 0.05, ww / 2 + 0.05, hh / 2 + 0.05, p))
        L.append('  OBS\n    LAYER M1 ;\n      RECT 0 0 %.3f %.3f ;\n  END\nEND M_%s' % (ww, hh, n))
    L.append('END LIBRARY')
    (w / 'blocks.lef').write_text('\n'.join(L) + '\n')
    V = ['module s81_hubs (%s);' % ', '.join(i[0] for i in ios)]
    for io, nn, _ in ios:
        V.append('  inout %s;' % io)
    for nn, _ in nets:
        V.append('  wire %s;' % nn)
    for io, nn, _ in ios:
        pass
    byb = {n: [] for n in mov}
    for nn, b, p in conns:
        byb[b].append('.%s(%s)' % (p, nn))
    for n in mov:
        V.append('  M_%s u_%s (%s);' % (n, n, ', '.join(byb[n])))
    # IO pin -> net through one buffer each; plus one buffer per net (RTL-MP refuses a macro-only design)
    for k, (io, nn, _) in enumerate(ios):
        V.append('  BUFx2_ASAP7_75t_R bi_%d (.A(%s), .Y(%s));' % (k, io, nn))
    for k, (nn, _) in enumerate(nets):
        V.append('  wire d_%d;' % k)
        V.append('  BUFx2_ASAP7_75t_R b_%d (.A(%s), .Y(d_%d));' % (k, nn, k))
    V.append('endmodule')
    (w / 'blocks.v').write_text('\n'.join(V) + '\n')
    import gzip, shutil
    lib = w / 'invbuf_tt.lib'
    with gzip.open(PLAT + '/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz') as fi, open(lib, 'wb') as fo:
        shutil.copyfileobj(fi, fo)
    T = ['read_lef %s/lef/asap7_tech_1x_201209.lef' % PLAT, 'read_lef %s/lef/asap7sc7p5t_28_R_1x_220121a.lef' % PLAT,
         'read_liberty %s' % lib, 'read_lef %s/blocks.lef' % w,
         'read_verilog %s/blocks.v' % w, 'link_design s81_hubs',
         'initialize_floorplan -die_area {0 0 %.3f %.3f} -core_area {0 0 %.3f %.3f} -site asap7sc7p5t' % (RW, RH, RW, RH),
         'source %s/openRoad/make_tracks.tcl' % PLAT, 'set block [ord::get_db_block]']
    for io, nn, (px, py) in ios:
        T.append('place_pin -pin_name %s -layer M4 -location {%.3f %.3f} -pin_size {0.1 0.1} -force_to_die_boundary' % (io, px, py))
    T.append('rtl_macro_placer -halo_width 21.6 -halo_height 21.6 %s -report_directory %s/rpt -write_macro_placement %s/placement.tcl' % (a.mpl_args, w, w))
    T.append('foreach i [$block getInsts] { set b [$i getBBox]; puts "PLACED [$i getName] [$b xMin] [$b yMin] [$b xMax] [$b yMax] [$i getPlacementStatus]" }')
    T.append('exit')
    (w / 'run.tcl').write_text('\n'.join(T) + '\n')
    r = subprocess.run(['openroad', '-no_init', '-no_splash', '-exit', str(w / 'run.tcl')], capture_output=True, text=True, timeout=3600)
    (w / 'run.log').write_text(r.stdout + '\n' + r.stderr)
    out = {}
    for line in r.stdout.splitlines():
        if line.startswith('PLACED '):
            _, nm, xa, ya, xb, yb, stt = line.split()
            n = nm[2:]
            if n in C.MOVABLE:
                out[n] = [int(xa) / 1000 + x0, int(ya) / 1000 + y0, (int(xb) - int(xa)) / 1000, (int(yb) - int(ya)) / 1000]
    res = dict(tool='openroad rtl_macro_placer', returncode=r.returncode, nets=len(nets), unit=a.unit, vm_shape=a.vm_shape,
               mpl_args=a.mpl_args, tag=a.tag or ('u%g' % a.unit),
               rects=out, notes=['OpenROAD %s rtl_macro_placer %s, fence = hub region, net multiplicity = traffic/%.0f' % (
                   subprocess.run(['openroad', '-version'], capture_output=True, text=True).stdout.strip(), a.mpl_args, a.unit)])
    Path(a.out).write_text(json.dumps(res, indent=1))
    print(r.returncode, len(out), 'moved blocks;', r.stdout[-1500:], r.stderr[-1500:])


if __name__ == '__main__':
    main()
