#!/usr/bin/env python3
"""HBM-FAULT 2026-10-17 (coordinator 0da+ (b)): regional sticky fault-aggregation tree for the HBM d4f die.

The 136 unread fault outputs of the d4f tie contract (HBM-TIE class MISSING: LG banks, LG term banks, SU pgslices,
SU qcores, SU bridge releases, VMS ring faults, COLL retry, DMA mv_fault, argmax nan_flag, COLL inj/idx join, stack
fault joins + their 7-bit cause) feed a tree of ot_hbm_fault_leaf tiles that ends at the host status join, remastered
to ot_hbm_status_join_fa (ot_hbm_status_join + NA region-root inputs, region cause vector, F20 fault-clear target).

Tree (no star hub, neighbour-only, every hop registered; the die relay planner adds registered stations on hops over
the reach):
  fl_<Q><k>  (Q in SW SE NE NW, k 0..3) one per SU slice column of the region row: the six LG banks of column k
             (lg_<Q>_{0,1,2}_b{2k,2k+1}, placed at x ~0.4/3.4/7.5/10.6 mm beside su_<Q>k) + su_<Q>k.fault (serial
             domain: SYNC) + child fl_<Q><k-1> (k > 0).  Chain west -> east toward the region root.
  fs_<S>     (S in SW NW) beside the stack fault join sfault_<S> (PHY edge): fault + status[6:0] (the stack cause).
  fr_<Q>     region root beside coll_<Q>: hb_vms_<Q>.ring_fault[2:0], hb_coll_<Q>.retry_requested, subr_<Q>.fault,
             hb_dbk_<Q>.mv_fault (SW NW), cij_SW.fault (SW), hb_argmax.nan_flag (NE), sucore_<Q>.fault (serial: SYNC),
             children fl_<Q>3 and fs_<Q> (SW NW).
  host_status (ot_hbm_status_join_fa NA 4): a_fault[i] = fr_<Q>.fault, region cause a_cause[i] (i = SW SE NE NW).
Leaves are registered ORs (2 edges, 3 for SYNC bits); the fault is held (sticky) at the join until the host writes an
F20 row to target FCLR (125); it raises die_fault (host status flit) and holds block_ready low (launch refused).

usage: hbm_fault_1017.py contract IN.json[.gz] OUT.json[.gz]
       hbm_fault_1017.py die IN_die.v OUT_die.v
bench: tools/hbm_die_v16/bench_fault_tree_1017.sh (full tree, random registered relay depth per edge)
"""
import gzip
import json
import os
import re
import sys

LGFOLD = os.environ.get('LGFOLD') == '1'   # H-DIE-R8b: run on a contract with the r8b LG tap fold (v16_layers/r8b_d4f.json)

REGION = 'hbm_fault_1017'
LEAF = 'ot_hbm_fault_leaf'
LEAF_SRC = 'rtl/hbm_accel/die_glue/ot_hbm_fault_leaf.sv'
JOIN = 'ot_hbm_status_join_fa'
JOIN_SRC = 'rtl/hbm_accel/host_static_20261015/ot_hbm_status_join_fa.sv'
QS = ['SW', 'SE', 'NE', 'NW']
STACKS = ['SW', 'NW']
FCLR = 125


def tree():
    """leaf name -> dict(inputs=[(inst, port, lo, hi, kind)], slot, parent); kind in L (local), S (sync), C (child)."""
    T = {}
    for q in QS:
        for k in range(4):
            if LGFOLD:   # H-DIE-R8b: the LG taps live in their consumer folds (one OR'd fault per pair and level)
                ins = [(f'su_{q}{k}', 'lg_fault', 0, 1, 'L'), (f'sfu_{q}{k}', 'fault', 0, 1, 'L'), (f'hc_{q}{k}', 'fault', 0, 1, 'L')]
            else:
                ins = [(f'lg_{q}_{g}_b{2 * k + j}', 'fault', 0, 1, 'L') for g in range(3) for j in range(2)]
            ins.append((f'su_{q}{k}', 'fault', 0, 1, 'S'))
            if k:
                ins.append((f'fl_{q}{k - 1}', 'fault', 0, 1, 'C'))
            T[f'fl_{q}{k}'] = dict(inputs=ins, slot=f'su_{q}{k}', parent=f'fl_{q}{k + 1}' if k < 3 else f'fr_{q}',
                                   note=f'LG column {k} of row {q} + SU slice {q}{k}')
        if q in STACKS:
            T[f'fs_{q}'] = dict(inputs=[(f'sfault_{q}', 'fault', 0, 1, 'L'), (f'sfault_{q}', 'status', 0, 7, 'L')],
                                slot=f'pc_{q}0', parent=f'fr_{q}', note=f'stack {q} PC fault join + its 7-bit cause')
        ins = [(f'hb_vms_{q}', 'ring_fault', 0, 3, 'L'), (f'hb_coll_{q}', 'retry_requested', 0, 2 if q == 'SW' else 1, 'L'),
               (f'subr_{q}', 'fault', 0, 1, 'L')]
        if q in STACKS:
            ins.append((f'hb_dbk_{q}', 'mv_fault', 0, 1, 'L'))
        if q == 'SW':
            ins.append(('cij_SW', 'fault', 0, 1, 'L'))
        if q == 'NE':
            ins.append(('hb_argmax', 'nan_flag', 0, 1, 'L'))
        ins.append((f'sucore_{q}', 'fault', 0, 1, 'S'))
        ins.append((f'fl_{q}3', 'fault', 0, 1, 'C'))
        if q in STACKS:
            ins.append((f'fs_{q}', 'fault', 0, 1, 'C'))
        T[f'fr_{q}'] = dict(inputs=ins, slot=f'coll_{q}', parent='host_status', note=f'region {q} root')
    for n, t in T.items():
        n_bits, sm = 0, 0
        for (_, _, lo, hi, kind) in t['inputs']:
            for _b in range(lo, hi):
                if kind == 'S':
                    sm |= 1 << n_bits
                n_bits += 1
        t.update(N=n_bits, SYNC_MASK=sm)
        t['children'] = [i for (i, _, _, _, kind) in t['inputs'] if kind == 'C']
    return T


def ld(p):
    return json.load(gzip.open(p) if p.endswith('.gz') else open(p))


def dump(c, p):
    s = json.dumps(c, indent=1)
    (gzip.open(p, 'wt') if p.endswith('.gz') else open(p, 'w')).write(s)


def edge(name, bits, src, snk, basis):
    return dict(name=name, bits=bits, source=src, sink=snk, clock='stream', ready_or_credit=False, allowed_exception=None,
                basis=basis, region=REGION)


def mask_add(param, ids):
    w, h = param.split("'h")
    v = int(h, 16)
    for i in ids:
        v |= 1 << i
    return f"{w}'h{v:0{len(h)}x}"


def contract(cin, cout):
    c = ld(cin)
    I, E = c['instances'], c['edges']
    T = tree()
    consumed = set()
    for n, t in T.items():
        p = dict(N=t['N'], SYNC_MASK=f"64'h{t['SYNC_MASK']:x}")
        I[n] = dict(master=LEAF, source=LEAF_SRC, params=p, slot=t['slot'], owner='HBM-FAULT', region=REGION,
                    note='fault-aggregation leaf: ' + t['note'], replaces_v15=None, rtl_deps=[],
                    ports={'clk': dict(direction='input', bits=1), 'rst_n': dict(direction='input', bits=1),
                           'in': dict(direction='input', bits=t['N']), 'fault': dict(direction='output', bits=1)})
        c['masters'][LEAF] = c['masters'].get(LEAF, 0) + 1
        c['clock_resets'] += [dict(instance=n, port='clk', bits=1, domain='stream', kind='clock', source=['hb_ckgen', 'pll_stream']),
                              dict(instance=n, port='rst_n', bits=1, domain='stream', kind='reset', source=['hb_ckgen', 'por_stream'])]
        b = 0
        for (i, port, lo, hi, kind) in t['inputs']:
            if kind != 'C':
                assert i in I and port in I[i]['ports'], (i, port)
                assert I[i]['ports'][port]['bits'] == hi - lo, (i, port)
                consumed.add((i, port))
            E.append(edge(f'flt_{n}_{i}_{port}', hi - lo, [i, port, lo, hi], [n, 'in', b, b + hi - lo],
                          {'L': 'fault bit (pulse or level): leaf pin flop, held at the status join', 'S': 'serial-domain sticky level: 2-flop sync',
                           'C': 'child leaf fault (registered OR)'}[kind]))
            b += hi - lo
    # host status join -> ot_hbm_status_join_fa
    hs = I['host_status']
    old = hs['master']
    assert old == 'ot_hbm_status_join', old
    hs['master'], hs['source'] = JOIN, JOIN_SRC
    hs['rtl_deps'] = sorted(set(hs.get('rtl_deps', []) + ['rtl/hbm_accel/host_static_20261015/ot_hbm_status_join.sv']))
    hs['params'].update(NA=len(QS), FCLR=FCLR)
    hs['ports'].update({'a_fault': dict(direction='input', bits=len(QS)), 'a_cause': dict(direction='output', bits=len(QS))})
    hs['note'] = hs.get('note', '') + ' | HBM-FAULT 1017: + fault-tree region roots (a_fault sticky -> a_cause, F20 clear target 125)'
    c['masters'][old] -= 1
    c['masters'][JOIN] = c['masters'].get(JOIN, 0) + 1
    c['masters'] = {k: v for k, v in c['masters'].items() if v}
    for k, q in enumerate(QS):
        E.append(edge(f'flt_root_{q}', 1, [f'fr_{q}', 'fault', 0, 1], ['host_status', 'a_fault', k, k + 1], 'region root -> status join'))
    ing = I['host_cp_ingress']
    m = int(ing['params']['TARGET_MASK'].split("'h")[1], 16)
    assert not (m >> FCLR) & 1, 'FCLR already admitted'
    assert FCLR not in [int(hs['params']['TGTS'].split("'h")[1][i:i + 2], 16) for i in range(0, len(hs['params']['TGTS'].split("'h")[1]), 2)]
    ing['params']['TARGET_MASK'] = mask_add(ing['params']['TARGET_MASK'], [FCLR])
    # open outputs: the 136 are consumed; new: a_cause (OBS until the ingress read map)
    n0 = len(c['open_outputs'])
    c['open_outputs'] = [o for o in c['open_outputs'] if (o[0], o[1]) not in consumed]
    n_cons = n0 - len(c['open_outputs'])
    c['open_outputs'].append(['host_status', 'a_cause', len(QS)])
    s = c['summary']
    s.update(instances=len(I), masters=len(c['masters']), edges=len(E), edge_bits=sum(e['bits'] for e in E),
             clock_reset_ports=len(c['clock_resets']), open_output_ports=len(c['open_outputs']))
    c.setdefault('notes', {})[REGION] = __doc__.split('usage:')[0].strip()
    dump(c, cout)
    print(f'contract: +{len(T)} leaves ({sum(t["N"] for t in T.values())} leaf input bits), consumed open outputs {n_cons} '
          f'({len(consumed)} ports), open outputs {n0} -> {len(c["open_outputs"])}, host_status -> {JOIN} NA {len(QS)}')


def die(din, dout):
    v = open(din).read()
    T = tree()
    decl, inst = [], []
    for n, t in T.items():
        decl.append(f'  wire [0:0] {n}__fault;\n')
        bits = []
        for (i, port, lo, hi, kind) in t['inputs']:
            net = f'{i}__{port}'
            if kind != 'C':
                assert re.search(r'wire \[\d+:0\] ' + re.escape(net) + ';', v), net
            bits += [f'{net}[{b}]' for b in range(lo, hi)]
        inst.append(f"  {LEAF} #(.N({t['N']}), .SYNC_MASK(64'h{t['SYNC_MASK']:x})) {n} (\n"
                    f'    .clk(hb_ckgen__pll_stream[0]),\n    .rst_n(hb_ckgen__por_stream[0]),\n'
                    f'    .in({{{", ".join(reversed(bits))}}}),\n    .fault({n}__fault)\n  );\n')
    decl.append(f'  wire [{len(QS) - 1}:0] host_status__a_cause;\n')
    i = v.index('  wire ')
    v = v[:i] + ''.join(decl) + v[i:]
    m = re.search(r"ot_hbm_status_join #\((\.NT\(\d+\), \.NF\(\d+\), \.NH\(\d+\), \.TGTS\([^)]*\))\) host_status \(", v)
    assert m, 'host_status'
    v = v[:m.start()] + f'{JOIN} #({m.group(1)}, .NA({len(QS)}), .FCLR({FCLR})) host_status (' + v[m.end():]
    j = v.index('    .irq(host_status__irq)', m.start())
    roots = ', '.join(f'fr_{q}__fault[0]' for q in reversed(QS))
    v = v[:j] + f'    .a_fault({{{roots}}}),\n    .a_cause(host_status__a_cause),\n' + v[j:]
    mm = re.search(r"(ot_hbm_host_static_ingress #\(\.MUT\(0\), \.TARGET_MASK\()([^)]*)(\)\) host_cp_ingress)", v)
    v = v[:mm.start(2)] + mask_add(mm.group(2), [FCLR]) + v[mm.end(2):]
    k = v.rindex('endmodule')
    v = v[:k] + ''.join(inst) + v[k:]
    open(dout, 'w').write(v)
    print(f'die.v: +{len(T)} {LEAF}, host_status -> {JOIN}')


if __name__ == '__main__':
    {'contract': contract, 'die': die}[sys.argv[1]](sys.argv[2], sys.argv[3])
