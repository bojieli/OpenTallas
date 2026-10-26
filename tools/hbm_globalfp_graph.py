#!/usr/bin/env python3
"""GLOBAL-FP-H: block-level data-flow graph of the HBM accelerator die (v15/v15.1 contract + system graph).

Nodes are die-level blocks at the granularity a global floorplan decides (SM frame, PC group, VM bank+LG chain,
engine port-group slice, COLL, SerDes/endpoint, ATT tile/gather/Q-P field, IDX parts, PHY).  Every node carries
its outline and area_src (actual = source LEF/outline/spec; estimate = stated rule).  Every link carries the
die-level bit width (from the RTL port lists recorded in the v15.1 contract / global_graph, or an explicit
estimate), bytes per token for Qwen3-8B TP4 @8K and DeepSeek-V4.1-Flash TP96 @1M (compiled HGI-1 programs,
operand n*m*fmt per record, loop-expanded) and a criticality = token-path critical share of the owning class.

Writes graph.json (schema opentallas.dataflow.links.v1 without coordinates).
"""
import argparse, collections, hashlib, json, math, os

QS = ['SW', 'SE', 'NW', 'NE']          # stack order 0..3 (dbk STK param, SM stack = SM//8)
NPG = {'SW': 5, 'SE': 5, 'NW': 4, 'NE': 4}   # v15.1 engine_lg_port_group_rule
BANK_GROUP5 = [0, 0, 1, 1, 2, 2, 3, 4]       # H-ELEM-B proposal 32'h43221100 (SW/SE)
SZ = {'FP32': 4, 'BF16': 2, 'U32': 4, 'FP4E2M1': 0.5, 'FP8E4M3': 1, 'UE8M0': 1, 'INT8': 1}
UM2_PER_FF = 2.35     # estimate: D drain mapped 31,942.5 um2 / 24,757 FF = 1.29 um2 per FF incl. logic, at 55% util


def bank_group(q, b):
    return BANK_GROUP5[b] if NPG[q] == 5 else b // 2


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def program_bytes(path, loop_n):
    R = json.load(open(path))['records_listing']
    agg = collections.defaultdict(float)
    inloop = False
    for r in R:
        if r['op'] == 'LOOP':
            inloop = True; continue
        if r['op'] == 'ENDLOOP':
            inloop = False; continue
        mult = loop_n if inloop else 1
        for slot, o in (r.get('opnd') or {}).items():
            b = o['n'] * max(1, o['m']) * SZ[o['fmt']] * mult
            agg[(r['unit'], r['op'], slot, o['space'])] += b
    return agg


def class_traffic(agg, wl):
    """Per-token bytes per die-level flow class (sum over records). Rules are stated in RULES."""
    def s(unit=None, op=None, slot=None, space=None):
        return sum(v for (u, o, sl, sp), v in agg.items()
                   if (unit is None or u in unit) and (op is None or o in op)
                   and (slot is None or sl in slot) and (space is None or sp == space))
    T = {}
    T['SM_hbm'] = s(('SM',), None, ('B',), 'HBM')
    T['SM_x'] = s(('SM',), None, ('A',), 'VM')                 # per SM (x is read by every SM)
    T['SM_out'] = s(('SM',), None, ('O',), 'VM') + s(('SM',), None, ('O',), 'STREAM')
    T['SU_vm'] = s(('SU',), None, None, 'VM') + s(('FUSED',), ('HC_PRE_NORM', 'HC_POST', 'ROW_NORM'), None, 'VM')
    T['SFU_vm'] = s(('SFU',), None, None, 'VM')
    T['HC_vm'] = s(('HC',), None, None, 'VM')
    T['QUANT_vm'] = s(('FUSED',), ('QDQ_FP8',), None, 'VM')
    T['HBM_to_vm'] = (s(('DMA',), ('LOAD',), None, 'HBM') + s(('FUSED',), None, None, 'HBM')
                      + s(('HC',), None, None, 'HBM'))
    T['VM_to_hbm'] = s(('DMA',), ('KVWB_DS', 'STORE'), ('O',), 'HBM')
    T['DMA_vm'] = s(('DMA',), None, None, 'VM')
    T['COLL_vm'] = s(('COLL',), None, None, 'VM')
    T['COLL_offdie'] = s(('COLL',), None, ('O',), 'VM') + s(('COLL',), None, ('O',), 'HBM')
    T['ATT_q'] = s(('ATT',), ('QK',), ('A',), 'VM') + s(('ATT',), ('PV',), ('A',), 'VM')
    T['ATT_o'] = s(('ATT',), ('PV',), ('O',), 'VM') + s(('ATT',), ('QK',), ('O',), 'VM')
    T['IDX_vm'] = s(('IDX',), None, None, 'VM')
    # KV rows are descriptors in the program (n*m is not the row volume): model-derived volume
    if wl == 'ds':
        T['KV_hbm'] = 40 * 640 * 8480 / 8          # 40 layers x T640 (512 top-k + 128 window) x 8480-bit row
        T['ATT_intra_scale'] = 40.0                 # T640 invocations per token (SYSTEM_GRAPH activity is per T640)
    else:
        T['KV_hbm'] = 36 * 2 * 2 * 8192 * 128 * 1   # 36 layers x 2 KV heads/die x K,V x 8K ctx x 128 x FP8
        T['ATT_intra_scale'] = 40.0 * T['KV_hbm'] / (40 * 640 * 8480 / 8)
    return T


RULES = {
    'SM_hbm': 'SM.MATVEC B(HBM) bytes / 32 SMs; each SM reads its own stack (stack=SM//8, PCs 4*(SM%8)..+3)',
    'SM_x': 'SM.MATVEC A(VM) bytes per SM (every SM loads the full x); x replicated per quadrant VM, read over 8 banks',
    'SU_vm': 'SU.VOP + FUSED norm/HC_PRE/HC_POST VM operands, SPMD over 4 quarters, 8 banks via LG near tap',
    'KV_hbm': 'model-derived row volume (program carries a descriptor): DS 40 x 640 x 8480 b; Qwen 36 x 2 x 2 x 8K x 128 B',
    'COLL': 'COLL VM operands per quarter; off-die = O bytes split over 9 links by link count; ring = 4 hop-bytes per byte / 8 directed links',
    'ATT_intra': 'SYSTEM_GRAPH T640 activity (Q 131,072 B, P 2,621,440 B, K|V 2,949,120 B/phase, PV fill 678,400 B, out 32,768 B) x invocations; Qwen scaled by KV volume',
}


ATT_SM_RULES = {
    'KV': 'attention on SM (owner adoption 10-15, H-ATTQ B): KV rows stream PHY -> PC -> SM on the existing SM HBM port like '
          'weights; QK and PV each stream the row set (KV_hbm already counts both). kv_home=stack_local: dense rows are '
          'sequence-sliced to the SM whose stack holds them (token t -> SM t%32), DS top-k rows are rank-assigned (rank r -> SM r%32) '
          'and the compressed KV is replicated in all four stacks so every SM reads its rows from its own stack (+3 row writes per '
          'layer per token, +3x KV capacity); kv_home=interleave: one copy, top-k rows read across quadrants over the VM ring',
    'SCORES': 'partial scores out of each SM (FP32, heads x rows), softmax on SU (read scores, write P), P back to the SM on the '
              'x-load port, PV partial outputs back to VM and reduced by SU: Qwen 8 q heads x 8192 x 4 B x 36, DS 16 x 640 x 4 B x 40',
    'DESC': 'KV prefetch descriptors (row ids from window + IDX top-k) read by each SM from its quadrant VM hub: 4 B per row',
}


def attention_on_sm(G, TQ, TD, crit, kv_home):
    """B = attention on the SM matvec engines + SU softmax (no ATT tiles)."""
    sc = {'qwen': 8 * 8192 * 4 * 36, 'ds': 16 * 640 * 4 * 40}          # scores FP32 per token (P has the same volume)
    desc = {'qwen': 0.0, 'ds': 40 * 640 * 4}
    kvw = {'qwen': 0.0, 'ds': 40 * 8480 / 8 * 3 if kv_home == 'stack_local' else 0.0}   # 3 extra replica row writes / layer
    xring = {'qwen': 0.0, 'ds': TD['KV_hbm'] * 0.75 if kv_home == 'interleave' else 0.0}
    c = crit('ATT', 'SM')
    for l in G['links']:
        q, d = l['bytes_per_token']['qwen'], l['bytes_per_token']['ds']
        if l['cls'] in ('SM_HBM', 'HBM_K'):
            q += TQ['KV_hbm'] / 32; d += TD['KV_hbm'] / 32 * (0.25 if kv_home == 'interleave' else 1.0)
            l['provenance'] += ' | attention on SM: + KV rows/32 (stack-local)'
            l['criticality'] = max(l['criticality'], c)
        elif l['cls'] == 'SM_X':
            q += TQ['ATT_q'] / 8; d += TD['ATT_q'] / 8   # program A operands (q + P), every SM reads all: upper bound
            l['provenance'] += ' | attention on SM: + q (broadcast) and P (own rows) on the x-load port'
        elif l['cls'] == 'SM_OUT':
            q += (sc['qwen'] + TQ['ATT_o'] * 32) / 32; d += (sc['ds'] + TD['ATT_o'] * 32) / 32
            l['provenance'] += ' | attention on SM: + partial scores and PV partials'
        elif l['cls'] == 'LG_SU':
            q += (3 * sc['qwen'] + TQ['ATT_o'] * 32) / 32; d += (3 * sc['ds'] + TD['ATT_o'] * 32) / 32
            l['provenance'] += ' | attention on SM: + softmax (scores in, P out) and PV partial reduction on SU'
        elif l['cls'] == 'VM_HBM':
            d += kvw['ds'] / 32
        elif l['cls'] == 'VM_RING':
            d += xring['ds'] / 8
        l['bytes_per_token']['qwen'], l['bytes_per_token']['ds'] = round(q, 1), round(d, 1)
    for qn in QS:
        for j in range(8):
            G['links'].append(dict(id=f'vmh_{qn}>sm_{qn}{j}:KV_DESC', src=f'vmh_{qn}', dst=f'sm_{qn}{j}', cls='KV_DESC', bits=64,
                                   bytes_per_token={'qwen': 0.0, 'ds': round(desc['ds'] / 32, 1)}, criticality=round(c, 4),
                                   provenance='NEW SM port (estimate 64 b): KV prefetch descriptor stream from the quadrant hub (H-ATTQ change 5)',
                                   rule='DESC', fixed_return=False))
    G['attention'] = dict(mode='sm', kv_home=kv_home, rules=ATT_SM_RULES,
                          freed='ATT tiles, gathers, Q/P fields, reduction, ATT control, attention RG/WG, LG ATT groups, PV return (H-ATTQ: 111.1 mm2 / ~161 W on v14)')


def build(args):
    G = {'nodes': {}, 'links': []}
    N = G['nodes']

    def node(i, kind, w, h, area_src, q=None, fixed=False, prov='', area_mm2=None):
        N[i] = dict(id=i, kind=kind, quadrant=q, w=round(w, 3), h=round(h, 3),
                    area_mm2=round(area_mm2 if area_mm2 is not None else w * h / 1e6, 4),
                    area_src=area_src, fixed=fixed, provenance=prov)

    links = G['links']

    def link(src, dst, cls, bits, tq, td, crit, prov, rule=None, fixed_return=False):
        links.append(dict(id=f'{src}>{dst}:{cls}', src=src, dst=dst, cls=cls, bits=int(round(bits)),
                          bytes_per_token={'qwen': round(tq, 1), 'ds': round(td, 1)}, criticality=round(crit, 4),
                          provenance=prov, rule=rule, fixed_return=fixed_return))

    # ---------------- traffic
    aq = program_bytes(args.qwen_prog, 36)
    ad = program_bytes(args.ds_prog, 1)
    TQ, TD = class_traffic(aq, 'qwen'), class_traffic(ad, 'ds')
    tpq, tpd = json.load(open(args.qwen_tp)), json.load(open(args.ds_tp))
    share = collections.defaultdict(float)
    for tp in (tpq, tpd):
        for c in tp['totals']['by_class']:
            share[c['cls']] = max(share[c['cls']], c['share'])
    crit = lambda *cls: max(share.get(c, 0.0) for c in cls)
    t = lambda k, f=1.0: (TQ[k] * f, TD[k] * f)

    # ---------------- nodes
    vm_dims = {'SW': (356.4, 365.04), 'SE': (356.4, 365.04), 'NW': (393.12, 339.12), 'NE': (393.12, 339.12)}
    LGW, LGH = 3 * 150.336, 151.2
    for qi, q in enumerate(QS):
        node(f'phy_{q}', 'PHY', 8500.056, 1177.2, 'actual', q, True, 'ot_hbm3e_phy_v41x_aw30_e8p5 LEF (PHY+controller K-port abstract)')
        for j in range(8):
            node(f'pc_{q}{j}', 'PC', 4 * 259.2, 345.6 + 54.0, 'actual+estimate', q, False,
                 '4 x native PC 259.2x345.6 (340cfd747 spec) + 4 x svc burst owner/bank/128x256 SRAM (estimate 0.0139 mm2/PC)')
            node(f'sm_{q}{j}', 'SM', 6609.6, 1712.08, 'actual', q, False, 'complete35 SM frame 11.316 mm2 (R0/MX/MY/R180 only)')
        bw, bh = vm_dims[q]
        for b in range(8):
            node(f'vmb_{q}{b}', 'VM_bank', bw + 5.4 + LGW, max(bh, LGH), 'actual', q, False,
                 f'VM bank {"RG7/WG3" if bh < 340 else "RG5/WG1"} {bw}x{bh} + LG su10/sfu14/hc18 leaf chain 3x150.336x151.2 (closed leaf), adopted W-side chain')
        node(f'vmh_{q}', 'VM_hub', 900, 900, 'estimate', q, False,
             'hub + 2 ringstops + replay + calendar + delivery + status + DMA-back (no views; 0.81 mm2 estimate)')
        for eng, area, src in (('su', 0.2836, 'actual prototypes K0 216^2 + K1/K2 302.4^2 + 6-reader bank 368.8x146.4'),
                               ('sfu', 0.5599, 'actual SFU side6 source outline 864x648'),
                               ('hc', 0.2500, 'actual HC combined shell request 500.04^2 (tap client; arithmetic engine separate)')):
            n = NPG[q]
            side = math.sqrt(area / n) * 1000
            for k in range(n):
                node(f'{eng}_{q}{k}', eng.upper(), side, side, 'actual/split', q, False,
                     f'{src}; split into {n} bank-pair port groups (v15.1 engine_lg_port_group_rule)')
        node(f'coll_{q}', 'COLL', 670, 670, 'estimate', q, False,
             'COLL host V3 (109/69 roots) + quarter bridge 31,228 FF x 2.35 um2; 0.45 mm2 estimate')
    for k in range(4):
        node(f'quant_NW{k}', 'QUANT', 245, 245, 'estimate', 'NW', False,
             'QUANT hb_quant_NW ot_hgi_qdq_host_static RL7/WC4/COMPACT1 (quadrant_abi sid 2, NW RG4/WG2), 4 bank-pair groups, 0.06 mm2 each estimate')
    node('hc_eng', 'HC_ENGINE', 1000, 1000, 'estimate', 'NE', False, 'HC_ENGINE proposed single NE engine (kernel join open), 1.0 mm2 estimate')
    links_per_q = {'SW': ['S0', 'S1', 'S2'], 'SE': ['S3', 'S4'], 'NW': ['N0', 'N1'], 'NE': ['N2', 'N3']}
    for q, L in links_per_q.items():
        for l in L:
            node(f'lk_{l}', 'SERDES', 250.056, 2250.216, 'actual', q, False, 'ot_pdie_serdes LEF (S5/N4 shoreline, package wiring open)')
            node(f'ep_{l}', 'ENDPOINT', 434.72, 515.2, 'actual(planning)', q, False, 'ot_hgi_coll_static_link_capture group reservation (FEC/PMA 544/512 open)')
    if args.attention == 'att':
      # ATT (D local PV): tile = 4 quads 2x2 + 64 PV 32x128 SRAMs + 18,432 transposer FF + 512 flags + 1 KV code SRAM
      tile_w = 2 * 514.89
      tile_h = 2 * 562.95 + (64 * 51.408 * 20.79 + 18944 * 1.0 + 174.744 * 70.488) / tile_w
      for g in range(32):
        node(f'att_t{g}', 'ATT_tile', tile_w, tile_h, 'actual+estimate', None, False,
             'quad LEF 514.89x562.95 x4 + D 64 PV SRAM + KV code SRAM (actual) + transposer/flag FF at 1.0 um2/bit (estimate)')
      for f in range(4):
        node(f'att_g{f}', 'ATT_gather', 500, 450, 'planning', None, False, 'registered gather adf0ef9d5 pin-first envelope 500x450')
        node(f'att_qp{f}', 'ATT_QP', 420, 420, 'actual+estimate', None, False, '16 Q + 128 P 32x128 SRAM (actual) + P4 logic/4 (mapped)')
      node('att_red', 'ATT_reduce', 700, 700, 'estimate', None, False, 'QK lane/head reduction trees + softmax (unplaced in D), 0.49 mm2 estimate')
      node('att_ctl', 'ATT_ctl', 450, 300, 'actual+estimate', None, False, 'programme 1024x256 + 2 KV metadata SRAM + instruction/mode34 guard')
    for p, a in (('op', 0.10), ('q', 0.20), ('s0', 0.25), ('s1', 0.25), ('s2', 0.25), ('s3', 0.25), ('sel', 0.10), ('link', 0.10)):
        side = math.sqrt(a) * 1000
        node(f'idx_{p}', 'IDX', side, side, 'estimate', 'SW', False, 'ot_hbm_idx_scheduled_static part (2198 clock inputs, no view); area estimate')

    # ---------------- links
    for qi, q in enumerate(QS):
        for j in range(8):
            tq, td = t('SM_hbm', 1 / 32)
            # HBM read stream: PHY K port -> PC group -> SM
            link(f'phy_{q}', f'pc_{q}{j}', 'HBM_K', (1120 + 1368) * 4 / 4.5, tq, td, crit('SM'),
                 'v15.1 phy->svc 1120 b + svc->phy 1368 b per 4-PC band (scaled to 4 PCs)', 'SM_hbm')
            link(f'pc_{q}{j}', f'sm_{q}{j}', 'SM_HBM', 1088 + 44, tq, td, crit('SM'),
                 'SM rsp_data 1088 + req 44 (global_graph SM frame ports)', 'SM_hbm')
            sq, sd = t('SM_out', 1 / 32)
            link(f'sm_{q}{j}', f'vmh_{q}', 'SM_OUT', 256 + 14, sq, sd, crit('SM'), 'SM rdata 256 + rrow/rv', 'SM_out')
            xq, xd = t('SM_x', 1 / 8)
            for b in range(8):
                link(f'vmb_{q}{b}', f'sm_{q}{j}', 'SM_X', 256 + 17, xq, xd, crit('SM'),
                     'vms rr -> SM xw_data 2048 = 8 banks x 256 (+rq 17)', 'SM_x')
            hq, hd = t('HBM_to_vm', 1 / 32)
            link(f'pc_{q}{j}', f'vmh_{q}', 'HBM_VM', 256, hq, hd, crit('DMA'), 'svc out_data 256 b per PC band -> delivery (estimate)')
            wq, wd = t('VM_to_hbm', 1 / 32)
            link(f'vmh_{q}', f'pc_{q}{j}', 'VM_HBM', 256, wq, wd, crit('DMA'), 'writeback k_wdata (estimate share)')
        for b in range(8):
            dq, dd = TQ['HBM_to_vm'] / 4 / 8 + TQ['SM_out'] / 4 / 8, TD['HBM_to_vm'] / 4 / 8 + TD['SM_out'] / 4 / 8
            link(f'vmh_{q}', f'vmb_{q}{b}', 'VM_HUB', 281 + 257, dq, dd, crit('DMA'), 'delivery kq 2248/8 + hub/replay read 257 per bank')
            k = bank_group(q, b)
            for eng, key, cls in (('su', 'SU_vm', 'SU'), ('sfu', 'SFU_vm', 'SFU'), ('hc', 'HC_vm', 'HC')):
                eq, ed = t(key, 1 / 32)
                link(f'vmb_{q}{b}', f'{eng}_{q}{k}', f'LG_{cls}', 258 + 298, eq, ed, crit(cls, 'FUSED'),
                     'LG split 556-bit faces per bank (rr 257 + rq/wq/w_done) v15.1 lg<->engine', key, fixed_return=True)
            cq, cd = t('COLL_vm', 1 / 32)
            link(f'vmb_{q}{b}', f'coll_{q}', 'COLL_VM', 257 + 281 + 17, cq, cd, crit('COLL'), 'COLL vm_rq 136/rr 2056/kq 2248 over 8 banks')
        for eng, key, cls in (('su', 'SU_vm', 'SU'), ('sfu', 'SFU_vm', 'SFU'), ('hc', 'HC_vm', 'HC')):
            for k in range(1, NPG[q]):
                eq, ed = t(key, 0.25 / NPG[q] / 4)
                link(f'{eng}_{q}{k}', f'{eng}_{q}0', f'{cls}_CORE', 256, eq, ed, crit(cls, 'FUSED'),
                     'engine-internal port-group <-> core (estimate 256 b, 25% of slice traffic)')
        hq, hd = t('HC_vm', 1 / 4)
        link(f'hc_{q}0', 'hc_eng', 'HC_ENG', 512, hq, hd, crit('FUSED'), 'HC tap client -> single NE HC engine (estimate 512 b)')
        # collective: endpoints, serdes, ring
        L = links_per_q[q]
        oq, od = t('COLL_offdie', 1 / 9)
        for l in L:
            link(f'coll_{q}', f'ep_{l}', 'COLL_EP', 612 * 2, oq, od, crit('COLL'), 'tx/rx_pin_flit 1836 = 3 x 612 per link, both directions')
            link(f'ep_{l}', f'lk_{l}', 'EP_SERDES', 544 + 512, oq, od, crit('COLL'), 'FEC 544 coded / SerDes 512 TX+RX (gearbox open)')
    ring = [('SW', 'SE'), ('SE', 'NE'), ('NE', 'NW'), ('NW', 'SW')]
    for a, b in ring:
        for s, d in ((a, b), (b, a)):
            rq, rd = TQ['COLL_offdie'] * 4 / 8, TD['COLL_offdie'] * 4 / 8
            link(f'coll_{s}', f'coll_{d}', 'COLL_RING', 280 + 546, rq, rd, crit('COLL'), 'pr_cw/ccw 280 + quarter-bridge seam 546 per direction')
            link(f'vmh_{s}', f'vmh_{d}', 'VM_RING', 2224, TQ['COLL_vm'] / 8, TD['COLL_vm'] / 8, crit('COLL'),
                 'hb_vms ring stop 2224 b per direction; x replica / cross-quarter VM = COLL VM bytes / 8 links (estimate)')
    # QUANT on NW banks (hb_vms_NW read group 'quant' RG4 / write group WG2)
    for b in range(8):
        k = bank_group('NW', b)
        qq, qd = t('QUANT_vm', 1 / 8)
        link(f'vmb_NW{b}', f'quant_NW{k}', 'QUANT_VM', 257 + 281 + 17, qq, qd, crit('FUSED'), 'QUANT NW RG4/WG2 bank-pair port group', fixed_return=True)
    # IDX on SW RG4
    iq, idd = t('IDX_vm', 1 / 8)
    for b in range(8):
        link(f'vmb_SW{b}', 'idx_op', 'IDX_VM', 257 + 17, iq, idd, crit('IDX'), 'IDX operand vm_rq 136 / vm_rr 2056 over 8 SW banks')
    link('idx_op', 'idx_q', 'IDX_INT', 1048, iq * 8, idd * 8, crit('IDX'), 'literal parent IDX_operand->IDX_query 1048')
    for s in range(4):
        link('idx_q', f'idx_s{s}', 'IDX_INT', 569, iq * 2, idd * 2, crit('IDX'), 'IDX_query->score 2276/4')
        link(f'idx_s{s}', 'idx_sel', 'IDX_INT', 592, iq, idd, crit('IDX'), 'score field selection 37x16')
    link('idx_sel', 'idx_link', 'IDX_INT', 2372, iq, idd, crit('IDX'), 'selector->topk link')
    link('idx_link', 'coll_SW', 'IDX_COLL', 2180, iq, idd, crit('IDX', 'COLL'), 'topk link tx 2180 -> COLL del_flit 2180')
    if args.attention == 'att':
        # ATT (D local PV): field f = tiles g%4 == f, NE bank pair f
        s_q = TQ['ATT_intra_scale']; s_d = TD['ATT_intra_scale']
        for f in range(4):
            for b in (2 * f, 2 * f + 1):
                aq_, ad_ = t('ATT_q', 1 / 8)
                link(f'vmb_NE{b}', f'att_qp{f}', 'ATT_Q', 257 + 17, aq_, ad_, crit('ATT'), 'ATT query front lg_read_group x4 on NE bank pairs (RG3)')
                oq_, od_ = t('ATT_o', 1 / 8)
                link(f'att_g{f}', f'vmb_NE{b}', 'ATT_O', 512 + 16, oq_, od_, crit('ATT'), 'registered gather: WG1 2048 data + 64 flags over 4 bank pairs = 512+16 per bank, both banks of the pair')
            link('att_red', f'att_qp{f}', 'ATT_P', 1024, 2621440 / 4 / 8 * s_q * 0.25, 2621440 / 4 / 8 * s_d * 0.25, crit('ATT'), 'softmax P -> field P store (estimate)')
        for g in range(32):
            f = g % 4
            stk = QS[g % 4]
            kq, kd = TQ['KV_hbm'] / 32, TD['KV_hbm'] / 32
            link(f'pc_{stk}{(g // 4) % 8}', f'att_t{g}', 'KV', 265, kq, kd, crit('ATT'),
                 'KV_multistack 8480 b = 32 groups x 265 b; group g from stack g%4 (current interleave; source UNJOINED)')
            for src in (g // 2, 16 + g // 2):
                if src != g:
                    link(f'att_t{src}', f'att_t{g}', 'ATT_KVX', 265, kq, kd, crit('ATT'),
                         'PV tile g reads both lanes group g/2 from code SRAMs g/2 and 16+g/2 (grouped staging 9cf430e13)')
            link(f'att_qp{f}', f'att_t{g}', 'ATT_QP', 1024, (131072 + 2621440) / 32 * s_q, (131072 + 2621440) / 32 * s_d, crit('ATT'),
                 'p_word 1024 / query SL slice to field tiles (Q+P quad-port bytes / 32)')
            link(f'att_t{g}', 'att_red', 'ATT_SC', 512, 640 * 16 * 4 * s_q / 32, 640 * 16 * 4 * s_d / 32, crit('ATT'),
                 'partial scores 16 heads x 32 b per tile (estimate)')
            link(f'att_t{g}', f'att_g{f}', 'ATT_PV', 528, 32768 / 32 * s_q, 32768 / 32 * s_d, crit('ATT'),
                 'D local selector 512 + 16 flags per tile into group 8:1 mux')
            link('att_ctl', f'att_t{g}', 'ATT_CTL', 64, 0, 0, crit('ATT'), 'instruction/mode broadcast (estimate)')
    if args.attention == 'sm':
        attention_on_sm(G, TQ, TD, crit, args.kv_home)
    G['traffic_classes'] = {'qwen': TQ, 'ds': TD}
    G['class_critical_share'] = dict(share)
    G['rules'] = RULES
    G['inputs'] = {k: {'path': p, 'sha256': sha(p)} for k, p in
                   (('qwen_program', args.qwen_prog), ('ds_program', args.ds_prog), ('qwen_token_path', args.qwen_tp), ('ds_token_path', args.ds_tp))}
    G['unknowns'] = [
        'SM tile parent pins unassigned (top-down pin assignment open): link length = closest-point Manhattan gap between outlines',
        'Engine/VM hub/COLL/IDX/QUANT/HC engine areas are estimates (no physical views); ATT reduction tree unplaced in D',
        'KV home mapping is not source-bound (KV_multistack_service UNJOINED); attention-on-SM assumes the stated kv_home layout',
        'SM attention modes (PV accumulate, BF16 x with FP8/FP4 W, GQA multi-x, KV descriptor port) are not in RTL yet (H-ATTQ changes 1-5)',
        'x replication across quadrants assumed (SU replica words); cross-quadrant traffic carried on VM ring',
        'SerDes shoreline/package contract open; PHY command-level successor and 544/512 gearbox open',
        'clock trees, PG, halos beyond 20 um, HOST/CP loader and ckgen not modelled',
    ]
    return G


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--qwen-prog', required=True); ap.add_argument('--ds-prog', required=True)
    ap.add_argument('--qwen-tp', required=True); ap.add_argument('--ds-tp', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--attention', choices=('att', 'sm'), default='sm', help='sm = owner-adopted attention on SM engines (no ATT tiles)')
    ap.add_argument('--kv-home', choices=('stack_local', 'interleave'), default='stack_local')
    a = ap.parse_args()
    G = build(a)
    json.dump(G, open(a.out, 'w'), indent=1)
    A = collections.Counter(); S = collections.Counter()
    for n in G['nodes'].values():
        A[n['area_src'].split('+')[0].split('/')[0].split('(')[0]] += n['area_mm2']
    print(len(G['nodes']), 'nodes', len(G['links']), 'links', 'area', {k: round(v, 2) for k, v in A.items()}, round(sum(A.values()), 2))
    for l in G['links']:
        S[l['cls']] += l['bits']
    print(dict(S))
