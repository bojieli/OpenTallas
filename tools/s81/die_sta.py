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
sys.path.insert(0, str(ROOT / 'tools'))
import dsrom_s81_fulldie as S  # noqa: E402

CLK_NAMES = ('ck', 'clk', 'cks', 'ckh', 'cw', 'wclk', 'fi0', 'fi', 'xf', 'ck_in')
K = dict(ss=dict(cq=90.0, su=30.0, ho=15.0), ff=dict(cq=32.0, su=10.0, ho=15.0))


def closed_libs(corner):
    out = {}
    for p in list((ROOT / 'physical').rglob(f'*_{corner}.lib')):
        t = p.read_text(errors='ignore')[:200000]
        for c in re.findall(r'^\s*cell\s*\(\s*"?([A-Za-z0-9_]+)"?\s*\)', t, re.M):
            out.setdefault(c, p)
    return out


def interim_lib(cells, corner):
    k = K[corner]
    L = [f'library (s81_interim_{corner}) {{', ' delay_model : table_lookup;', ' time_unit : "1ps";',
         ' voltage_unit : "1V";', ' current_unit : "1mA";', ' pulling_resistance_unit : "1kohm";',
         ' leakage_power_unit : "1nW";', ' capacitive_load_unit (1, ff);', ' nom_voltage : 0.7;', ' nom_temperature : 25;',
         ' nom_process : 1;']
    widths = sorted({w for _, _, ports in cells for _, (d, w) in ports.items() if w > 1})
    for w in widths:
        L.append(f' type (b{w}) {{ base_type : array; data_type : bit; bit_width : {w}; bit_from : {w - 1}; bit_to : 0; '
                 'downto : true; }')
    for name, area, ports in cells:
        ck = next((c for c in CLK_NAMES if c in ports and ports[c][0] == 'input'), None)
        L.append(f' cell ({name}) {{ area : {area:.3f};')
        for p, (d, w) in sorted(ports.items()):
            head = f'  bus ({p}) {{ bus_type : b{w};' if w > 1 else f'  pin ({p}) {{'
            body = [head, f'   direction : {"input" if d == "input" else "output" if d == "output" else "inout"};']
            if d == 'input':
                body.append('   capacitance : 1.0;')
            if p == ck:
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
    for corner in ('ss', 'ff'):
        cl = closed_libs(corner)
        cells, libs = [], set()
        for mst, it in sorted(first.items()):
            if mst in cl:
                libs.add(str(cl[mst]))
                rec['masters'][mst] = dict(view='closed', lib=str(cl[mst].relative_to(ROOT)))
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
            rec['masters'][mst] = dict(view='interim', ports=len(ports))
        (a.out / f'interim_{corner}.lib').write_text(interim_lib(cells, corner))
        (a.out / f'libs_{corner}.txt').write_text('\n'.join(sorted(libs) + [str(a.out / f'interim_{corner}.lib')]) + '\n')
    # clocks: die domain sources (collective PLL pins) and the column roots (cfifo co)
    srcs = []
    for bid, cls, bits, eps in m['buses']:
        if cls == 'clock':
            srcs.append((bid, f'{eps[0][0]}/{eps[0][1]}', dict(clk_stream=833.333, clk_serial=1111.111,
                                                                clk_hbm=1023.96).get(bid, 833.333)))
        elif cls == 'col_clock':
            srcs.append((bid, f'{eps[0][0]}/{eps[0][1]}', 833.333))
    rec['clocks'] = srcs
    for corner, (us, uh) in (('ss', (210.0, 75.0)), ('ff', (210.0, 75.0))):
        T = ['set libs [split [string trim [read [open /kit/libs_%s.txt]]] "\\n"]' % corner,
             'foreach l $libs { read_liberty $l }', 'read_verilog /kit/die.v', 'link_design dsfd_die',
             'if {[file exists /kit/die.spef]} { read_spef /kit/die.spef; puts OT_SPEF }']
        for n_, pin, per in srcs:
            T.append(f'create_clock -name {n_} -period {per} [get_pins {{{pin}}}]')
        T += [f'set_clock_uncertainty -setup {us} [all_clocks]', f'set_clock_uncertainty -hold {uh} [all_clocks]',
              'set_clock_groups -asynchronous ' + ' '.join(f'-group {{{n_}}}' for n_ in ('clk_serial', 'clk_hbm')
                                                            if any(s[0] == n_ for s in srcs)) if False else '',
              f'report_checks -path_delay {"max" if corner == "ss" else "min"} -group_path_count 200 -endpoint_path_count 1 '
              f'-fields {{fanout}} -digits 1 > /kit/paths_{corner}.rpt',
              f'report_worst_slack -{"max" if corner == "ss" else "min"} -digits 1',
              f'report_tns -digits 1', 'report_check_types -violators -max_slew -max_capacitance > /kit/drv.rpt']
        (a.out / f'sta_{corner}.tcl').write_text('\n'.join(t for t in T if t) + '\n')
    (a.out / 'kit.json').write_text(json.dumps(rec, indent=1) + '\n')
    n = defaultdict(int)
    for v in rec['masters'].values():
        n[v['view']] += 1
    print(json.dumps(dict(n), indent=0), len(srcs), 'clock sources')


if __name__ == '__main__':
    main()
