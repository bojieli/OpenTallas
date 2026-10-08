#!/usr/bin/env python3
"""S81 die-context STA kit (CLAUDE S81-RERUN 2026-10-07, coordinator audit: no S81 die had post-route die STA).

From a die variant (tools/dsrom_s81_fulldie.py options) writes, for SS and FF:
  * the liberty set: every CLOSED view lib in the tree (station / cfifo / ROM / ... *_ss.lib / *_ff.lib whose cell name
    is a die master), and an INTERIM pin-registered lib for every other master (generator glue, slabs, real macros
    without a lib): each data input a setup / hold arc to the master's clock pin, each output a clk->q arc; areas from
    the floorplan.  Interim constants (SS / FF): clk->q 90 / 32, setup 30 / 10, hold 15 / 15 ps (budget sheet).
  * sta_<corner>.tcl: read libs + die.v (+ SPEF when given), ideal clocks on the die clock sources (collective PLL
    pins, column roots), signoff uncertainty + the inter-region die budget (setup 60 + 150, hold 25 + 50), and report
    the worst paths per (start master, end master) class.  Forwarded-clock lanes have no clock in this model (station
    views carry them: unconstrained here, reported as such).
  die_sta.py kit --s81-opts "<opts>" --die layer --out DIR
"""
import argparse, json, re, shlex, sys
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
# --gen-root: import the die generator from another checkout (the source the die case / GRT SPEF was built from), so a
# kit refreshed with newer views keeps the netlist of the routed case
_g = next((sys.argv[i + 1] for i, x in enumerate(sys.argv[:-1]) if x == '--gen-root'), None)
sys.path.insert(0, str(Path(_g) / 'tools' if _g else ROOT / 'tools'))
import dsrom_s81_fulldie as S  # noqa: E402

CLK_NAMES = ('ck', 'clk', 'cks', 'ckh', 'cw', 'wclk', 'fi0', 'fi', 'xf', 'ck_in')
K = dict(ss=dict(cq=90.0, su=30.0, ho=15.0), tt=dict(cq=55.0, su=18.0, ho=15.0), ff=dict(cq=32.0, su=10.0, ho=15.0))
# owner option B (2026-10-07): die setup at TT, hold at FF, SS as sensitivity.  TT planned clock arrival = mean of the
# CTS-validated SS and FF insertions (the plan's CTS ran SS / FF libraries only): an estimate, marked in kit.json


# S81-PH partitions (tools/budgets/tiles.py): a die slab master hardened as tiles.  The die STA still models the slab
# as one interim master (no composite view); the index reports how many of its tile kinds are closed.
PARTS = dict(dsfd_bk_selector=('dsfd_selt_q', 'dsfd_selt_c'), dsfd_bk_collector=('dsfd_colt_lane', 'dsfd_colt_mrg'),
             dsfd_sp_capture=('dsfd_capt_x', 'dsfd_capt_g2', 'dsfd_capt_ctl'),
             dsfd_sp_collective=('dsfd_coll_lane_w', 'dsfd_coll_lane_e', 'dsfd_coll_core', 'dsfd_coll_ck'),
             dsfd_ctrl=('dsfd_ctrl_pc', 'dsfd_ctrl_ctr'),
             dsfd_svc=('dsfd_svc_pc', 'dsfd_svc_stn', 'dsfd_svcio_ad', 'dsfd_svcio_od', 'dsfd_svcio_q', 'dsfd_svcio_x'),
             dsfd_sp_vm=('dsfd_vm_bg',), dsfd_sp_gather=('ot_s81ph_root_tile', 'ot_s81ph_root_blk'))


def _rank(p, root, label):
    """lib preference when several files define one cell: this die variant's closed records, then S81-PH closed tiles,
    then other S81 die view records, then anything else (newest first within a rank)"""
    r = str(p.relative_to(root))
    k = (0 if r.startswith(f'physical/s81_die_views/views/{label}/') else 1 if r.startswith('physical/s81_ph_views/closed/')
         else 2 if r.startswith('physical/s81_die_views/views/') else 3)
    return (k, -p.stat().st_mtime)


def closed_libs(corner, root=ROOT, label='m221pq'):
    """cell -> (lib path, kind): kind 'closed' when the lib sits in a closure-loop record dir (corner_sta.json beside it),
    else 'macro' (memory / PHY / hard IP liberty)"""
    out = {}
    for p in sorted((root / 'physical').rglob(f'*_{corner}.lib'), key=lambda q: _rank(q, root, label)):
        t = p.read_text(errors='ignore')[:200000]
        for c in re.findall(r'^\s*cell\s*\(\s*"?([A-Za-z0-9_]+)"?\s*\)', t, re.M):
            out.setdefault(c, (p, 'closed' if (p.parent / 'corner_sta.json').exists() else 'macro'))
    return out


def measured_insertion(path):
    """block -> {ss, ff, tt} routed clock insertion (ps) from the closure loop's measured_insertion.json; a corner whose
    routed measurement is on another clock than the block's falls back to the calibrate CTS-only value; tt missing ->
    mean(ss, ff)"""
    if not path or not Path(path).exists():
        return {}
    out = {}
    for b, r in json.loads(Path(path).read_text())['blocks'].items():
        v = {}
        for c in ('ss', 'ff', 'tt'):
            x = r.get(c)
            if x and x.get('clock', r.get('clock')) == r.get('clock') and 'mean' in x:
                v[c] = float(x['mean'])
            elif (r.get('calibrate') or {}).get(c):
                v[c] = float(r['calibrate'][c]['mean'])
        if 'ss' in v and 'ff' in v:
            v.setdefault('tt', (v['ss'] + v['ff']) / 2)
            out[b] = v
    return out


def interim_lib(cells, corner):
    k = K[corner]
    L = [f'library (s81_interim_{corner}) {{', ' delay_model : table_lookup;', ' time_unit : "1ps";',
         ' voltage_unit : "1V";', ' current_unit : "1mA";', ' pulling_resistance_unit : "1kohm";',
         ' leakage_power_unit : "1nW";', ' capacitive_load_unit (1, ff);', ' nom_voltage : 0.7;', ' nom_temperature : 25;',
         ' nom_process : 1;']
    # every port a bus (width 1 too): the die SPEF / odb netlist name 1-bit macro pins 'ck[0]' (LEF bit pins)
    widths = sorted({w for _, _, ports in cells for _, (d, w) in ports.items()})
    for w in widths:
        L.append(f' type (b{w}) {{ base_type : array; data_type : bit; bit_width : {w}; bit_from : {w - 1}; bit_to : 0; '
                 'downto : true; }')
    for name, area, ports in cells:
        ck = next((c for c in CLK_NAMES if c in ports and ports[c][0] == 'input'), None)
        L.append(f' cell ({name}) {{ area : {area:.3f};')
        for p, (d, w) in sorted(ports.items()):
            head = f'  bus ({p}) {{ bus_type : b{w};'
            body = [head, f'   direction : {"input" if d == "input" else "output" if d == "output" else "inout"};']
            if d == 'input':
                body.append('   capacitance : 1.0;')
            if p == ck or (d == 'input' and p in CLK_NAMES):     # every clock pin of a multi-clock glue master
                body.append('   clock : true;')
            elif ck and d == 'input':
                for tt, v in (('setup_rising', k['su']), ('hold_rising', k['ho'])):
                    body.append(f'   timing () {{ related_pin : "{ck}"; timing_type : {tt}; '
                                f'rise_constraint (scalar) {{ values ("{v}"); }} fall_constraint (scalar) {{ values ("{v}"); }} }}')
            elif ck and d == 'output':
                body.append(f'   timing () {{ related_pin : "{ck}"; timing_type : rising_edge; '
                            f'cell_rise (scalar) {{ values ("{k["cq"]}"); }} cell_fall (scalar) {{ values ("{k["cq"]}"); }} '
                            'rise_transition (scalar) { values ("20"); } fall_transition (scalar) { values ("20"); } }')
            body.append('  }')
            L += body
        L.append(' }')
    L.append('}')
    return '\n'.join(L) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['kit'])
    ap.add_argument('--s81-opts', required=True)
    ap.add_argument('--die', default='layer')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--clock-plan', type=Path, help='results/rtl/budgets_20261006/clock_plan/<die>.json.gz: per-sink '
                    'planned SS / FF insertion (sinks not in the plan take the nearest planned sink of the same clock)')
    ap.add_argument('--gen-root', type=Path, help='checkout whose tools/dsrom_s81_fulldie.py builds the die (default: this one)')
    ap.add_argument('--views-root', type=Path, default=ROOT, help='checkout whose physical/ supplies the view libs')
    ap.add_argument('--label', default='m221pq', help='die variant label of physical/s81_die_views/views/<label>/')
    ap.add_argument('--measured', type=Path, default=ROOT / 'results/rtl/budgets_20261006/measured_insertion.json',
                    help='closure-loop routed block clock insertion: added to the planned pin latency of every INTERIM '
                         'master (or S81-PH slab via its tiles) that has one; closed views carry it in their arcs')
    ap.add_argument('--index-out', type=Path, help='also write the master -> view index (JSON) here')
    a = ap.parse_args()
    S.apply_options(S.die_options(argparse.ArgumentParser()).parse_args(shlex.split(a.s81_opts) + ['--die', a.die]))
    m = S.build()
    pdir = S.finalize_r8(m)
    a.out.mkdir(parents=True, exist_ok=True)
    first = {}
    for it in m['insts']:
        first.setdefault(it.master, it)
    rp = S.real_ports_r8()
    S.write_netlist(m, 1, a.out / 'die.v')
    rec = dict(masters={}, clocks=[])
    vroot = a.views_root.resolve()
    cls_ = {c: closed_libs(c, vroot, a.label) for c in ('ss', 'tt', 'ff')}
    for corner in ('ss', 'tt', 'ff'):
        cl = cls_[corner]
        cells, libs = [], set()
        for mst, it in sorted(first.items()):
            src = cl.get(mst)
            if not src and corner == 'tt' and mst in cls_['ss']:
                src = cls_['ss'][mst]        # routed view without a TT extraction: its SS liberty (pessimistic, marked)
            if src:
                libs.add(str(src[0]))
                r_ = rec['masters'].setdefault(mst, dict(view=src[1], libs={}))
                r_['libs'][corner] = str(src[0].relative_to(vroot)) + (' (SS as TT)' if src is not cl.get(mst) else '')
                continue
            if mst in rp:      # real macro without a lib: its die ports, bit names from the real port map
                ports = {}
                for p_, names in rp[mst].items():
                    for n_ in names:
                        mm = re.match(r'^(.*)\[(\d+)\]$', n_)
                        b, i = (mm.group(1), int(mm.group(2)) + 1) if mm else (n_, 1)
                        ports[b] = ('input', max(i, ports.get(b, ('input', 0))[1]))
                d_ = defaultdict(int)
                for bid, cls, bits, eps in m['buses']:
                    if eps[0][0] == it.name:
                        for n_ in rp[mst].get(S.pslice(eps[0][1])[0], []):
                            d_[re.sub(r'\[\d+\]$', '', n_)] = 1
                ports = {b: ('output' if d_.get(b) else 'input', w) for b, (_, w) in ports.items()}
            else:
                ports = dict(pdir.get(mst, {}))
            cells.append((mst, (it.w + S.SHAVE) * (it.h + S.SHAVE), ports))
            r_ = dict(view='interim', ports=len(ports))
            if mst in PARTS:
                done = sorted(x for x in PARTS[mst] if x in cls_['ss'] and cls_['ss'][x][1] == 'closed')
                r_.update(view='partitioned', tiles=list(PARTS[mst]), tiles_closed=done)
            rec['masters'][mst] = r_
        (a.out / f'interim_{corner}.lib').write_text(interim_lib(cells, corner))
        (a.out / f'libs_{corner}.txt').write_text('\n'.join(sorted(libs) + [f'/kit/interim_{corner}.lib']) + '\n')
    # clocks: die domain sources (collective PLL pins) and the column roots (cfifo co)
    srcs = []
    for bid, cls, bits, eps in m['buses']:
        if cls == 'clock':
            srcs.append((bid, f'{eps[0][0]}/{eps[0][1]}', dict(clk_stream=833.333, clk_serial=1111.111,
                                                                clk_hbm=1023.96).get(bid, 833.333)))
        elif cls == 'col_clock':
            srcs.append((bid, f'{eps[0][0]}/{eps[0][1]}', 833.333))
    rec['clocks'] = srcs
    lat = {}
    if a.clock_plan:
        import gzip, math
        cp = json.load(gzip.open(a.clock_plan))
        si = cp['sink_insertion']
        by = {it.name: it for it in m['insts']}
        cen = lambda n: (by[n].x + by[n].w / 2, by[n].y + by[n].h / 2)
        known = defaultdict(list)          # clock bus -> [(x, y, ss, ff)]
        sinks = []
        for bid, cls, bits, eps in m['buses']:
            if cls not in ('clock', 'col_clock'):
                continue
            for inst, p_ in eps[1:]:
                if inst not in by:
                    continue
                k_ = f'{inst}/{p_}'
                sinks.append((bid, inst, p_))
                if k_ in si:
                    known[bid].append(cen(inst) + tuple(si[k_]))
        for bid, inst, p_ in sinks:
            k_ = f'{inst}/{p_}'
            pk = f'{inst}/' + rp.get(by[inst].master, {}).get(p_, [p_])[0]   # real macros: the pin of the die port
            if k_ in si:
                lat[pk] = si[k_]
            elif known[bid]:
                x, y = cen(inst)
                nb = min(known[bid], key=lambda q: abs(q[0] - x) + abs(q[1] - y))
                lat[pk] = [nb[2], nb[3]]
        for k_ in list(lat):
            lat[k_] = [lat[k_][0], lat[k_][1], (lat[k_][0] + lat[k_][1]) / 2.0]
        # routed insertion: an interim master has no clock tree in its arcs; add the block's measured routed insertion
        #   (its own, else the mean over its closed S81-PH tiles) so its flops arrive where a hardened view's would
        mi = measured_insertion(a.measured)
        added = defaultdict(int)
        for k_ in list(lat):
            mst = by[k_.split('/')[0]].master
            if rec['masters'][mst]['view'] not in ('interim', 'partitioned'):
                continue
            src = [mst] if mst in mi else [x for x in PARTS.get(mst, ()) if x in mi]
            if src:
                add = [sum(mi[x][c] for x in src) / len(src) for c in ('ss', 'ff', 'tt')]
                lat[k_] = [lat[k_][i] + add[i] for i in range(3)]
                rec['masters'][mst]['insertion_added_ps'] = [round(x, 1) for x in add]
                rec['masters'][mst]['insertion_from'] = src
                added[mst] += 1
        rec['routed_insertion'] = dict(file=str(a.measured), interim_masters=len(added), pins=sum(added.values()))
        for ci, corner in ((0, 'ss'), (1, 'ff'), (2, 'tt')):
            (a.out / f'latency_{corner}.tcl').write_text(''.join(
                f'set_clock_latency {v[ci]:.1f} [get_pins -quiet {{{k_} {k_}[0]}}]\n' for k_, v in sorted(lat.items())))
        rec['tt_latency'] = 'estimate: mean of the CTS-validated SS and FF sink insertion'
        rec['clock_plan'] = dict(file=str(a.clock_plan), sinks=len(sinks), planned=sum(1 for s in sinks if f'{s[1]}/{s[2]}' in si),
                                 nearest=len(lat) - sum(1 for s in sinks if f'{s[1]}/{s[2]}' in si))
    for corner, (us, uh) in ((('ss', (85.0, 75.0)), ('tt', (85.0, 75.0)), ('ff', (85.0, 75.0))) if lat else
                             (('ss', (210.0, 75.0)), ('tt', (210.0, 75.0)), ('ff', (210.0, 75.0)))):
        T = ['set libs [split [string trim [read [open /kit/libs_%s.txt]]] "\\n"]' % corner,
             'foreach l $libs { read_liberty $l }', 'read_verilog /kit/die.v', 'link_design dsfd_die',
             'if {[file exists /kit/die.spef]} { read_spef /kit/die.spef; puts OT_SPEF }']
        for n_, pin, per in srcs:
            T.append(f'create_clock -name {n_} -period {per} [get_pins -quiet {{{pin} {pin}[0]}}]')
        if lat:   # planned per-sink insertion (the die tree's skew); uncertainty = signoff 60 + 25 plan tolerance
            T.append(f'source /kit/latency_{corner}.tcl')
            # a column clock is the stream trunk passed through its cfifo root: source latency = the trunk insertion
            # at that cfifo's ck pin (the plan's column-sink values are relative to the column root)
            ci = dict(ss=0, ff=1, tt=2)[corner]
            for n_, pin, per in srcs:
                if n_.startswith('ck_col_'):
                    root = pin.split('/')[0] + '/ck[0]' if pin.split('/')[0] + '/ck[0]' in lat else pin.split('/')[0] + '/ck'
                    if root in lat:
                        T.append(f'set_clock_latency -source {lat[root][ci]:.1f} [get_clocks {n_}]')
        T += [f'set_clock_uncertainty -setup {us} [all_clocks]', f'set_clock_uncertainty -hold {uh} [all_clocks]',
              'set_clock_groups -asynchronous -group {clk_serial} -group {clk_hbm} -group [get_clocks -quiet {clk_stream ck_col_*}]',
              'set_false_path -through [get_nets -quiet {n_rst_* n_rs_col_* por_n}]',
              f'report_checks -path_delay {"min" if corner == "ff" else "max"} -group_path_count 200 -endpoint_path_count 1 '
              f'-fields {{fanout}} -digits 1 > /kit/paths_{corner}.rpt',
              f'report_checks -path_delay {"min" if corner == "ff" else "max"} -group_path_count 100000 '
              f'-endpoint_path_count 1 -format end -digits 1 > /kit/end_{corner}.rpt',
              f'report_worst_slack -{"min" if corner == "ff" else "max"} -digits 1',
              f'report_tns -{"min" if corner == "ff" else "max"} -digits 1',
              f'report_check_types -violators -max_slew -max_capacitance > /kit/drv_{corner}.rpt']
        (a.out / f'sta_{corner}.tcl').write_text('\n'.join(t for t in T if t) + '\n')
    n = defaultdict(int)
    for v in rec['masters'].values():
        n[v['view']] += 1
    rec['counts'] = dict(n)
    rec['views_root'] = str(vroot)
    (a.out / 'kit.json').write_text(json.dumps(rec, indent=1) + '\n')
    if a.index_out:
        cnt = defaultdict(int)
        for it in m['insts']:
            cnt[it.master] += 1
        idx = dict(schema='opentallas.s81.die_view_index.v1', die=a.die, label=a.label, s81_opts=a.s81_opts,
                   counts=dict(n), instances={k: sum(cnt[m_] for m_, v in rec['masters'].items() if v['view'] == k) for k in n},
                   masters={k: dict(v, instances=cnt[k]) for k, v in sorted(rec['masters'].items())},
                   routed_insertion=rec.get('routed_insertion'))
        a.index_out.parent.mkdir(parents=True, exist_ok=True)
        a.index_out.write_text(json.dumps(idx, indent=1) + '\n')
    print(json.dumps(dict(n), indent=0), len(srcs), 'clock sources')


if __name__ == '__main__':
    main()
