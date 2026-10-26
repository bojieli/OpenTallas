#!/usr/bin/env python3
"""H-NETLIST/D4F-RELAY 1017: per-lane LOCKSTEP bench of the d4f relay layer (tools/hbm_die_v16/relay_layer_d4f.py) on the
REAL relay tile RTL (hbfd_rly_*_fc / _fc_f<N> / hbfd_rly_*), generated from the layer's relay_splice_v2 trees.
For every selected bus a source register drives a fresh random word each edge; the tree is instantiated exactly as the
layer wires it (driver -> lanes / tiles, fork branches o<k>/clk_out<k>, clk_out -> clk_in chains, sink-root stages; spare
lane positions fed with real source bits j % bits) and at every sink the reassembled bus (all lanes) must equal the
source word of exactly sink_edges[sink] cycles earlier, on every cycle: lanes in lockstep.  One clock drives every root
clk_in / ck (the bench checks logical lockstep; clock skew is the die STA's).
Mutants (--mut): lane_stage = lane 0 of one sink chain gets +1 stage; bitswap = two bits of one lane swapped on one hop;
branch_drop = one fork branch of a fork tile left unconnected (its sink sees no data).  Each must FAIL.
    relay_lockstep_bench.py --layer L.json.gz --out DIR [--mut lane_stage|bitswap|branch_drop] [--max-buses N]
"""
import argparse, gzip, json, random
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--layer', required=True); ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--mut'); ap.add_argument('--max-buses', type=int, default=0); ap.add_argument('--cycles', type=int, default=400)
    a = ap.parse_args()
    if any(i['master'].startswith(('hbfd_lh', 'hbfd_land')) for i in json.loads(gzip.open(a.layer).read() if a.layer.endswith('.gz') else open(a.layer).read())['instances']):
        return lane_main(a)
    L = json.loads(gzip.open(a.layer).read() if a.layer.endswith('.gz') else open(a.layer).read())
    mast = {i['name']: i['master'] for i in L['instances']}
    buses = L['relay_splice_v2']
    forks = [b for b in buses if any(len(nd['outs']) > 1 for nd in b['nodes'])]
    rest = [b for b in buses if b not in forks]
    sel = forks + rest
    if a.max_buses:
        sel = forks + rest[:max(0, a.max_buses - len(forks))]
    rnd = random.Random(1)
    V = ['`timescale 1ns/1ps', 'module tb_relay_lockstep;', '  reg clk = 0; always #1 clk = ~clk; reg rs = 0;',
         '  integer cyc = 0, errs = 0, chk = 0; always @(posedge clk) cyc <= cyc + 1;']
    mut_done = False
    for bi, b in enumerate(sel):
        W, T, n, tag = b['width'], b['tiles'], b['bits'], b['bus']
        nodes = {nd['id']: nd for nd in b['nodes']}
        dep = max(len(sk['chain']) for sk in b['sinks'].values()) + len(b['nodes']) + 4
        V.append(f'  // bus {tag} {b["driver"]} bits {n} kind {b["kind"]} lanes {T}x{W}')
        V.append(f'  reg [{n - 1}:0] {tag}_src; reg [{n - 1}:0] {tag}_h [0:{dep}];')
        V.append(f'  integer {tag}_k; always @(posedge clk) begin {tag}_src <= {{' + ','.join(['$random'] * ((n + 31) // 32)) + '}; '
                 f'{tag}_h[0] <= {tag}_src; for ({tag}_k = 1; {tag}_k <= {dep}; {tag}_k = {tag}_k + 1) {tag}_h[{tag}_k] <= {tag}_h[{tag}_k - 1]; end')
        def lane_in(t):   # driver bits feeding lane t (spares = j % n)
            return '{' + ','.join(f'{tag}_src[{(t * W + L_) if t * W + L_ < n else (t * W + L_) % n}]' for L_ in reversed(range(W))) + '}'
        def inst(name, outs_conn, i_expr, clk_expr, clk_outs):
            m = mast[name]
            ports = [f'.i({i_expr})', '.rs(rs)']
            if m.endswith('_fc') or '_fc_f' in m:
                ports.append(f'.clk_in({clk_expr})')
            else:
                ports.append(f'.ck({clk_expr})')
            for pn, w in outs_conn:
                ports.append(f'.{pn}({w})')
            for pn, w in clk_outs:
                ports.append(f'.{pn}({w})')
            return f'  {m} {name} (' + ', '.join(ports) + ');'
        # declare outputs
        for nd in b['nodes']:
            for t, nm in enumerate(nd['names']):
                for k, op in enumerate(sorted(set(nd['outs']))):
                    V.append(f'  wire [{W - 1}:0] {nm}__{op}; wire {nm}__c{op};')
        for s_, sk in b['sinks'].items():
            for st_ in sk['chain']:
                for nm in st_:
                    V.append(f'  wire [{W - 1}:0] {nm}__o; wire {nm}__co;')
        swap = None
        if a.mut == 'bitswap' and not mut_done and b['nodes']:
            swap = b['nodes'][-1]['names'][0]; mut_done = True
        drop = None
        if a.mut == 'branch_drop' and not mut_done:
            fn = [nd for nd in b['nodes'] if len(nd['outs']) > 1]
            if fn:
                drop = (fn[0]['id'], len(fn[0]['outs']) - 1); mut_done = True
        nck = {}   # node instance -> the clock its ck / clk_in sees
        for nd in b['nodes']:
            for t, nm in enumerate(nd['names']):
                if nd['parent'] is None:
                    i_expr, ck = lane_in(t), 'clk'
                else:
                    pn = nodes[nd['parent']]; op = pn['outs'][nd['pbranch']]
                    i_expr = f'{pn["names"][t]}__{op}'
                    pm = mast[pn['names'][t]]   # plain relay parent: no clk_out, the child shares its clock
                    ck = f'{pn["names"][t]}__c{op}' if (pm.endswith('_fc') or '_fc_f' in pm) else nck[pn['names'][t]]
                    if drop and drop == (pn['id'], nd['pbranch']):
                        i_expr = f"{W}'d0"
                if nm == swap:   # mutant: bits 0/1 of this lane swapped on its input hop
                    V.append(f'  wire [{W - 1}:0] {nm}__sw0 = {i_expr};')
                    V.append(f'  wire [{W - 1}:0] {nm}__sw1 = {{{nm}__sw0[{W - 1}:2],{nm}__sw0[0],{nm}__sw0[1]}};')
                    i_expr = f'{nm}__sw1'
                outs = [(op, f'{nm}__{op}') for op in sorted(set(nd['outs']))]
                couts = [(('clk_out' + op[1:]) if op != 'o' else 'clk_out', f'{nm}__c{op}') for op in sorted(set(nd['outs']))] \
                    if (mast[nm].endswith('_fc') or '_fc_f' in mast[nm]) else []
                nck[nm] = ck
                V.append(inst(nm, outs, i_expr, ck, couts))
        for si, (s_, sk) in enumerate(b['sinks'].items()):
            src_node, br = sk['src']
            prev = None if src_node is None else [(f'{nm}__{nodes[src_node]["outs"][br]}') for nm in nodes[src_node]['names']]
            dropped = drop is not None and src_node == drop[0] and br == drop[1]
            chain = sk['chain']
            extra = a.mut == 'lane_stage' and not mut_done and chain
            pck = None   # per lane: the clock that clocked the previous chain stage
            for k, st_ in enumerate(chain):
                cks = []
                for t, nm in enumerate(st_):
                    i_expr = lane_in(t) if prev is None else prev[t]
                    if dropped and k == 0:
                        i_expr = f"{W}'d0"
                    # a forwarded-clock (fc) stage drives clk_out; a plain relay has none and sits on the clock that
                    # clocked it (the die's regional clock), so the next stage stays on that clock
                    pm = mast[chain[k - 1][t]] if k else ''
                    ck = 'clk' if k == 0 else (f'{chain[k - 1][t]}__co' if (pm.endswith('_fc') or '_fc_f' in pm) else pck[t])
                    cks.append(ck)
                    couts = [('clk_out', f'{nm}__co')] if (mast[nm].endswith('_fc') or '_fc_f' in mast[nm]) else []
                    V.append(inst(nm, [('o', f'{nm}__o')], i_expr, ck, couts))
                prev = [f'{nm}__o' for nm in st_]; pck = cks
            if extra:   # mutant: lane 0 of this sink gets one more stage (same tile master)
                nm0 = chain[-1][0]; xn = f'{nm0}__mutx'
                V.append(f'  wire [{W - 1}:0] {xn}__o; wire {xn}__co;')
                V.append(inst(nm0, [('o', f'{xn}__o')], prev[0], 'clk', [('clk_out', f'{xn}__co')] if (mast[nm0].endswith('_fc')) else []).replace(f' {nm0} (', f' {xn} ('))
                prev = [f'{xn}__o'] + prev[1:]; mut_done = True
            if prev is None:
                continue
            # expected depth: tree depth of the feeding node + chain stages
            d_ = 0; x = src_node
            while x is not None:
                d_ += 1; x = nodes[x]['parent']
            d_ += len(chain)
            got = '{' + ','.join(reversed([f'{prev[j // W]}[{j % W}]' for j in range(n)])) + '}'
            V.append(f'  wire [{n - 1}:0] {tag}_g{si} = {got};')
            V.append(f'  always @(negedge clk) if (cyc > {dep + 4}) begin chk = chk + 1; if ({tag}_g{si} !== {tag}_h[{d_ - 1}]) begin errs = errs + 1; '
                     f'if (errs < 5) $display("LOCKSTEP_MISMATCH {tag} sink {s_} cyc %0d", cyc); end end')
    V.append(f'  initial begin repeat (3) @(posedge clk); rs = 1; repeat ({a.cycles}) @(posedge clk); '
             '$display("RELAY_LOCKSTEP %s checks=%0d errors=%0d", (errs == 0 && chk > 0) ? "PASS" : "FAIL", chk, errs); $finish; end')
    V.append('endmodule')
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'tb_relay_lockstep.sv').write_text('\n'.join(V) + '\n')
    print('RELAY_LOCKSTEP_TB buses', len(sel), 'forks', len(forks), 'mut', a.mut, 'applied', mut_done if a.mut else '-')


def lane_main(a):
    """HBM-LANDING 10-18: lockstep bench of a --land layer (relay_layer_d4f.py --land) on the real lane RTL
    (hbfd_lh0 / hbfd_lh[_f<N>] half-cycle stations with the in-band epoch, hbfd_land / hbfd_land0 landings, plain
    hbfd_rly pads).  One root clock for every region (ideal clocks: dL = N half-periods); every reset (source en, sink rs,
    pads rs) releases a quarter period after one root posedge (no edge race).  Each landing's K is set to the ideal-clock
    value K = ceil(N/2) + 1 (E = 1; the die's K comes from the die STA E and is NOT what this bench checks), so every
    sink pin must see the source word of exactly ceil(N/2) + 2 + pads cycles earlier on every checked cycle, all lanes in
    lockstep, and no landing may raise fault.  Mutants (each must FAIL): lane_stage (lane 0 of one landed sink gets one
    more plain stage), bitswap (bits 0/1 of one lane swapped on one hop), branch_drop (one fork branch's data cut),
    land_k (lane 0 landing of one sink reads K + 1)."""
    L = json.loads(gzip.open(a.layer).read() if a.layer.endswith('.gz') else open(a.layer).read())
    mast = {i['name']: i['master'] for i in L['instances']}
    buses = [b for b in L['relay_splice_v2'] if b['kind'] != 'old']
    forks = [b for b in buses if any(len(nd['outs']) > 1 for nd in b['nodes'])]
    rest = [b for b in buses if b not in forks]
    sel = forks + (rest[:max(0, a.max_buses - len(forks))] if a.max_buses else rest)
    V = ['`timescale 1ns/1ps', 'module tb_relay_lockstep;', '  reg clk = 0; always #1 clk = ~clk; reg rs = 0;',
         '  integer cyc = 0, errs = 0, chk = 0, ferr = 0; always @(posedge clk) cyc <= cyc + 1;']
    mut_done = False; faults = []
    def bsel(o, W):   # node output ref -> (port, lo)
        return (o, 0) if isinstance(o, str) else (o[0], o[1])
    for b in sel:
        W, T, n, tag = b['width'], b['tiles'], b['bits'], b['bus']
        nodes = {nd['id']: nd for nd in b['nodes']}
        def tdep(x):
            d_ = 0
            while x is not None:
                d_ += 1; x = nodes[x]['parent']
            return d_
        lat = {s_: (-(-tdep(sk['src'][0]) // 2) + 2 + len(sk['chain']) - 1) for s_, sk in b['sinks'].items()}
        dep = max(lat.values()) + 8
        V.append(f'  // bus {tag} {b["driver"]} bits {n} kind {b["kind"]} lanes {T}x{W}')
        V.append(f'  reg [{n - 1}:0] {tag}_src; reg [{n - 1}:0] {tag}_h [0:{dep}];')
        V.append(f'  integer {tag}_k; always @(posedge clk) begin {tag}_src <= {{' + ','.join(['$random'] * ((n + 31) // 32)) + '}; '
                 f'{tag}_h[0] <= {tag}_src; for ({tag}_k = 1; {tag}_k <= {dep}; {tag}_k = {tag}_k + 1) {tag}_h[{tag}_k] <= {tag}_h[{tag}_k - 1]; end')
        def lane_in(t):
            return '{' + ','.join(f'{tag}_src[{(t * W + L_) if t * W + L_ < n else (t * W + L_) % n}]' for L_ in reversed(range(W))) + '}'
        swap = None
        if a.mut == 'bitswap' and not mut_done and b['nodes']:
            swap = b['nodes'][-1]['names'][0]; mut_done = True
        drop = None
        if a.mut == 'branch_drop' and not mut_done:
            fn = [nd for nd in b['nodes'] if len(nd['outs']) > 1]
            if fn:
                drop = (fn[0]['id'], len(fn[0]['outs']) - 1); mut_done = True
        for nd in b['nodes']:
            nb = len(nd['outs'])
            for t, nm in enumerate(nd['names']):
                V.append(f'  wire [{nb * W - 1}:0] {nm}__b; wire [{nb - 1}:0] {nm}__eb; wire [{nb - 1}:0] {nm}__ck;')
        for nd in b['nodes']:
            for t, nm in enumerate(nd['names']):
                m = mast[nm]
                if nd['parent'] is None:
                    i_expr = lane_in(t); cks = f'.ck(clk), .en(rs)'
                else:
                    pn = nodes[nd['parent']]; pnm = pn['names'][t]; k = nd['pbranch']
                    i_expr = f'{pnm}__b[{k * W + W - 1}:{k * W}]'
                    if drop and drop == (pn['id'], k):
                        i_expr = f"{W}'d0"
                    cks = f'.ckf({pnm}__ck[{k}]), .ea({pnm}__eb[{k}])'
                if nm == swap:
                    V.append(f'  wire [{W - 1}:0] {nm}__sw0 = {i_expr};')
                    V.append(f'  wire [{W - 1}:0] {nm}__sw1 = {{{nm}__sw0[{W - 1}:2],{nm}__sw0[0],{nm}__sw0[1]}};')
                    i_expr = f'{nm}__sw1'
                V.append(f'  {m} {nm} ({cks}, .a({i_expr}), .b({nm}__b), .eb({nm}__eb), .ck_o({nm}__ck));')
        for si, (s_, sk) in enumerate(b['sinks'].items()):
            src_node, br = sk['src']
            chain = sk['chain']
            if not chain:
                continue
            kmut = a.mut == 'land_k' and not mut_done
            extra = a.mut == 'lane_stage' and not mut_done
            prev = None
            for k, st_ in enumerate(chain):
                outs = []
                for t, nm in enumerate(st_):
                    m = mast[nm]
                    V.append(f'  wire [{W - 1}:0] {nm}__o;')
                    if k == 0:
                        K_ = (-(-tdep(src_node) // 2) + 1) % 8 + (1 if kmut and t == 0 else 0)
                        K_ %= 8
                        kk = ', '.join(f".k{j}(1'b{(K_ >> j) & 1})" for j in range(3))
                        if src_node is None:
                            src_ = f'.ck_s(clk), .en(rs), .a({lane_in(t)})'
                        else:
                            pn = nodes[src_node]; pnm = pn['names'][t]
                            src_ = f'.ckf({pnm}__ck[{br}]), .ea({pnm}__eb[{br}]), .a({pnm}__b[{br * W + W - 1}:{br * W}])'
                            if drop and drop == (src_node, br):
                                src_ = src_.replace(f'.a({pnm}__b[{br * W + W - 1}:{br * W}])', f".a({W}'d0)")
                        V.append(f'  wire {nm}__f; {m} {nm} ({src_}, .ck(clk), .rs(rs), {kk}, .b({nm}__o), .fault({nm}__f));')
                        faults.append(f'{nm}__f')
                    else:
                        V.append(f'  {m} {nm} (.ck(clk), .rs(rs), .i({prev[t]}), .o({nm}__o));')
                    outs.append(f'{nm}__o')
                prev = outs
            if kmut:
                mut_done = True
            if extra:
                nm0 = chain[-1][0]; xn = f'{nm0}__mutx'
                V.append(f'  wire [{W - 1}:0] {xn}__o; hbfd_rly_{W}_WE {xn} (.ck(clk), .rs(rs), .i({prev[0]}), .o({xn}__o));')
                prev = [f'{xn}__o'] + prev[1:]; mut_done = True
            d_ = lat[s_]
            got = '{' + ','.join(reversed([f'{prev[j // W]}[{j % W}]' for j in range(n)])) + '}'
            V.append(f'  wire [{n - 1}:0] {tag}_g{si} = {got};')
            V.append(f'  always @(negedge clk) if (cyc > {dep + 8}) begin chk = chk + 1; if ({tag}_g{si} !== {tag}_h[{d_ - 1}]) begin errs = errs + 1; '
                     f'if (errs < 5) $display("LOCKSTEP_MISMATCH {tag} sink {s_} cyc %0d", cyc); end end')
    if faults:
        for j in range(0, len(faults), 64):
            V.append(f"  always @(negedge clk) if (cyc > 4 && (|{{{', '.join(faults[j:j + 64])}}})) ferr = ferr + 1;")
    V.append(f'  initial begin repeat (3) @(posedge clk); #0.5 rs = 1; repeat ({a.cycles}) @(posedge clk); '
             '$display("RELAY_LOCKSTEP %s checks=%0d errors=%0d landing_fault_cycles=%0d", (errs == 0 && ferr == 0 && chk > 0) ? "PASS" : "FAIL", '
             'chk, errs + ferr, ferr); $finish; end')
    V.append('endmodule')
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'tb_relay_lockstep.sv').write_text('\n'.join(V) + '\n')
    print('RELAY_LOCKSTEP_TB lane buses', len(sel), 'forks', len(forks), 'landings', len(faults), 'mut', a.mut,
          'applied', mut_done if a.mut else '-')


if __name__ == '__main__':
    main()
