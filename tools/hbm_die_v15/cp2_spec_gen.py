#!/usr/bin/env python3
"""cp2 spec maker: writes tools/hbm_die_v15/v16_specs/cp2.json and updates host_misc.json (owned by cp2)."""
import json, sys
from pathlib import Path
WT = Path(sys.argv[1])
SP = WT / 'tools/hbm_die_v15/v16_specs'
HS = 'rtl/hbm_accel/host_static_20261015/'
OWN = 'host owner (H-NETLIST cp2)'
Q = ['SW', 'SE', 'NW', 'NE']
inst, edges, clocks, straps, gaps = [], [], [], [], []

def E(src, dst, basis, clock='stream'):
    s, d = list(src), list(dst)
    bits = (s[3] - s[2]) if len(s) == 4 else None
    e = dict(src=s, dst=d, clock=clock, basis=basis)
    if bits is not None:
        e['bits'] = bits
    edges.append(e)

def clk(i, port, dom, kind='clock'):
    clocks.append(dict(inst=i, port=port, domain=dom, kind=kind))

COLLAR = dict(master='ot_hbm_static_cfg_collar', source=HS + 'ot_hbm_static_cfg_collar.sv')
P_SU = dict(PAGE_W=12, NS=1, NPR=1, NREC=0, NGO=1, NB=2, NF=1, XSER=1)
P_SFU = dict(PAGE_W=3, NS=2, NPR=1, NREC=0, NGO=1, NB=2, NF=1, XSER=0)
P_IDX = dict(PAGE_W=1, NS=1, NPR=6, NREC=8, NGO=2, NB=2, NF=4, XSER=0)
collars = [('col_su', 112, P_SU, 'serial', 'SU programme (ot_hbm_su_programme su_prog): linear row L=bank*128+row '
            '(bank=L[22:7], row=L[6:0]) via 12-b pages, so the 16-b bank / 7-b row ABI is fully representable on ONE '
            'target id; length16 = operand row 0 [15:0]; serial 3:4 domain behind the in-collar rational crossing')]
for k, q in enumerate(Q):
    collars.append((f'col_sfu_{q}', 116 + k, P_SFU, 'stream', f'SFU {q} (sfucore_{q}): space0 = arithmetic programme '
                    '{stripe3,addr11}, space1 = IO calendar {stripe2,addr11}; operand row 0 = start base/limit/loops '
                    '[38:0] and io_start base/limit/loops [77:39]; io_start_v = launch (the IO calendar starts the '
                    'arithmetic programme itself)'))
collars.append(('col_idx', 120, P_IDX, 'stream', 'IDX + TOPK + ARGMAX.LOCAL of the SW slice (hb_idx, hb_argmax): '
                'space0 = IDX programme (addr8); operand rows 0..5 = length/sectors/rank/gbase/nkeys/keep/die_id + '
                'keep_bitmap; record rows = TOPK descriptors (go[0]) and ARGMAX records (go[1]) on compiler offsets. '
                'ARGMAX shares this collar (target 121 not used): one launch domain, one SW slice, one fewer tile'))
for name, t, p, dom, note in collars:
    inst.append(dict(name=name, **COLLAR, params=p, slot=None, owner=OWN,
                     note=f'F20 target {t}. ' + note + '. Pin-registered: cfg->write 2 edges, launch->start 2 edges '
                          '(XSER: + crossing 2-3 serial edges, phase-fixed under the common epoch).'))
    straps.append(dict(inst=name, port='tgt', value=t, reason=f'identity: F20 target id {t} of this collar instance'))
    clk(name, 'clk', dom); clk(name, 'clk_in', 'stream'); clk(name, 'rst_n', dom, 'reset')
    for pt in ['cfg_v', 'cfg_target', 'cfg_addr', 'cfg_data', 'desc_v', 'launch_v']:
        E(['host_cp_ingress', pt], [name, pt], 'static ingress F20 broadcast (ot_hbm_host_static_ingress)')
# ---- SU
B = 'cp2 collar ABI (ot_hbm_static_cfg_collar.sv header)'
E(['col_su', 'pw_we', 0, 1], ['su_prog', 'cfg_we'], B, 'serial')
E(['col_su', 'pw_addr', 7, 23], ['su_prog', 'cfg_bank'], B, 'serial')
E(['col_su', 'pw_addr', 0, 7], ['su_prog', 'cfg_row'], B, 'serial')
E(['col_su', 'pw_data', 0, 256], ['su_prog', 'cfg_data'], B, 'serial')
E(['col_su', 'start_v', 0, 1], ['su_prog', 'start'], B, 'serial')
E(['col_su', 'prm', 0, 16], ['su_prog', 'length'], B, 'serial')
E(['su_prog', 'busy', 0, 1], ['col_su', 'c_busy', 0, 1], 'status', 'serial')
E(['su_prog', 'valid', 0, 1], ['col_su', 'c_busy', 1, 2], 'status', 'serial')
E(['su_prog', 'done', 0, 1], ['col_su', 'c_done'], 'status', 'serial')
E(['su_prog', 'fault', 0, 1], ['col_su', 'c_fault'], 'status', 'serial')
# ---- SFU
for q in Q:
    c, s = f'col_sfu_{q}', f'sfucore_{q}'
    for a, b in [(['pw_we', 0, 1], 'cfg_we'), (['pw_addr', 11, 14], 'cfg_stripe'), (['pw_addr', 0, 11], 'cfg_addr'),
                 (['pw_data', 0, 256], 'cfg_data'), (['prm', 0, 11], 'start_base'), (['prm', 11, 23], 'start_limit'),
                 (['prm', 23, 39], 'start_loops'), (['pw_we', 1, 2], 'io_cfg_we'), (['pw_addr', 11, 13], 'io_cfg_stripe'),
                 (['pw_addr', 0, 11], 'io_cfg_addr'), (['pw_data', 0, 256], 'io_cfg_data'), (['start_v', 0, 1], 'io_start_v'),
                 (['prm', 39, 50], 'io_start_base'), (['prm', 50, 62], 'io_start_limit'), (['prm', 62, 78], 'io_start_loops')]:
        E([c] + a, [s, b], B)
    E([s, 'programme_active', 0, 1], [c, 'c_busy', 0, 1], 'status')
    E([s, 'io_active', 0, 1], [c, 'c_busy', 1, 2], 'status')
    E([s, 'io_done', 0, 1], [c, 'c_done'], 'status')
    E([s, 'fault', 0, 1], [c, 'c_fault'], 'status')
# ---- IDX / TOPK / ARGMAX
for a, b in [(['pw_we', 0, 1], 'program_we'), (['pw_addr', 0, 8], 'program_addr'), (['pw_data', 0, 256], 'program_data'),
             (['start_v', 0, 1], 'start'), (['prm', 0, 12], 'length'), (['prm', 12, 28], 'weight_sector'),
             (['prm', 28, 44], 'query_sector'), (['prm', 44, 51], 'rank'), (['prm', 51, 59], 'gbase'),
             (['prm', 59, 73], 'nkeys'), (['prm', 73, 74], 'keep_en'), (['prm', 82, 1450], 'keep_bitmap'),
             (['go', 0, 1], 'topk_go'), (['rec', 0, 4], 'topk_k'), (['rec', 4, 5], 'topk_order'), (['rec', 5, 25], 'topk_n'),
             (['rec', 25, 45], 'topk_m'), (['rec', 45, 46], 'topk_a_mirror'), (['rec', 46, 64], 'topk_a_base'),
             (['rec', 64, 82], 'topk_a_str'), (['rec', 82, 83], 'topk_o_mirror'), (['rec', 83, 101], 'topk_o_base'),
             (['rec', 101, 119], 'topk_o_str'), (['rec', 119, 120], 'topk_has_r'), (['rec', 120, 138], 'topk_r_base'),
             (['rec', 138, 156], 'topk_r_str')]:
    E(['col_idx'] + a, ['hb_idx', b], B)
for a, b in [(['go', 1, 2], 'go'), (['rec', 0, 1], 'mode'), (['rec', 1, 19], 'imm_a'), (['rec', 19, 20], 'a_mirror'),
             (['rec', 20, 38], 'a_base'), (['rec', 38, 56], 'n'), (['rec', 56, 74], 'o_base'), (['rec', 74, 90], 'o_is'),
             (['prm', 74, 82], 'die_id')]:
    E(['col_idx'] + a, ['hb_argmax', b], B + '; die_id = host-configured die rank (operand row 0 [81:74]), same row as IDX rank')
E(['hb_idx', 'topk_busy', 0, 1], ['col_idx', 'c_busy', 0, 1], 'status')
E(['hb_argmax', 'busy', 0, 1], ['col_idx', 'c_busy', 1, 2], 'status')
E(['hb_idx', 'done', 0, 1], ['col_idx', 'c_done'], 'status')
for k, (i, p) in enumerate([('hb_idx', 'fault'), ('hb_idx', 'topk_fault'), ('hb_idx', 'share_fault'), ('hb_argmax', 'fault')]):
    E([i, p, 0, 1], ['col_idx', 'c_fault', k, k + 1], 'status')
# ---- host link adapter (PHY framing, reserved lanes, session pin)
inst.append(dict(name='host_phy', master='ot_hbm_host_phy_adapt', source=HS + 'ot_hbm_host_phy_adapt.sv', params={},
                 slot='host_N', owner=OWN, note='endpoint 487-b word <-> 512-b UCIe beat framer (reserved lanes zero / '
                 'checked), PHY status, host session pin flop; +1 edge each way on the elastic host link'))
clk('host_phy', 'clk', 'stream'); clk('host_phy', 'rst_n', 'stream', 'reset')
E(['host_cp_ep', 'x_tx', 0, 487], ['host_phy', 'ep_tx'], 'endpoint PHY word (was direct to host_N.tx[486:0])')
E(['host_phy', 'phy_tx', 0, 512], ['host_N', 'tx'], 'framed UCIe beat, reserved lanes [511:487] from the framer flop')
E(['host_N', 'rx', 0, 512], ['host_phy', 'phy_rx'], 'UCIe RX beat')
E(['host_N', 'st', 0, 2], ['host_phy', 'phy_st'], 'PHY status {live, rate-match fault}')
E(['host_phy', 'ep_rx', 0, 487], ['host_cp_ep', 'x_rx'], 'endpoint RX word')
E(['host_phy', 'session', 0, 24], ['host_cp_ep_face', 'f_lk_rx', 547, 571], 'host link session id (pin flop of the strap pads)')
# ---- status join
T = [('hb_quant_NW', 48, 'configured', 'program_active')] + \
    [(f'hb_coll_{q}', 52 + k, 'program_configured', 'hgi_busy') for k, q in enumerate(Q)] + \
    [('col_su', 112, 'ready', 'active')] + [(f'col_sfu_{q}', 116 + k, 'ready', 'active') for k, q in enumerate(Q)] + \
    [('col_idx', 120, 'ready', 'active')]
F = [('hb_quant_NW', 'fault')] + [(f'hb_coll_{q}', p) for q in Q for p in ('program_fault', 'hgi_fault', 'fault')] + \
    [('col_su', 'fault')] + [(f'col_sfu_{q}', 'fault') for q in Q] + [('col_idx', 'fault')]
H = [('host_cp_ingress', 'fault', 0), ('host_cp_packet', 'protocol_fault', 0), ('host_cp_landing', 'fault', 0),
     ('host_cp_ep_face', 'f_lk_tx', 547), ('host_phy', 'pad_fault', 0), ('host_phy', 'phy_fault', 0)]
tg = ''.join(f'{t:02x}' for _, t, _, _ in reversed(T))
inst.append(dict(name='host_status', master='ot_hbm_status_join', source=HS + 'ot_hbm_status_join.sv',
                 params=dict(NT=len(T), NF=len(F), NH=len(H), TGTS=f"{8 * len(T)}'h{tg}"), slot='host_cp_ingress', owner=OWN,
                 note='die status aggregation leaf: participation from the descriptor broadcast, block_ready = AND of '
                      'participants, active/fault OR, irq = programme complete; inputs ' +
                      ', '.join(f'{i}({t})' for i, t, _, _ in T) + '. cp1 targets 64..107 join via a second leaf of '
                      'this master + a root (TGTS 0 = always-participating child).'))
clk('host_status', 'clk', 'stream'); clk('host_status', 'rst_n', 'stream', 'reset')
for pt in ['cfg_v', 'desc_v', 'launch_v', 'cfg_target']:
    E(['host_cp_ingress', pt], ['host_status', pt], 'broadcast snoop for participation')
for k, (i, t, r, a) in enumerate(T):
    E([i, r, 0, 1], ['host_status', 't_ready', k, k + 1], f'target {t} readiness')
    E([i, a, 0, 1], ['host_status', 't_active', k, k + 1], f'target {t} active')
for k, (i, p) in enumerate(F):
    E([i, p, 0, 1], ['host_status', 't_fault', k, k + 1], 'target fault')
for k, (i, p, b) in enumerate(H):
    E([i, p, b, b + 1], ['host_status', 'h_fault', k, k + 1], 'host link fault')
E(['host_status', 'block_ready', 0, 1], ['host_cp_ingress', 'block_ready'], 'G-HOST-READY')
E(['host_status', 'program_active', 0, 1], ['host_cp_ingress', 'program_active'], 'G-HOST-READY')
E(['host_status', 'program_fault', 0, 1], ['host_cp_ingress', 'program_fault'], 'G-HOST-READY')
E(['host_status', 'die_fault', 0, 1], ['host_cp_packet', 'fault'], 'G-STATUS: die fault -> host status packet')
E(['host_status', 'irq', 0, 1], ['host_cp_packet', 'irq'], 'G-STATUS: programme complete -> host status packet')
# ---- packet static (re-mastered in host_misc): tx credit + flit
E(['host_cp_packet', 'f_send', 0, 1], ['host_cp_ep_face', 'f_lk_rx', 0, 1], 'G-HOST-TXCREDIT: credit-gated send')
E(['host_cp_packet', 'f_flit', 0, 545], ['host_cp_ep_face', 'f_lk_rx', 1, 546], 'G-HOST-PAD: full 545-b flit (reserved header from the packet flop)')
E(['host_cp_ep_face', 'f_lk_tx', 546, 547], ['host_cp_packet', 't_cr'], 'endpoint transmit credit return')
gaps.append(dict(id='G-HOST-SESSION', owner='H-DIE (die pins) + host owner', missing_rtl='die strap pads: host_phy.session_pad'
                 '[23:0] is the host link session id (off-die sideband, agreed by both link ends before any configuration '
                 'can cross the link). Needs DIE_PIN entry (ot_hbm_host_phy_adapt, ^session_pad$) in full_die_v16.py '
                 '(parent/VMSM-owned generator).', affects=[['host_phy', 'session_pad']],
                 note='closes when the generator declares the pad; no on-die producer is possible'))
cp2 = dict(region='cp2', author='Claude H-NETLIST sub-agent cp2 (host face + programme targets + status)',
           basis_commit='4b43cd77c', instances=inst, edges=edges, clocks=clocks, straps=straps, gaps=gaps,
           notes=['ingress TARGET_MASK (host_misc) admits 48, 52..55, 64..107 (cp1), 112, 116..120',
                  'collar row map: 0x000 programme (sequential per space), 0x800 operand rows, 0xC00 record rows, '
                  '0xE00 space/page select, 0xE01 install need + wait-done'])
(SP / 'cp2.json').write_text(json.dumps(cp2, indent=1) + '\n')
# ---------------- host_misc (owned): packet re-master, PHY path through host_phy, mask, closed gaps
hm = json.loads((SP / 'host_misc.json').read_text())
mask = (1 << 48) | sum(1 << t for t in range(52, 56)) | sum(1 << t for t in range(64, 108)) | (1 << 112) | \
    sum(1 << t for t in range(116, 121))
for i in hm['instances']:
    if i['name'] == 'host_cp_packet':
        i.update(master='ot_hbm_host_packet_static', source=HS + 'ot_hbm_host_packet_static.sv', params={},
                 note='STATIC successor of ot_hbm_host_packet (cp2): dynamic-loader faces h_*/h_dma_*/m_* retired '
                      '(ops 03/04/91..94 refused), credit-gated 545-b flit to the endpoint face, status packets from '
                      'host_status; pin-registered')
    if i['name'] == 'host_cp_ingress':
        i['params']['TARGET_MASK'] = f"256'h{mask:x}"
        i['note'] += ' | cp2: TARGET_MASK = 48, 52..55, 64..107 (cp1), 112 (SU), 116..119 (SFU), 120 (IDX+TOPK+ARGMAX)'
drop = lambda e: (e['src'][:2] == ['host_cp_ep', 'x_tx'] or e['dst'][:2] == ['host_cp_ep', 'x_rx'] or
                  e['src'][:2] == ['host_cp_packet', 'tx_packet'])
n0 = len(hm['edges']); hm['edges'] = [e for e in hm['edges'] if not drop(e)]
closed = {'G-HOST-TXCREDIT', 'G-HOST-PAD', 'G-HOST-LOADERFACE', 'G-HOST-READY', 'G-HOST-LOADER-OTHERS', 'G-STATUS',
          'G-HOST-SESSION'}
hm['gaps'] = [g for g in hm['gaps'] if g['id'] not in closed]
_n = ('cp2 2026-10-15: host face/status gaps G-HOST-TXCREDIT/PAD/LOADERFACE/READY/LOADER-OTHERS/STATUS closed by '
      'cp2.json (G-HOST-SESSION re-pointed there)')
if isinstance(hm.get('notes'), list): hm['notes'].append(_n)
else: hm['notes'] = (hm.get('notes') or '') + ' | ' + _n
(SP / 'host_misc.json').write_text(json.dumps(hm, indent=1) + '\n')
print(f'cp2: {len(inst)} instances, {len(edges)} edges; host_misc edges {n0}->{len(hm["edges"])}, mask {mask:x}')
