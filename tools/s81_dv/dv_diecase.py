#!/usr/bin/env python3
"""S81-DV die case (p4 and later): plan -> OpenROAD die-top case for a GRT (+ die STA) trial.

Emits in --out:
  views/<master>.lef   one ABSTRACT per block instance (pins at the plan's link end points, bits spread along the face
                       at 2-track pitch; OBS M1-M6 over the body, so die nets may cross blocks only on M7+)
  die.v                the die top: every block as a cell, every planned relay stage as one DFF per bit
                       (DFFHQNx1_ASAP7_75t_R), chained driver pin -> stages -> receiver pin; one clock net per die
                       region (marked special: GRT routes data only; clocks are DIE-CLOCK's neighbour-relative roots)
  place.tcl            FIRM block placement from the plan + relay flops at their planned hop points (rows/site snapped)
  run.tcl / run.sh     floorplan, place, snap-legalise, [DIE-FLOW repeater step], GRT, gcell usage, census
  case.json            census (real / stand-in per block kind), nets, bits, flops, region, honest memory estimate
Labels: NOT_A_DIE_RESULT until every block binds to a real view (the census says which are stand-ins).
"""
import argparse
import collections
import gzip
import json
import math
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GITDIR = __import__('os').environ.get('OT_GIT_DIR', str(ROOT))   # S81-BIND3: sources from a git archive, refs from the repo
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from die_cluster import boundary as CB   # noqa: E402
import abstract_pin_windows as APW       # noqa: E402

PLAT = '/OpenROAD-flow-scripts/flow/platforms/asap7'
DFF = 'DFFHQNx1_ASAP7_75t_R'
BUF = 'BUFx8_ASAP7_75t_R'
LCB = 'BUFx16f_ASAP7_75t_R'   # station local clock buffer (F1 chain sink)
ROW, SITE = 0.27, 0.054
PIN_PITCH = 0.096            # 2 tracks of M4 (y) / M5 (x)
# what each plan block kind is today (DV p4): a real closed view exists for none of the DV-specific blocks yet
CENSUS = {'frame': 'stand-in (frame cluster wrappers from GEN not hardened; in-frame tiles bind native-PASS views)',
          'slice': 'stand-in (S81-SLICE 5-leaf cluster in progress; xfin leaf in closure)',
          'unit': 'stand-in (G-unit / seq / coll edge / bk / mix: re-parented units, not hardened)',
          'svc': 'stand-in (HBM service halves)', 'phy': 'stand-in abstract (vendor PHY)', 'ctrl': 'stand-in',
          'link': 'stand-in abstract (SerDes / UCIe PHY)'}


def load(p):
    return json.load(gzip.open(p) if str(p).endswith('.gz') else open(p))


def stand_in_lib(m, ports, c_ps=25.0, u_ps=25.0):
    """STAND-IN liberty (labelled): flop-first block, outputs launch C after clk, inputs set up / hold against clk.
    C = 25 / U = 25 are the recipe-4 leaf numbers DIE-FLOW takes for diagnostic stand-ins."""
    L = [f'library ({m}_standin) {{', '  /* STAND-IN: S81-DV die case diagnostic, not a closed view */',
         '  delay_model : table_lookup ; time_unit : "1ps" ; capacitive_load_unit (1, ff) ; voltage_unit : "1V" ;',
         '  current_unit : "1mA" ; pulling_resistance_unit : "1kohm" ; leakage_power_unit : "1nW" ;',
         '  nom_voltage : 0.7 ; nom_temperature : 25 ; nom_process : 1 ;',
         '  input_threshold_pct_rise : 50 ; input_threshold_pct_fall : 50 ; output_threshold_pct_rise : 50 ;',
         '  output_threshold_pct_fall : 50 ; slew_lower_threshold_pct_rise : 10 ; slew_lower_threshold_pct_fall : 10 ;',
         '  slew_upper_threshold_pct_rise : 90 ; slew_upper_threshold_pct_fall : 90 ;']
    widths = sorted({b for _, _, b, *_ in ports})
    for b in widths:
        L.append(f'  type (b{b}) {{ base_type : array ; data_type : bit ; bit_width : {b} ; bit_from : {b - 1} ; bit_to : 0 ; downto : true ; }}')
    L += [f'  cell ({m}) {{', '    area : 1 ;', '    pin (clk) { direction : input ; clock : true ; capacitance : 1.0 ; }']
    for port, d, b, *_ in ports:
        L.append(f'    bus ({port}) {{ bus_type : b{b} ; direction : {d} ;')
        if d == 'input':
            L += ['      capacitance : 0.6 ;',
                  f'      timing () {{ related_pin : "clk" ; timing_type : setup_rising ; rise_constraint (scalar) {{ values ("{u_ps}") ; }} fall_constraint (scalar) {{ values ("{u_ps}") ; }} }}',
                  '      timing () { related_pin : "clk" ; timing_type : hold_rising ; rise_constraint (scalar) { values ("0") ; } fall_constraint (scalar) { values ("0") ; } }']
        else:
            L += ['      max_capacitance : 40 ;',
                  f'      timing () {{ related_pin : "clk" ; timing_type : rising_edge ; cell_rise (scalar) {{ values ("{c_ps}") ; }} cell_fall (scalar) {{ values ("{c_ps}") ; }} rise_transition (scalar) {{ values ("20") ; }} fall_transition (scalar) {{ values ("20") ; }} }}']
        L.append('    }')
        if d != 'input':   # forwarded clock out beside the bus (F1 hop 0: the source block forwards its clock)
            L += [f'    pin (cko_{port}) {{ direction : output ; max_capacitance : 40 ;',
                  f'      timing () {{ related_pin : "clk" ; timing_sense : positive_unate ; cell_rise (scalar) {{ values ("{c_ps}") ; }} cell_fall (scalar) {{ values ("{c_ps}") ; }} rise_transition (scalar) {{ values ("20") ; }} fall_transition (scalar) {{ values ("20") ; }} }}',
                  '    }']
    L += ['  }', '}']
    return '\n'.join(L) + '\n'


RLY = {'EW': (17.28, 32.4), 'WE': (17.28, 32.4), 'NS': (25.92, 17.28), 'SN': (25.92, 17.28)}


def station_dir(hops, px, py):
    """direction of travel on the straight piece that ENDS at the station point -> relay master suffix"""
    best = None
    for x1, y1, x2, y2, _ in hops:
        d = abs(x2 - px) + abs(y2 - py)
        if best is None or d < best[0]:
            best = (d, x2 - x1, y2 - y1)
    _, dx, dy = best
    if abs(dx) >= abs(dy):
        return 'WE' if dx > 0 else 'EW'
    return 'SN' if dy > 0 else 'NS'


def face_of(b, x, y):
    d = {'W': abs(x - b['x']), 'E': abs(x - b['x'] - b['w']), 'S': abs(y - b['y']), 'N': abs(y - b['y'] - b['h'])}
    return min(d, key=d.get)


def die_repair_tcl(out, dieflow_ref, skip=('n*_lck\\[*\\]',)):
    """DIE-FLOW shared repeater step (claude/dieflow-1017 -> main): files materialised from dieflow_ref, the step tcl
    written to out/die_repeaters_step.tcl; returns the run.tcl fragment that sources it"""
    a = argparse.Namespace(dieflow_ref=dieflow_ref)
    import subprocess, tempfile
    tmp = Path(tempfile.mkdtemp(prefix='dvrep_'))
    (tmp / 'tools/die_repeaters').mkdir(parents=True)
    names = subprocess.run(['git', '-C', GITDIR, 'ls-tree', '--name-only', a.dieflow_ref, 'tools/die_repeaters/'],
                           capture_output=True, text=True, check=True).stdout.split()
    for f in (Path(n).name for n in names):
        (tmp / 'tools/die_repeaters' / f).write_bytes(subprocess.run(['git', '-C', GITDIR, 'show', f'{a.dieflow_ref}:tools/die_repeaters/{f}'],
                                                                    capture_output=True, check=True).stdout)
    (tmp / 'tools/die_cluster').mkdir(); shutil.copy(ROOT / 'tools/die_cluster/cluster_bounds.tcl', tmp / 'tools/die_cluster/')
    for f in ('die_reach.py',):
        shutil.copy(ROOT / 'tools' / f, tmp / 'tools' / f)
    (tmp / 'results/arch').mkdir(parents=True); shutil.copy(ROOT / 'results/arch/die_reach_1016.json', tmp / 'results/arch/')
    subprocess.run([sys.executable, str(tmp / 'tools/die_repeaters/step.py'), 'copy', str(out)], check=True)
    libs = [f'{PLAT}/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz', f'{PLAT}/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib']
    t = subprocess.run([sys.executable, str(tmp / 'tools/die_repeaters/step.py'), 'tcl', '--design', 's81', '--report',
                        '/work/die_repeaters.json', '--legalize', 'snap',
                        '--repeat-nets', 'n*_fck*', '--fclk-globs', 'n*_fck*', '--fclk-policy', 'fail', *[x for g in skip for x in ('--skip', g)], '--libs', *libs], capture_output=True, text=True, check=True).stdout
    (out / 'die_repeaters_step.tcl').write_text(t)
    return f'# DIE-FLOW repeater step ({dieflow_ref})\nsource /work/die_repeaters_step.tcl\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--region', type=float, nargs=4, metavar=('X0', 'Y0', 'X1', 'Y1'),
                    help='pilot: keep blocks whose centre lies inside and links with both ends inside')
    ap.add_argument('--die-repair', action='store_true', help='splice DIE-FLOW step output (die_repeaters_step.tcl)')
    ap.add_argument('--congestion-iterations', type=int, default=30)
    ap.add_argument('--dieflow-ref', default='origin/main')
    ap.add_argument('--relay-ref', default=None, help='git ref holding the closed dsfd_dvrly_276_{EW,WE,NS,SN} views '
                    '(276-b lane stations become real relay macros; other widths stay DFF stand-ins)')
    ap.add_argument('--relay-widths', type=int, nargs='+', default=[276],
                    help='with --relay-ref: lane widths whose stations bind the closed dsfd_dvrly_<W>_<dir> views (S81-LAND2: '
                    '276 70 512 562 682); a (width, direction) without a closed view stays a DFF stand-in station (census)')
    ap.add_argument('--relay-kind', choices=('rly', 'rlyh'), default='rly',
                    help='rlyh (S81-BIND3): stations bind the closed HALF-CYCLE dsfd_dvrlyh_<W>_<dir> views (s81dv_rlyh_*)')
    # ROOT-0440 10-18 (Q-DIE11 class: fully obstructed abstracts gave Qwen GRT overflow 72k-747k at the pin faces):
    # pin-access window depth (um) per face pin cluster, OBS-free on M4..M6 (tools/abstract_pin_windows.py); M1-M3 stay
    # obstructed.  Default env OT_ABS_PIN_WINDOW_UM, 0 = previous abstracts byte for byte.
    ap.add_argument('--pin-window', type=float, default=float(__import__('os').environ.get('OT_ABS_PIN_WINDOW_UM', '0') or 0))
    ap.add_argument('--bind', choices=('standin', 'real'), default='standin',
                    help='real: S81-BIND real-view mode (tools/s81_dv/dv_bind.py) -- every plan master binds its RTL by the '
                    'bind table, real F1 relay masters on every link, regional reset relay tree, sourced forwarded clocks; '
                    'writes <out>/bind/ and runs the STRICT die_port_bind')
    ap.add_argument('--bind-table', default=str(ROOT / 'results/arch/s81_dv_1016/bind/bind_table.json'))
    ap.add_argument('--land-plan', default=None, help='LANDFIX-SQ: per-link landing E / tile (dv_land_pilot plan) for --bind real; '
                    'default = the bind table land_plan')
    a = ap.parse_args()
    plan = load(a.plan)
    out = Path(a.out); (out / 'views').mkdir(parents=True, exist_ok=True); (out / 'out').mkdir(exist_ok=True)
    W, H = plan['facts']['die_um']
    blocks = plan['blocks']
    keep = set(range(len(blocks)))
    ox = oy = 0.0
    if a.region:
        x0, y0, x1, y1 = a.region
        keep = {i for i, b in enumerate(blocks) if x0 <= b['x'] and b['x'] + b['w'] <= x1 and y0 <= b['y'] and b['y'] + b['h'] <= y1}
        ox, oy = x0, y0
        W, H = x1 - x0, y1 - y0
    bidx = {blocks[i]['name']: i for i in keep}
    # ------------------------------------------------------------------ links -> ports on blocks + relay chains
    pins = collections.defaultdict(list)          # inst -> [(port, dir, bits, x, y, face)]
    nets, flops, chains = [], [], []
    fsrc, sdir = {}, {}
    chain_pts = {}
    nbits = 0
    used = collections.Counter()
    for l in plan['links']:
        (bi0, p0, x0_, y0_, _), (bi1, p1, x1_, y1_, _) = l['e']
        n0, n1 = blocks[bi0]['name'], blocks[bi1]['name']
        if n0 not in bidx or n1 not in bidx:
            continue
        b = l['b']
        nm = l['i'].replace('-', '_')
        po = f'o_{nm}'; pi = f'i_{nm}'
        pins[n0].append((po, 'output', b, x0_ - ox, y0_ - oy, face_of(blocks[bi0], x0_, y0_)))
        pins[n1].append((pi, 'input', b, x1_ - ox, y1_ - oy, face_of(blocks[bi1], x1_, y1_)))
        hops = l['h']
        if 'sp' in l:      # explicit station points (stations on straights; die wire turns between stations)
            pts = [(x - ox, y - oy) for x, y in l['sp']]
        else:              # older plans: stage k at the end of hop k
            pts = [(h[2] - ox, h[3] - oy) for h in hops[:-1]]
        st = len(pts)
        chain_pts[nm] = pts
        chains.append(dict(link=l['i'], cls=l['c'], bits=b, stages=st, src=f'{n0}.{po}', dst=f'{n1}.{pi}', hop_um=round(max(abs(h[2] - h[0]) + abs(h[3] - h[1]) for h in hops), 1)))
        for k, (px, py) in enumerate(pts):
            flops.append((nm, k, b, px, py))
            sdir[(nm, k)] = station_dir(hops, px + ox, py + oy)
        nets.append((nm, n0, po, n1, pi, b, st))
        fsrc[nm] = (x0_ - ox, y0_ - oy)
        nbits += b
        used[l['c']] += b
    if a.bind == 'real':
        if a.region:
            raise SystemExit('dv_diecase: --bind real is a full-die netlist (no --region)')
        import dv_bind
        rec = dv_bind.emit(plan, out / 'bind', Path(a.bind_table), sdir, chain_pts,
                           land_plan=Path(a.land_plan) if a.land_plan else None)
        print(json.dumps({k: v for k, v in rec.items() if k in ('relay_masters', 'clock_forward_cells', 'reset', 'port_bind_rc')}, indent=1))
        # A caller must never launch physical work after a failed strict bind.
        # emit() keeps its failure record; propagate that verdict to the shell.
        rc = rec.get('port_bind_rc')
        if rc != 0:
            raise SystemExit(rc if isinstance(rc, int) and rc > 0 else 1)
        return
    # ------------------------------------------------------------------ abstracts (one master per kept instance)
    for i in sorted(keep):
        bl = blocks[i]
        m = f"dv_{bl['name']}"
        w, h = bl['w'], bl['h']
        lines = [f'MACRO {m}', '  CLASS BLOCK ;', '  ORIGIN 0 0 ;', f'  SIZE {w:.3f} BY {h:.3f} ;', '  SYMMETRY X Y ;']
        sig = []
        for port, d, bits, px, py, f in pins.get(bl['name'], []):
            lx, ly = px - (bl['x'] - ox), py - (bl['y'] - oy)
            span = bits * PIN_PITCH
            for k in range(bits):
                t = -span / 2 + (k + 0.5) * PIN_PITCH
                if f in 'WE':
                    yy = min(max(ly + t, 0.2), h - 0.2); xx = 0.0 if f == 'W' else w - 0.1
                    rect = f'RECT {xx:.3f} {yy - 0.012:.3f} {xx + 0.1:.3f} {yy + 0.012:.3f}'; layer = 'M4'
                else:
                    xx = min(max(lx + t, 0.2), w - 0.2); yy = 0.0 if f == 'S' else h - 0.1
                    rect = f'RECT {xx - 0.012:.3f} {yy:.3f} {xx + 0.012:.3f} {yy + 0.1:.3f}'; layer = 'M5'
                lines += [f'  PIN {port}[{k}]', f'    DIRECTION {d.upper()} ;', '    USE SIGNAL ;', '    PORT',
                          f'      LAYER {layer} ;', f'        {rect} ;', '    END', f'  END {port}[{k}]']
                sig.append((f'{port}[{k}]', layer, tuple(float(v) for v in rect.split()[1:])))
            if d != 'input':
                t = span / 2 + PIN_PITCH
                if f in 'WE':
                    yy = min(max(ly + t, 0.2), h - 0.2); xx = 0.0 if f == 'W' else w - 0.1
                    rect = f'RECT {xx:.3f} {yy - 0.012:.3f} {xx + 0.1:.3f} {yy + 0.012:.3f}'; layer = 'M4'
                else:
                    xx = min(max(lx + t, 0.2), w - 0.2); yy = 0.0 if f == 'S' else h - 0.1
                    rect = f'RECT {xx - 0.012:.3f} {yy:.3f} {xx + 0.012:.3f} {yy + 0.1:.3f}'; layer = 'M5'
                lines += [f'  PIN cko_{port}', '    DIRECTION OUTPUT ;', '    USE SIGNAL ;', '    PORT',
                          f'      LAYER {layer} ;', f'        {rect} ;', '    END', f'  END cko_{port}']
                sig.append((f'cko_{port}', layer, tuple(float(v) for v in rect.split()[1:])))
        lines += ['  PIN clk', '    DIRECTION INPUT ;', '    USE CLOCK ;', '    PORT', '      LAYER M5 ;',
                  f'        RECT {w / 2 - 0.012:.3f} 0.000 {w / 2 + 0.012:.3f} 0.100 ;', '    END', '  END clk']
        lines += ['  OBS', '    LAYER M1 ;', f'      RECT 0.2 0.2 {w - 0.2:.3f} {h - 0.2:.3f} ;']
        win = APW.windows(w, h, sig, a.pin_window, 4, 6) if a.pin_window > 0 and sig else {}
        for li, L in enumerate(('M2', 'M3', 'M4', 'M5', 'M6'), 2):
            if not win.get(li):
                lines += [f'    LAYER {L} ;', f'      RECT 0.2 0.2 {w - 0.2:.3f} {h - 0.2:.3f} ;']
                continue
            lines += [f'    LAYER {L} ;'] + [f'      RECT {q[0]:.3f} {q[1]:.3f} {q[2]:.3f} {q[3]:.3f} ;'
                                             for q in APW.minus_rect((0.2, 0.2, w - 0.2, h - 0.2), win[li])]
        lines += ['  END', f'END {m}', '']
        (out / 'views' / f'{m}.lib').write_text(stand_in_lib(m, pins.get(bl['name'], [])))
        (out / 'views' / f'{m}.lef').write_text('VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n' + '\n'.join(lines) + 'END LIBRARY\n')
    rview = {}                                    # (bits, dir) -> (w, h) of a closed relay view bound in this case
    if a.relay_ref:
        import subprocess
        for b in sorted(set(a.relay_widths)):
            for d in RLY:
                rk = a.relay_kind
                base = f'physical/ref_tile/s81dv_{rk}_{b}_{d.lower()}/views/dsfd_dv{rk}_{b}_{d}/dsfd_dv{rk}_{b}_{d}'
                lef = subprocess.run(['git', '-C', GITDIR, 'show', f'{a.relay_ref}:{base}.lef'], capture_output=True)
                if lef.returncode:
                    continue
                sz = next(l.split() for l in lef.stdout.decode().splitlines() if l.strip().startswith('SIZE'))
                rview[(b, d)] = (float(sz[1]), float(sz[3]))
                tag = d if b == 276 else f'{b}_{d}'      # 276 keeps its p4j file names
                (out / 'views' / f'rly_{tag}.lef').write_bytes(lef.stdout)
                (out / 'views' / f'rly_{tag}_tt.lib').write_bytes(subprocess.run(
                    ['git', '-C', GITDIR, 'show', f'{a.relay_ref}:{base}_tt.lib'], capture_output=True, check=True).stdout)
    # ------------------------------------------------------------------ die netlist
    v = ['module dv_die (input clk, input rst);', '  wire n_rst_dv = rst;']
    nreal = 0
    for i in sorted(keep):
        bl = blocks[i]
        conns = []
        for port, d, bits, *_ in pins.get(bl['name'], []):
            conns.append(f'.{port}(w_{bl["name"]}_{port})')
            v.append(f'  wire [{bits - 1}:0] w_{bl["name"]}_{port};')
            if d != 'input':
                conns.append(f'.cko_{port}(c_{bl["name"]}_{port})')
                v.append(f'  wire c_{bl["name"]}_{port};')
        v.append(f'  dv_{bl["name"]} u_{bl["name"]} ({", ".join(conns + ["." + "clk(clk)"])});')
    nf = 0
    for nm, n0, po, n1, pi, b, st in nets:
        src = f'w_{n0}_{po}'; dst = f'w_{n1}_{pi}'
        if st == 0:
            v.append(f'  assign {dst} = {src};')
            continue
        prev = src
        # forwarded clock per lane (p4c-lanes): source buffer at the driver from the regional clock, stage k clocked
        # by n<link>_fck[k], a forwarding BUFx8 at each station drives the next segment (DIE-FLOW fclk audit glob
        # 'n*_fck\\[*\\]'); the sink re-time is the last station (DIE-CLOCK method section 3)
        # F1 chain (DIE-CLOCK): the hop net n<link>_fck[k] has ONE sink, the station's local clock buffer lcb_k
        # (BUFx16f), which drives the station flops on the short local net n<link>_lck[k] (never repeated); the
        # forwarding BUFx8 ff_k beside the data output starts hop k+1 -- station k+1 clk_in = station k clk_out
        v.append(f'  wire [{st}:0] n{nm}_fck;')
        v.append(f'  wire [{max(st - 1, 0)}:0] n{nm}_lck;')
        v.append(f'  assign n{nm}_fck[0] = c_{n0}_{po};   // hop 0: source block forwards its clock (cko beside the bus)')
        for k in range(st):
            wn = f'r_{nm}_{k}'
            v.append(f'  wire [{b - 1}:0] {wn};')
            if (b, sdir[(nm, k)]) in rview:
                # real closed station (flop-first, recipe 4): ck = hop clock in, ck_o = forwarded out (F1)
                v.append(f'  dsfd_dv{a.relay_kind}_{b}_{sdir[(nm, k)]} st_{nm}_{k} (.i({prev}), .o({wn}), .ck(n{nm}_fck[{k}]), '
                         f'.ck_o(n{nm}_fck[{k + 1}]), .rs(n_rst_dv));')
                nreal += 1
                prev = wn
                continue
            v.append(f'  {LCB} lcb_{nm}_{k} (.A(n{nm}_fck[{k}]), .Y(n{nm}_lck[{k}]));')
            for j in range(b):
                v.append(f'  {DFF} f_{nm}_{k}_{j} (.CLK(n{nm}_lck[{k}]), .D({prev}[{j}]), .QN({wn}[{j}]));')
            v.append(f'  {BUF} ff_{nm}_{k} (.A(n{nm}_lck[{k}]), .Y(n{nm}_fck[{k + 1}]));')
            nf += b
            prev = wn
        v.append(f'  assign {dst} = {prev};')
    v.append('endmodule')
    # blocks are library cells (LEF + stand-in liberty): no Verilog module bodies (an empty module would flatten away)
    (out / 'die.v').write_text('\n'.join(v) + '\n')
    # ------------------------------------------------------------------ placement
    pl = []
    for i in sorted(keep):
        bl = blocks[i]
        pl.append(f'place_inst -name u_{bl["name"]} -location {{{bl["x"] - ox:.3f} {bl["y"] - oy:.3f}}} -orientation R0 -status FIRM')
    # relay flops: a station of `b` flops on a small square of rows / sites at the hop point
    for nm, k, b, px, py in flops:
        if (b, sdir[(nm, k)]) in rview:
            w_, h_ = rview[(b, sdir[(nm, k)])]
            pl.append(f'place_inst -name st_{nm}_{k} -location {{{px - w_ / 2:.3f} {py - h_ / 2:.3f}}} -orientation R0 -status FIRM')
            continue
        pl.append(f'place_inst -name ff_{nm}_{k} -location {{{round((px - 2) / SITE) * SITE:.3f} {round((py - 1) / ROW) * ROW + 1.08:.3f}}} -orientation R0 -status PLACED')
        pl.append(f'place_inst -name lcb_{nm}_{k} -location {{{round((px - 4) / SITE) * SITE:.3f} {round((py - 2) / ROW) * ROW + 1.08:.3f}}} -orientation R0 -status PLACED')
    for nm, k, b, px, py in flops:
        if (b, sdir[(nm, k)]) in rview:
            continue
        side = max(1, int(math.ceil(math.sqrt(b * 0.648 / (ROW * SITE)) / 12)))   # ~12 sites per DFF
        cols = max(1, int(math.ceil(math.sqrt(b))))
        for j in range(b):
            cx = px + (j % cols) * 12 * SITE
            cy = py + (j // cols) * ROW
            cx = round(cx / SITE) * SITE; cy = round(cy / ROW) * ROW + 1.08
            pl.append(f'place_inst -name f_{nm}_{k}_{j} -location {{{cx:.3f} {cy:.3f}}} -orientation R0 -status PLACED')
    (out / 'place.tcl').write_text('\n'.join(pl) + '\n')
    repair = '# no die repair (pure GRT diagnostic)\n'
    if a.die_repair:
        repair = die_repair_tcl(out, a.dieflow_ref)
    post = ('estimate_parasitics -global_routing\n'
            'if {[llength [info procs ot_die_rep_post_grt_audit]]} { ot_die_rep_post_grt_audit /work/die_repeaters.post_grt.json }\n'
            if a.die_repair else 'estimate_parasitics -global_routing\n')
    tcl = f'''# S81-DV die case (tools/s81_dv/dv_diecase.py) -- NOT_A_DIE_RESULT (stand-in census in case.json)
read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob /work/views/*.lef] {{ read_lef $f }}
read_liberty {PLAT}/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
read_liberty {PLAT}/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
foreach f [glob /work/views/*.lib] {{ read_liberty $f }}
read_verilog /work/die.v
link_design dv_die
{CB.floorplan_tcl(W, H)}
make_tracks M9 -x_offset 0.116 -x_pitch 0.080 -y_offset 0.116 -y_pitch 0.080
make_tracks M8 -x_offset 0.116 -x_pitch 0.080 -y_offset 0.116 -y_pitch 0.080
make_tracks M7 -x_offset 0.016 -x_pitch 0.064 -y_offset 0.016 -y_pitch 0.064
make_tracks M6 -x_offset 0.012 -x_pitch 0.048 -y_offset 0.016 -y_pitch 0.064
make_tracks M5 -x_offset 0.012 -x_pitch 0.048 -y_offset 0.012 -y_pitch 0.048
make_tracks M4 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.012 -y_pitch 0.048
make_tracks M3 -x_offset 0.009 -x_pitch 0.640 -y_offset 0.009 -y_pitch 0.640
make_tracks M2 -x_offset 0.009 -x_pitch 0.640 -y_offset 0.045 -y_pitch 0.640
make_tracks M1 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.009 -y_pitch 0.036
set p0 [clock seconds]
source /work/place.tcl
puts "OT_PLACE_S [expr {{[clock seconds]-$p0}}] insts [llength [get_cells *]]"
{CB.legalize_tcl('place', max_dpl_gsites=2.0)}
write_db /work/out/place.odb
source {PLAT}/setRC.tcl
set_wire_rc -signal -layer M6
create_clock -name clk -period 833.333 [get_ports clk]
set ck [[ord::get_db_block] findNet clk]
if {{$ck ne "NULL"}} {{ $ck setSpecial }}
# relay rs: regional reset tree (die reset plan) not modelled here -- special, DIAGNOSTIC (listed in case.json)
foreach rn {{rst n_rst_dv}} {{ set r [[ord::get_db_block] findNet $rn]; if {{$r ne "NULL"}} {{ $r setSpecial }} }}
{repair}set_routing_layers -signal M2-M7 -clock M5-M9
set_global_routing_layer_adjustment M2-M3 0.50
set_global_routing_layer_adjustment M4-M5 0.30
set_global_routing_layer_adjustment M6-M7 0.20
set t0 [clock seconds]
global_route -congestion_iterations {a.congestion_iterations} -allow_congestion -verbose -congestion_report_file /work/out/grt_congestion.rpt
puts "OT_GRT_S [expr {{[clock seconds]-$t0}}]"
write_db /work/out/grt.odb
{post}
puts OT_DONE
'''
    (out / 'run.tcl').write_text(tcl)
    shutil.copy(ROOT / 'tools/die_cluster/cluster_bounds.tcl', out / 'cluster_bounds.tcl')
    (out / 'run.sh').write_text('''#!/bin/bash
D=$(cd $(dirname $0) && pwd); N=dvdie-$$
docker run --rm --name $N --cpus=${CPUS:-8} --memory=${MEMG:-128}g -v $D:/work -w /work openroad/orfs:asap7lock \\
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads ${CPUS:-8} -no_init -exit /work/run.tcl > /work/out/run.log 2>&1; rc=\\$?; chmod -R a+rwX /work/out; exit \\$rc"
rc=$?; echo $rc > $D/out/run.exit; exit $rc
''')
    kinds = collections.Counter(blocks[i]['kind'] for i in keep)
    area = W * H / 1e6
    info = dict(schema='opentallas.s81_dv.die_case.v1', plan=str(a.plan), region=a.region, die_um=[W, H], area_mm2=round(area, 2),
                blocks=dict(kinds), census={k: CENSUS.get(k, 'stand-in') for k in kinds},
                real_views=dict(relay_276_stations=sum(1 for nm, k, b, *_ in flops if b == 276 and (b, sdir[(nm, k)]) in rview),
                                relay_stations=nreal, relay_views=sorted(f'{b}_{d}' for b, d in rview),
                                standin_stations=dict(collections.Counter(f'{b}_{sdir[(nm, k)]}' for nm, k, b, *_ in flops
                                                                          if (b, sdir[(nm, k)]) not in rview)),
                                relay_ref=a.relay_ref, relay_kind=a.relay_kind,
                                diagnostic='relay rs pins on one special net (regional reset tree not modelled in this case)'),
                links=len(nets), bits=nbits, bits_by_class=dict(used), relay_flops=nf,
                die_nets_est=nbits + nf, die_repair=a.die_repair,
                memory_note=('H-REACH measured ~3.5 GB/mm2 for full-die GRT (flat, with block internals); this case is die-top '
                             'only (abstract blocks), so the pilot measures its own GB/mm2 before the full run'),
                label='NOT_A_DIE_RESULT: all DV blocks are stand-in abstracts; GRT diagnostic of the die-top nets')
    (out / 'case.json').write_text(json.dumps(dict(info, chains=chains), indent=1))
    print(json.dumps(info, indent=1))


if __name__ == '__main__':
    main()
