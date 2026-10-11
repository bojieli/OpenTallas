#!/usr/bin/env python3
"""bf-hier 2026-10-10: composed timing of the hierarchical BF pair  col0 | front | col1  from the routed blocks' ETMs.

The pair is three abutted hardened blocks (tools/s81/gen_bf_hier.py; s81-gen --bf-hier):
  ot_s81_bf_front c<k>_{issue,a_ctr,i1_*,i2x_*,ze_d,so_*}  ->  ot_v41_bf_col #k  {issue,...}   (k = 0 west, 1 east)
  ot_v41_bf_col #k qy_bkf                                   ->  ot_s81_bf_front c_qy_bkf_in[k]
  clk / reset to all three; every other port is a die port (judged by the die STA, not here).
Every column input is registered at the column boundary (gen_bf_hier.py: g_pin.r_*), so each front->column net is one
abutted flop-to-flop hop: the ETM arcs carry each block's own clock insertion (write_timing_model), so the only
composition terms are the die clock tree's arrival at the three clock pins and the abutment wire.

Two clock conventions (as tools/s81/assemble_views.py):
  raw  ideal die clock at every block clock pin (each ETM's routed insertion inside its arcs, unbalanced)
  bal  the die tree delivers each block early by its own mean insertion (min/max_clock_tree_path of the ETM): equal
       mean flop arrival, what die CTS of the three clock pins targets; residual die-tree skew is carried by
       --die-skew (default 50 ps, the die budget's inter-region hold term) on top of the 60 / 25 ps uncertainty.
Setup at TT, hold at FF (owner option B), 1.2 GHz (833.333 ps).

  bf_hier_compose_sta.py --front-dir D --col-dir D --out DIR [--sta /usr/bin/sta]
"""
import argparse, json, re, subprocess
from pathlib import Path

COL_IN = ['issue', 'a_ctr', 'i1_v', 'i1_bk', 'i1_bf', 'i1_t', 'i2x_q0', 'i2x_e0', 'i2x_q1', 'i2x_e1', 'ze_d',
          'so_row', 'so_idx', 'so_n']


def lib_ports(path):
    """{port: (direction, width or None)} and mean clock-tree insertion of pin clk from a write_timing_model liberty"""
    t = Path(path).read_text()
    widths = {m.group(1): int(m.group(2)) for m in re.finditer(r'type \("([^"]+)"\) \{[^}]*?bit_width : (\d+);', t)}
    ports = {}
    for m in re.finditer(r'\n    (bus|pin)\("([^"]+)"\) \{\s*(?:bus_type : "?([^";]+)"?;\s*)?direction : (\w+);', t):
        kind, name, btype, d = m.groups()
        if '[' in name:
            continue
        ports[name] = (d, widths[btype] if kind == 'bus' else None)
    ins = {}
    for k in ('min', 'max'):
        m = re.search(r'timing_type : ' + k + r'_clock_tree_path;\s*cell_rise\(scalar\) \{\s*values\("([-\d.]+)"\)', t)
        ins[k] = float(m.group(1)) if m else 0.0
    cell = re.search(r'\n  cell\s*\(\s*"?([\w]+)"?\s*\)', t).group(1)
    return cell, ports, ins


def decl(name, w):
    return f'[{w - 1}:0] {name}' if w else name


def netlist(front, col):
    fc, fp, _ = front
    cc, cp, _ = col
    wires, top, conn_f, conn_c = [], [], {}, [{}, {}]
    for k in (0, 1):
        for p in COL_IN:
            fpn = f'c{k}_{p}'
            assert fpn in fp and p in cp, (fpn, p)
            assert fp[fpn][1] == cp[p][1], (fpn, fp[fpn], cp[p])
            n = f'n_c{k}_{p}'
            wires.append(f'  wire {decl(n, fp[fpn][1])};')
            conn_f[fpn] = n
            conn_c[k][p] = n
        n = f'n_c{k}_qy_bkf'
        wires.append(f'  wire {n};')
        conn_c[k]['qy_bkf'] = n
    conn_f['c_qy_bkf_in'] = '{n_c1_qy_bkf, n_c0_qy_bkf}'
    conn_f['clk'] = 'clk'
    conn_f['rst_n'] = 'rst_n'
    for k in (0, 1):
        conn_c[k]['clk'] = 'clk'
        conn_c[k]['rst_n_pin'] = 'rst_n'
    top += ['  input clk;', '  input rst_n;']
    for p, (d, w) in sorted(fp.items()):
        if p not in conn_f:
            n = f'f_{p}'
            top.append(f'  {d} {decl(n, w)};')
            conn_f[p] = n
    for k in (0, 1):
        for p, (d, w) in sorted(cp.items()):
            if p not in conn_c[k]:
                n = f'c{k}x_{p}'
                top.append(f'  {d} {decl(n, w)};')
                conn_c[k][p] = n
    ports = ['clk', 'rst_n'] + [ln.split()[-1].rstrip(';') for ln in top[2:]]
    inst = lambda cell, nm, c: f'  {cell} {nm} (' + ', '.join(f'.{p}({n})' for p, n in sorted(c.items())) + ');'
    return '\n'.join([f'module bf_pair ({", ".join(ports)});', *top, *wires, inst(fc, 'u_front', conn_f),
                      inst(cc, 'u_col0', conn_c[0]), inst(cc, 'u_col1', conn_c[1]), 'endmodule', ''])


def tcl(libs, corner, mode, lat, out, die_skew):
    chk = 'max' if corner == 'tt' else 'min'
    unc = 60 if chk == 'max' else 25
    L = [*(f'read_liberty {x}' for x in libs), f'read_verilog {out}/bf_pair.v', 'link_design bf_pair',
         'create_clock -name core_clk -period 833.333 [get_ports clk]',
         f'set_clock_uncertainty -{"setup" if chk == "max" else "hold"} {unc + die_skew} [all_clocks]',
         'set_false_path -from [get_ports rst_n]']
    if mode == 'bal':
        for i, v in lat.items():
            L.append(f'set_clock_latency {v:.3f} [get_pins {i}/clk]')
    # only the composed interface: front -> column and column -> front
    L += ['set fo [open ' + f'{out}/sta_{corner}_{mode}.txt w]',
          'foreach {nm fr to} {f2c0 u_front u_col0 f2c1 u_front u_col1 c02f u_col0 u_front c12f u_col1 u_front} {',
          f'  set ps [find_timing_paths -path_delay {chk} -from [get_pins $fr/clk] -to [get_cells $to] -group_count 1]',
          '  if {[llength $ps] == 0} { puts $fo "$nm none"; continue }',
          '  set p [lindex $ps 0]',
          '  puts $fo "$nm [get_property $p slack] [get_full_name [get_property $p endpoint]]"',
          '}', 'close $fo',
          f'report_checks -path_delay {chk} -through [get_pins u_col0/*] -through [get_pins u_front/*] -group_count 3 -format full_clock_expanded > {out}/paths_{corner}_{mode}.rpt',
          f'report_checks -path_delay {chk} -from [get_pins u_front/clk] -group_count 3 -format full_clock_expanded >> {out}/paths_{corner}_{mode}.rpt',
          'exit']
    return '\n'.join(L) + '\n'


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--front-dir', required=True)
    a.add_argument('--col-dir', required=True)
    a.add_argument('--out', required=True)
    a.add_argument('--sta', default='sta')
    a.add_argument('--die-skew', type=float, default=50.0)
    o = a.parse_args()
    out = Path(o.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    res = dict(period_ps=833.333, uncertainty=dict(setup=60, hold=25), die_skew_ps=o.die_skew, corners={})
    for corner in ('tt', 'ff'):
        fl = Path(o.front_dir) / f'ot_s81_bf_front_{corner}.lib'
        cl = Path(o.col_dir) / f'ot_v41_bf_col_{corner}.lib'
        front, col = lib_ports(fl), lib_ports(cl)
        if corner == 'tt':
            (out / 'bf_pair.v').write_text(netlist(front, col))
        ins = {'u_front': front[2], 'u_col0': col[2], 'u_col1': col[2]}
        mean = {i: (v['min'] + v['max']) / 2 for i, v in ins.items()}
        c = max(mean.values())
        lat = {i: c - m for i, m in mean.items()}
        res['corners'][corner] = dict(insertion=ins, bal_latency=lat)
        for mode, sk in (('raw', 0.0), ('bal', 0.0), ('bal_skew', o.die_skew)):
            m = 'bal' if mode.startswith('bal') else 'raw'
            t = tcl([fl.resolve(), cl.resolve()], corner, m, lat, out, sk).replace(f'sta_{corner}_{m}.txt', f'sta_{corner}_{mode}.txt') \
                .replace(f'paths_{corner}_{m}.rpt', f'paths_{corner}_{mode}.rpt')
            (out / f'sta_{corner}_{mode}.tcl').write_text(t)
            r = subprocess.run([o.sta, '-no_init', '-no_splash', '-exit', str(out / f'sta_{corner}_{mode}.tcl')],
                               capture_output=True, text=True, timeout=3600)
            (out / f'sta_{corner}_{mode}.log').write_text(r.stdout + r.stderr)
            rows = {}
            f = out / f'sta_{corner}_{mode}.txt'
            for ln in (f.read_text().splitlines() if f.exists() else []):
                x = ln.split()
                rows[x[0]] = None if x[1] == 'none' else dict(slack_ps=round(float(x[1]), 2), endpoint=x[2] if len(x) > 2 else '')
            res['corners'][corner][mode] = rows
    (out / 'compose.json').write_text(json.dumps(res, indent=1))
    print(json.dumps({k: {m: {p: (v or {}).get('slack_ps') for p, v in r[m].items()} for m in ('raw', 'bal', 'bal_skew')}
                      for k, r in res['corners'].items()}))


if __name__ == '__main__':
    main()
