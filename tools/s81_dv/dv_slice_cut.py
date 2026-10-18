#!/usr/bin/env python3
"""dv_slice_cut.py -- cut a slice top out of the GENERATED S81-DV die netlist (LAYERBENCH-S81, TOK.DS.BENCH.3, 10-18).

The slice is a set of die instances, copied VERBATIM from die.v (same masters, same parameters, same strap literals,
same internal net names): the real bound RTL, no stand-ins, no stubs, no ties added.  Every die net bit the slice
reads but does not drive becomes an input port bit; every bit it drives that is read outside the slice (or is a die
output) becomes an output port bit.  The replay bench (tb_dv_slice.sv) drives / checks those ports at the compiler's
scheduled cycles.

Instance set: --insts FILE (one instance name or /regex/ per line, # comments).  Growth (default on):
  * fan-in  : every relay-class instance (forwarded-lane relays dsfd_dvrlyh_* / dsfd_rly_*, landings dsfd_dvland_*,
              clock-forward cells BUFx* / INVx*) that drives a slice input bit is added, recursively through relay-class
              inputs: a lane arriving from a neighbour enters the slice at the neighbour master's output register (its
              real relay chain, forwarded clock and landing are inside the slice);
  * fan-out : every relay-class instance fed by a slice core output is added, recursively through relay-class
              outputs: the slice's outgoing lanes leave at the neighbour's landing input.
  Reset stations (dsfd_rly_1_*) are relay-class too, so the slice carries its reset tree path from the die rst_n.
Clock-type boundary inputs (bits that reach a ck / clk / ck_f pin) are reported with `clock_from`: the clock net of
the outside driver (a forwarded root = the source master's clk, e.g. ot_s81sl_slice ck_v = {2{clk}}), so the bench
drives them from that die clock.

Usage: dv_slice_cut.py --die-v die.v[.gz] --kit KITDIR (dv_rtl_kit.py of the die: master port directions)
                       --insts SET --out DIR [--name slice_top] [--no-grow]
Output: DIR/<name>.sv, DIR/slice_ports.json {port: {dir, width, net, lo, bits [boundary bit indices], peers, kind,
clock_from}}, DIR/slice_insts.json (instances by master, how each was included).
"""
import argparse
import gzip
import json
import re
import sys
from collections import defaultdict, Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dv_rtl_kit as K  # noqa: E402

RELAY_RE = re.compile(r'^(dsfd_dvrlyh_|dsfd_rly_|dsfd_dvland_|BUFx|INVx)')
RESET_RE = re.compile(r'^dsfd_rly_1_')
CLOCK_PORT_RE = re.compile(r'^(clk|ck|ck_f|ck_i|cr|cr_s)$')


def load_masters(kit, D, names):
    """port directions of the masters, from the kit's chosen files"""
    rec = json.loads((Path(kit) / 'kit.json').read_text())
    out = {}
    for f in rec['files']:
        t = (Path(kit) / 'src' / f['path']).read_text(errors='replace')
        if not any(n in t for n in names):
            continue
        t = D.preprocess(D.strip_comments(t), {d: '' for d in rec.get('defines', [])})
        for m in D.parse_modules(t, f['path']):
            if m.name in names and m.name not in out:
                ch = rec['variant_choices'].get(m.name)
                if ch and ch['file'] != f['path']:
                    continue
                out[m.name] = m
    return out, rec


def ranges(bits):
    """sorted ints -> [(hi, lo)] contiguous runs, high first"""
    bits = sorted(bits)
    out, s, p = [], None, None
    for b in bits:
        if s is None:
            s = p = b
        elif b == p + 1:
            p = b
        else:
            out.append((p, s)); s = p = b
    if s is not None:
        out.append((p, s))
    return out[::-1]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--die-v', required=True)
    ap.add_argument('--kit', required=True)
    ap.add_argument('--insts', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--name', default='slice_top')
    ap.add_argument('--top', default='dv_die')
    ap.add_argument('--no-grow', action='store_true')
    ap.add_argument('--land-plan', help='p4l land_plan.json: back-annotate every landing input (ck_f and i together) with '
                    'the lane flight time dL = -S1 at --corner (the landing contract window is defined against it; RTL '
                    'relays are zero-delay, so without it every lane with E > 1 violates its window)')
    ap.add_argument('--corner', default='tt', choices=['tt', 'ff'])
    ap.add_argument('--rom-instance', action='store_true',
                    help='give every instance of a master with a string INSTANCE parameter (the frames: their ROM macros '
                         'load <OT_ROM_DIR>/<INSTANCE>_cX_Y.viamap.hex) .INSTANCE("<instance name>") -- die.v passes none, so '
                         'every frame of one master would read the same ROM image (die-netlist gap, recorded)')
    ap.add_argument('--repo', default=str(K.ROOT))
    a = ap.parse_args(argv)
    out = Path(a.out).resolve(); out.mkdir(parents=True, exist_ok=True)
    kitrec = json.loads((Path(a.kit) / 'kit.json').read_text())
    D = K.load_dpb(Path(a.repo), kitrec['sha'])
    dv = a.die_v
    if dv.endswith('.gz'):
        p = out / 'die.v'
        p.write_text(gzip.open(dv, 'rt').read()); dv = str(p)
    text = Path(dv).read_text(errors='replace')
    nets, tin, tout, insts = D.parse_die(dv, a.top)
    insts = [i for i in insts if i[0] != '__assign__']
    byname = {i[1]: i for i in insts}
    masters, _ = load_masters(a.kit, D, {i[0] for i in insts})
    miss = sorted({i[0] for i in insts} - set(masters))
    if miss:
        raise SystemExit(f'dv_slice_cut: no RTL port list for masters {miss}')

    # per instance: [(port, dir, bits)]
    conns = {}
    drv, use = {}, defaultdict(set)              # (net, bit) -> inst / {inst}
    for mst, inst, params, cm in insts:
        mod = masters[mst]
        lst = []
        for port, expr in cm.items():
            if port not in mod.ports:
                raise SystemExit(f'dv_slice_cut: {inst}.{port} not a port of {mst}')
            d = mod.ports[port][0]
            bits = D.expr_bits(expr, nets)
            if bits is None:
                raise SystemExit(f'dv_slice_cut: unparsable connection {inst}.{port}({expr[:80]})')
            nb = [b for b in bits if b[0] not in ('CONST', 'Z', 'UNDECL')]
            lst.append((port, d, nb))
            for b in nb:
                if d == 'output':
                    if b in drv:
                        raise SystemExit(f'dv_slice_cut: {b} driven by {drv[b]} and {inst}')
                    drv[b] = inst
                else:
                    use[b].add(inst)
        conns[inst] = lst
    for n in tin:
        w, lo = nets[n]
        for i in range(lo, lo + w):
            drv[(n, i)] = '<die_in>'
    for n in tout:
        w, lo = nets[n]
        for i in range(lo, lo + w):
            use[(n, i)].add('<die_out>')

    # ---- instance set
    S, how = set(), {}
    pats = [ln.split('#')[0].strip() for ln in Path(a.insts).read_text().split('\n')]
    for p in [p for p in pats if p]:
        if p.startswith('/') and p.endswith('/'):
            rx = re.compile(p[1:-1])
            hit = [i for i in byname if rx.fullmatch(i)]
        else:
            hit = [p] if p in byname else []
        if not hit:
            raise SystemExit(f'dv_slice_cut: instance pattern {p!r} matches nothing in {a.top}')
        for h in hit:
            S.add(h); how[h] = 'set'
    def fan_in(seeds):
        todo = list(seeds)
        while todo:                               # fan-in through relay-class drivers (lanes, reset stations, fwd cells)
            i = todo.pop()
            for port, d, bits in conns[i]:
                if d == 'output':
                    continue
                for b in bits:
                    j = drv.get(b)
                    if j and j in byname and j not in S and RELAY_RE.match(byname[j][0]):
                        S.add(j); how[j] = f'fan-in of {i}'; todo.append(j)

    if not a.no_grow:
        fan_in(list(S))
        todo, new = [i for i in S if how[i] == 'set'], []
        while todo:                               # fan-out through LANE relays / landings (never the reset tree)
            i = todo.pop()
            for port, d, bits in conns[i]:
                if d != 'output':
                    continue
                for b in bits:
                    for j in use.get(b, ()):
                        if j in byname and j not in S and RELAY_RE.match(byname[j][0]) and not RESET_RE.match(byname[j][0]):
                            S.add(j); how[j] = f'fan-out of {i}'; todo.append(j); new.append(j)
        fan_in(new)                               # their forwarded clocks / reset leaves back to the die roots

    # ---- boundary
    snets = set()
    in_bits, out_bits = defaultdict(set), defaultdict(set)
    peers_in, peers_out = defaultdict(set), defaultdict(set)
    clk_bits = defaultdict(set)
    for i in S:
        for port, d, bits in conns[i]:
            for b in bits:
                snets.add(b[0])
                if d != 'output':
                    j = drv.get(b)
                    if j not in S:
                        in_bits[b[0]].add(b[1]); peers_in[b[0]].add(j or '<undriven>')
                        if CLOCK_PORT_RE.match(port):
                            clk_bits[b[0]].add(b[1])
                else:
                    outside = [j for j in use.get(b, ()) if j not in S]
                    if outside:
                        out_bits[b[0]].add(b[1]); peers_out[b[0]].update(outside)

    def clock_from(net):
        srcs = set()
        for i in sorted(peers_in[net]):
            if i == '<die_in>':
                srcs.add(net)
                continue
            if i not in byname:
                continue
            for port, d, bits in conns[i]:
                if d != 'output' and CLOCK_PORT_RE.match(port) and bits:
                    srcs.add(bits[0][0])
        return sorted(srcs)

    ports, decl, body = {}, [], []
    for n in sorted(snets):
        w, lo = nets[n]
        rng = f'[{lo + w - 1}:{lo}] ' if (w > 1 or lo) else ''
        if n in in_bits:
            pn = f'i__{n}'
            kind = 'clock' if clk_bits.get(n) else ('die_input' if peers_in[n] == {'<die_in>'} else 'boundary')
            ports[pn] = dict(dir='input', width=w, lo=lo, net=n, bits=ranges(in_bits[n]), peers=sorted(peers_in[n]),
                             kind=kind, clock_from=clock_from(n) if kind == 'clock' else None)
            decl.append(f'  input wire {rng}{pn};')
        if n in out_bits:
            pn = f'o__{n}'
            ports[pn] = dict(dir='output', width=w, lo=lo, net=n, bits=ranges(out_bits[n]), peers=sorted(peers_out[n]),
                             kind='die_output' if peers_out[n] == {'<die_out>'} else 'boundary')
            decl.append(f'  output wire {rng}{pn};')
        body.append(f'  wire {rng}{n};')
        for hi, lo_ in ranges(in_bits.get(n, ())):
            sel = f'[{hi}:{lo_}]' if (w > 1 or lo) else ''
            body.append(f'  assign {n}{sel} = i__{n}{sel};')
        if n in out_bits:
            body.append(f'  assign o__{n} = {n};')
    # instance lines verbatim from die.v (statement text, comments dropped)
    lines = {}
    for ln in text.split('\n'):
        m = re.match(r'\s*([\w\\]\S*)\s+(?:#\s*\(.*?\)\s*)?([\w\\]\S*)\s*\(', ln)
        if m and m.group(2) in S:
            lines[m.group(2)] = ln.split(');')[0].rstrip() + ');'
    rom_inst = []
    if a.rom_instance:
        for i in sorted(lines):
            mst = byname[i][0]
            if 'INSTANCE' in masters[mst].params and 'INSTANCE' not in byname[i][2]:
                ln = lines[i]
                if re.match(r'\s*\S+\s+#\s*\(', ln):
                    ln = re.sub(r'#\s*\(', f'#(.INSTANCE("{i}"), ', ln, count=1)
                else:
                    ln = re.sub(r'^(\s*\S+)\s+', lambda m: f'{m.group(1)} #(.INSTANCE("{i}")) ', ln, count=1)
                lines[i] = ln
                rom_inst.append(i)
    lane_dl = {}
    if a.land_plan:
        LP = {r['link']: r for r in json.loads(Path(a.land_plan).read_text())['links']}
        for i in sorted(lines):
            if not byname[i][0].startswith('dsfd_dvland'):
                continue
            r = LP.get(i[3:] if i.startswith('ld_') else i)
            if r is None:
                raise SystemExit(f'dv_slice_cut: landing {i} has no land-plan row')
            dl = max(0.0, -float(r['s1'][a.corner]))
            cm = byname[i][3]
            ln = lines[i]
            ln = ln.replace(f'.ck_f({cm["ck_f"]})', f'.ck_f({i}__ckf_d)', 1).replace(f'.i({cm["i"]})', f'.i({i}__i_d)', 1)
            w = nets[re.match(r'[\w\\]+', cm['i']).group(0)][0] if re.fullmatch(r'[\w\\]+', cm['i'].strip()) else None
            if w is None:
                raise SystemExit(f'dv_slice_cut: landing {i} data is not a whole net: {cm["i"][:60]}')
            # TRANSPORT delay (non-blocking intra-assignment): a continuous-assign delay is inertial and would swallow
            # every clock pulse / one-cycle beat shorter than the 2-3 ns flight time
            body.append(f'  reg {i}__ckf_d = 1\'b0; reg [{w - 1}:0] {i}__i_d = 0;   // lane flight time {dl:.1f} ps ({a.corner}, land plan S1)')
            body.append(f'  always @({cm["ck_f"]}) {i}__ckf_d <= #({dl / 1000.0:.4f}) {cm["ck_f"]};')
            body.append(f'  always @({cm["i"]}) {i}__i_d <= #({dl / 1000.0:.4f}) {cm["i"]};')
            lines[i] = ln
            lane_dl[i] = dict(dl_ps=round(dl, 1), E=r['E'], K=r['K'], corner=a.corner)
    lost = sorted(S - set(lines))
    if lost:
        raise SystemExit(f'dv_slice_cut: instance line not found verbatim for {lost[:5]}')
    hdr = '`timescale 1ns/1ps\n' + f'// {a.name}: cut by tools/s81_dv/dv_slice_cut.py from {Path(a.die_v).name} ({a.top}); {len(S)} instances, ' \
          f'{len(ports)} ports -- instance lines verbatim from the die netlist\nmodule {a.name} (\n' + \
          ',\n'.join(f'  {p}' for p in ports) + '\n);'
    sv = [hdr] + decl + body + [lines[i] for i in sorted(S, key=lambda x: list(byname).index(x))] + ['endmodule', '']
    (out / f'{a.name}.sv').write_text('\n'.join(sv))
    (out / 'slice_ports.json').write_text(json.dumps(dict(schema='opentallas.s81_dv.slice_ports.v1', top=a.name,
                                                          die_v=a.die_v, ports=ports), indent=1) + '\n')
    cnt = Counter(byname[i][0] for i in S)
    (out / 'slice_insts.json').write_text(json.dumps(dict(instances=len(S), by_master=dict(sorted(cnt.items())),
                                                          how={i: how[i] for i in sorted(S)}, rom_instance_param=rom_inst, lane_flight_time=lane_dl), indent=1) + '\n')
    nin = sum(sum(h - l + 1 for h, l in p['bits']) for p in ports.values() if p['dir'] == 'input')
    nout = sum(sum(h - l + 1 for h, l in p['bits']) for p in ports.values() if p['dir'] == 'output')
    print(f'dv_slice_cut: {len(S)} instances {dict(sorted(cnt.items()))}; ports {len(ports)} '
          f'(in bits {nin}, out bits {nout}; clock ports {sum(p["kind"] == "clock" for p in ports.values())})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
