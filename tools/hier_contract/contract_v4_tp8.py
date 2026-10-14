#!/usr/bin/env python3
"""qwen-tp8 contract v4 (2026-10-13): the answers to the open SLOT_CHANGE_REQUESTs on qwen_rom_tp8 v3, as one
re-runnable transformation of the derived contract (derive_tp8.py calls apply() for --version >= 4, so a re-derivation
from a regenerated case reproduces v4; every step is idempotent).

    contract_v4_tp8.py --in V3.json --out V4.json [--regen REGEN.json] [--case CASE --regen-out REGEN.json]
    contract_v4_tp8.py --check V4.json            schema + slot overlap + pin span fit + seam widths, exit 1 on a FAIL

Deltas (lead decisions, el1011-qwen-tp8.log 2026-10-13):
  T7  qfd_cst_s/n, qfd_chead_e/w: every bundle x[508:0] -> x_d[507:0] (with the flow) + x_r (against it) on the same
      face, rst_n on N beside ck; heads 323 -> 509 bits (D5); span_um from the pin count at 2 tracks
  T8  qkd_cdc_wleaf: outline 183.6 x 183.6 (same origin), the real RTL ports on the bundle faces / layers
  T9  qkd_rhead: hardened-once cluster, option (A) outline 691.2 x 453.6 (+43.2 um centre N-S relay channel)
  T10 qfd_sp_vector_memory: REGION of hardened leaves 4708.8 x 2347.92 at (13284.0, 17249.76)
  T11 ot_qwen_rst_rep_t: planned channel master (open item, no slots)
--case (a generator case dir: die.v / place.tcl / *.lef) recomputes the relay objects the two outline changes displace.
"""
import argparse, collections, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
V = 4
PITCH = 0.048          # asap7 M4 / M5 track pitch, tracks at 0.012 + 0.048 k
TRACKS = 2             # PIN_MIN_TRACKS of the station kits
STEP = PITCH * TRACKS
DW = 508
STATIONS = {'qfd_cst_s': dict(N=('a', 'in'), S=('b', 'out'), W=('tap', 'out')),
            'qfd_cst_n': dict(S=('b', 'in'), N=('a', 'out'), W=('tap', 'out')),
            'qfd_chead_w': dict(E=('e', 'in'), W=('w', 'out'), N=('n', 'out'), S=('s', 'out')),
            'qfd_chead_e': dict(W=('w', 'in'), E=('e', 'out'), N=('n', 'out'), S=('s', 'out'))}
FACE_LAYER = dict(N='M5', S='M5', E='M4', W='M4')
CDC = dict(W=[('l_v', 1, 'co'), ('l_sec', 17, 'co'), ('l_row', 8, 'co'), ('l_data', 256, 'co'), ('l_pop', 1, 'co'),
              ('hclk', 1, None), ('c_arst_n', 1, None), ('h_arst_n', 1, None)],
           N=[('h_lv', 1, 'hi'), ('h_lsec', 17, 'hi'), ('h_lrow', 8, 'hi'), ('h_ldata', 256, 'hi'), ('h_hand', 1, 'hi'),
              ('h_wcon', 1, 'hi'), ('h_av', 1, 'hi'), ('h_atag', 9, 'hi')],
           E=[('h_cred', 3, 'ho'), ('h_wv', 1, 'ho'), ('h_wsec', 24, 'ho'), ('h_cv', 1, 'ho'), ('h_csec', 24, 'ho'),
              ('h_cdata', 256, 'ho'), ('h_ctag', 9, 'ho'), ('h_fault', 1, 'ho')],
           S=[('w_v', 1, 'wi'), ('w_sec', 24, 'wi'), ('w_data', 256, 'wi'), ('w_tag', 9, 'wi'), ('w_room', 1, 'wr'),
              ('wd_v', 1, 'wr'), ('wd_tag', 9, 'wr'), ('c_fault', 1, 'cf')])
CDC_WH = 183.6
RHEAD_WH = (691.2, 453.6)
RHEAD_OLD_W = 648.0
VM = dict(x=13284.0, y=17249.76, w=4708.8, h=2347.92, region=(1166.4, 1080.0), band=187.92,
          regions={0: (13284.0, 17249.76), 1: (16783.2, 17249.76), 2: (14450.4, 17249.76), 3: (15616.8, 17249.76),
                   4: (13284.0, 18517.68), 5: (16783.2, 18517.68), 6: (14450.4, 18517.68), 7: (15616.8, 18517.68)})
VM_LEAVES = [  # (master, per region, total, status, planned outline or None)
    ('ot_qfd_vm_bank_t', 8, 64, 'closed view', None), ('ot_qfd_vm_su_t', 6, 48, 'closed view', None),
    ('ot_qfd_vm_xfifo8_t', 16, 128, 'closed view', None), ('ot_qfd_vm_su1024_t', 3, 24, 'closed view', None),
    ('ot_qwen_tree_delay1_t', 8, 64, 'in route (w17, 17.28 x 64.8)', None),
    ('ot_qwen_tree_delay2_t', 14, 112, 'closed view', None),
    ('ot_qfd_vm_rowrd_t', 1, 8, 'NEW leaf, M5, not synthesized', None),
    ('ot_qfd_vm_gctl_t', 1, 8, 'NEW leaf, M5, not synthesized', None),
    ('ot_qfd_vm_xplane_t', 0, 32, 'NEW leaf, M5, planned outline, die level on the middle strips', (129.6, 43.2)),
    ('ot_qfd_vm_xrelay_t', 0, 328, 'NEW leaf, M5, planned outline, 328 routed + depth pads, full-height double-column '
                                   'strips at <= 432 um pitch', (17.28, 64.8))]
# die-level pairs of the it2 / it3 cases (tools/hier_contract/contract_v4_tp8.py --check resolves them through relays)
SEAMS = [('qfd_cst_s', 'a', 'qfd_cst_s', 'b'), ('qfd_cst_n', 'b', 'qfd_cst_n', 'a'),
         ('qfd_chead_w', 's', 'qfd_cst_s', 'a'), ('qfd_chead_e', 's', 'qfd_cst_s', 'a'),
         ('qfd_chead_w', 'n', 'qfd_cst_n', 'b'), ('qfd_chead_e', 'n', 'qfd_cst_n', 'b'),
         ('qfd_chead_w', 'w', 'qfd_chead_w', 'e'), ('qfd_chead_e', 'e', 'qfd_chead_e', 'w')]
SEAMS_OTHER = [('qfd_cst_s', 'tap', 'qfd_tile_nk', 'tap'), ('qfd_cst_n', 'tap', 'qfd_tile_nk', 'tap'),
               ('qfd_chead_w', 'e', 'qfd_sp_vector_memory', 'xw'), ('qfd_chead_e', 'w', 'qfd_sp_vector_memory', 'xe')]
LOG = 'el1011-qwen-tp8.log 2026-10-13'


def snap(v):
    """the first track at or above v"""
    k = -(-(v - 0.012) // PITCH)
    return round(0.012 + PITCH * k, 3)


def band(face_len, n):
    """n pin slots at STEP, centred on the face, on track: (lo, [slot centres])"""
    lo = snap((face_len - (n - 1) * STEP) / 2)
    return [round(lo + STEP * i, 3) for i in range(n)]


def station_pins(cell, w, h):
    """T7.  N carries bundle + ck + rst_n (511 slots: ck / rst_n on the two centre slots, x_r on the last); the other
    faces use the same slot grid without the centre pair, so a column of stations lines up bit for bit."""
    pins, ck = [], None
    for f, (b, d) in STATIONS[cell].items():
        L = w if f in 'NS' else h
        sl = band(L, DW + 3)
        mid = (DW + 3) // 2
        data = sl[:mid] + sl[mid + 2:-1]
        assert len(data) == DW and sl[0] > 0.3 and sl[-1] < L - 0.3, (cell, f, L, sl[0], sl[-1])
        pins += [dict(name=f'{b}_d[{DW - 1}:0]', face=f, layer=FACE_LAYER[f], span_um=[data[0], data[-1]],
                      direction='INPUT' if d == 'in' else 'OUTPUT', pins_per_um=round(1 / STEP, 3),
                      offset_pending_view=True),
                 dict(name=f'{b}_r', face=f, layer=FACE_LAYER[f], span_um=[sl[-1], sl[-1]],
                      direction='OUTPUT' if d == 'in' else 'INPUT', offset_pending_view=True)]
        if f == 'N':
            ck = sl[mid]
            pins.append(dict(name='rst_n', face='N', layer='M5', span_um=[sl[mid + 1], sl[mid + 1]], direction='INPUT',
                             offset_pending_view=True))
    return sorted(pins, key=lambda p: p['name']), ck


def bits(p):
    m = re.search(r'\[(\d+):(\d+)\]$', p['name'])
    return int(m.group(1)) - int(m.group(2)) + 1 if m else 1


def base(n):
    return re.sub(r'\[[^\]]*\]$', '', n)


def rect(s):
    o, u = s['origin'], s['outline']
    return o['x'], o['y'], o['x'] + u['w'], o['y'] + u['h']


def ov(a, b, e=1e-4):
    return min(a[2], b[2]) - max(a[0], b[0]) > e and min(a[3], b[3]) - max(a[1], b[1]) > e


def apply(C, when='2026-10-13', regen=None, source_note='', skip=()):
    """v3 (or a fresh derivation) -> v4, in place; returns C.  skip: cells a later version owns (v5: the generator
    places qkd_rhead and the VM region itself, so their outline / origin are the case's)"""
    regen = regen or {}
    die = C['slots'][0]
    changed = collections.Counter()
    for s in C['slots'][1:]:
        cell = s['cell']
        if cell in STATIONS:
            pins, ck = station_pins(cell, s['outline']['w'], s['outline']['h'])
            if s.get('pins') != pins:
                s['pins'] = pins
                s['clock_entry'] = dict(pin='ck', face='N', layer='M5', offset=ck)
                s['reset_pins'] = ['rst_n']
                s['notes'] = (s.get('notes', '') + ' | ' if s.get('notes') else '') + \
                    ('v4 T7: bundle x[508:0] -> x_d[507:0] (flow) + x_r (against the flow) on the bundle face; rst_n '
                     '(async reset of the 4 ready flops) on N beside ck; spans = pin count at 2 tracks (0.096 um), pin '
                     'order inside a span from the closed LEF (kits qfd_cst_s/n, qfd_chead_e/w @465253000)')
                s.pop('pin_replan', None)
                s['version'] = V
                changed[cell] += 1
        elif cell == 'qkd_cdc_wleaf':
            pins = [dict(name=f'{n}[{b - 1}:0]' if b > 1 else n, face=f, layer=FACE_LAYER[f], offset_pending_view=True,
                         **({'bundle': g} if g else {})) for f, l in CDC.items() for n, b, g in l]
            if s.get('pins') != pins or s['outline']['w'] != CDC_WH:
                s['outline'] = dict(w=CDC_WH, h=CDC_WH)
                s['pins'] = pins
                s['clock_entry'] = dict(pin='clk', face='N', layer='M5')
                s['reset_pins'] = ['c_arst_n', 'h_arst_n']
                s.update(pg_layer='M5', strap_layer='M6', signal_max_layer='M5',
                         layer_cap=dict(cap='M5', conforms=True, basis='new M5 leaf (kit qkd_cdc_wleaf_ref)'))
                s['notes'] = ('v4 T8 (q13-cdcw 04:11): outline 183.72 -> 183.6 square on the 2.16 grid, same origin; real '
                              'RTL ports of qkd_cdc_wleaf on the faces / layers of the v3 bundles (pin field "bundle" = the '
                              'die generator bus co/hi/ho/wi/wr/cf, kv_die.py BINDINGS order); clock port clk (die net '
                              'ck) N/M5; pin offsets from the LEF when the view closes (offset_pending_view)')
                s['version'] = V
                changed[cell] += 1
        elif cell == 'qkd_rhead' and cell not in skip:
            if abs(s['outline']['w'] - RHEAD_WH[0]) > 1e-6:
                o = s['origin']
                # the nb face (cell E) looks at the astk column: that edge stays, the slot grows away from it
                if o.get('orient', 'R0') in ('R0', 'MX'):
                    o['x'] = round(o['x'] + s['outline']['w'] + (RHEAD_OLD_W - s['outline']['w']) - RHEAD_WH[0], 3)
                s['outline'] = dict(w=RHEAD_WH[0], h=RHEAD_WH[1])
                old = {base(p['name']): p for p in s.get('pins', [])}

                def pin(n, f, l, span, why):
                    return dict(name=old[n]['name'] if n in old else n, face=f, layer=l, span_um=span,
                                offset_pending_view=True, **({'moved': why} if why else {}))
                s['pins'] = [pin('e', 'S', 'M5', [216.0, 475.2], 'v3 S x 4.5-5.9'),
                             pin('nb', 'E', 'M6', [151.2, 302.4], 'v3 E M4 y 177.7-275.9'),
                             pin('rst_n', 'S', 'M5', [216.0, 475.2], 'v3 W M4'),
                             pin('s', 'S', 'M5', [216.0, 475.2], 'v3 S x 13.6-16.8'),
                             pin('ti', 'S', 'M5', [216.0, 475.2], 'v3 S x 259.2-408.7')]
                s['clock_entry'] = dict(pin='ck', face='N', layer='M7', offset=345.6)
                s['reset_pins'] = ['rst_n']
                s['kind'] = 'parent'
                s.update(pg_layer='M7', strap_layer='M8', signal_max_layer='M7', pin_layers=['M5', 'M6', 'M7'])
                s['layer_cap'] = dict(cap='M7', kind='cluster', die_over='M8+', pin_layers=['M5', 'M6', 'M7'],
                                      layer_cap_grant='qwen-tp8 die lead 2026-10-13: hardened-once head cluster (16 x '
                                                      'ot_qkh_lane8 M5 leaves + ot_qkh_ktree), PG M7, signals to M7, '
                                                      'nb on M6 (q13-rhead-fit option A)')
                s['notes'] = ('v4 T9 (q13-rhead-fit 04:13, option A): hardened-once cluster 691.2 x 453.6 = 6 x 3 lane '
                              'cells of 108 x 151.2 + a 43.2-um centre N-S relay channel at x 324-367.2 (hub cut 0.78 -> '
                              '~0.41); the nb face edge is fixed, the slot grows 43.2 um away from the astk column; '
                              'envelope is the requester\'s estimate, NOT gate-checked; contract bundles e/s/ti/nb/ck vs '
                              'ot_qwen_nearhbm_head_hs ports (c_in, row_in, e_in, lt_in, hid, q_*_in, sc_d, sc_f, g_f / '
                              'nb_d / clk): the view is exported under the slot bundle names or the pins are re-listed '
                              'from its LEF at closure')
                s.pop('pin_replan', None)
                s['version'] = V
                changed[cell] += 1
        elif cell == 'qfd_sp_vector_memory' and cell not in skip:
            if abs(s['outline']['w'] - VM['w']) > 1e-6:
                old = rect(s)
                s['outline'] = dict(w=VM['w'], h=VM['h'])
                s['origin'] = dict(x=VM['x'], y=VM['y'], orient='R0')
                s['kind'] = 'parent'
                s['pins'] = [dict(name=p['name'], face=p['face'], layer=p['layer'], face_pending_view=True,
                                  offset_pending_view=True) for p in s.get('pins', []) if base(p['name']) != 'ckx']
                s.pop('target_insertion_ps', None)
                s['clock_entry'] = dict(pin='ck', face='N', layer='M5')
                s['clock_taps'] = dict(kind='per_leaf', slot_level_tree=False, max_leaf_sinks=4141,
                                       note='one die clock tap per hardened leaf at the leaf\'s exported insertion '
                                            '(closed leaves: their views; new leaves target 175-250 ps, not measured); '
                                            'me_en K + 1 edges early for the relay strips; clock_entry is kept for the '
                                            'schema only')
                s.update(pg_layer='M5', strap_layer='M6', signal_max_layer='M5',
                         layer_cap=dict(cap='M5', kind='region', conforms=True,
                                        basis='new leaves M5; closed children keep their accepted view layers'))
                s['region'] = dict(regions=[dict(r=r, x=x, y=y, w=VM['region'][0], h=VM['region'][1])
                                            for r, (x, y) in sorted(VM['regions'].items())],
                                   xplane_band=dict(x=VM['x'], y=round(VM['y'] + VM['region'][1], 3), w=VM['w'],
                                                    h=VM['band']),
                                   bbox_with_relief_bays=dict(x=13288.32, y=16977.6, w=4702.32, h=2890.08),
                                   v3_slot_vacated=[round(v, 3) for v in old])
                s['notes'] = ('v4 T10 (claude/qwen-tp8-vm-1013 ~04:20): REGION of hardened leaves, 4 x 2 regions of '
                              '1166.4 x 1080 (region r at column slot (0,3,1,2)[r % 4], row r // 4) + one 187.92-um '
                              'x-plane band between the rows; no region-level soft logic, no slot-level clock tree; '
                              'leaf masters and counts in sub_layouts; external bus faces are NOT fixed (leaves not '
                              'synthesized): the v3 bundle names / faces are kept as provisional pins; x read latency '
                              '+ 10 engine edges (delta T10); supersedes the 1,536-lane stage design and the vm_grp '
                              '4596.48 x 2298.24 request')
                s['version'] = V
                changed[cell] += 1
    sub = C.setdefault('sub_layouts', {})
    sub['qfd_sp_vector_memory'] = dict(
        kind='region', plan='results/arch/qwen_tp8_1012/vm_leaf_plan_claude.json @ claude/qwen-tp8-vm-1013 (c4e0b0883)',
        rows=[dict(cell=m, tile=m, count=tot, per_region=per, status=st, layer_cap='M5' if 'NEW' in st else 'view',
                   **({'w': wh[0], 'h': wh[1]} if wh else {})) for m, per, tot, st, wh in VM_LEAVES])
    sub['qkd_rhead'] = dict(
        kind='cluster', plan='physical/ref_tile/qkh_head_hs_fit_spec.json @ claude/q13-rhead-fit (be049dd70), option A',
        rows=[dict(cell='ot_qkh_lane8', tile='lane_c', count=16, w=108.0, h=151.2, layer_cap='M5'),
              dict(cell='ot_qkh_ktree', tile='ktree', count=1, w=151.2, h=97.2, layer_cap='M5')])
    # ---- deltas
    D = {d['id']: d for d in C['deltas']}
    if 'D5' in D:
        D['D5']['slots'] = sorted(set(D['D5']['slots']) | {'qfd_chead_e', 'qfd_chead_w'})
        if 'v4' not in D['D5']['status']:
            D['D5']['status'] += '; v4: heads carry the same 509-bit word (T7)'
    new = [
        dict(id='T7', slots=sorted(STATIONS), status='decided v4',
             change='station / head bundles x[508:0] are the port pair x_d[507:0] (data, with the flow) + x_r (ready, '
                    'against the flow) on the bundle face: stations a_d/a_r N, b_d/b_r S, tap_d/tap_r W; heads e_d/e_r '
                    'E, w_d/w_r W, n_d/n_r N, s_d/s_r S; new pin rst_n on N beside ck; head bundles 323 -> 509 bits; '
                    'span_um = 509 pins at 2 tracks (48.8 um; N with ck + rst_n 49.0 um of the 52.68-um face)'),
        dict(id='T8', slots=['qkd_cdc_wleaf'], status='decided v4',
             change='outline 183.72 -> 183.6 square (2.16 grid, same origin); slot pins = the RTL ports of '
                    'qkd_cdc_wleaf on the v3 bundle faces / layers (co W M4, hi N M5, ho E M4, wi / wr / cf S M5, clk N '
                    'M5, hclk / c_arst_n / h_arst_n W M4); offsets from the closed LEF'),
        dict(id='T9', slots=['qkd_rhead'], status='decided v4 (envelope estimate, not gate-checked)',
             change='hardened-once head cluster, outline 648 x 453.6 -> 691.2 x 453.6 (+43.2 um centre relay channel, '
                    '+2.39 mm2 over 128 heads); ti / e / s / rst_n S M5 inside x 216-475.2, nb E M6 y 151.2-302.4, ck N '
                    'M7 at the channel (x 345.6); PG M7, signals to M7, die over it on M8+; no other slot moves; the '
                    'relay objects of the two 43.2-um growth strips are re-placed by the generator'),
        dict(id='T10', slots=['qfd_sp_vector_memory'], status='decided v4 (plan level; no kit, route or view)',
             change='bit-plane VM as a REGION of hardened leaves: envelope 4708.8 x 2347.92 at (13284.0, 17249.76) = '
                    '4 x 2 regions of 1166.4 x 1080 + 187.92-um x-plane band (v3: 2332.776 x 2073.576 at (14070.24, '
                    '10944.72), vacated); one clock tap per leaf, no slot-level tree; INTERFACE: x read latency + 10 '
                    'engine edges (RTL XPR 10 at RO 1, + 9 at RO 2; XVM of the x consumer + 10); SU / row / write '
                    'unchanged in RTL, their external buses to the new slot are not routed (relay depth unknown)'),
        dict(id='T11', slots=[], status='planned (open item; sites not legalised)',
             change='channel master ot_qwen_rst_rep_t (1-b reset repeater, <= 5.4 x 2.16 um, M1-M3): 1,160 instances '
                    'of the registered reset tree, results/arch/qwen_tp8_1013/reset_tree_plan.json @ '
                    'claude/qwen-tp8-relay-1013 (431ce7827)')]
    C['deltas'] = [d for d in C['deltas'] if d['id'] not in {n['id'] for n in new}] + new
    # ---- open items
    O = C.setdefault('open_items', {})

    def item(k, *msgs):
        O[k] = sorted(set(m for m in O.get(k, []) if not m.startswith('v4 ')) | set(msgs))
    vm_r, rh_r = regen.get('vm_envelope', {}), regen.get('rhead_growth', {})
    rfile = regen.get('_file', 'qwen_rom_tp8_v4_regen.json')
    for c in STATIONS:
        O[c] = sorted({m for m in O.get(c, []) if 'layer cap M5: current view uses M8' not in m})
        item(c, 'v4 GENERATOR (T7): the die netlist still connects the aggregated ports (.a/.b/.tap, .e/.w/.n/.s) with '
                'n_cor 444-b / n_tap 507-b nets (it2 case) and no rst_n: emit x_d (508 b; unused data bits tied at the '
                'source or the word widened) and x_r as a second net in the reverse direction with its own relay per '
                'hop, and tie rst_n to the tile-field reset; the case LEF master takes the slot pins')
    item('qfd_tile_nk',
         'v4 SEAM (T7): station tap_d[507:0] + tap_r vs tile tap[506:0] (507 b, case-LEF derived): the tile side must '
         'list tap_d / tap_r (D5: 508 + ready) or the tap word be fixed at one width on both sides (q-tile + die lead)',
         'v4 q13 03:55-04:05 rpair/kvl/node SLOT ARITHMETIC (tile slot, NOT the qkd_rhead request): full-width bands '
         'rpair 5 x 129.6 = 648 (not 475) + kvl 108 + lsl 561.6 = 1,317.6 um > the 1,296-um slot before the node leaf '
         '(+53) and glue; and the W pin band y 356.4-946 faces rpair / kvl rows. Slot unchanged in v4: decision owner '
         'coordinator + die lead (shrink rpair to the 86.4-95 um ROM row pitch, or a taller tile = die regen)')
    item('qkd_cdc_wleaf', 'v4 GENERATOR (T8): master outline 183.6 square and the RTL port list (bundle map in the slot '
                          'pins); re-derive pin offsets from the LEF of kit qkd_cdc_wleaf_ref at closure')
    item('qkd_rhead',
         'v4 GENERATOR (T9): master 691.2 x 453.6, R0/MX instances x - 43.2 (E edge fixed), MY/R180 origin unchanged; '
         'channel to qkd_land / qkd_land_n shrinks 129.7 -> 86.5 um; no slot overlap, no slot moves',
         f'v4 GENERATOR (T9): {rh_r.get("count", "?")} relay objects of the {rh_r.get("case", "it2")} case stand in '
         f'the 43.2-um growth strips (krs / krq head feeds and the N-S chains beside the head columns) and are '
         f're-placed >= 43.2 um outward: names in {rfile} rhead_growth')
    item('qfd_sp_vector_memory',
         f'v4 GENERATOR (T10): move the VM to the region envelope; {vm_r.get("count", "?")} relay objects of the '
         f'{vm_r.get("case", "it2")} case inside it are regenerated with their chains: names in {rfile} vm_envelope; '
         f'no v3 slot overlaps the envelope',
         'v4 SEAM (T10): head e / w corridor into the VM: v3 xw / xe[443:0] vs head w_d / e_d[507:0] + _r; the VM x '
         'ports are re-listed with the leaf pins (faces not fixed)',
         'v4 T10: the VM plan also removes sp_su64_sfu from the spine stack (reservation 1991.52 x 2829.6 at (16424.64, '
         '19662.72), unsized): NOT a v4 change, the su64 slot keeps its v3 place until requested',
         'v4 T10: new leaves rowrd_t / gctl_t / xplane_t / xrelay_t have no kit; the plane-control and me_e registered '
         'trees are not in RTL; per-lane stage length (plan max detour 622 um) is not re-audited against 500 um')
    O['qfd_sp_vector_memory'] = [m for m in O['qfd_sp_vector_memory'] if not m.startswith('slot request: outline')]
    item('ot_qwen_rst_rep_t',
         'v4 PLANNED MASTER (T11, relay-1013 04:16): 1-b reset repeater (1 input flop, 2 output flops; pad depth '
         'variants _p1.._p64 or one 6-b strap), outline <= 5.4 x 2.16 um, M1-M3, clk + d on W, q0 / q1 on E / N; 1,160 '
         'instances / 1,472 nets at the 240-um lattice sites of results/arch/qwen_tp8_1013/reset_tree_plan.json @ '
         'claude/qwen-tp8-relay-1013 (431ce7827); clock = the sink domain\'s region clock; channel cells (die_top_logic), '
         'no slot moves; becomes a die_top_logic master once the sites are legalised against the placement')
    C['open_items'] = {k: v for k, v in sorted(O.items()) if v}
    # ---- file level
    area = collections.Counter()
    for s in C['slots'][1:]:
        area[s['cell']] += s['outline']['w'] * s['outline']['h'] / 1e6
    fp = C.setdefault('floorplan', {})
    dmm2 = die['outline']['w'] * die['outline']['h'] / 1e6
    tot = sum(area.values())
    fp.update(slot_mm2=round(tot, 3), slot_share=round(tot / dmm2, 4), channel_share=round(1 - tot / dmm2, 4),
              slots_by_cell_mm2={k: round(v, 3) for k, v in sorted(area.items())})
    C['regen_objects'] = dict(file=f'results/arch/hier_contract_1012/{rfile}',
                              vm_envelope=vm_r.get('count'), rhead_growth=rh_r.get('count'), case=vm_r.get('case'))
    if C.get('version', 0) < V or changed:
        C['changelog'] = [c for c in C.get('changelog', []) if c.get('version') != V] + [dict(
            version=V, when=when,
            change='slot change answers (' + LOG + '; tools/hier_contract/contract_v4_tp8.py' +
                   (', ' + source_note if source_note else '') + '): T7 stations / heads _d/_r pairs + rst_n, heads 509 b '
                   '(' + ', '.join(f'{c} {changed[c]}' for c in sorted(STATIONS)) + '); T8 qkd_cdc_wleaf 183.6 sq + RTL '
                   f'ports ({changed["qkd_cdc_wleaf"]}); T9 qkd_rhead cluster 691.2 x 453.6 option A '
                   f'({changed["qkd_rhead"]}); T10 VM region envelope 4708.8 x 2347.92 at (13284.0, 17249.76); T11 '
                   'ot_qwen_rst_rep_t planned master; other slots unchanged (version 3)')]
    C['version'] = V
    C['updated'] = when
    die['version'] = V
    die['notes'] = re.sub(r'contract v\d+', f'contract v{V}', die.get('notes', ''))
    return C


# ---------------------------------------------------------------------------------------------------------- checks
def schema_errors(C):
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource
    s = json.load(open(HERE / 'contract.schema.json'))
    reg = Registry().with_resources([(p.name, Resource.from_contents(json.load(open(p))))
                                     for p in HERE.glob('*.schema.json')])
    return [e.message[:160] for e in Draft202012Validator(s, registry=reg).iter_errors(C)]


def overlaps(C):
    """slot pairs that overlap, slots outside the die, slots off the 0.216 placement lattice"""
    S = C['slots'][1:]
    dw, dh = C['slots'][0]['outline']['w'], C['slots'][0]['outline']['h']
    R = sorted(((rect(s), s['name']) for s in S), key=lambda t: t[0][0])
    bad = [f'{n} outside the die' for r, n in R if r[0] < 0 or r[1] < 0 or r[2] > dw + 1e-6 or r[3] > dh + 1e-6]
    for i, (a, n) in enumerate(R):
        for b, m in R[i + 1:]:
            if b[0] >= a[2] - 1e-4:
                break
            if ov(a, b):
                bad.append(f'{n} overlaps {m}')
    return bad


def span_fit(C):
    """every span inside its face; T7 faces: all pins of the face fit at 2 tracks"""
    bad = []
    seen = set()
    for s in C['slots'][1:]:
        if s['cell'] in seen:
            continue
        seen.add(s['cell'])
        w, h = s['outline']['w'], s['outline']['h']
        need = collections.Counter()
        for p in s.get('pins', []):
            L = w if p['face'] in 'NS' else h
            need[p['face']] += bits(p)
            sp = p.get('span_um')
            if sp and (sp[0] < 0 or sp[1] > L + 1e-6):
                bad.append(f'{s["cell"]} {p["name"]} span {sp} outside the {p["face"]} face {L}')
            if sp and s['cell'] in STATIONS and (sp[1] - sp[0]) + 1e-6 < (bits(p) - 1) * STEP:
                bad.append(f'{s["cell"]} {p["name"]} span {sp} shorter than {bits(p)} pins at {TRACKS} tracks')
        if s['cell'] in STATIONS:
            need[s['clock_entry']['face']] += 1
            for f, n in need.items():
                L = w if f in 'NS' else h
                if n * STEP > L:
                    bad.append(f'{s["cell"]} {f} face: {n} pins x {STEP} = {n * STEP:.2f} > {L}')
    return bad


def seams(C):
    """(fails, open): both ends of every station / head pair agree in _d and _r width and direction"""
    W = {}
    for s in C['slots'][1:]:
        W.setdefault(s['cell'], {base(p['name']): (bits(p), p.get('direction')) for p in s.get('pins', [])})
    bad, opn = [], []
    for ca, pa, cb, pb in SEAMS:
        for suf in ('_d', '_r'):
            a, b = W.get(ca, {}).get(pa + suf), W.get(cb, {}).get(pb + suf)
            if not a or not b:
                bad.append(f'{ca}.{pa}{suf} / {cb}.{pb}{suf}: pin missing')
            elif a[0] != b[0]:
                bad.append(f'{ca}.{pa}{suf} {a[0]} b != {cb}.{pb}{suf} {b[0]} b')
            elif a[1] == b[1]:
                bad.append(f'{ca}.{pa}{suf} and {cb}.{pb}{suf} are both {a[1]}')
    for ca, pa, cb, pb in SEAMS_OTHER:
        a = W.get(ca, {}).get(pa + '_d')
        b = W.get(cb, {}).get(pb + '_d') or W.get(cb, {}).get(pb)
        if not a or not b or a[0] != b[0] or (pb + '_r') not in W.get(cb, {}):
            opn.append(f'{ca}.{pa}_d {a[0] if a else "?"} b + {pa}_r vs {cb}.{pb} {b[0] if b else "?"} b'
                       f'{"" if (pb + "_r") in W.get(cb, {}) else " (no ready pin)"}')
    return bad, opn


def case_objects(case, C3, C4):
    """relay / tree-delay objects of a generator case that stand inside the two changed envelopes"""
    sys.path.insert(0, str(HERE.parent / 'qwen_kv_die'))
    from hier_contract_export import parse_lef
    case = Path(case)
    lef = {}
    for f in sorted(case.glob('*.lef')):
        parse_lef(f, lef)
    master = {}
    for line in open(case / 'die.v'):
        m = re.match(r'\s*(\w+)\s+(\\?\S+)\s*\(', line)
        if m and m.group(1) in lef:
            master[m.group(2).lstrip('\\')] = m.group(1)
    old = {s['name']: rect(s) for s in C3['slots'][1:]}
    vm = [rect(s) for s in C4['slots'][1:] if s['cell'] == 'qfd_sp_vector_memory']
    rh = [rect(s) for s in C4['slots'][1:] if s['cell'] == 'qkd_rhead']
    hit = dict(vm_envelope=[], rhead_growth=[])
    for line in open(case / 'place.tcl'):
        m = re.search(r'findInst (\S+)\]\s+([\d.]+)\s+([\d.]+)\s+(\w+)', line)
        if not m or m.group(1) in old or m.group(1) not in master:
            continue
        c = master[m.group(1)]
        if not (re.match(r'q[fk]d_rly', c) or 'delay' in c):
            continue
        x, y = float(m.group(2)), float(m.group(3))
        r = (x, y, x + lef[c]['w'], y + lef[c]['h'])
        if any(ov(r, q) for q in vm):
            hit['vm_envelope'].append(m.group(1))
        if any(ov(r, q) for q in rh):
            hit['rhead_growth'].append(m.group(1))
    src = (case / 'SOURCE_COMMIT').read_text().strip() if (case / 'SOURCE_COMMIT').exists() else ''
    return {k: dict(case=f'{case.parent.name} (src {src})', count=len(v), names=sorted(v)) for k, v in hit.items()}


def check(C):
    res = dict(schema=schema_errors(C), overlap=overlaps(C), span=span_fit(C))
    res['seam'], res['seam_open'] = seams(C)
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--in', dest='src')
    ap.add_argument('--out')
    ap.add_argument('--when', default='2026-10-13')
    ap.add_argument('--regen', help='the committed regen-object list (read)')
    ap.add_argument('--case', help='generator case: recompute the regen-object list')
    ap.add_argument('--regen-out')
    ap.add_argument('--check')
    a = ap.parse_args(argv)
    if a.check:
        C = json.load(open(a.check))
    else:
        C3 = json.load(open(a.src))
        regen = json.load(open(a.regen)) if a.regen and Path(a.regen).exists() else {}
        C = apply(json.loads(json.dumps(C3)), a.when, regen)
        if a.case:
            regen = dict(schema='qwen_rom_tp8.v4_regen_objects.v1',
                         note='relay objects of the generator case that the v4 VM envelope (T10) and the 43.2-um '
                              'qkd_rhead growth strips (T9) displace; the die generator regenerates them',
                         **case_objects(a.case, C3, C))
            Path(a.regen_out or a.regen).write_text(json.dumps(regen, indent=1) + '\n')
            C = apply(json.loads(json.dumps(C3)), a.when, regen)
        Path(a.out).write_text(json.dumps(C, indent=1) + '\n')
    res = check(C)
    for k in ('schema', 'overlap', 'span', 'seam'):
        print(f'{k.upper()} {"PASS" if not res[k] else "FAIL"} {len(res[k])}', *res[k][:6], sep='\n  ' if res[k] else ' ')
    for m in res['seam_open']:
        print(f'SEAM OPEN (other owner, in open_items) {m}')
    print(json.dumps(dict(version=C['version'], slots=len(C['slots']), slot_share=C.get('floorplan', {}).get('slot_share'),
                          regen=C.get('regen_objects'))))
    return 1 if any(res[k] for k in ('schema', 'overlap', 'span', 'seam')) else 0


if __name__ == '__main__':
    sys.exit(main())
