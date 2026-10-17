#!/usr/bin/env python3
"""H-NETLIST 2200: equivalence bench of the VM bank hoist (layer tools/hbm_die_v15/v16_layers/vm_hoist_d4f.json).
Emits, FROM THE LAYER (the same data full_die_v16 binds), a composition module vms_hoist_comp_<Q> with exactly the ports
of the original wrapper hfd_hgi_vms_static_<Q>: the hoisted glue hfd_hgi_vms_static_<Q>_glue + 8 bank instances
(+ 8 NW merge leaves) wired by the layer's port_split (old hub port bits -> bank / merge ports), internal edges and
bid/sid straps (bank / merge clk = clk_bank[b], rst_n = rst_n, the slice's own binding).  The testbench drives the
original wrapper (STRAP_BANKS=1, Q2_MERGE=1 for NW) and the composition with the same random inputs and compares EVERY
output on every edge.  MUT: the composition swaps bank 0/1 rslot (must FAIL).
    vms_hoist_equiv.py --layer L.json --quadrant SW|NW --out DIR [--mut]
"""
import argparse, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]


def ports_of(text, mod):
    m = re.search(rf'module {mod}\s*(#\(.*?\))?\s*\((.*?)\);', text, re.S)
    out = []
    for line in m.group(2).split('\n'):
        line = line.split('//')[0].strip().rstrip(',')
        mm = re.match(r'(input|output)\s+wire\s*(\[(\d+):0\])?\s*(.+)', line)
        if mm:
            for n in mm.group(4).split(','):
                out.append((mm.group(1), int(mm.group(3)) + 1 if mm.group(3) else 1, n.strip()))
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--layer', required=True); ap.add_argument('--quadrant', required=True)
    ap.add_argument('--out', required=True, type=Path); ap.add_argument('--mut', action='store_true')
    a = ap.parse_args(); q = a.quadrant; L = json.loads(Path(a.layer).read_text())
    hub = f'hb_vms_{q}'; rem = L['remaster'][hub]
    w = (ROOT / 'rtl/hbm_accel/generic/vm/static/hfd_hgi_vms_static.sv').read_text()
    g = (ROOT / 'rtl/hbm_accel/generic/vm/static/hfd_hgi_vms_static_glue.sv').read_text()
    P = ports_of(w, f'hfd_hgi_vms_static_{q}')
    GP = {n: (d, b) for d, b, n in ports_of(g, f'hfd_hgi_vms_static_{q}_glue')}
    insts = [i for i in L['instances'] if i['name'].endswith(tuple(f'_{q}{b}' for b in range(8))) and i['name'][:4] in ('vmb_', 'vmm_')]
    conn = {i['name']: {} for i in insts}; conn[hub] = {}
    decl = []
    def wire(name, bits):
        decl.append(f'  wire [{bits - 1}:0] {name};'); return name
    # internal edges: driver port -> one wire per driver port; sink slices from it
    drv = {}
    for e in L['edges']:
        s, d = e['src'], e['dst']
        if s[0] not in conn or d[0] not in conn:
            continue
        key = (s[0], s[1])
        if key not in drv:
            wb = GP[s[1]][1] if s[0] == hub else {'xq_done': 1, 'xq2_done': 1, 'eg': 276, 'pr': 266, 'status': 18, 'wq_m': 281,
                                                   'wq_done1': 1, 'flt': 1}[s[1]]
            drv[key] = wire(f'n_{s[0]}_{s[1]}', wb); conn[s[0]][s[1]] = drv[key]
        sl = drv[key] + (f'[{s[3] - 1}:{s[2]}]' if len(s) > 2 else '')
        conn[d[0]].setdefault(d[1], {})
        lo = d[2] if len(d) > 2 else 0
        conn[d[0]][d[1]] = conn[d[0]][d[1]] if isinstance(conn[d[0]][d[1]], dict) else {}
        conn[d[0]][d[1]][lo] = sl
    # external (old hub port) bits -> bank / merge ports
    outs_asm = {}
    for p, segs in rem['port_split'].items():
        for ni, np_, lo, hi in segs:
            if np_ == 'clk':
                conn[ni]['clk'] = f'{p}[{lo}]'; continue
            d = dict(P_ := {n: dd for dd, b, n in P})[p]
            if d == 'input':
                conn[ni][np_] = f'{p}[{hi - 1}:{lo}]'
            else:
                wn = wire(f'o_{ni}_{np_}', hi - lo); conn[ni][np_] = wn; outs_asm.setdefault(p, []).append((lo, hi, wn))
    for i in insts:
        n = i['name']; b = int(n[-1])
        conn[n].setdefault('rst_n', 'rst_n')
        if n.startswith('vmm_'):
            conn[n]['clk'] = f'clk_bank[{b}]'
    for s in L['straps']:
        if s['inst'] in conn:
            conn[s['inst']][s['port']] = f"{ {'bid': 3, 'sid': 2}[s['port']] }'d{s['value']}"
    if a.mut:
        b0, b1 = f'vmb_{q}0', f'vmb_{q}1'
        conn[b0]['rslot'], conn[b1]['rslot'] = conn[b1]['rslot'], conn[b0]['rslot']
    # hub glue: its remaining ports are the wrapper ports of the same name
    for d, b, n in P:
        if n in GP and n not in conn[hub]:
            conn[hub][n] = n
    # the wrapper's bank_status output = each bank's status (NW: merge flt ORed into bit 17, as the q2m adapter)
    bs = []
    for b in range(8):
        st = f'n_vmb_{q}{b}_status'
        bs.append(f'{{{st}[17] | n_vmm_{q}{b}_flt, {st}[16:0]}}' if q == 'NW' else st)
    outs_asm['bank_status'] = [(b * 18, b * 18 + 18, bs[b]) for b in range(8)]
    L_ = [f'module vms_hoist_comp_{q} (']
    L_ += [',\n'.join(f'  {d} wire [{b - 1}:0] {n}' for d, b, n in P), ');']
    L_ += decl
    for p, parts in outs_asm.items():
        parts.sort()
        L_.append(f"  assign {p} = {{{', '.join(w_ for _, _, w_ in reversed(parts))}}};")
    def cat(v):
        if isinstance(v, dict):
            return '{' + ', '.join(v[k] for k in sorted(v, reverse=True)) + '}'
        return v
    L_.append(f'  hfd_hgi_vms_static_{q}_glue u_glue (' + ', '.join(f'.{k}({cat(v)})' for k, v in conn[hub].items()) + ');')
    for i in insts:
        L_.append(f"  {i['master']} {i['name']} (" + ', '.join(f'.{k}({cat(v)})' for k, v in conn[i['name']].items()) + ');')
    L_.append('endmodule')
    ins = [(n, b) for d, b, n in P if d == 'input']
    outs = [(n, b) for d, b, n in P if d == 'output']
    prm = '#(.STRAP_BANKS(1)' + (',.Q2_MERGE(1)' if q == 'NW' else '') + ')'
    T = ['`timescale 1ns/1ps', 'module tb_vms_hoist;', '  reg clk = 0; always #1 clk = ~clk;']
    T += [f'  reg [{b - 1}:0] {n};' for n, b in ins]
    T += [f'  wire [{b - 1}:0] a_{n}, b_{n};' for n, b in outs]
    T.append(f'  hfd_hgi_vms_static_{q} {prm} u_ref (' + ', '.join([f'.{n}({n})' for n, _ in ins] + [f'.{n}(a_{n})' for n, _ in outs]) + ');')
    T.append(f'  vms_hoist_comp_{q} u_dut (' + ', '.join([f'.{n}({n})' for n, _ in ins] + [f'.{n}(b_{n})' for n, _ in outs]) + ');')
    clk_in = [n for n, _ in ins if n.startswith('clk')]
    T.append('  integer cyc, errs = 0, chk = 0;')
    T.append('  task rnd; begin')
    for n, b in ins:
        if n in clk_in or n == 'rst_n':
            continue
        T.append(f"    {n} = {{{(b + 31) // 32}{{$random}}}};")
    T.append('  end endtask')
    T.append('  initial begin')
    T.append('    rst_n = 0; ' + ' '.join(f"{n} = {{{b}{{1'b0}}}};" for n, b in ins if n in clk_in) + ' rnd;')
    T.append('    repeat (6) @(negedge clk); rst_n = 1;')
    T.append('    for (cyc = 0; cyc < 3000; cyc = cyc + 1) begin @(negedge clk); rnd; #0.5;')
    for n, b in outs:
        T.append(f'      chk = chk + 1; if (a_{n} !== b_{n}) begin errs = errs + 1; if (errs < 4) $display("MISMATCH cyc %0d {n}", cyc); end')
    T.append('    end')
    T.append(f'    $display("VMS_HOIST_EQUIV {q} %s checks=%0d errors=%0d", (errs == 0) ? "PASS" : "FAIL", chk, errs); $finish;')
    T.append('  end')
    # every clock input toggles with the bench clock (the slice's clocks are independent roots at the same edge)
    T.append('  always @(clk) begin ' + ' '.join(f"{n} = {{{b}{{clk}}}};" for n, b in ins if n in clk_in) + ' end')
    T.append('endmodule')
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / f'vms_hoist_comp_{q}.sv').write_text('\n'.join(L_) + '\n')
    (a.out / 'tb_vms_hoist.sv').write_text('\n'.join(T) + '\n')
    print('VMS_HOIST_TB', q, len(insts), 'instances', len(outs), 'outputs', 'MUT' if a.mut else '')


if __name__ == '__main__':
    main()
