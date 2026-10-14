#!/usr/bin/env python3
"""qwen_rom_tp8 contract v5 (die lead r8, 2026-10-13): the contract re-derived from the case of the generator that now
FOLLOWS v4 / v4b (tools/qwen_kv_die/tp8b_v5.py), plus the coordinator decisions of 10-13.  derive_tp8.py --version 5
calls apply() after the v4 / v4b passes; a slot whose cell, outline and pin set did not change keeps its v4 record
(only its origin follows the case), so v5 touches exactly the slots listed in the deltas.

Deltas (lead decisions, el1011-qwen-tp8.log 2026-10-13 r8):
  T14 tile slot 311.04 x 1,317.6 (row gap 190.08 -> 168.48, row pitch kept); tiles M5-capped: die M6 over the tile field
      for horizontal buses (cut model CLUSTER_PLAN 'M6'); tile pin tap[507:0], station tap_r tied high at the die
  T15 SU group (su64_sfu, 8 cbuf_g, 8 crom_g, seq_su) N of the VM region, SU abutted on the VM N face
  T16 qfd_crom_g 194.376 x 550.776 (+32.4 N)
  T17 KV control strip = 32 x qkd_ctrl_pc + qkd_ctrl_kc per stack; ot_hbm3e_phy pins per PC
  T18 qfd_seq_su bundles: ib / dflt dropped, dc 56 b, dh 187 b, cc 517 b, cd = cd_d + cd_cr, cbr0..7 kept
  T19 reset: qkd_pll / qfd_clkrx hard-macro abstracts, qkd_rstseq / qfd_rstseq leaves, rst_field / rst_spine trees
  T20 qkd_rhead 712.8 x 453.6 (coordinator grant to qkh_head_hs; supersedes T9's 691.2)
  T21 ROM IO: PHY abstract re-shape <= 2,320.2 x 1,563.8, RXD 512, FDI on W; io_serdes / io_ucie c / r as data + credit
      ports; slots pending the regenerated abstracts (el1013-qwen-romio.log)
  T22 qkd_seq merged-die port set: rf / tf deleted, r_sd 56 b, t_ds 187 b, t_flt deleted (pin list from el1013-qwen-kvcentre)
r9 (same day, same version: v5 was not issued before):
  T21 is no longer pending for the host PHY: the slot IS the merged abstract (physical/qwen_missing_phy/tp8_1013, 2320.056 x
      1563.570, FDI 2,089 b on the W face M4); io_serdes_1 / _2 moved 43.2 um W (FDI access strip); link words = data +
      valid with the flow, credit against it; cluster rst_n (reset net rst_io) and fault (to io_xfifo lf<k>)
  T23 closed views are adopted pin for pin by the generator (stations, heads, cdc_wleaf, kvwq leaf / ctl_bin, qkd_rstseq 21.6
      x 21.6, host PHY): slot pins = the view's LEF pins
  T24 reset: rst_seq / rst_seq_ctlm / rst_fwd_s join the registered reset tree (tt_ctlm rsi on W)
  T25 qkd_ectl head pins (e / s / t) stand under the grown head's S-face pin window (far-head nets 458 um)
  T26 die clock delivery (el1013-pinreg-audit.log): insertion-compensated clock entry per tile; --stamp writes the per-cell
      entry offsets of a pinreg audit into the slots

    contract_v5_tp8.py --stamp V5.json --clock AUDIT.json     per-cell die clock entry (T26) into the contract, in place

    contract_v5_tp8.py --check V5.json [--case CASE]      schema + overlap + span + seams (+ every case instance a slot)
"""
import argparse, collections, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import contract_v4_tp8 as V4   # noqa: E402
import contract_v4b_tp8 as V4B   # noqa: E402

V = 5
LOG = 'el1011-qwen-tp8.log 2026-10-13 r8 / r9'
TILE = (311.04, 1317.6)
RHEAD = (712.8, 453.6)
VM = V4.VM
HARD_MACRO = ('qkd_pll', 'qfd_clkrx', 'ot_hbm3e_phy', 'ot_qfd_serdes_112g_x12_phy')
PENDING_IO = ('qfd_io_serdes', 'qfd_io_ucie')          # r9: the host PHY slot is the merged abstract
SEAMS_TAP = [('qfd_cst_s', 'tap_d', 'qfd_tile_nk', 'tap'), ('qfd_cst_n', 'tap_d', 'qfd_tile_nk', 'tap'),
             ('qfd_chead_w', 'e_d', 'qfd_sp_vector_memory', 'xw_d'), ('qfd_chead_e', 'w_d', 'qfd_sp_vector_memory', 'xe_d')]


def base(n):
    return re.sub(r'\[[^\]]*\]$', '', n)


def sig(s):
    return (s['cell'], round(s['outline']['w'], 3), round(s['outline']['h'], 3),
            tuple(sorted((base(p['name']), V4.bits(p)) for p in s.get('pins', []))))


def apply(C, prev=None, when='2026-10-13', source_note=''):
    die = C['slots'][0]
    P = {s['name']: s for s in (prev or {}).get('slots', [])[1:]}
    changed, moved, new_cells = collections.Counter(), collections.Counter(), collections.Counter()
    out = [die]
    for s in C['slots'][1:]:
        cell = s['cell']
        if cell == 'qfd_tile_nk':
            s['outline'] = dict(w=TILE[0], h=TILE[1])
            s.update(signal_max_layer='M5', pg_layer='M5', strap_layer='M6', pin_layers=['M4'])
            s['layer_cap'] = dict(cap='M5', kind='cluster', die_over='M6 (horizontal buses, 75 % beside the tile straps), '
                                  'M8, M9', pin_layers=['M4'],
                                  layer_cap_grant='coordinator DECISION 2026-10-13 (tile growth): the tile is M5-capped, the '
                                                  'die owns M6 over the tile field for horizontal buses (cuts.py '
                                                  'CLUSTER_PLAN M6); M7 over the tile is not counted')
            s['notes'] = re.sub(r' \| v5 T14.*$', '', s.get('notes', '')) + \
                ' | v5 T14: slot 311.04 x 1,317.6 (rpair 648 + kvl 108 + lsl 561.6); tap[507:0] = {xl 128, ib 379, ib_go} ' \
                '(ot_qwen_rom_tile_nk: no ready port; the station tap_r is tied high at the die); rst_n on E'
        elif cell == 'qkd_rhead':
            for p in s.get('pins', []):
                p['offset_pending_view'] = True
            s['clock_entry'] = dict(pin='ck', face='N', layer='M7', offset=356.4)
            s['reset_pins'] = ['rst_n']
            s['kind'] = 'parent'
            s.update(pg_layer='M7', strap_layer='M8', signal_max_layer='M7', pin_layers=['M5', 'M6', 'M7'])
            s['layer_cap'] = dict(cap='M7', kind='cluster', die_over='M8+', pin_layers=['M5', 'M6', 'M7'],
                                  layer_cap_grant='qwen-tp8 die lead 2026-10-13: hardened-once head cluster qkh_head_hs '
                                                  '(16 x ot_qkh_lane8 M5 leaves + ot_qkh_ktree), PG M7, signals to M7, nb on M6')
            s['notes'] = ('v5 T20 (coordinator grant 2026-10-13, supersedes v4 T9 691.2): cluster 712.8 x 453.6 = 6 x 3 lane '
                          'cells of 108 x 151.2 + a 64.8-um centre N-S relay channel; 4 columns x 32 heads on the die, the '
                          'growth is taken from the strip channels (head | landing 129.7 -> 64.9 um); R0 / MX origin x - '
                          '64.8, MY / R180 unchanged; ti / e / s / rst_n S M5 x 216-475.2, nb E M6 y 151.2-302.4, ck N M7 '
                          'x 356.4; the 734.4 x 855.36 fallback is refused')
            s.pop('pin_replan', None)
        elif cell == 'qfd_sp_vector_memory':
            s['kind'] = 'parent'
            for p in s.get('pins', []):
                p['face_pending_view'] = p['offset_pending_view'] = True
            s.pop('target_insertion_ps', None)
            s['clock_entry'] = dict(pin='ck', face='N', layer='M5')
            s['clock_taps'] = dict(kind='per_leaf', slot_level_tree=False, max_leaf_sinks=4141,
                                   note='one die clock tap per hardened leaf at the leaf\'s exported insertion; me_en K + 1 '
                                        'edges early for the relay strips; clock_entry is kept for the schema only')
            s.update(pg_layer='M5', strap_layer='M6', signal_max_layer='M5',
                     layer_cap=dict(cap='M5', kind='region', conforms=True,
                                    basis='new leaves M5; closed children keep their accepted view layers'))
            s['region'] = dict(regions=[dict(r=r, x=x, y=y, w=VM['region'][0], h=VM['region'][1])
                                        for r, (x, y) in sorted(VM['regions'].items())],
                               xplane_band=dict(x=VM['x'], y=round(VM['y'] + VM['region'][1], 3), w=VM['w'], h=VM['band']),
                               bbox_with_relief_bays=dict(x=13288.32, y=16977.6, w=4702.32, h=2890.08))
            s['notes'] = ('v4 T10 region of hardened leaves (4 x 2 regions of 1166.4 x 1080 + 187.92-um x-plane band), now '
                          'PLACED by the generator (v5): pins on the face toward their die peer (provisional until the '
                          'leaves close): head root xw_d / xe_d[507:0] + xw_r / xe_r on S (W / E end), ib[379:0] from '
                          'tt_ctlm on S, sa / sq on N under the abutted SU (T15), result / sequencer words toward their '
                          'peers; x read latency + 10 engine edges (T10)')
        elif cell == 'qfd_crom_g':
            s['notes'] = re.sub(r' \| v5 T16.*$', '', s.get('notes', '')) + \
                ' | v5 T16 (q13-cromcbuf request): 194.376 x 550.776 (+32.4 um N: six 62.91-um ROMs + 20-um channels + the ' \
                'N pin band); the answer side faces the buffer rows (S on this die: the SU group is mirrored above the SU)'
        elif cell in ('qkd_ctrl_pc', 'qkd_ctrl_kc'):
            s.update(pg_layer='M5', strap_layer='M6', signal_max_layer='M5',
                     layer_cap=dict(cap='M5', conforms=True, basis='new M5 leaf (el1013-qwen-kvstrips)'))
            for p in s.get('pins', []):
                p['offset_pending_view'] = True
            s['notes'] = ('v5 T17 (el1013-qwen-kvstrips 08:06): ' + (
                'per-PC controller leaf, hardened ONCE, 247.512 x 378 at the PC pitch: head + pcport KVW 2 + kcmd tap; ci '
                '[318:0] / co[293:0] W at the CDC leaf, phy[277:0] E = {rsp_v, rsp_rdy, rsp_beat 4, rsp_tag 16, rsp_data '
                '256} of ITS PC, kci S -> kco N (command chain, abutted 378-um hops), rqi N -> rqo S (request chain toward '
                'the kc leaf), pc[4:0] strap (constant at the die), hclk / h_arst_n; registers at every pin; c<k>i / c<k>o '
                'credit bits are split x_d + x_cr in the view (pin list from the builder)'
                if cell == 'qkd_ctrl_pc' else
                'kc async FIFO leaf at the S end of every strip (one PC master, one pin plan; the N stacks\' S end is the '
                'end nearer the KV centre): kc[32:0] S from qkd_seq, kco N to PC 0, rqi N from PC 0, req[310:0] E = the '
                'PHY request port {req_v, req_rdy, req_we, req_len 5, req_tag 16, req_addr 31, req_wdata 256}, core clock '
                'ck + rsi, HBM clock / reset roots pll_hbm / hrst'))
        elif cell == 'ot_hbm3e_phy':
            s['notes'] = re.sub(r' \| v5 T17.*$', '', s.get('notes', '')) + \
                ' | v5 T17: pin plan per PC (tools/qwen_kv_die/tp8b_v5.py phy_repin: rsp_* of PC k centred 150.0 + 378 k ' \
                'above the PHY S edge at 2 tracks, req_* at y 4-34): the abstract must be regenerated with these pin ' \
                'positions before it binds (the case writes the re-pinned LEF as phy_ew.lef)'
            s['pin_plan'] = dict(tool='tools/qwen_kv_die/tp8b_v5.py phy_repin', per_pc_bits=278, request_bits=311,
                                 pc_pitch_um=378.0, status='abstract regeneration owed (el1013-qwen-kvstrips)')
        elif cell == 'qkd_kvwq_ctl_bin':
            s['notes'] = re.sub(r' \| v5 seam.*$', '', s.get('notes', '')) + \
                ' | v5 seam (closed view -sl1-ecdaf6345 vs the closed leaf wrapper -sl1-4df79ee4f): kvn = kvn_d[1046:0] in + ' \
                'kvn_cr out; f<g>[292:0] = {f_v, f_d 256, f_sec 24, f_lane 3, f_tag 9} and r<g> = {r_v, r_bad} are in the ' \
                'REVERSE field order of the leaf\'s c / n = {tag, lane, sec, d, v} and dn / dp = {bad, v}: the die net keeps ' \
                'the leaf order and die.v wires field to field at these pins (tools/qwen_kv_die/tp8b_v5.py PERM)'
        elif cell in ('qkd_rstseq', 'qfd_rstseq'):
            s.update(pg_layer='M5', strap_layer='M6', signal_max_layer='M5',
                     layer_cap=dict(cap='M5', conforms=True, basis='new M5 leaf'))
            s['notes'] = ('v5 T19: ot_qwen_sys_rst_seq as its own leaf (54 x 54) beside the ' +
                          ('KV PLL: lock in, registered reset roots rso_{WS,WN,ES,EN,c,fwd}' if cell == 'qkd_rstseq' else
                           'clock receiver: forwarded reset in, roots rso_seq / rso_ctlm / rso_f (tile field: tiles, '
                           'stations, heads) / rso_s (spine: res_ser, tt_up4, crom_g, cbuf_g)'))
        if cell in ('qkd_pll', 'qfd_clkrx'):
            s['hard_macro'] = True
            s['view_status'] = 'HARD-MACRO ABSTRACT (v5 T19): not a routed tile; LEF + lib owed by el1013-qwen-romio'
        if cell in PENDING_IO:
            s['pending_view'] = ('v5 T21: cluster of qfd_link_adp512 (237.6 x 583.2, in the 237.6-um strip beside the PHY) + '
                                 'FDI relay stations + the re-shaped PHY abstract (2320.056 x 1563.570, RXD 512, flit 1,043 '
                                 'b, FDI on its W face); slot pins: c_d[1023:0] + c_v in + c_cr out, r_d[1023:0] + r_v out + '
                                 'r_cr in, rst_n, fault; the cluster parent is not built (el1013-qwen-romio.log)')
            s['kind'] = 'parent'
        if cell == 'ot_qfd_serdes_112g_x12_phy':
            s['hard_macro'] = True
            s.pop('pending_view', None)
            s['view_status'] = ('HARD-MACRO ABSTRACT (v5 T21): physical/qwen_missing_phy/tp8_1013/ot_qfd_serdes_112g_x12_phy '
                                '(licensed-IP abstract, footprint and boundary timing ASSUMED); not judged by the routed-'
                                'tile lint (a) / (c) (coordinator 2026-10-13)')
            s['notes'] = re.sub(r' \| v5 T21.*$', '', s.get('notes', '')) + \
                ' | v5 T21: host SerDes = the abstract by its own LEF: clk, rst_n, tx_up, tx_v, tx_flit[1042:0], rx_v, ' \
                'rx_flit[1042:0] on the W face M4 y 600-700.344 (one track); the die reaches them from a 127.4-um strip W ' \
                'of the macro (the last relays of host_fdi, 2,089 b)'
        if cell == 'qkd_ectl':
            s['notes'] = re.sub(r' \| v5 T25.*$', '', s.get('notes', '')) + \
                ' | v5 T25: e0 / e3, s0 / s3, t0 / t1 stand straight under / over the head pins e / s / ti (head-local x - ' \
                '64.8: 155.06 / 159.46 / 237.93); e1 / e2 and s1 / s2 beside them (- 11 / - 7 um): far-head nets 458 um'
        if cell == 'qkd_rstseq':
            s['notes'] = s.get('notes', '') + ' | r9: the CLOSED leaf qkd_rstseq-kc1-b4a0a3156 (21.6 x 21.6), reset in = ' \
                'por_n (PLL lock); boot_done / boot_ok / link_up / soft_rst in and boot_go / rst_st / rso_host / rso_link ' \
                'out have NO die net yet (open item)'
        p = P.get(s['name'])
        if p is not None and sig(p) == sig(s) and cell not in ('qfd_sp_vector_memory', 'qkd_rhead', 'qfd_tile_nk'):
            o = s['origin']
            keep = json.loads(json.dumps(p))
            if any(abs(keep['origin'][k] - o[k]) > 1e-6 for k in 'xy') or keep['origin'].get('orient') != o.get('orient'):
                keep['origin'] = o
                keep['version'] = V
                moved[cell] += 1
            for k in ('hard_macro', 'view_status', 'pending_view', 'pin_plan'):
                if k in s:
                    keep[k] = s[k]
            s = keep
        else:
            if p is not None:
                for k, val in p.items():      # view / kit records of the previous version survive a pin-list change
                    if k not in s and k not in ('pin_replan',):
                        s[k] = val
                changed[cell] += 1
            else:
                new_cells[cell] += 1
            s['version'] = V
        out.append(s)
    gone = collections.Counter(p['cell'] for n, p in P.items() if n not in {s['name'] for s in out})
    C['slots'] = out
    # ---- deltas
    new = [
        dict(id='T14', slots=['qfd_tile_nk', 'qfd_cst_s', 'qfd_cst_n'], status='decided v5 (coordinator 2026-10-13)',
             change='tile slot 311.04 x 1,296 -> 1,317.6 (rpair / kvl / lsl bands); the 21.6 um comes out of the row gap '
                    '(190.08 -> 168.48), row pitch 1,486.08 kept; die 31,785.696 x 25,891.92 (+21.6 um: 16 tile rows, 15 '
                    'gaps; inside the 26.0-mm reticle side); the tile is M5-capped: die M6 over the tile field for '
                    'horizontal buses; tile pin tap[507:0] (ib_go 1 + ib 379 + xl 128), no ready: the station tap_r is tied '
                    'high at the die; tile rst_n joins the registered reset tree'),
        dict(id='T15', slots=['qfd_sp_su64_sfu', 'qfd_su_cbuf_g', 'qfd_crom_g', 'qfd_seq_su', 'qfd_sp_vector_memory',
                              'qfd_clkrx'], status='decided v5 (die lead; cut analysis)',
             change='the SU group follows the VM region: sp_su64_sfu abuts the VM N face at (16424.64, 19597.68), the 8 '
                    'buffer groups, 8 constant ROM groups and seq_su mirrored above it (masters R0, N / S pin faces '
                    'swapped); su_vm 8,511 b is an abutment again (0 relays, 0 cycles).  Left in place it needed 14.2 kb of '
                    'vertical capacity at 0.60 through the 12.6-kb A|B channel for 6.3 mm and ~15 stages each way per SU '
                    'read.  The control tile stays at mid-die: tt_xd / tt_mx / tt_ib and the head roots are relayed 2.4-3.2 '
                    'mm (cycles in el1013-rom-layer-tput-qwen.log); qfd_clkrx moves to the W sub-column'),
        dict(id='T16', slots=['qfd_crom_g'], status='decided v5', change='outline 194.376 x 518.376 -> 550.776 (+32.4 um N)'),
        dict(id='T17', slots=['qkd_ctrl_pc', 'qkd_ctrl_kc', 'ot_hbm3e_phy'], status='decided v5 (plan level; no RTL, no kit)',
             change='the 247.512 x 12,141.336 strips qkd_ctrl / qkd_ctrl_n are replaced by 32 x qkd_ctrl_pc (247.512 x 378) '
                    '+ one qkd_ctrl_kc (45.36 um, S end) per stack; the PHY abstract is re-pinned per PC (278 b per PC '
                    'facing its leaf, 311-b request port at the S end); every PC bundle is a <= 60-um face-to-face hop'),
        dict(id='T18', slots=['qfd_seq_su', 'qfd_tt_ctlm', 'qfd_io_xfifo', 'qkd_seq'], status='decided v5 (consumer side)',
             change='qfd_seq_su packing questions (el1013-qwen-romspine 08:01): (a) ib[381:0]: CONTRACT WRONG: the ME '
                    'instruction {go, tb 379} is issued by the ME-side controller in the control tile; bundle moved to '
                    'tt_ctlm.ib[379:0] -> VM head root (BODY LACKS A PORT there: ot_qfd_tt_ctlm_i_fpm exports p_v_e2 / '
                    'p_f_e2 only; owner el1011-q-seq exports tgo / tb); (b) dflt[8:0]: CONTRACT WRONG: no link end on one '
                    'die, dropped with qkd_seq.t_flt; (c) cbr0..7: CONTRACT RIGHT (8 producers), BODY LACKS PORTS: the '
                    'seq_su cell owns a registered 8:1 reducer (st_rdy AND, stage of group 0, fault OR into rom_fault), +1 '
                    'cycle on the stage handshake; cbc1..7 = copies of cbc0; (d) dc / dh: CONTRACT WRONG (r22k link-frame '
                    'width): dc[55:0], dh[186:0]; (e) cc: CONTRACT WRONG: valid-only cc[516:0] (the body never back-'
                    'pressures; io_xfifo o_coll_seq drops its credit pin), cd = cd_d[546:0] + cd_cr'),
        dict(id='T19', slots=['qkd_pll', 'qfd_clkrx', 'qkd_rstseq', 'qfd_rstseq'], status='decided v5',
             change='qkd_pll and qfd_clkrx are hard-macro abstracts (M8 pins under layer_rule hard_ip, no route); '
                    'ot_qwen_sys_rst_seq is a 54 x 54 M5 leaf beside each; reset nets rst_field (768 tiles + 768 stations + '
                    '48 heads) and rst_spine (res_ser 3, tt_up4, crom_g 8, cbuf_g 8) join the 13 KV reset nets in the '
                    'registered reset tree (0 cycles per token)'),
        dict(id='T20', slots=['qkd_rhead'], status='decided v5 (coordinator grant)',
             change='outline 691.2 x 453.6 (v4 T9) -> 712.8 x 453.6; 4 columns x 32 heads, die width unchanged'),
        dict(id='T21', slots=list(PENDING_IO) + ['ot_qfd_serdes_112g_x12_phy', 'qfd_io_xfifo'],
             status='decided v5 (abstracts merged from codex/tp8-phy-prepared-1013; cluster parents not built)',
             change='ROM IO (el1013-qwen-romio): the host SerDes slot is the re-shaped abstract by its own LEF (2320.056 x '
                    '1563.570, RXD 512, flit 1,043 b, 2,091 pins on the W face M4 y 600-700.344), E edge kept; '
                    'io_serdes_1 / _2 move 43.2 um W so a 127.4-um strip W of the macro holds the last host_fdi relays '
                    '(FDI 2,085 -> 2,089 b); io_serdes / io_ucie stay 2557.848 / 6394.872 x 1563.816 cluster slots: the '
                    'strip beside the PHY inside the cluster is 237.6 um (+80: the re-shape) for qfd_link_adp512; link '
                    'words c / r = x_d[1023:0] + x_v with the flow and x_cr against it (the credit rides the word\'s relay '
                    'frames), + rst_n (reset net rst_io from qfd_rstseq.rso_io, clocked by clk_serdes) and fault (1 b to '
                    'io_xfifo.lf<k>)'),
        dict(id='T23', slots=['qfd_cst_s', 'qfd_cst_n', 'qfd_chead_e', 'qfd_chead_w', 'qkd_cdc_wleaf', 'qkd_kvwq_leaf_s_w129_m',
                              'qkd_kvwq_ctl_bin', 'qkd_rstseq', 'ot_qfd_serdes_112g_x12_phy'], status='decided v5 (r9)',
             change='the generator adopts every CLOSED view pin for pin (tools/qwen_kv_die/tp8b_v5.py VIEWS): the slot pin '
                    'positions are the view LEF\'s, so the relay plan, this contract and the case are made on the real '
                    'pins and tools/qwen_tp8/bind_real.py drops the view LEF in unchanged (a master whose view differs in '
                    'outline or pin set is refused with the reason)'),
        dict(id='T24', slots=['qfd_rstseq', 'qfd_tt_ctlm', 'qfd_seq_su', 'qkd_rstseq'], status='decided v5 (r9)',
             change='the ROM-side reset roots rst_seq (seq_su), rst_seq_ctlm (tt_ctlm, pin rsi on the W face) and the '
                    'forwarded root rst_fwd_s (qkd_rstseq -> qfd_rstseq) are resets, not data: registered repeater trees '
                    'like every other reset over the reach (0 cycles per token)'),
        dict(id='T25', slots=['qkd_ectl', 'qkd_rhead'], status='decided v5 (r9)',
             change='the engine-control leaf\'s head pins follow the grown head (T20): e0 / e3, s0 / s3, t0 / t1 in line '
                    'with the head\'s S-face pins, so the far-head nets are 458 um (were 564-608 um after T20: 192 nets)'),
        dict(id='T26', slots=['*'], status='decided (coordinator 2026-10-13 09:25, el1013-pinreg-audit.log)',
             change='die clock delivery: the die brings the clock to tile X\'s clock pin at phi - R_X (R = insertion.json '
                    'boundary mean), never a common phase at the pins; hop A -> B: o_A + 0.76 ps/um x L + s_B <= 833.3 - '
                    '60 - SKEW (90 on one level, 150 across levels); tiles with R <= 300 ps share one level, R > 300 takes '
                    'an earlier trunk tap; boundary spread <= 80 ps; clock_entry.die_arrival per slot is stamped from '
                    'the pinreg audit of the case (contract_v5_tp8.py --stamp)'),
        dict(id='T22', slots=['qkd_seq'], status='decided v5 (port list owed by el1013-qwen-kvcentre)',
             change='merged-die sequencer: rf / tf deleted, r_sd[55:0], t_ds[186:0], t_flt deleted, r_kvd from seq_su, '
                    't_pw to tt_ctlm, gq / gr kept; valid / tag / credit ports as x_d + x_cr when ot_qkvd_seq_m is posted')]
    C['deltas'] = [d for d in C.get('deltas', []) if d['id'] not in {n['id'] for n in new}] + new
    D = {d['id']: d for d in C['deltas']}
    if 'T9' in D and 'T20' not in D['T9']['status']:
        D['T9']['status'] += '; superseded by T20 (712.8)'
    for k in ('T7', 'T8', 'T10', 'T12', 'T13'):
        if k in D and 'generator follows' not in D[k]['status']:
            D[k]['status'] += '; v5: the generator follows (case = contract)'
    # ---- open items: the v4 generator follow-ups are done; the seams are closed or re-stated
    O = C.setdefault('open_items', {})
    for k in list(O):
        O[k] = [m for m in O[k] if not m.startswith(('v4 GENERATOR', 'v4 SEAM', 'v4 q13 03:55', 'v5 '))]
    for k in ('qkd_ctrl', 'qkd_ctrl_n', 'qfd_tt_up4_g'):
        O.pop(k, None)

    def item(k, *msgs):
        O[k] = sorted(set(O.get(k, [])) | set(msgs))
    item('qfd_sp_vector_memory',
         'v5 SEAM (ask el1013-qwen-vm): which leaf assembles the head-chain root word {ib_go, ib[378:0], xl[127:0]} + '
         'ready on the S face (xw at the W end, xe at the E end): the VM parent RTL exports x_q (65,536 b through '
         'ot_qfd_vm_xqface_t) and no xw / xe port; the die provides ib from tt_ctlm on the S face',
         'v5: region-level pins are provisional (faces toward the die peers); leaves rowrd_t / gctl_t / xplane_t / '
         'xrelay_t have no closed view')
    item('qfd_tt_ctlm', 'v5 T18 (a): BODY LACKS PORT ib[379:0] (ME spine tgo / tb to the head root); mer0..2 (me_en to the '
                        'result serializers) and rf0..2 (their faults) are new slot pins: owner el1011-q-seq',
         'v5: me_en arrives at the VM / serializers through different relay depths: the control tile announces me '
         'max-depth edges early and the shallower legs are padded (same rule as the tree pads); not yet in RTL')
    item('qfd_seq_su', 'v5 T18 (c): the slot wrapper owns the registered 8:1 cbr reducer (+1 cycle on st_rdy); bench + '
                       'mutant with it before the M5 re-route (el1013-qwen-romspine)')
    item('qfd_io_xfifo', 'v5 T18 (e): o_coll_seq is valid-only (517 b), i_seq_coll = data 547 b + credit 1 b')
    item('qkd_ctrl_pc', 'v5 T17: RTL owed (ot_qwen_kv_strip_leaves.sv qkd_ctrl_pc: head + pcport KVW 2 + kcmd tap + the '
                        'request chain stage), bench + mutant, kit, --cts gate (el1013-qwen-kvstrips)')
    item('qkd_ctrl_kc', 'v5 T17: RTL owed (kc async FIFO + PHY request port + HBM clock / reset entry)')
    item('ot_hbm3e_phy', 'v5 T17: regenerate the abstract with the per-PC pin plan (tools/qwen_kv_die/tp8b_v5.py phy_repin)')
    item('qkd_rhead', 'v5 T20: build qkh_head_hs at 712.8 x 453.6 (el1013-qwen-kvleaves); pin offsets from its LEF at closure')
    item('qfd_tile_nk', 'v5 T14: tile parent at 311.04 x 1,317.6, layer cap M5, tap[507:0], rst_n E (el1011-q-tile)')
    for c in PENDING_IO:
        item(c, 'v5 T21: cluster parent owed (qfd_link_adp512 + FDI relay stations + PHY abstract; el1013-qwen-romio); '
                'qfd_link_adp512-m5a failed GRT on M4 (11 overflow): structural pin / channel repair first')
    item('qfd_io_xfifo', 'v5 T21: link words as x_d + x_v + x_cr on both sides; lf0..3 = the link clusters\' fault bits')
    item('qkd_host', 'v5 T21: host FDI is 2,089 b at RXD 512 (flit 1,043): the adapter in qkd_host follows '
                     '(el1013-qwen-kvcentre)')
    item('qkd_rstseq', 'v5 T23: the closed leaf has ports without a die net (boot_done / boot_ok / link_up / soft_rst in; '
                       'boot_go / rst_st / rso_host / rso_link out): the die nets are owed by el1013-qwen-kvcentre')
    item('qkd_ectl', 'v5 T25: rebuild the slot tile on the aligned head pins (qkd_ectl_slot-q13r3 failed hold; '
                     'el1013-qwen-kvleaves)')
    for c in ('qkd_pll', 'qfd_clkrx'):
        item(c, 'v5 T19: hard-macro abstract owed (LEF + SS / TT / FF lib, el1013-qwen-romio)')
    item('qkd_seq', 'v5 T22: ot_qkvd_seq_m port list owed (el1013-qwen-kvcentre); the slot then takes it (v5b)')
    C['open_items'] = {k: v for k, v in sorted(O.items()) if v}
    # ---- sub layouts
    sub = C.setdefault('sub_layouts', {})
    if 'qkd_rhead' in sub:
        sub['qkd_rhead']['plan'] = 'qkh_head_hs at 712.8 x 453.6 (coordinator grant 2026-10-13; el1013-qwen-kvleaves.log)'
    sub['qkd_ctrl_strip'] = dict(kind='abutment', plan='el1013-qwen-kvstrips.log 08:06 (no parent block: the die places the leaves)',
                                 rows=[dict(cell='qkd_ctrl_pc', tile='pc', count=32, w=247.512, h=378.0, layer_cap='M5'),
                                       dict(cell='qkd_ctrl_kc', tile='kc', count=1, w=247.512, h=45.36, layer_cap='M5')])
    # ---- file level
    area = collections.Counter()
    for s in C['slots'][1:]:
        area[s['cell']] += s['outline']['w'] * s['outline']['h'] / 1e6
    fp = C.setdefault('floorplan', {})
    dmm2 = die['outline']['w'] * die['outline']['h'] / 1e6
    tot = sum(area.values())
    fp.update(die_um=[die['outline']['w'], die['outline']['h']], die_mm2=round(dmm2, 3), slot_mm2=round(tot, 3),
              slot_share=round(tot / dmm2, 4), channel_share=round(1 - tot / dmm2, 4),
              slots_by_cell_mm2={k: round(v, 3) for k, v in sorted(area.items())})
    C['layer_plan'] = dict(tile_cap='M5', die_over_tiles='M6 horizontal (75 %), M8 horizontal, M9 vertical',
                           cut_model='results/arch/qwen_tp8_1012/cuts.py CAP_MODE v3, CLUSTER_PLAN M6', rule='bits / usable <= 0.60')
    C.pop('regen_objects', None)

    def cnt(c_):
        return ', '.join(f'{k} {n}' for k, n in sorted(c_.items())) or 'none'
    C['changelog'] = [c for c in C.get('changelog', []) if c.get('version') != V] + [dict(
        version=V, when=when,
        change='re-derived from the case of the v5 generator (' + LOG + '; tools/hier_contract/contract_v5_tp8.py' +
               (', ' + source_note if source_note else '') + '): T14 tile 1,317.6 / die M6 over tiles / tap 508; T15 SU '
               'group N of the VM; T16 crom +32.4; T17 control strips as leaves + PHY per-PC pins; T18 seq_su bundles; '
               'T19 reset leaves and trees; T20 rhead 712.8; T21 ROM IO (host PHY abstract bound, clusters owed); T22 '
               'qkd_seq ports; T23 closed views adopted pin for pin; T24 ROM reset roots in the tree; T25 ectl head pins; '
               'T26 die clock delivery.  Slots with a new '
               'outline or pin list: ' + cnt(changed) + '.  New cells: ' + cnt(new_cells) + '.  Removed: ' + cnt(gone) +
               '.  Moved only: ' + cnt(moved) + '.  Every other slot keeps its v4 record')]
    C['version'] = V
    C['updated'] = when
    die['version'] = V
    die['notes'] = re.sub(r'contract v\d+', f'contract v{V}', die.get('notes', ''))
    return C


def stamp_clock(C, audit):
    """T26: per-cell die clock entry (pinreg_audit.py v2 tiles[].die_clock) into every slot of that cell"""
    T = {t['cell']: t['die_clock'] for t in audit.get('tiles', []) if t.get('die_clock')}
    n = 0
    for s in C['slots'][1:]:
        d = T.get(s['cell'])
        if not d:
            continue
        R = d['reference_ps']
        ce = s.setdefault('clock_entry', {})
        ce['die_arrival'] = dict(vs_phi_tt_ps=d['entry_offset_ps'], vs_phi_ff_ps=d.get('entry_offset_ff_ps'),
                                 reference_ps=R, reference_src=d.get('reference_src'),
                                 boundary_spread_ps=d.get('boundary_spread_ps'),
                                 level='common (R <= 300 ps)' if R <= 300.0 else f'early trunk tap by {round(R - 300.0, 1)} ps; its hops at SKEW 150')
        n += 1
    r = audit.get('rule', {})
    C['clock_delivery'] = dict(
        rule='clock at tile X clock pin = phi - R_X (insertion-compensated); never a common phase at the pins',
        hop='o_A + w x L + s_B <= T - U - SKEW', period_ps=r.get('period_ps'), setup_unc_ps=r.get('setup_unc_ps'),
        skew_same_level_ps=r.get('die_skew_ps'), skew_across_levels_ps=150.0, wire_ps_per_um=r.get('wire_ps_per_um'),
        max_boundary_spread_ps=r.get('max_spread_ps'), level_cap_ps=300.0,
        source=f"pinreg audit {audit.get('contract')} v{audit.get('contract_version')} @ {audit.get('source_commit')}",
        cells_stamped=sorted(T), slots_stamped=n,
        cells_without_view=sorted(q['cell'] for q in audit.get('not_auditable', [])))
    return n


def seams(C):
    W = {}
    for s in C['slots'][1:]:
        W.setdefault(s['cell'], {base(p['name']): V4.bits(p) for p in s.get('pins', [])})
    bad = []
    for ca, pa, cb, pb in SEAMS_TAP:
        a, b = W.get(ca, {}).get(pa), W.get(cb, {}).get(pb)
        if not a or not b or a != b:
            bad.append(f'{ca}.{pa} {a} b vs {cb}.{pb} {b} b')
    return bad


def case_slots(C, case):
    """every non-relay, non-reset-repeater instance of the case is a slot at the case position and outline"""
    sys.path.insert(0, str(HERE.parent / 'qwen_kv_die'))
    from hier_contract_export import parse_lef
    case = Path(case)
    lef = {}
    for f in sorted(case.glob('*.lef')):
        parse_lef(f, lef)
    S = {s['name']: s for s in C['slots'][1:]}
    bad, n = [], 0
    for line in open(case / 'place.tcl'):
        m = re.search(r'findInst (\S+)\]\s+([\d.]+)\s+([\d.]+)\s+(\w+)', line)
        if not m or m.group(1).startswith(('rly_', 'rstt_')):
            continue
        n += 1
        s = S.get(m.group(1))
        if s is None:
            bad.append(f'{m.group(1)}: no slot')
        elif abs(s['origin']['x'] - float(m.group(2))) > 1e-3 or abs(s['origin']['y'] - float(m.group(3))) > 1e-3:
            bad.append(f'{m.group(1)}: slot origin {s["origin"]["x"]}, {s["origin"]["y"]} != case {m.group(2)}, {m.group(3)}')
    return bad, n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check')
    ap.add_argument('--case')
    ap.add_argument('--stamp', help='contract to stamp in place with --clock (T26)')
    ap.add_argument('--clock', help='pinreg_audit.py JSON of the case')
    a = ap.parse_args(argv)
    if a.stamp:
        C = json.load(open(a.stamp))
        n = stamp_clock(C, json.load(open(a.clock)))
        Path(a.stamp).write_text(json.dumps(C, indent=1) + '\n')
        print(json.dumps(dict(stamped_slots=n, cells=C['clock_delivery']['cells_stamped'])))
        return 0
    C = json.load(open(a.check))
    res = V4.check(C)
    res['seam_v5'] = seams(C)
    if a.case:
        res['case'], n = case_slots(C, a.case)
        print('case instances checked', n)
    fail = 0
    for k in ('schema', 'overlap', 'span', 'seam', 'seam_v5', 'case'):
        if k in res:
            print(f'{k.upper()} {"PASS" if not res[k] else "FAIL"} {len(res[k])}', *res[k][:8], sep='\n  ' if res[k] else ' ')
            fail += bool(res[k])
    print(json.dumps(dict(version=C['version'], slots=len(C['slots']), slot_share=C.get('floorplan', {}).get('slot_share'))))
    return 1 if fail else 0


if __name__ == '__main__':
    sys.exit(main())
