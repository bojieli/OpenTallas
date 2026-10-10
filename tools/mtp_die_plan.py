#!/usr/bin/env python3
"""MTP die / array plan for the DS-V4.1 ROM S81 array and the HBM accelerator (stream mtp-die, 2026-10-08).

Top-down (design-top-down-from-a-budget): the MTP step (draft -> verify -> accept) is split into per-stage and
per-block budgets the block streams (mtp-rom, mtp-hbm) route against; then the die / array homes of every MTP function
(replicate-hardened-elements-sized-to-goal, die-count-is-not-scarce, v41-array-realistic-interconnect: full FEC on
every off-package link).

Inputs are committed records (listed with sha256 in the output) plus the die-generator check outputs of the MTP
variants (results/arch/mtp_die_20261008/checks/*.txt, produced by tools/dsrom_s81_fulldie.py check / tools/
hbm_accel_die_fp.py check, see README).  Nothing here is a measurement: every row says measured / derived / budget.

    python3 tools/mtp_die_plan.py            # writes results/arch/mtp_die_20261008/plan.json
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/arch/mtp_die_20261008'
CLK_MHZ = 1200.0
CYC_US = 1.0 / CLK_MHZ

REC = dict(
    audit_ar='results/arch/reprice_20261008/reprice.json',
    recovery='results/rtl/dsrom_recovery_20261004/composition.json',
    draft_lever='results/rtl/dsrom_recovery_20261004/levers/draft.json',
    draft_place='results/rtl/dsrom_recovery_20261004/draft/placement.json',
    rack='results/arch/dsrom_s81_rack_20261006/rack.json',
    head_model='results/uarch/dsrom_l2_head_mac_20261004/model.json',
    wfc='results/rtl/dsrom_wfc_split_20261006/closure.json',
    wfc_phys='results/rtl/dsrom_wfc_split_20261006/routes_r22_src_r11_stg.json',
    wfc_res='results/uarch/dsrom_s81_wfc_parent_allocation_20261006/model.json',
    fused_head='results/rtl/dsrom_fused_draft_head_20261004/l1_compose.json',
    hbm_ctl='results/rtl/hbm_accel_fmax_inventory_20261004/ctl_takeover_20261005/closure.json',
)
HBM_BLOCKS = ('accept_a0', 'argmax_f1', 'ctl_f2', 'scratch_c2', 'spec_f3', 'topk_f3', 'union_f3', 'fence_a1')


def J(rel):
    return json.loads((ROOT / rel).read_text())


def sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def r(v, n=3):
    return round(v, n)


# ------------------------------------------------------------------------------------------------ check outputs
def _json_blocks(text):
    """the top-level JSON objects a generator 'check' prints, in order"""
    out, dec, i = [], json.JSONDecoder(), 0
    while True:
        j = text.find('{', i)
        if j < 0:
            return out
        try:
            o, k = dec.raw_decode(text, j)
            out.append(o)
            i = k
        except json.JSONDecodeError:
            i = j + 1


def check(name):
    p = OUT / 'checks' / f'{name}.txt'
    if not p.is_file():
        return dict(status='missing', file=str(p.relative_to(ROOT)))
    t = p.read_text()
    bl = _json_blocks(t)
    rec = dict(file=str(p.relative_to(ROOT)), sha256=hashlib.sha256(t.encode()).hexdigest())
    if 'Traceback' in t:
        rec['status'] = 'FAIL'
        rec['error'] = [ln for ln in t.splitlines() if 'Error' in ln][-1:]
        return rec
    rec['status'] = 'PASS'
    for o in bl:
        if 'overlaps' in o:
            rec['legality'] = {k: o[k] for k in ('instances', 'overlaps', 'outside') if k in o}
        if 'generated_pin_clashes' in o:
            rec['pin_clashes'] = dict(k1=o['generated_pin_clashes'], k16=o.get('k16_clashes'))
        if 'margin_lint' in o:
            ml = o['margin_lint']
            rec['margin_lint'] = {k: ml.get(k) for k in ('verdict', 'reach_violations', 'far_side_relays', 'chains',
                                                         'reach_um', 'fail', 'warn') if k in ml}
        if 'die_mm2' in o:
            rec['outline'] = {k: o[k] for k in ('die_mm2', 'W', 'H', 'notes', 'power') if k in o}
        if 'placed_footprint_mm2' in o:
            rec['plan'] = {k: o[k] for k in ('placed_footprint_mm2', 'utilisation', 'instances', 'slot') if k in o}
    return rec


# ------------------------------------------------------------------------------------------------ 1. budget sheet
def budget():
    rp = J(REC['audit_ar'])
    rc = J(REC['recovery'])['MTP']
    tau = 4.159
    ds = {}
    for mode, key in (('half_phl', 'half_phl'), ('full_rate_shared98', 'full_rate_shared98')):
        mtp = rp['ds_rom']['after'][key]['MTP_tok_s']
        step = tau * 1e6 / mtp
        ds[mode] = dict(MTP_tok_s=mtp, step_us=r(step))
    # term split of today's HALF_PHL step: draft and seed from the recovery composition (+ the 195-cycle head SAFE
    # adder of the re-price), verify = the remainder (= AR + 5 II)
    head_occ = rc['draft_terms']['head_occ_us']
    r_markov = rc['draft_terms']['r_markov']
    draft = rc['draft_us'] + 195 * CYC_US
    seed = rc['seed_commit_us']
    blocks = J(REC['draft_lever'])['blocks_old_new_us']['block_us_new']
    blocks_total = sum(blocks)
    fec = rc['draft_us'] - blocks_total - 5 * head_occ * (1 + r_markov)
    step = ds['half_phl']['step_us']
    verify = step - draft - seed
    ar_us = 1e6 / rp['ds_rom']['after']['half_phl']['AR_tok_s']
    ii = (verify - ar_us) / 5
    wfc = J(REC['wfc'])['charge']
    ds_rom = dict(
        basis='today\'s HALF_PHL re-price (results/arch/reprice_20261008: 4,351.6 tok/s, tau 4.159); draft / seed terms '
              'from the recovery composition (dsrom_recovery_20261004/composition.json MTP) + the re-price head SAFE '
              'adder (195 cycles); verify = step - draft - seed (DERIVED); II = (verify - AR) / 5 (DERIVED)',
        step_us=r(step), verify_us=r(verify), draft_us=r(draft), seed_commit_us=seed, AR_us=r(ar_us), II_us=r(ii),
        phases=[
            dict(phase='verify', us=r(verify), rule='AR + 5 x II (6 positions through the 120-stage wavefront)',
                 blocks=[
                     dict(block='WFC (ot_rom_pkg_ctrl_wfc src/stg) every stage', budget='handoff <= 49 cycles a '
                          'position a stage (measured 49, ref 46); hop delta <= 13 cycles a stage hop (measured)',
                          class_='measured'),
                     dict(block='WFC shims (dsfd_wfc_vmx VM 1.2/0.9 GHz 3:4 crossing, _lnk, _tok, _cep)',
                          budget='<= 5 cycles each way on the VM crossing (meso_d4 class), <= 2 cycles on link / '
                          'token / core endpoint pin flops; total shim adder <= 14 cycles a stage a position',
                          class_='budget'),
                     dict(block='worst stage (II limiter)', budget=f'II <= {r(ii, 2)} us: stage busy x (1 + {wfc["measured_interval_overhead"]}) + '
                          'hop + cable; the MTP shims may add <= 0.1 % to II (<= 28 ns)', class_='derived'),
                     dict(block='head dies (verify lm_head, 6 positions)', budget=f'{head_occ} us a position (head '
                          'stage occupancy, inside the head stage busy)', class_='measured'),
                 ]),
            dict(phase='accept', us=None, rule='inside seed_commit: accept + acc_n / squash broadcast',
                 blocks=[
                     dict(block='ot_dsrom_mtp_seq accept (ot_hdc_accept NSLOT 8 / NW 17) on head die h0',
                          budget='<= 3 cycles compare + 2 pin-flop cycles; the 12-die argmax merge result arrives '
                          'through the head collective (existing)', class_='budget'),
                     dict(block='acc_n / bonus / squash / epoch word', budget='rides the existing token-return hop '
                          '(head -> S0, 1,008 cycles full KP4 + 4 flight); +1 field (16 b) in the token word; the '
                          'squash of in-flight wavefront positions is the WFC kill on the next stage boundary '
                          '(no extra hop)', class_='budget'),
                 ]),
            dict(phase='draft', us=r(draft), rule='3 DSpark blocks + 5 serial head steps (lm_head sweep + Markov '
                 'row + bias + argmax) + closure adders',
                 blocks=[
                     dict(block='DSpark blocks mtp.0 / mtp.1 / mtp.2 (DP1 primary on head dies h0..h3, experts on the '
                          'draft row packages)', budget=f'{[r(b, 3) for b in blocks]} us (measured element RTL on '
                          f'the S81 L0 graph) + full-FEC delta {r(fec, 3)} us; package-pair fan-out (UCIe crossings '
                          'for mtp.1 and half of mtp.2) <= 0.2 us a step', class_='measured + budget'),
                     dict(block='draft link (primary -> row package A die, per row)', budget='x_row 10,240 B + ids '
                          '64 B + weights 64 B out, ret_row 5,120 B back a block a row; 512 b / cycle a direction '
                          '(S81 link chain): 160 + 80 cycles serialisation, hop 1,008 cycles full KP4 (measured '
                          'hops x_row 0.3567 / ret_row 0.29 us incl. serialisation)', class_='measured'),
                     dict(block='UCIe A <-> B (in package)', budget='<= 10 ns + 2 x 8 cycles endpoint, cut-through; '
                          '512 b / cycle', class_='budget'),
                     dict(block='draft head step x 5 (head bundles, fused bias + argmax)', budget=f'{head_occ} us '
                          f'sweep x (1 + r_markov {r_markov}) + 39 cycles bias/argmax SAFE adder a sweep', class_='measured'),
                     dict(block='Markov head (markov_head.embed 129,280 x 32 lookup + markov_head.head 129,280 x 32 '
                          'matvec a draft row)', budget=f'<= {r(head_occ * r_markov * 1000, 1)} ns a draft row '
                          '(r_markov share of the sweep) + the 64 B embed-row broadcast to the 12 head dies <= 24 '
                          'cycles: NO RTL (gap MTP-G1, review_queue/mtp-die.md)', class_='model-only'),
                     dict(block='ot_dsrom_mtp_seq chain FSM', budget='<= 4 cycles issue a head step; seed dispatch '
                          'to the primary is die-local on h0 (primary on head dies): the head -> draft board hop is '
                          'removed from the seed path', class_='budget'),
                 ]),
            dict(phase='seed_commit', us=seed, rule='measured seed_commit_over_verify ratio x verify (reduced '
                 'vehicle)', blocks=[]),
        ],
        link_widths=dict(stage_link='512 b / cycle each way (ot_dsrom_link_rt, S81 link chains tx / rx)',
                         draft_row_link='512 b / cycle each way, 1 SerDes a row package a primary rank die',
                         ucie_pair='512 b / cycle each way (in-package UCIe, ot_pdie_ucie)',
                         token_return='existing word + 16 b acc_n / squash / epoch field'),
    )
    h_step = tau * 1e6 / rp['hbm_ds']['upper']['after']['MTP_tok_s']
    h_draft, h_seed, h_union = 45.28, 3.567, 76.19
    hbm = dict(
        basis='re-price upper bound 3,700.3 tok/s (step = tau / rate); draft 45.28 us measured (dshbm_dspark_draft_'
              '20261004), seed / commit 3.567 us, union 76.19 us W19 model (token-path.log)',
        step_us=r(h_step), verify_us=r(h_step - h_draft - h_seed), draft_us=h_draft, seed_commit_us=h_seed,
        phases=[
            dict(phase='verify', us=r(h_step - h_draft - h_seed), blocks=[
                dict(block='SM (ot_hbm_accel_sm_v NC 8)', budget='P = 6 positions on the MMA columns of one weight '
                     'fetch: NC 8 >= 6, no added SM columns (mtp-hbm 21:23)', class_='measured'),
                dict(block='expert union (union_f3 in hfd_mtp)', budget=f'+1 cycle a flush; union increment '
                     f'{h_union} us (W19 model, to be measured)', class_='model'),
                dict(block='hfd_mtp <-> cmdproc command round trip', budget='<= 2 x 6 relay stages + 2 (PRL) + 2 pin '
                     'flops = 16 cycles a command; total MTP control <= 1 % of the step (11.2 us)', class_='budget'),
                dict(block='spec_state rollback (spec_state_f)', budget='<= 2 cycles a request', class_='budget'),
            ]),
            dict(phase='accept', blocks=[
                dict(block='accept_a0 + argmax_f1', budget='argmax: +1 cycle a row (f1); die merge 16 cycles; '
                     '96-die select 24 cycles through hfd_coll (2 x 10 relay stages hfd_mtp <-> hfd_coll)',
                     class_='measured + derived'),
            ]),
            dict(phase='draft', us=h_draft, blocks=[
                dict(block='draft chain', budget='5 x 1.212 us chain step (52 % merge transport) + head pass 3,671 '
                     'cycles; 23 draft collectives charged full FEC (gap: not charged today)', class_='measured'),
                dict(block='logit rows su_red -> hfd_mtp', budget='20 relay stages (8.0 mm), once a pass: <= 6 x 20 '
                     'cycles a step', class_='derived'),
                dict(block='drafter router (topk f384)', budget='+1 cycle a selection', class_='measured'),
            ]),
        ],
    )
    return dict(ds_rom=ds_rom, hbm=hbm, tau=tau)


# ------------------------------------------------------------------------------------------------ 2. DS ROM array
def array():
    dl, pl = J(REC['draft_lever']), J(REC['draft_place'])
    rack = J(REC['rack'])
    hm = J(REC['head_model'])['basis']
    die_mm2 = dl['placement']['dies']['die_mm2']
    pair_words = pl['capacity']['pair_words']
    die_words = pl['capacity']['die_words']
    pairs_full = die_words // pair_words                   # 2,417 (decision layer die)
    prim_pairs = math.ceil(pl['capacity']['words_per_rank_die']['draft.primary'] / pair_words)
    rep_pairs = math.ceil(pl['capacity']['words_per_rank_die']['draft.mtp0.rep0'] / pair_words)
    globals_ = hm['global_pairs'] - hm['lm_head_pairs_total']
    head_dies = rack['counts']['head']
    markov_bytes = 2 * 129280 * 32 * 2                     # embed + head, BF16
    markov_pairs_die = math.ceil(markov_bytes / 2 / hm['pair_bytes'] / head_dies) + math.ceil(markov_bytes / 2 / hm['pair_bytes'])
    head_pairs = math.ceil(globals_ / head_dies) + prim_pairs + markov_pairs_die
    rows, ranks, blocks_ = 5, 4, 3
    l1_pairs = 1792
    a_pairs = rep_pairs + math.ceil(rep_pairs / 2)
    topo = [
        dict(name='S15 star (DP1-EP5 as recorded)', primary_dies=4, draft_dies=64,
             links_per_primary_die=rows * blocks_, board_links_total=4 * rows * blocks_, ucie_pairs=0,
             added_hops_on_path=0, path_delta_us=0.0,
             die_edge='UCIe + 10 SerDes max per S81 edge column: 15 extra need 7 + 7 + 1 corner (draft.json)',
             verdict='REJECT: 15 SerDes + 1,024-b buses per primary die (9.28 mm2), 64 dies (+12 vs the rack)'),
        dict(name='T2 board tree (block lead relays to 4 sibling replicas)', primary_dies=4, draft_dies=64,
             links_per_primary_die=blocks_, board_links_total=4 * blocks_ + 4 * blocks_ * (rows - 1),
             ucie_pairs=0, added_hops_on_path=2 * blocks_,
             path_delta_us=r(2 * blocks_ * rack['draft_links']['hop_cycles'] * CYC_US, 3),
             verdict='REJECT: +2 full-FEC board hops a block (+5.0 us a step, -0.5 % MTP) and still 64 dies'),
        dict(name='P2 package-pair fan-out (ADOPT-PROPOSED)', primary_dies=0, primary_on='head dies h0..h3 (one head '
             'TP4 group: the head die repeats the layer spine: attention, SU, HC, collectives; its 4 HBM stacks hold '
             'the drafter KV / window caches)', draft_dies=rows * ranks * 2,
             links_per_primary_die=rows, board_links_total=4 * rows, ucie_pairs=rows * ranks,
             added_hops_on_path=0, path_delta_us=0.2,
             rule='row r, rank k: one 2-die package; die A = mtp.0 experts 0..127 (rank-k slices) + mtp.2 experts '
                  '0..63, die B = mtp.1 experts 0..127 + mtp.2 experts 64..127.  The primary rank-k die sends row r\'s '
                  'x_row / ids / weights to die A (board, full KP4) which forwards over UCIe what B needs (cut-through); '
                  'each expert output returns to A, which sums the row\'s 3 experts in id order (the DP1-EP5 rule, '
                  'exact: the per-expert results are the same values, the sum order is unchanged) and returns ret_row '
                  'to the primary.  mtp.0 rows: 0 UCIe crossings; mtp.1: 2; mtp.2: 0 or 2 (expert split)',
             capacity=dict(die_A_pairs=a_pairs, die_B_pairs=a_pairs, die_pairs_available=l1_pairs,
                           fill=r(a_pairs / l1_pairs, 3), rep_pairs_one_block=rep_pairs,
                           note='layer1 recipe (m221pq 1,792 pairs), q words on q and BF pairs (full_shared rule)'),
             verdict='ADOPT-PROPOSED: 5 SerDes a primary head die (fits the edge column: 4 + 3 W, 4 + 2 E), 40 '
                     'draft dies (-12 vs the rack, -24 vs DP1-EP5), +0.2 us a step (UCIe crossings, budget)'),
    ]
    p2 = topo[2]
    counts_rack = rack['counts']
    counts_new = dict(counts_rack, draft=p2['draft_dies'], src=dict(counts_rack['src'], draft='tools/mtp_die_plan.py P2 package-pair fan-out (5 rows x 4 ranks x 2 dies)'))
    counts_new['dies'] = sum(counts_new[k] for k in ('layer', 'head', 'table', 'draft'))
    return dict(
        reconciliation=dict(
            finding='the 64 vs 52 conflict: DP1-EP5 needs 64 dedicated dies (4 primary + 60 expert replicas); '
                    'its "12 baseline draft dies" were TP4 x 3 blocks of the old timing model, and the rack\'s 12 '
                    'head dies still carry the WHOLE drafter as head content (head model basis: 15,131 DSpark pairs '
                    '= 7.93 GB over 12 dies, 1,261 a die).  So the rack (52) double-counts nothing but under-counts '
                    'the dedicated draft dies by 12, and the head dies carry 15,131 pairs that DP1-EP5 never reads.',
            dspark_pairs_on_head_dies=hm['dspark_pairs'], head_content_pairs_per_die_before=1472,
            head_content_pairs_per_die_after=head_pairs,
            head_after_basis=f'non-lm-head globals {globals_} / {head_dies} + DP1 primary {prim_pairs} (words '
                             f'{pl["capacity"]["words_per_rank_die"]["draft.primary"]}) + Markov {markov_pairs_die} '
                             '(markov_head.head rows of the die\'s vocab share + the full 129,280 x 32 embed table '
                             'replicated per head die for a local lookup)',
            dies=dict(rack=counts_rack['draft'], dp1_ep5=dl['placement']['dies']['total'], proposed=p2['draft_dies']),
        ),
        topologies=topo,
        die_counts=dict(rack_20261006=counts_rack, proposed=counts_new,
                        silicon_delta_mm2=r((counts_new['dies'] - counts_rack['dies']) * die_mm2, 1),
                        note='stage count 85 here is the rack record; the 1,792 mapping (120 stages / 480 layer dies '
                             'HALF_PHL) re-sizes layer dies only; head / table / draft counts are independent of the '
                             'stage count (s81-dies owns the array v2 composition)'),
        homes=dict(
            sequencer='ot_dsrom_mtp_seq (dsfd_mtp_seq) on head die h0 (the head die that ends the 12-die argmax merge '
                      'and launches the token return to S0): spine centre stack between capture (argmax tokens in) and '
                      'collective (token return / seed out); same recipe on all 12 head dies (inactive on h1..h11)',
            accept='inside ot_dsrom_mtp_seq (ot_hdc_accept NSLOT 8 / NW 17, closed on the HBM side SS +55.3 / FF +14.0)',
            markov_head='head dies: markov_head.head rows beside each die\'s lm-head vocab rows (32 extra words a row, a '
                        'second 32-term accumulator and the golden add order logits + markov in the head element: '
                        'NOT the 4,096 + 32 concatenation, which changes rounding) + the embed table (8.27 MB, 17 '
                        'pairs) on every head die; NO RTL (gap MTP-G1)',
            draft_primary='head dies h0..h3 (one head TP4 group), 282 pairs each + their spine (attention, SU, HC, '
                          'collectives) + the drafter window caches in the head dies\' HBM stacks',
            draft_experts=f'{p2["draft_dies"]} draft dies (layer1 recipe, {a_pairs} of 1,792 pairs), {rows} row '
                          f'packages x {ranks} ranks',
            wfc='every layer-class die (layer AND layer1): bound dsfd_wfc slab after the capture (the r3 / r4 layer1 '
                'die carries NO WFC at all today: the soft reservation was on the 4-stack scan die only)',
        ),
        links=dict(
            per_primary_head_die=dict(added_serdes=rows, fec='RS(544,514) KP4 full', hop_cycles=rack['draft_links']['hop_cycles'],
                                      width_b=512, note='real ot_pdie_serdes LEF in the head die edge column '
                                      '(W 4 + 3, E 4 + 2), each through its own link chain to the collective'),
            per_draft_die=dict(A='1 SerDes up (primary) + UCIe to B', B='UCIe to A only'),
            board_links_total=p2['board_links_total'], ucie_pairs=p2['ucie_pairs'],
        ),
    )


# ------------------------------------------------------------------------------------------------ 3. die areas
def areas(ch):
    wp = J(REC['wfc_phys'])['cases']
    src, stg = wp['r22/src_u55']['die_area_um2'], wp['r11/stg_u50']['die_area_um2']
    res = J(REC['wfc_res'])
    hbm_cells = {}
    for b in HBM_BLOCKS:
        p = ROOT / 'results/rtl/hbm_accel_fmax_inventory_20261004/ctl_takeover_20261005' / b / 'physical.json'
        hbm_cells[b] = json.loads(p.read_text())['design']['area_um2']
    return dict(
        wfc=dict(reservation_mm2=r(res['slot_area_mm2'], 4), real_need_mm2=r((src + stg) / 1e6, 4),
                 src_um2=src, stg_um2=stg, bound_slab='hub column width x 231.12 um (both blocks 196.56 um tall + '
                 '17.28 um halos); 0.399 mm2 gross at the 1,728 um m221pq column'),
        hfd_mtp=dict(cells_um2=r(sum(hbm_cells.values()), 1), by_block=hbm_cells,
                     slot_um=[466.56, 200.88], slot_mm2=r(466.56 * 200.88 / 1e6, 4),
                     util_cells=r(sum(hbm_cells.values()) / (466.56 * 200.88), 3)),
        dies={k: ch.get(k) for k in ch},
    )


# ------------------------------------------------------------------------------------------------ 5. token path
def token_schedule(b):
    d = b['ds_rom']
    return dict(
        ds_rom=[
            dict(op='verify wavefront', dies='all layer dies (WFC on every layer-class die) + head dies (lm_head x 6)',
                 us=d['verify_us'], positions=6, limiter='II'),
            dict(op='accept', dies='head die h0 (dsfd_mtp_seq)', cycles='<= 5'),
            dict(op='acc_n / squash broadcast', dies='head h0 -> S0 token return (existing hop + 16 b field)'),
            dict(op='seed', dies='head h0 -> h0..h3 (DP1 primary, die-local / head TP4)', us=d['seed_commit_us']),
            dict(op='DSpark blocks mtp.0..2', dies='head h0..h3 (primary) + 40 draft dies (5 row packages x 4 ranks)',
                 us=r(d['draft_us'] - 5 * 6.9892 * 1.00781, 3)),
            dict(op='draft head x 5 (lm_head sweep + Markov + bias + argmax)', dies='12 head dies (head bundles) + h0 '
                 '(sequencer: Markov embed broadcast, argmax merge)', us=r(5 * 6.9892 * 1.00781, 3)),
        ],
        hbm=[
            dict(op='verify P6 walk + union', die='every HBM die: SM columns NC 8, hfd_mtp union', us=b['hbm']['verify_us']),
            dict(op='accept / commit', die='hfd_mtp (low spine slot) + hfd_coll 96-die select'),
            dict(op='draft chain', die='SM + hfd_mtp argmax / Markov', us=b['hbm']['draft_us']),
            dict(op='seed / commit', die='hfd_mtp spec_state', us=b['hbm']['seed_commit_us']),
        ],
    )


# ------------------------------------------------------------------------------------------------ 4. extra items
def extras(b, ch):
    rack = J(REC['rack'])
    fec_delta = rack['link_basis']['hop_cycles'] - rack['link_basis']['light_fec_hop_cycles_was']   # full - light KP4
    d = 4096
    mh_bytes = 3 * d * 2                            # concat of the 3 BF16 main-hidden parts (golden dspark_seed mh)
    ser = math.ceil(mh_bytes * 8 / 512)             # cycles at the 512 b stage link
    window, speculative, row_b = 128, 6, 512        # window_tokens, gamma + 1 in-flight rows, head_dim FP8 row
    h_step = b['hbm']['step_us']
    h_add = 23 * 2 * fec_delta * CYC_US             # 23 draft collectives, 2 off-package hops each (die-switch-die)
    out = dict(
        main_hidden_transport=dict(
            what='the drafter seed reads mh = concat of the BF16 means of the 4 residual copies at the input of layers '
                 '37, 38, 39 (golden dspark_seed / main_hidden_part) for every committed position; main_proj + '
                 'main_norm then run on the DP1 primary (head dies h0..h3, mtp.0 seed projection)',
            capture='layer dies of the stages that hold layers 37 / 38 / 39: the hc-mean (sequential sum x 1/hc, '
                    'BF16: exact) on the SU at the layer input, staged at the WFC (the closed WFC src carries '
                    'SEND_HIDDEN / HID_DEST: binding to verify by mtp-rom)',
            transport='a TRAILING payload on the existing stage-hop flits from those stages to the head dies (cut-through: '
                      'the activation leads, the 8 KB part of each layer follows in the same link), then head -> '
                      'primary is die-local / head TP4',
            bytes_per_position=mh_bytes, link_bits=512, serialisation_cycles_per_hop=ser,
            latency_exposed_us=0.0, latency_basis=f'the trailing tail reaches the head {r(ser * CYC_US, 3)} us after '
                      'the last activation; the seed needs it only after the head lm_head sweep (6.99 us) and accept',
            link_occupancy_per_position_hop_pct=r(100 * ser / (b['ds_rom']['II_us'] / CYC_US), 2),
            hops='from the L37 stage to the head (the rest of the pipeline), each carrying <= 3 parts',
            class_='budget (no RTL: the trailing-payload framing is a WFC / link_rt change, mtp-rom)'),
        window_rows=dict(
            what='DSpark window rows (3 stages x 128-token window, kv_norm(wkv(main_x)) FP8, 512 B a row) + the '
                 'speculative rows of the in-flight step (gamma + 1 = 6) under the dead-row invariant',
            bytes_per_user=3 * (window + speculative) * row_b,
            home='head dies h0..h3 HBM (per-user state; the drafter KV rides on the head dies\' stacks); one '
                 'step reads 3 x 128 rows = 196,608 B a user, at the head die stack bandwidth << 1 us',
            rollback='no rollback hardware: rows of rejected positions are rewritten before read (dead-row invariant); '
                     'sizing to be confirmed with mtp-rollback (log not yet present at 22:00 PT)'),
        draft_fanout_price=dict(
            topology='P2 package-pair', board_hops_per_block='1 out + 1 back (in the measured block times)',
            ucie_crossings_per_step='mtp.1: 2 a row; mtp.2: <= 2 a row', added_us_per_step=0.2,
            area_per_primary_head_die_mm2=r(9.28 * 5 / 15, 2),
            area_basis='draft.json: 15 SerDes + hub FIFO slots + waypoints = 9.28 mm2 a die -> 5 = 3.09 mm2',
            mtp_rate_effect_pct=r(-100 * 0.2 / b['ds_rom']['step_us'], 3)),
        hbm_draft_fec=dict(
            crossings=23, hops_each=2, full_minus_light_cycles_per_hop=fec_delta,
            basis='rack link_basis: full KP4 hop 1,004 cycles vs light 909 (measured RTL hop); every off-package '
                  'link full FEC (OWNER 2026-10-06); 2 off-package hops a collective (die -> switch -> die)',
            added_us_per_step=r(h_add, 3), step_us_before=r(h_step, 3), step_us_after=r(h_step + h_add, 3),
            MTP_tok_s_before=r(b['tau'] * 1e6 / h_step, 1), MTP_tok_s_after=r(b['tau'] * 1e6 / (h_step + h_add), 1),
            class_='derived (priced, not measured)'),
    )
    return out


def hbm_fit(ch):
    lim = dict(H_um=26000.0, W_um=33000.0, mm2=858.0)
    rows = {}
    for k in ('hbm_r25', 'hbm_r25m', 'hbm_r25s', 'hbm_r25sm'):
        o = (ch.get(k) or {}).get('outline')
        if o:
            rows[k] = dict(W_um=o['W'], H_um=o['H'], mm2=o['die_mm2'], H_margin_um=r(lim['H_um'] - o['H'], 1),
                           W_headroom_um=r(lim['W_um'] - o['W'], 1),
                           area_headroom_mm2=r(lim['mm2'] - o['die_mm2'], 2), status=ch[k]['status'],
                           pin_clashes=ch[k].get('pin_clashes'), margin_lint=ch[k].get('margin_lint'))
    return dict(limits=lim, variants=rows, content=dict(
        hfd_mtp=dict(mm2=0.0937, where='low spine slot below the loader (spine column free bottom: 2.2 mm r25 / 2.1 mm '
                     'r25s), outline unchanged'),
        loader_mem=dict(mm2=0.3071, stations=88, chains='4 stacks x (request 904 b + response 624 b), worst 57 stages '
                        '(NE, 24.1 mm)', where='expert-fetch route lanes (new lane "lm" in the spine-side and hub-edge '
                        'channels, 96 k16 bundles)'),
        quant_smaller_slot=dict(mm2=None, note='inside the spine column: frees spine height, no outline change'),
        loader_host_if_fix=dict(mm2=None, note='ingest stream; budget: the remaining low-spine free area (~1.4 mm x '
                                '1.5 mm = 2.1 mm2 under hfd_mtp) + the W slack 242.8 um; width headroom 2.41 mm '
                                '(~62 mm2 at 25.73 mm) for anything larger'),
    ), options=[
        'width first: a 0.5-2.4 mm E or W strip (SerDes / host strips move out) = 12.9-62 mm2 at 25.73 mm',
        'collective + SerDes strip to the package partner die (2-die package): frees ~18 mm2 + the S-band channel',
        'content to a companion die (loader / host / quant): frees ~11 mm2',
        're-place: quant / su_full slots shrink (quant 4.6 % util)',
    ])


def main():
    ch = {n: check(n) for n in ('hbm_r25', 'hbm_r25m', 'hbm_r25s', 'hbm_r25sm', 's81_layer1_base', 's81_layer1_wfc',
                                's81_head_base', 's81_head_mtp')}
    b = budget()
    plan = dict(schema='opentallas.mtp-die-plan.v1', tool='tools/mtp_die_plan.py', stream='mtp-die 2026-10-08',
                budget=b, ds_rom_array=array(), areas=areas(ch), token_path_mtp=token_schedule(b),
                extras=extras(b, ch), hbm_die_fit=hbm_fit(ch),
                inputs={k: sha(v) for k, v in REC.items()})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'plan.json').write_text(json.dumps(plan, indent=1) + '\n')
    print(json.dumps(dict(step=b['ds_rom']['step_us'], verify=b['ds_rom']['verify_us'], II=b['ds_rom']['II_us'],
                          draft=b['ds_rom']['draft_us'], dies=plan['ds_rom_array']['die_counts']['proposed'],
                          checks={k: v.get('status') for k, v in ch.items()}), indent=1))


if __name__ == '__main__':
    main()
