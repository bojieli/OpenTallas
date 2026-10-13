#!/usr/bin/env python3
"""qfd_seq_su slot cell (Qwen ROM TP8 contract v3 slot seq_su): ONE packing table -> wrapper RTL, bench shim, JSON.
Table: bundle -> body ports of ot_qfd_seq_su_bi, LSB-FIRST, fixed order.  None = contract bits with no body port
(reported, never tied off: those bits are not ports of the cell).  Run from the repo root; --check only validates."""
import json, re, sys
NW, AW, SW = 18, 24, 64
BODY = 'rtl/qwen_sys/redesign_qwen/ot_qfd_seq_su_bi.sv'
PARAMS = dict(PSRAM=1, HQ2=1)      # the closed body (qfd_seq_su-fea-f3e3d6b6f)
SU_I = ('nout nin asrc abase aso asi bsrc bbase bso bsi csrc cbase cso csi ma mb ad sfu mc md dst dbase dso dsi red '
        'redsq rbase rso imm1 imm2').split()
# bundle: (contract width, direction of the bundle's flow, peer, [body ports LSB-first | (None, bits)])
T = [
 ('su', 476, 'out', 'sp_su64_sfu.si', ['po_su_go'] + ['po_su_i_' + f for f in SU_I] + ['su_asrc', 'su_tok']),
 ('sd', 133, 'in', 'sp_su64_sfu.sd', ['pi_su_rt_active', 'pi_su_rt_inflight', 'pi_su_ready', 'pi_su_idle', 'pi_su_wrom_re',
                                    'pi_su_wrom_addr', 'pi_su_kv_we', 'pi_su_progress', 'pi_su_progress_rows', 'pi_su_fault']),
 ('acc', 24, 'in', 'sp_su64_sfu.acc', ['pi_su_acc']),
] + [(f'cbc{k}', 25, 'out', f'cbuf_g_{k}.ctl', ['cb_tpos', 'cb_tok_start', 'cb_stage']) for k in range(8)] + [
 ('cbr0', 10, 'in', 'cbuf_g_0.rdy', [(None, 3), 'cb_st_rdy_stage', 'cb_st_rdy']),
] + [(f'cbr{k}', 10, 'in', f'cbuf_g_{k}.rdy', [(None, 10)]) for k in range(1, 8)] + [
 ('st', 49, 'out', 'tt_ctlm.st', ['me_prog_base_o', 'me_pos_o', 'me_token_o', 'me_start_o']),
 ('xs', 57, 'out', 'tt_ctlm.xs', ['su_rows_o', 'su_prog_o', 'su_idle_o', 'su_acc_o']),
 ('xm', 92, 'in', 'tt_ctlm.xm', ['x_fval', 'x_fidx', 'x_ofin', 'x_oprog', 'x_oidle', 'x_oacc']),
 ('vrd', 9, 'out', 'sp_vector_memory', ['vm_raddr', 'vm_re']),
 ('vrq', 512, 'in', 'sp_vector_memory', ['vm_rq']),
 ('vwr', 521, 'out', 'sp_vector_memory', ['vm_wdata', 'vm_waddr', 'vm_we']),
 ('ib', 382, 'out', 'sp_vector_memory.ib', [(None, 382)]),
 ('dc', 530, 'out', 'd2d_rom.dc', ['seq_nval', 'seq_ntok', 's_done', 's_fault', 'core_fault', 'coll_busy', 'kv_write_flush',
                                 'rom_fault', (None, 474)]),
 ('dh', 530, 'in', 'd2d_rom.dh', ['tp_pos', 'tp_token', 'stage_in', 'h_start', 'kv_write_drained', 'pw_data', 'pw_addr', 'pw_v',
                                'dw_data', 'dw_addr', 'dw_v', (None, 343)]),
 ('dflt', 9, 'in', 'd2d_rom.flt', [(None, 9)]),
 ('kvd', 201, 'out', 'd2d_rom.kvd', ['kvd_pos', 'kvd_kindk', 'kvd_nout', 'kvd_k', 'kvd_tiles', 'kvd_jsh', 'kvd_split', 'kvd_wcs',
                                   'kvd_js', 'kvd_ks', 'kvd_ts', 'kvd_wbase', 'kvd_v']),
 # credit links: the data word and the credit run opposite ways -> two ports on the bundle's face (as qkd kvn_d / kvn_cr)
 ('cd', 548, 'out', 'io_xfifo.i_seq_coll', ['c_data', 'c_last', 'c_mode', 'c_tag', 'c_valid', ('!c_ready', 1)]),
 ('cc', 518, 'in', 'io_xfifo.o_coll_seq', ['r_data', 'r_last', 'r_rank', 'r_err', 'r_valid', (None, 1)]),
 ('rsi', 1, 'in', 'clk_rx.rso_seq', ['rst_n']),
]
def body_ports():
    src = open(BODY).read()
    hdr = src[src.index('module ot_qfd_seq_su_bi '):]
    hdr = hdr[re.search(r'^\) \($', hdr, re.M).start():re.search(r'^\);$', hdr, re.M).start()]
    P = {}
    for d, w, n in re.findall(r'(input|output)\s+wire\s*(\[[^\]]+\])?\s*(\w+)', hdr):
        if w:
            hi = w[1:w.index(':')].replace('NW', str(NW)).replace('AW', str(AW)).replace('SW', str(SW))
            w = eval(hi) + 1
        P[n] = (d, w or 1)
    return P
def build():
    P = body_ports(); used = {}; rows = []
    for name, cw, flow, peer, fl in T:
        lsb = 0; fields = []
        for f in fl:
            if isinstance(f, tuple):
                if f[0] is None:
                    fields.append(dict(port=None, lsb=lsb, width=f[1])); lsb += f[1]; continue
                n, against = f[0][1:], True
            else:
                n, against = f, False
            d, w = P[n]
            assert n not in used or name.startswith('cbc'), n
            assert (d == 'output') == ((flow == 'out') != against), (name, n, d)
            used[n] = name
            fields.append(dict(port=n, lsb=lsb, width=w, dir='in' if d == 'input' else 'out', against_flow=against)); lsb += w
        assert lsb == cw, (name, lsb, cw)
        rows.append(dict(bundle=name, width=cw, flow=flow, peer=peer, fields=fields))
    miss = sorted(set(P) - set(used) - {'clk'})
    assert not miss, miss
    return P, rows
def cell_ports(rows):
    """the cell's RTL ports: per bundle one port of the bound same-direction bits [bound-1:0] (unbound bits are always
    the top or the whole bundle, except cbr0's low fault bits: cbr0 keeps its width, bits [2:0] unloaded inputs)."""
    out = []
    for r in rows:
        main = [f for f in r['fields'] if f['port'] and not f['against_flow']]
        ag = [f for f in r['fields'] if f['port'] and f['against_flow']]
        if main:
            hi = max(f['lsb'] + f['width'] for f in main)
            out.append((r['bundle'] if not ag and r['bundle'] != 'cc' else r['bundle'] + '_d', r['flow'], hi, main))
        for f in ag:
            out.append((r['bundle'] + '_cr', 'in' if r['flow'] == 'out' else 'out', 1, [dict(f, lsb=0)]))
    return out
def main():
    P, rows = build(); cp = cell_ports(rows)
    unb = [dict(bundle=r['bundle'], bits=[f['lsb'] + f['width'] - 1, f['lsb']], flow=r['flow'], peer=r['peer'])
           for r in rows for f in r['fields'] if f['port'] is None]
    if '--check' in sys.argv:
        print('OK', len(rows), 'bundles', sum(r['width'] for r in rows), 'contract bits', len(unb), 'unbound ranges'); return
    json.dump(dict(cell='qfd_seq_su', body='ot_qfd_seq_su_bi', body_params=PARAMS, order='LSB-first', clock='ck -> clk',
                   bundles=rows, unbound=unb, cell_ports=[dict(port=n, dir=d, width=w) for n, d, w, _ in cp]),
              open('physical/qwen_kv_slots/qfd_seq_su_pack.json', 'w'), indent=1)
    L = ['// GENERATED by physical/qwen_kv_slots/gen_seq_su_slot.py from its packing table (qfd_seq_su_pack.json): do not edit.',
         '// Qwen ROM TP8 slot cell qfd_seq_su (contract v3 slot seq_su, single instance): WIRING ONLY around the closed body',
         '// ot_qfd_seq_su_bi #(PSRAM=1, HQ2=1).  No flop added: every body port is a pin flop (IS = OS = 1 ot_hdc_delay).',
         '// Contract bits with no body port (ib, dflt, cbr1..7, cbr0[2:0], dc[529:56], dh[529:187], cc credit) are NOT ports.',
         '// OT_QFD_SEQ_SU_SLOT_MUT (bench mutant only): vwr bits 0 and 1 swapped.',
         'module qfd_seq_su (', '    input  wire ck,']
    L += [f"    {'input ' if d == 'in' else 'output'} wire [{w - 1}:0] {n}," for n, d, w, _ in cp if n != 'rsi']
    L += ['    input  wire rsi', ');']
    conn = {'clk': 'ck'}; asg = []
    for n, d, w, fs in cp:
        for f in fs:
            sl = f"{n}[{f['lsb'] + f['width'] - 1}:{f['lsb']}]" if w > 1 else n
            if n == 'rsi': conn['rst_n'] = 'rsi'
            elif d == 'in': conn[f['port']] = sl
            elif n.startswith('cbc') and n != 'cbc0': asg.append(f"    assign {n} = cbc0;") if f['lsb'] == 0 else None
            elif n == 'vwr':
                conn[f['port']] = 'w_' + f['port']
                if f['lsb'] == 0:
                    asg += [f"    wire [{P[x][1] - 1}:0] w_{x};" for x in ('vm_wdata', 'vm_waddr', 'vm_we')]
                    asg += ['`ifdef OT_QFD_SEQ_SU_SLOT_MUT', '    assign vwr = {w_vm_we, w_vm_waddr, w_vm_wdata[511:2], w_vm_wdata[0], w_vm_wdata[1]};',
                            '`else', '    assign vwr = {w_vm_we, w_vm_waddr, w_vm_wdata};', '`endif']
            else: conn[f['port']] = sl
    L += asg + ['    ot_qfd_seq_su_bi #(' + ', '.join(f'.{k}({v})' for k, v in PARAMS.items()) + ') u_body (']
    L += [',\n'.join(f'        .{p}({conn[p]})' for p in P), '    );', 'endmodule', '']
    open('rtl/physical/ot_qfd_seq_su_slot.sv', 'w').write('\n'.join(L))
    # bench shim: the body's port list around the slot cell (unpacks with the same table; unbound bits do not exist)
    S = ['// GENERATED by physical/qwen_kv_slots/gen_seq_su_slot.py: body-shaped view of slot cell qfd_seq_su for the lockstep bench.',
         'module qfd_seq_su_bodyview #(parameter integer PSRAM = 1, PMUT = 0, HQ2 = 1, RRG = 0, PCUT = 0, OLAG = 0) (']
    S += [',\n'.join(f"    {d} wire [{w - 1}:0] {n}" for n, (d, w) in P.items()), ');']
    for n, d, w, fs in cp:
        if n == 'rsi': continue
        S.append(f'    wire [{w - 1}:0] b_{n};')
        for f in fs:
            sl = f"b_{n}[{f['lsb'] + f['width'] - 1}:{f['lsb']}]"
            if n.startswith('cbc') and n != 'cbc0': continue
            S.append(f"    assign {sl} = {f['port']};" if d == 'in' else f"    assign {f['port']} = {sl};")
        if n == 'cbr0': S.append('    assign b_cbr0[2:0] = 3\'b0;')
    S += ['    qfd_seq_su u_slot (.ck(clk), .rsi(rst_n), ' + ', '.join(f'.{n}(b_{n})' for n, _, _, _ in cp if n != 'rsi') + ');',
          '    wire cbc_same = ' + ' && '.join(f'(b_cbc{k} === b_cbc0)' for k in range(1, 8)) + ';', 'endmodule', '']
    open('rtl/test/qfd_seq_su_slot_shim.sv', 'w').write('\n'.join(S))
    print('OK', len(rows), 'bundles;', len(cp), 'cell ports;', sum(w for _, _, w, _ in cp), 'cell port bits;', len(unb), 'unbound ranges')
main()
