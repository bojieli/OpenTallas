#!/usr/bin/env python3
"""QC type FACE-REACH form (QC-TYPES-6s 11-07): stage the output faces that cannot be reached in one cycle.

Class (SETUP-AT-GRT on hc0/hc1/hc2): the bound type registers every crossing at its face (u_bout_<port>), but the
leaf that drives the bus sits ~1 mm from that face, so source flop -> face flop is ~800 ps of repeated wire in one
833 ps cycle.  OWNER 11-07: pin cycles first; feedthrough flops <= 450 um.

  measure  KIT --viol viol_tt.tsv --out reach.json [--reach-um 450]
           groups the failing TT setup endpoints (probe TSV: slack, start, end, start inst, x, y, end inst, x, y) by
           u_bout_<port>, takes the launch-flop centroid and the port pin centroid (KIT/pins.json), and asks
           ceil(distance / reach) - 1 extra stages per port (Manhattan, um).
  apply    KIT --spec reach.json --bench DIR
           wraps each listed u_bout_<port> data input in ot_qc_face_reach #(W, N) (N epoch-carrying ot_dp_st stages,
           reset like the face flop), anchors stage j at fraction (j+1)/(N+1) of the source -> pin line, writes the
           pin-cycle receipt (added_rx_clk_PIN_cycles.json, N per port) and an old/new lock-step bench with mutants.

The kit must be input-only (no synthesis result): a changed RTL form synthesises and proves afresh (kit LEC is
against the new RTL; the bench proves new == old delayed by N cycles, data and epoch).  Pin cycles are a neighbour
/ compiler obligation recorded in the receipt; no plan file is edited here.
"""
import argparse, collections, hashlib, json, math, re, sys
from pathlib import Path

def reach_module(n):
    """ot_qc_face_reach_n<N>: N epoch-carrying ot_dp_st stages, flat instance names s0..s<N-1> (anchor prefixes)."""
    L = ['`default_nettype none', '(* keep_hierarchy, keep *)',
         f'module ot_qc_face_reach_n{n} #(parameter integer W = 1) (input wire clk, input wire rst_n, '
         'input wire [W-1:0] d, input wire ea, output wire [W-1:0] q, output wire eq);']
    for j in range(n - 1):
        L.append(f'    wire [W-1:0] q{j}; wire e{j};')
    for j in range(n):
        di, ei = ('d', 'ea') if j == 0 else (f'q{j-1}', f'e{j-1}')
        qo, eo = ('q', 'eq') if j == n - 1 else (f'q{j}', f'e{j}')
        L.append(f'    ot_dp_st #(.W(W)) s{j} (.clk(clk), .rst_n(rst_n), .d({di}), .ea({ei}), .q({qo}), .eq({eo}));')
    L += ['endmodule', '`default_nettype wire', '']
    return '\n'.join(L)


def reach_modules(ns):
    return ''.join(reach_module(n) for n in sorted(set(ns)))

# RSTN-TAP (bind.py boundary_reset_selector): a far face flop names its same-depth tap rst_n_t<i>; the reach stages
# take the face flop's own reset net (group 3)
BOUT = r'^(    ot_dp_st #\(\.W\((\d+)\)\) u_bout_{port} \(\.clk\(clk\), \.rst_n\((rst_n(?:_t\d+)?)\), \.d\()(.*?)(\), \.ea\()(.*?)(\), .*\);)$'
EP = re.compile(r'^u_bound\.u_bout_([A-Za-z0-9_]+)/')


def bout_re(port):
    return re.compile(BOUT.format(port=re.escape(port)), re.M)


def pin_centroids(pins):
    acc = collections.defaultdict(list)
    for p in pins:
        acc[p['bus']].append((float(p['x']), float(p['y'])))
    return {b: (sum(x for x, _ in v) / len(v), sum(y for _, y in v) / len(v)) for b, v in acc.items()}


def measure(viol_lines, pins, reach_um=450.0, min_viol=1):
    """viol_lines: probe TSV rows -> {port: {...}} for ports whose failing endpoints are face flops."""
    src = collections.defaultdict(list)
    worst = {}
    for line in viol_lines:
        f = line.rstrip('\n').split('\t')
        if len(f) < 9:
            continue
        slack, ep_inst = float(f[0]), f[6]
        m = EP.match(ep_inst + '/')
        if not m or f[4] == 'NA':
            continue
        port = m.group(1)
        src[port].append((float(f[4]), float(f[5])))
        worst[port] = min(worst.get(port, 0.0), slack)
    pc = pin_centroids(pins)
    out = {}
    for port, pts in sorted(src.items()):
        if len(pts) < min_viol or port not in pc:
            continue
        sx = sum(x for x, _ in pts) / len(pts)
        sy = sum(y for _, y in pts) / len(pts)
        px, py = pc[port]
        dist = abs(px - sx) + abs(py - sy)
        n = max(0, math.ceil(dist / reach_um) - 1)
        if n:
            out[port] = dict(stages=n, src_xy=[round(sx, 2), round(sy, 2)], pin_xy=[round(px, 2), round(py, 2)],
                             dist_um=round(dist, 1), endpoints=len(pts), worst_ps=round(worst[port], 2))
    return out


def transform(text, spec):
    """returns (new text, old body lines, new body lines, {port: width}); every spec port must match exactly once."""
    olds, news, widths = [], [], {}
    for port, s in sorted(spec.items()):
        n = int(s['stages'])
        assert n >= 1, port
        found = bout_re(port).findall(text)
        assert len(found) == 1, f'u_bout_{port}: {len(found)} matches'
        m = bout_re(port).search(text)
        head, w, rst, dexpr, mid, ea, tail = (m.group(1), int(m.group(2)), m.group(3), m.group(4), m.group(5),
                                              m.group(6), m.group(7))
        stem = f'reach_{port}'
        rep = (f'    wire [{w-1}:0] {stem}; wire {stem}_eq;  // FACE-REACH +{n} PIN cycles (QC-TYPES-6s)\n'
               f'    ot_qc_face_reach_n{n} #(.W({w})) u_{stem} (.clk(clk), .rst_n({rst}), .d({dexpr}), .ea({ea}), '
               f'.q({stem}), .eq({stem}_eq));\n'
               f'{head}{stem}{mid}{stem}_eq{tail}')
        text = text.replace(m.group(0), rep, 1)
        olds.append(m.group(0))
        news.append(rep)
        widths[port] = w
    return text, olds, news, widths


def place_tcl(spec, die):
    dx, dy = die
    L = ['# FACE-REACH stage anchors (QC-TYPES-6s): stage j of port P on the source -> pin line at (j+1)/(N+1).',
         'set cland_fh [open $::env(RESULTS_DIR)/ot_cland_reach.txt w]', 'set reach_moved {}', 'set reach_groups {}']
    for port, s in sorted(spec.items()):
        n = int(s['stages'])
        (sx, sy), (px, py) = s['src_xy'], s['pin_xy']
        for j in range(n):
            a = (j + 1) / (n + 1)
            x, y = sx + (px - sx) * a, sy + (py - sy) * a
            r = [max(4.5, x - 18), max(4.5, y - 18), min(dx - 4.5, x + 18), min(dy - 4.5, y + 18)]
            L.append(f'lappend reach_groups [list u_bound.u_reach_{port}.s{j} {{{" ".join(f"{v:.3f}" for v in r)}}}]')
    L += ['foreach spec $reach_groups {', ' lassign $spec prefix rect', ' set got 0',
          ' foreach i [cland_group_insts $prefix] { cland_put $i $rect reach:$prefix; lappend reach_moved [$i getName]; incr got }',
          ' if {!$got} { error "FACE_REACH missing mapped group $prefix" }',
          ' puts "FACE_REACH placed $got cells $prefix in $rect"', '}', 'close $cland_fh']
    return '\n'.join(L) + '\n'


def bench(out, olds, news, widths, spec, cells):
    """old/new adapters over the exact bound lines; tb checks new == old delayed by N (data when epoch set, epoch always)."""
    out.mkdir(parents=True, exist_ok=True)
    (out / 'cells.sv').write_text(cells)
    mods = reach_modules(int(s['stages']) for s in spec.values())
    (out / 'reach.sv').write_text(mods)
    ids = sorted(set(re.findall(r'\b(w_[A-Za-z0-9_]+)\[', '\n'.join(olds))))
    ins = {}
    for i in ids:
        his = [int(h) for h in re.findall(re.escape(i) + r'\[(\d+)', '\n'.join(olds))]
        ins[i] = max(his) + 1
    decl = ['input wire clk', 'input wire rst_n'] + [f'input wire [{w-1}:0] {n}' for n, w in ins.items()] + \
           [f'output wire [{w}:0] {p}' for p, w in widths.items()]
    # RSTN-TAP: a face flop on a same-depth tap net rst_n_t<i> (same release cycle) is driven by the bench reset
    taps = ''.join(f'    wire {t} = rst_n;\n' for t in sorted(set(re.findall(r'\.rst_n\((rst_n_t\d+)\)', '\n'.join(olds)))))
    body_old = taps + '\n'.join(olds)
    body_new = taps + '\n'.join(news)
    ref = 'module old_adapter(' + ', '.join(decl) + ');\n' + body_old + '\nendmodule\n'
    cand = 'module new_adapter(' + ', '.join(decl) + ');\n' + body_new + '\nendmodule\n'
    (out / 'adapters.sv').write_text(ref + cand)
    # bit mutant: the first reach instance carries inverted data
    (out / 'mut_bit.sv').write_text(ref + re.sub(r'(ot_qc_face_reach_n\d+ #\(\.W\(\d+\)\) u_\w+ \(\.clk\(clk\), \.rst_n\(rst_n(?:_t\d+)?\), \.d\()', r'\1~', cand, count=1))
    # skip mutant: every reach module one stage short (N-1 stages; N = 1 becomes a wire)
    short = []
    for n in sorted({int(v['stages']) for v in spec.values()}):
        if n == 1:
            short.append('module ot_qc_face_reach_n1 #(parameter integer W = 1) (input wire clk, input wire rst_n, '
                         'input wire [W-1:0] d, input wire ea, output wire [W-1:0] q, output wire eq);\n'
                         '    assign q = d; assign eq = ea;\nendmodule\n')
        else:
            short.append(reach_module(n - 1).replace(f'ot_qc_face_reach_n{n-1} ', f'ot_qc_face_reach_n{n} ', 1))
    (out / 'reach_skip.sv').write_text(''.join(short))
    nmax = max(int(s['stages']) for s in spec.values())
    tb = ['`timescale 1ns/1ps', 'module tb; reg clk=0; always #5 clk=~clk; reg rst_n=0; integer errors=0, cycle=0, seen=0;']
    tb += [f'reg [{w-1}:0] {n}=0;' for n, w in ins.items()]
    for p, w in widths.items():
        n = int(spec[p]['stages'])
        tb += [f'wire [{w}:0] old_{p}, new_{p}; reg [{w}:0] h_{p} [0:{nmax}]; integer k_{p};',
               f'always @(posedge clk) begin h_{p}[0] <= old_{p}; for (k_{p}=1; k_{p}<={nmax}; k_{p}=k_{p}+1) h_{p}[k_{p}] <= h_{p}[k_{p}-1]; end']
    conns = ['.clk(clk)', '.rst_n(rst_n)'] + [f'.{n}({n})' for n in ins]
    for kind in ('old', 'new'):
        tb.append(f'{kind}_adapter {kind}_dut(' + ', '.join(conns + [f'.{p}({kind}_{p})' for p in widths]) + ');')
    tb.append('always @(negedge clk) begin cycle=cycle+1; if (cycle > %d) begin' % (nmax + 4))
    for p, w in widths.items():
        n = int(spec[p]['stages'])
        tb += [f'  if (new_{p}[{w}] !== h_{p}[{n-1}][{w}]) errors=errors+1;',
               f'  if (h_{p}[{n-1}][{w}] && new_{p}[{w-1}:0] !== h_{p}[{n-1}][{w-1}:0]) errors=errors+1; else if (h_{p}[{n-1}][{w}]) seen=seen+1;']
    tb.append('end')
    tb += [f'{n} <= {{' + ', '.join(['$random'] * ((w + 31) // 32)) + '};' for n, w in ins.items()]
    tb += ['end', 'initial begin #13 rst_n=1; #4000; if (errors || !seen) begin $display("REACH_FAIL errors=%0d seen=%0d", errors, seen); $fatal(1); end',
           '  else $display("REACH_PASS cycles=%0d checks=%0d", cycle, seen); $finish; end', 'endmodule']
    (out / 'tb.sv').write_text('\n'.join(tb) + '\n')
    (out / 'run.sh').write_text('#!/bin/bash\n# PASS = base passes, both mutants fail.\ncd "$(dirname "$0")"\nr=0\n'
                                'iverilog -g2012 -o base.vvp cells.sv reach.sv adapters.sv tb.sv && vvp -n base.vvp | tee base.log | grep -q REACH_PASS || r=1\n'
                                'iverilog -g2012 -o m1.vvp cells.sv reach.sv mut_bit.sv tb.sv && vvp -n m1.vvp > m1.log; grep -q REACH_PASS m1.log && r=1\n'
                                'iverilog -g2012 -o m2.vvp cells.sv reach_skip.sv adapters.sv tb.sv && vvp -n m2.vvp > m2.log; grep -q REACH_PASS m2.log && r=1\n'
                                'echo BENCH_RC $r; exit $r\n')


def apply(kit, spec, bench_dir):
    kit = Path(kit)
    assert not list((kit / 'run/results').glob('**/1_2_yosys.v')), 'input-only kit required (fresh synthesis + proof)'
    assert not (kit / 'rtl/ot_qc_face_reach.sv').exists() and not (kit / 'rtl/ot_qc_face_reach_n1.sv').exists(), 'kit already carries the reach form'
    if (kit / 'resume.json').exists():
        (kit / 'resume.json').rename(kit / 'resume.json.before_face_reach')
    for m in kit.glob('.kwrs_done*'):
        m.rename(m.with_name(m.name + '.before_face_reach'))
    p = next((kit / 'rtl').glob('*_bound.sv'))
    old = p.read_text()
    new, olds, news, widths = transform(old, {k: v for k, v in spec.items() if not k.startswith('_')})
    p.with_suffix('.sv.before_face_reach').write_text(old)
    p.write_text(new)
    mods = reach_modules(int(v['stages']) for k, v in spec.items() if not k.startswith('_'))
    (kit / 'rtl/ot_qc_face_reach.sv').write_text(mods)
    c = kit / 'config.mk'
    t = c.read_text()
    assert 'export VERILOG_FILES = ' in t
    c.write_text(t.replace('export VERILOG_FILES = ', 'export VERILOG_FILES = /work/rtl/ot_qc_face_reach.sv ', 1))
    pins = json.loads((kit / 'pins.json').read_text())
    pins = pins['pins'] if isinstance(pins, dict) else pins
    die = tuple(spec.get('_die', [max(float(q['x']) for q in pins), max(float(q['y']) for q in pins)]))
    ports = {k: v for k, v in spec.items() if not k.startswith('_')}
    (kit / 'face_reach_place.tcl').write_text(place_tcl(ports, die))
    f = kit / 'face_flops.tcl'
    f.write_text(f.read_text() + '\nsource /work/face_reach_place.tcl\n')
    meta = {'form': 'FACE-REACH (QC-TYPES-6s)', 'source_bound_sha256_before': hashlib.sha256(old.encode()).hexdigest(),
            'source_bound_sha256_after': hashlib.sha256(new.encode()).hexdigest(),
            'adapter_sha256': hashlib.sha256(mods.encode()).hexdigest(),
            'added_rx_clk_PIN_cycles': {k: int(v['stages']) for k, v in ports.items()},
            'added_data_flops': sum((widths[k] + 1) * int(v['stages']) for k, v in ports.items()),
            'neighbor_obligation': 'receiver lanes + compiler/token schedule +N per listed output bus (plan event, count dry run)',
            'rate_change': 0, 'ports': ports}
    canon = kit / 'added_rx_clk_PIN_cycles.json'
    if canon.exists():
        meta['inherited_pin_cycles_receipt'] = json.loads(canon.read_text())
    canon.write_text(json.dumps(meta, indent=2) + '\n')
    bench(Path(bench_dir), olds, news, widths, ports, (kit / 'rtl/bind_cells.sv').read_text())
    return meta


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    m = sub.add_parser('measure')
    m.add_argument('kit', type=Path)
    m.add_argument('--viol', type=Path, required=True)
    m.add_argument('--out', type=Path, required=True)
    m.add_argument('--reach-um', type=float, default=450.0)
    m.add_argument('--die', type=float, nargs=2, metavar=('X_UM', 'Y_UM'), help='die size of the measured DB (anchor clip)')
    a = sub.add_parser('apply')
    a.add_argument('kit', type=Path)
    a.add_argument('--spec', type=Path, required=True)
    a.add_argument('--bench', type=Path, required=True)
    o = ap.parse_args(argv)
    if o.cmd == 'measure':
        pins = json.loads((o.kit / 'pins.json').read_text())
        pins = pins['pins'] if isinstance(pins, dict) else pins
        spec = measure(o.viol.read_text().splitlines(), pins, o.reach_um)
        if o.die:
            spec['_die'] = list(o.die)
        o.out.write_text(json.dumps(spec, indent=2) + '\n')
        print(json.dumps(spec))
    else:
        print(json.dumps({k: v for k, v in apply(o.kit, json.loads(o.spec.read_text()), o.bench).items() if k != 'ports'}))


if __name__ == '__main__':
    sys.exit(main())
