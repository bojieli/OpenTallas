#!/usr/bin/env python3
"""H-NETLIST 1815: d4c revision layer XQL (quadrant-local x read, H-SM 8d98d5225 / pegress x3 325202058) for full_die_v16.

Per quadrant Q the cl2 x-store (xl_Q_bfq0..3 + xl_Q_bd, one per quadrant, 2048-b xw broadcast to 8 SMs) is replaced by
NP = 4 PAIR stores, each = 4 BF quarters (ot_hgi_sm_xload_cl2_bfq) + the BD ring (ot_hgi_sm_xload_cl2_bdring) + the
pair-egress leaf (ot_hgi_sm_xload_xq_pegress), exactly ot_hgi_sm_xload_xq_pair (rtl/hbm_accel/generic/peers/
ot_hgi_sm_xload_static_xql.sv) flattened to die level.  xl_Q_ctl (folded ctlw) gets EGRESS_SPLIT=1 and multicasts the
ctl -> pair bundle (the XQL equal-age tree of depth T = the die relay stations of these buses: class equal_age_pad, every
pair the same depth); its own xw_* / x_done outputs become open and its rwq / bq_d inputs (unused under EGRESS_SPLIT=1,
tied 0 in the reference parent) are strapped 0 (H-SM: drop them from an EGRESS_SPLIT master).  Pair p drives SMs
PAIRS[p] (default 2p, 2p+1 as in the RTL; H-DIE may re-pair to the 2-row SM tile adjacency with --pairs).
Netlist only: no slot homes (H-DIE places from its d4c trial and re-runs relay_router).

    xql_layer.py --out tools/hbm_die_v15/v16_layers/xql_d4c.json [--pairs 0-1,2-3,4-5,6-7]
"""
import argparse, json
from pathlib import Path

Q = ('SW', 'SE', 'NW', 'NE')
SRC = 'rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_static_cl2.sv'
XQL = 'rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_static_xql.sv'
PMAX, NR = 8, 32
NBQ2 = 2 * ((PMAX * 3152 + 2047) // 2048)
BFQG = False
B = 'rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_static_xql.sv ot_hgi_sm_xload_static_xql / ot_hgi_sm_xload_xq_pair (XQL, H-SM 8d98d5225)'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--pairs', default='0-1,2-3,4-5,6-7')
    ap.add_argument('--bfqg', action='store_true', help='BF quarters = ot_hgi_sm_xload_cl2_bfqg (H-SM, native PASS)')
    a = ap.parse_args()
    global BFQG
    BFQG = a.bfqg
    pairs = [tuple(int(x) for x in p.split('-')) for p in a.pairs.split(',')]
    assert len(pairs) == 4 and sorted(s for p in pairs for s in p) == list(range(8)), pairs
    inst, edges, clocks, straps, remove, drop = [], [], [], [], [], []

    def E(src, dst, bits, note=''):
        edges.append(dict(src=src, dst=dst, bits=bits, clock='stream', basis=B + note))

    for q in Q:
        ctl = f'xl_{q}_ctl'
        remove += [f'xl_{q}_bfq{g}' for g in range(4)] + [f'xl_{q}_bd']
        drop += [[ctl, p] for p in ('xw_en', 'xw_last', 'xw_addr', 'xw_grp', 'xw_data', 'x_done')]
        straps += [dict(inst=ctl, port='rwq', value=0, reason='XQL EGRESS_SPLIT=1: input unused (reference parent ties 0)'),
                   dict(inst=ctl, port='bq_d', value=0, reason='XQL EGRESS_SPLIT=1: input unused (reference parent ties 0)')]
        for p, sms in enumerate(pairs):
            pre = f'xq_{q}_p{p}'
            sm_names = [f'sm_{q}{k}' for k in sms]
            for g in range(4):
                n = f'{pre}_bfq{g}'
                if BFQG:   # H-SM bfqg (native PASS, route hgi_sm_xl2_bfqg-local1r-a327f9402): bank-local mask captures,
                    # 8 identical mhi/mlo copies (the caller supplies them on the same compiled edge: one ctl pin, 8 loads)
                    inst.append(dict(name=n, master='ot_hgi_sm_xload_cl2_bfqg', source='rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_bfqg.sv',
                                     params={}, slot=None, owner='H-SM',
                                     note=f'XQL pair {p} ({"/".join(sm_names)}) BF16 quarter {g} (bfqg: view hgi_sm_xl2_bfqg)'))
                    clocks += [dict(inst=n, port=c_, domain='stream', kind='clock')
                               for c_ in ['clk', 'clk_n', 'clk_s', 'clk_ctrl'] + [f'clk_m{k}' for k in range(8)] + [f'clk_l{k}' for k in range(8)]]
                    for k in range(8):
                        E([ctl, 'c_mhi'], [n, f'mhi{k}'], 1); E([ctl, 'c_mlo'], [n, f'mlo{k}'], 1)
                    mports = ()
                else:
                    inst.append(dict(name=n, master='ot_hgi_sm_xload_cl2_bfq', source=SRC, params={}, slot=None, owner='H-SM',
                                     note=f'XQL pair {p} ({"/".join(sm_names)}) BF16 quarter {g} (kit hgi_sm_xl2_bfq)'))
                    clocks += [dict(inst=n, port='clk', domain='stream', kind='clock')]
                    mports = (('c_mhi', 'mhi', 1), ('c_mlo', 'mlo', 1))
                E([ctl, 'rn_o'], [n, 'rst_n'], 1, ' (rn through the tree)')
                for cp, bp, w in (('c_d', 'c_d', 1024), ('c_wa', 'wa', 7), ('r_ce', 'r_ce', 8), ('r_a', 'r_a', 7)) + mports:
                    E([ctl, cp], [n, bp], w)
                E([ctl, 'c_wce', g, g + 1], [n, 'wce'], 1)
            bd = f'{pre}_bd'
            inst.append(dict(name=bd, master='ot_hgi_sm_xload_cl2_bdring', source=SRC, params=dict(PMAX=PMAX, NR=NR),
                             slot=None, owner='H-SM', note=f'XQL pair {p} block-dot lane ring (kit hgi_sm_xl2_bdring)'))
            clocks.append(dict(inst=bd, port='clk', domain='stream', kind='clock'))
            for cp, bp, w in (('r_wsel', 'r_wsel', 16), ('zlo', 'zlo', 1), ('zhi', 'zhi', 1), ('bsel', 'bsel', NBQ2),
                              ('lane_en', 'lane_en_i', PMAX * 8)):
                E([ctl, cp], [bd, bp], w)
            for h in ('lo', 'hi'):
                E([f'xl_{q}_aq{h}', 'q'], [bd, f'qq_{h}'], 256)
                E([f'xl_{q}_aq{h}', 'e'], [bd, f'qe_{h}'], 10)
            eg = f'{pre}_eg'
            inst.append(dict(name=eg, master='ot_hgi_sm_xload_xq_pegress', source=XQL, params=dict(PMAX=PMAX, NR=NR),
                             slot=None, owner='H-SM', note=f'XQL pair {p} egress leaf (kit hgi_sm_xq_pegress x3 325202058, 369.36 sq)'))
            clocks.append(dict(inst=eg, port='clk', domain='stream', kind='clock'))
            E([ctl, 'rn_o'], [eg, 'rn'], 1)
            for cp, ep, w in (('eg_ed5', 'ed5', 8), ('eg_ede', 'ede', 17), ('eg_bqv', 'bq_v', 1), ('eg_bqlast', 'bq_last', 1),
                              ('eg_bqaddr', 'bq_addr', 7), ('eg_bqb', 'bq_b', 7)):
                E([ctl, cp], [eg, ep], w)
            for g in range(4):
                E([f'{pre}_bfq{g}', 'rwq'], [eg, 'rwq', 256 * g, 256 * g + 256], 256)
            E([bd, 'bq_d'], [eg, 'bq_d'], 2048)
            for sm in sm_names:
                for xp, w in (('xw_en', 1), ('xw_addr', 7), ('xw_grp', 7), ('xw_data', 2048)):
                    E([eg, xp], [sm, xp], w)
    spec = dict(region='xql_d4c', author='Claude H-NETLIST 1815', basis_commit='H-SM XQL 8d98d5225 + pegress x3 325202058',
                instances=inst, edges=edges, clocks=clocks, straps=straps, remove_instances=remove, drop_edges=drop,
                param_override={f'xl_{q}_ctl': dict(EGRESS_SPLIT=1) for q in Q}, gaps=[],
                notes=__doc__.split('\n\n')[1], pairs=pairs)
    a.out.write_text(json.dumps(spec, indent=1) + '\n')
    print('XQL_LAYER', len(inst), 'instances', len(edges), 'edges', len(remove), 'removed', 'pairs', pairs)


if __name__ == '__main__':
    main()
