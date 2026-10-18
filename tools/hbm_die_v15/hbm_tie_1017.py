#!/usr/bin/env python3
"""HBM-TIE 2026-10-17 (stub audit 0da, coordinator rulings a-d): contract + die-netlist layer for the HBM d4f die.

Applies to the d4f source contract (results/arch/hbm_die_v16_d4f_tp192 / run6 views/contract.json) and, for the
port-bind evidence, to the run6 case die.v (same instance and net names):

 K   (0da d, H-2)  hb_idx__selector.k = col_idx.prm[1459:1450] (IDX operand row 5 bits [179:170], written by the host
                   boot/launch configuration through the F20 ingress; the IDX calendar's op 1 latches it). Strap
                   k=10'd512 removed.
 REF (0da d, H-3)  refcfg_SW / refcfg_NW = ot_hbm_pc_refresh_cfg (F20 targets 126 / 127, identity strap tgt) drive
                   ctl_<S>_pNN.refresh_reload = refcfg_<S>.refresh_reload[8 NN +: 8] and hold the stack's 32 PC
                   controllers in reset (ctl_<S>_pNN.rst_n = refcfg_<S>.pc_rst_n, a reset tree like por_hbm) until
                   the row is loaded. Straps refresh_reload removed. Host side: ingress TARGET_MASK admits 126/127;
                   host_status gains two targets (NT+2: t_ready/t_active, NF+2: t_fault, TGTS += 7e,7f).
 XLD (0da c, H-1)  xl_SW_ctl / xl_NW_ctl remastered to ot_hgi_sm_xload_cl2_ctlx (HBM-B 2c49a6986: ctlw EGRESS_SPLIT 1
                   with exactly the die-connected ports): straps rwq/bq_d (6,144 b) and open outputs xw_*/x_done
                   (4,130 b) disappear, clk_eg folds into clk.

usage: hbm_tie_1017.py contract IN.json OUT.json
       hbm_tie_1017.py die IN_die.v OUT_die.v
"""
import json
import re
import sys

REGION = 'hbm_tie_1017'
K_LO, K_HI = 1450, 1460
STACKS = {'SW': 126, 'NW': 127}
NPC = 32
REF_SRC = 'rtl/hbm_accel/loader/service_native/ot_hbm_pc_refresh_cfg.sv'
CTLX = 'ot_hgi_sm_xload_cl2_ctlx'
CTLX_DROP = ['rwq', 'bq_d', 'xw_data', 'xw_addr', 'xw_grp', 'xw_en', 'xw_last', 'x_done', 'clk_eg']


def edge(name, bits, src, snk, basis, clock='stream'):
    return dict(name=name, bits=bits, source=src, sink=snk, clock=clock, ready_or_credit=False, allowed_exception=None,
                basis=basis, region=REGION)


def mask_add(param, ids):
    w, h = param.split("'h")
    v = int(h, 16)
    for i in ids:
        v |= 1 << i
    return f"{w}'h{v:0{len(h)}x}"


def tgts_add(param, ids):
    w, h = param.split("'h")
    add = ''.join(f'{i:02x}' for i in reversed(ids))
    return f"{int(w) + 8 * len(ids)}'h{add}{h}"


def contract(cin, cout):
    c = json.load(open(cin))
    I, E = c['instances'], c['edges']
    n_straps = len(c['straps'])
    # ---- K
    c['straps'] = [s for s in c['straps'] if not (s['inst'] == 'hb_idx__selector' and s['port'] == 'k')]
    E.append(edge('tie_idx_k', 10, ['col_idx', 'prm', K_LO, K_HI], ['hb_idx__selector', 'k', 0, 10],
                  'IDX operand row 5 [179:170] = top-k K of the launch; latched by selector op 1 on the IDX calendar'))
    # ---- refresh producers
    c['straps'] = [s for s in c['straps'] if s['port'] != 'refresh_reload']
    hs = I['host_status']
    nt, nf = int(hs['params']['NT']), int(hs['params']['NF'])
    for k, (st, tid) in enumerate(STACKS.items()):
        n = f'refcfg_{st}'
        I[n] = dict(master='ot_hbm_pc_refresh_cfg', source=REF_SRC, params={'NPC': NPC}, slot=f'pc_{st}0', owner='HBM-TIE',
                    region=REGION, note=f'F20 target {tid}: boot-configured refresh_reload of the {st} stack PCs + PC reset '
                    'release after the row is loaded (replaces the refresh_reload strap, 0da d)', replaces_v15=None,
                    rtl_deps=[], ports={'clk': dict(direction='input', bits=1), 'rst_n': dict(direction='input', bits=1),
                                        'clk_hbm': dict(direction='input', bits=1), 'rst_hbm_n': dict(direction='input', bits=1),
                                        'tgt': dict(direction='input', bits=8), 'cfg_v': dict(direction='input', bits=1),
                                        'cfg_target': dict(direction='input', bits=8), 'cfg_addr': dict(direction='input', bits=12),
                                        'cfg_data': dict(direction='input', bits=256),
                                        'refresh_reload': dict(direction='output', bits=8 * NPC),
                                        'pc_rst_n': dict(direction='output', bits=1), 'ready': dict(direction='output', bits=1),
                                        'active': dict(direction='output', bits=1), 'fault': dict(direction='output', bits=1)})
        c['masters']['ot_hbm_pc_refresh_cfg'] = c['masters'].get('ot_hbm_pc_refresh_cfg', 0) + 1
        c['straps'].append(dict(inst=n, port='tgt', value=tid, reason=f'identity: F20 target id {tid} of this target instance',
                                lo=0, hi=8, master='ot_hbm_pc_refresh_cfg'))
        c['clock_resets'] += [dict(instance=n, port='clk', bits=1, domain='stream', kind='clock', source=['hb_ckgen', 'pll_stream']),
                              dict(instance=n, port='rst_n', bits=1, domain='stream', kind='reset', source=['hb_ckgen', 'por_stream']),
                              dict(instance=n, port='clk_hbm', bits=1, domain='hbm', kind='clock', source=['hb_ckgen', 'pll_hbm']),
                              dict(instance=n, port='rst_hbm_n', bits=1, domain='hbm', kind='reset', source=['hb_ckgen', 'por_hbm'])]
        for p, b in [('cfg_v', 1), ('cfg_target', 8), ('cfg_addr', 12), ('cfg_data', 256)]:
            E.append(edge(f'tie_{n}_{p}', b, ['host_cp_ingress', p, 0, b], [n, p, 0, b],
                          'static ingress F20 broadcast (ot_hbm_host_static_ingress)'))
        for pc in range(NPC):
            ctl = f'ctl_{st}_p{pc:02d}'
            assert I[ctl]['master'].startswith('ot_hbm_svc_pc_ctrl_leaf_cfg'), ctl
            E.append(edge(f'tie_{ctl}_refresh_reload', 8, [n, 'refresh_reload', 8 * pc, 8 * pc + 8], [ctl, 'refresh_reload', 0, 8],
                          'boot-configured refresh phase (quasi-static: stable >= 5 HBM edges before the controller samples it)', 'hbm'))
            for x in c['clock_resets']:
                if x['instance'] == ctl and x['port'] == 'rst_n':
                    x['source'] = [n, 'pc_rst_n']
                    x['note'] = 'PC reset released only after the refresh row is loaded (one balanced reset tree per stack, as por_hbm)'
        E.append(edge(f'tie_{n}_ready', 1, [n, 'ready', 0, 1], ['host_status', 't_ready', nt + k, nt + k + 1], 'status'))
        E.append(edge(f'tie_{n}_active', 1, [n, 'active', 0, 1], ['host_status', 't_active', nt + k, nt + k + 1], 'status'))
        E.append(edge(f'tie_{n}_fault', 1, [n, 'fault', 0, 1], ['host_status', 't_fault', nf + k, nf + k + 1],
                      'Actual static component sticky fault observation; never reschedules execution'))
    hs['params']['NT'] = nt + len(STACKS)
    hs['params']['NF'] = nf + len(STACKS)
    hs['params']['TGTS'] = tgts_add(hs['params']['TGTS'], list(STACKS.values()))
    for p in ('t_ready', 't_active'):
        hs['ports'][p]['bits'] = nt + len(STACKS)
    hs['ports']['t_fault']['bits'] = nf + len(STACKS)
    ing = I['host_cp_ingress']
    ing['params']['TARGET_MASK'] = mask_add(ing['params']['TARGET_MASK'], list(STACKS.values()))
    # ---- x-load ctl remaster
    for q in ('SW', 'NW'):
        n = f'xl_{q}_ctl'
        old = I[n]['master']
        assert old == 'ot_hgi_sm_xload_cl2_ctlw', old
        I[n]['master'] = CTLX
        I[n]['params'] = {k: v for k, v in I[n]['params'].items() if k not in ('EGRESS_SPLIT', 'SEL_KEEP')}
        I[n]['note'] = I[n].get('note', '') + ' | HBM-TIE 1017: ctlx (HBM-B 2c49a6986) = ctlw EGRESS_SPLIT 1 with die-connected ports only'
        for p in CTLX_DROP:
            I[n]['ports'].pop(p, None)
        c['masters'][old] -= 1
        c['masters'][CTLX] = c['masters'].get(CTLX, 0) + 1
    c['masters'] = {k: v for k, v in c['masters'].items() if v}
    c['straps'] = [s for s in c['straps'] if not (s['inst'] in ('xl_SW_ctl', 'xl_NW_ctl') and s['port'] in CTLX_DROP)]
    for s_ in c['straps']:
        if s_['inst'] in ('xl_SW_ctl', 'xl_NW_ctl'):
            s_['master'] = CTLX
    c['clock_resets'] = [x for x in c['clock_resets'] if not (x['instance'] in ('xl_SW_ctl', 'xl_NW_ctl') and x['port'] in CTLX_DROP)]
    dropped = [o for o in c['open_outputs'] if o[0] in ('xl_SW_ctl', 'xl_NW_ctl') and o[1] in CTLX_DROP]
    c['open_outputs'] = [o for o in c['open_outputs'] if o not in dropped]
    bad = [e['name'] for e in E if (e['source'][0] in ('xl_SW_ctl', 'xl_NW_ctl') and e['source'][1] in CTLX_DROP) or
           (e['sink'][0] in ('xl_SW_ctl', 'xl_NW_ctl') and e['sink'][1] in CTLX_DROP)]
    assert not bad, bad
    s = c['summary']
    s['instances'] = len(I)
    s['masters'] = len(c['masters'])
    s['edges'] = len(E)
    s['edge_bits'] = sum(e['bits'] for e in E)
    s['clock_reset_ports'] = len(c['clock_resets'])
    s['straps'] = len(c['straps'])
    s['open_output_ports'] = len(c['open_outputs'])
    c.setdefault('notes', {})[REGION] = __doc__.split('usage:')[0].strip()
    json.dump(c, open(cout, 'w'), indent=1)
    print(f'contract: straps {n_straps} -> {len(c["straps"])}, instances {len(I)}, open outputs -> {len(c["open_outputs"])} '
          f'(-{len(dropped)} ctlx), host_status NT {nt}->{nt + 2} NF {nf}->{nf + 2}')


def die(din, dout):
    v = open(din).read()
    n0 = len(v)
    # ---- K
    v, k = re.subn(r"\.k\(10'd512\)", f'.k(col_idx__prm[{K_HI - 1}:{K_LO}])', v)
    assert k == 1, k
    # ---- refresh producers: PC straps and resets
    for st, tid in STACKS.items():
        n = f'refcfg_{st}'
        for pc in range(NPC):
            ctl = f'ctl_{st}_p{pc:02d}'
            pat = re.compile(r'(ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #\([^\n]*\) ' + ctl + r' \(\n)(.*?)(\n  \);)', re.S)
            m = pat.search(v)
            assert m, ctl
            body = m.group(2)
            body, a = re.subn(r"\.refresh_reload\(8'd\d+\)", f'.refresh_reload({n}__refresh_reload[{8 * pc + 7}:{8 * pc}])', body)
            body, b = re.subn(r'\.rst_n\(hb_ckgen__por_hbm\[0\]\)', f'.rst_n({n}__pc_rst_n[0])', body)
            assert a == 1 and b == 1, (ctl, a, b)
            v = v[:m.start(2)] + body + v[m.end(2):]
        decl = (f'  wire [{8 * NPC - 1}:0] {n}__refresh_reload;\n  wire [0:0] {n}__pc_rst_n;\n  wire [0:0] {n}__ready;\n'
                f'  wire [0:0] {n}__active;\n  wire [0:0] {n}__fault;\n')
        inst = (f'  ot_hbm_pc_refresh_cfg #(.NPC({NPC})) {n} (\n    .clk(hb_ckgen__pll_stream[0]),\n'
                f'    .rst_n(hb_ckgen__por_stream[0]),\n    .clk_hbm(hb_ckgen__pll_hbm[0]),\n    .rst_hbm_n(hb_ckgen__por_hbm[0]),\n'
                f"    .tgt(8'd{tid}),\n    .cfg_v(host_cp_ingress__cfg_v[0]),\n    .cfg_target(host_cp_ingress__cfg_target[7:0]),\n"
                f'    .cfg_addr(host_cp_ingress__cfg_addr[11:0]),\n    .cfg_data(host_cp_ingress__cfg_data[255:0]),\n'
                f'    .refresh_reload({n}__refresh_reload),\n    .pc_rst_n({n}__pc_rst_n),\n    .ready({n}__ready),\n'
                f'    .active({n}__active),\n    .fault({n}__fault)\n  );\n')
        i = v.index('  wire ')
        v = v[:i] + decl + v[i:]
        j = v.rindex('endmodule')
        v = v[:j] + inst + v[j:]
    # ---- host status join: two more targets (new bits at the MSB end of each concatenation)
    m = re.search(r"ot_hbm_status_join #\(\.NT\((\d+)\), \.NF\((\d+)\), \.NH\((\d+)\), \.TGTS\(([^)]*)\)\) host_status \(", v)
    assert m, 'host_status'
    nt, nf = int(m.group(1)), int(m.group(2))
    hdr = (f"ot_hbm_status_join #(.NT({nt + 2}), .NF({nf + 2}), .NH({m.group(3)}), "
           f".TGTS({tgts_add(m.group(4), list(STACKS.values()))})) host_status (")
    v = v[:m.start()] + hdr + v[m.end():]
    seg_start = v.index(hdr)
    seg_end = v.index('\n  );', seg_start)
    seg = v[seg_start:seg_end]
    for p, sig in [('t_ready', 'ready'), ('t_active', 'active'), ('t_fault', 'fault')]:
        mm = re.search(r'\.' + p + r'\(\{', seg)
        assert mm, p
        seg = seg[:mm.end()] + f'refcfg_NW__{sig}[0], refcfg_SW__{sig}[0], ' + seg[mm.end():]
    v = v[:seg_start] + seg + v[seg_end:]
    m = re.search(r"(ot_hbm_host_static_ingress #\(\.MUT\(0\), \.TARGET_MASK\()([^)]*)(\)\) host_cp_ingress)", v)
    v = v[:m.start(2)] + mask_add(m.group(2), list(STACKS.values())) + v[m.end(2):]
    # ---- x-load ctl remaster
    for q in ('SW', 'NW'):
        n = f'xl_{q}_ctl'
        pat = re.compile(r'ot_hgi_sm_xload_cl2_ctlw #\(([^\n]*)\) ' + n + r' \(\n(.*?)\n  \);', re.S)
        m = pat.search(v)
        assert m, n
        params = ', '.join(p for p in re.findall(r'\.\w+\([^()]*\)', m.group(1))
                           if not p.startswith(('.EGRESS_SPLIT', '.SEL_KEEP')))
        lines = [ln for ln in m.group(2).split('\n') if not re.match(r'\s*\.(' + '|'.join(CTLX_DROP) + r')\(', ln)]
        lines[-1] = lines[-1].rstrip(',')
        new = f'{CTLX} #({params}) {n} (\n' + '\n'.join(lines) + '\n  );'
        v = v[:m.start()] + new + v[m.end():]
    open(dout, 'w').write(v)
    print(f'die.v: {n0} -> {len(v)} chars')


if __name__ == '__main__':
    {'contract': contract, 'die': die}[sys.argv[1]](sys.argv[2], sys.argv[3])
