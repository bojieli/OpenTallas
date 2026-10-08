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


# S81-PH partitions (tools/budgets/tiles.py): a die slab master hardened as tiles.  A slab with every tile closed has an
# assembled view (physical/s81_ph_views/assembled/<slab>, tools/s81/assemble_views.py: tile ETM arcs on the slab die
# ports + the inter-tile glue check); the others stay one interim master and the index reports their closed tiles.
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
    k = (0 if r.startswith(f'physical/s81_die_views/views/{label}/') else 1 if r.startswith(('physical/s81_ph_views/closed/',
                                                                                        'physical/s81_ph_views/assembled/'))
         else 2 if r.startswith('physical/s81_die_views/views/') else 3)
    return (k, -p.stat().st_mtime)


def closed_libs(corner, root=ROOT, label='m221pq'):
    """cell -> (lib path, kind): kind 'closed' when the lib sits in a closure-loop record dir (corner_sta.json beside it),
    'assembled' for an S81-PH slab assembled from its closed tile ETMs (tools/s81/assemble_views.py, assembled.json beside
    it), else 'macro' (memory / PHY / hard IP liberty)"""
    out = {}
    for p in sorted((root / 'physical').rglob(f'*_{corner}.lib'), key=lambda q: _rank(q, root, label)):
        t = p.read_text(errors='ignore')[:200000]
        for c in re.findall(r'^\s*cell\s*\(\s*"?([A-Za-z0-9_]+)"?\s*\)', t, re.M):
            out.setdefault(c, (p, 'assembled' if (p.parent / 'assembled.json').exists() else
                               'closed' if (p.parent / 'corner_sta.json').exists() else 'macro'))
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


def arcs_insertion(mst, view, mi, libpath=None):
    """[ss, ff, tt] clock insertion carried INSIDE a view's arcs (closed: its routed measurement, else the calib.json
    boundary mean beside the lib; assembled: mean over its tiles); interim / partitioned / macro carry none"""
    if view == 'closed':
        if mst in mi:
            return [mi[mst][c] for c in ('ss', 'ff', 'tt')]
        cj = libpath and Path(libpath).parent / 'calib.json'
        if cj and cj.exists():
            j = json.loads(cj.read_text())
            ss, ff = j['ss']['boundary']['mean'], j['ff']['boundary']['mean']
            return [ss, ff, (ss + ff) / 2]
    if view == 'assembled':
        src = [x for x in PARTS.get(mst, ()) if x in mi]
        if src:
            return [sum(mi[x][c] for x in src) / len(src) for c in ('ss', 'ff', 'tt')]
    return [0.0, 0.0, 0.0]


def balance_latency(lat, pin_master, masters, mi, libs=None, group=None):
    """in place: lat[pin] = planned [ss, ff, tt] arrival -> pin latency so that every flop arrives at plan + D
    (D = the deepest in-arc insertion per corner within the pin's clock tree: the trunk, or one column tree, which
    hangs off its cfifo `co` and can only pad below it; group: pin -> tree key, default one tree).  Returns the record."""
    ins = {}
    for k_ in lat:
        mst = pin_master[k_]
        if mst not in ins:
            r = masters.get(mst, {})
            lp = libs and libs['ss'].get(mst, (None,))[0]
            ins[mst] = arcs_insertion(mst, r.get('view', 'interim'), mi, lp)
            if any(ins[mst]):
                r['insertion_in_arcs_ps'] = [round(x, 1) for x in ins[mst]]
            r.pop('insertion_added_ps', None)
    grp = (lambda k_: group.get(k_, 'trunk')) if group else (lambda k_: 'trunk')
    D = defaultdict(lambda: [0.0, 0.0, 0.0])
    for k_ in lat:
        g, v = grp(k_), ins[pin_master[k_]]
        D[g] = [max(D[g][i], v[i]) for i in range(3)]
    for k_ in lat:
        v, d = ins[pin_master[k_]], D[grp(k_)]
        lat[k_] = [lat[k_][i] + d[i] - v[i] for i in range(3)]
    return dict(model='balanced: flop arrival = planned sink arrival + D (per clock tree); pin latency = that - in-arc '
                      'insertion; a column clock source = its cfifo ck pin latency',
                pad_ps={g: [round(x, 1) for x in d] for g, d in sorted(D.items()) if any(d)},
                masters_offset=sorted(m for m, v in ins.items() if any(v)), pins=len(lat))


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
                    help='closure-loop routed block clock insertion: the in-arc insertion of closed / assembled views, '
                         'subtracted from their planned pin latency (balanced die tree, balance_latency)')
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
                if src[1] == 'assembled' and 'glue_worst_ps' not in r_:
                    aj = json.loads((src[0].parent / 'assembled.json').read_text())
                    r_.update(tiles=list(PARTS.get(mst, ())), glue_worst_ps=aj['glue_worst_ps'],
                              tiles_ss_as_tt=aj['corners']['tt']['tiles_ss_as_tt'])
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
        # balanced die tree (s81-die-timing 2026-10-08): every block flop arrives at the PLANNED sink arrival.  The
        #   block sign-off (flow-ioref, io_ref_routed.sdc) references its IO to its OWN mean boundary-register arrival,
        #   so the die tree must deliver each partition clock pin early by the block's internal insertion (CTS macro
        #   pin insertion offsets).  sta_v2/v3 instead ADDED the routed insertion to 24 interim masters only (the q
        #   element +373 ps FF against its abutting interim bank): one-sided skew -> FF -823.8 on 3.0M endpoints.
        mi = measured_insertion(a.measured)
        grp = {}
        for bid, inst, p_ in sinks:
            pk = f'{inst}/' + rp.get(by[inst].master, {}).get(p_, [p_])[0]
            grp[pk] = bid if bid.startswith('ck_col_') else 'trunk'
        bal = balance_latency(lat, {k_: by[k_.split('/')[0]].master for k_ in lat}, rec['masters'], mi, cls_, grp)
        rec['routed_insertion'] = dict(file=str(a.measured), **bal)
        for ci, corner in ((0, 'ss'), (1, 'ff'), (2, 'tt')):
            (a.out / f'latency_{corner}.tcl').write_text(''.join(
                f'set_clock_latency {v[ci]:.1f} [get_pins -quiet {{{k_} {k_}[0]}}]\n' for k_, v in sorted(lat.items())))
        rec['tt_latency'] = 'estimate: mean of the CTS-validated SS and FF sink insertion'
        rec['clock_plan'] = dict(file=str(a.clock_plan), sinks=len(sinks), planned=sum(1 for s in sinks if f'{s[1]}/{s[2]}' in si),
                                 nearest=len(lat) - sum(1 for s in sinks if f'{s[1]}/{s[2]}' in si))
    # with the CTS plan: setup 60 + 25 plan tolerance, hold 25 + 25 plan tolerance (rule H1: the die-link hold term
    # (+50) is not counted at the die, the receiver block signs off its input min at L; was 75)
    for corner, (us, uh) in ((('ss', (85.0, 50.0)), ('tt', (85.0, 50.0)), ('ff', (85.0, 50.0))) if lat else
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
                    if root in lat:      # the balanced cfifo pin latency (the column tree pads below it)
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
