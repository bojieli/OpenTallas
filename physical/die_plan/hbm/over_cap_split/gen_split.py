#!/usr/bin/env python3
"""HBM-P4-SPLIT (2026-10-23): hard-core cuts of the HBM d4g plan's over-cap leaves (plan_notes_v2.json over_cap).

Input : stats_summary.json (measured Yosys cell counts per module, parsed by stathier.py from the hierarchical
        synthesis .stat files named in each entry's `basis`; r18h5 recipe = tools/hbm_die_v15/synth_master.sh HIER=1,
        ASAP7 RVT TT, the v16w wrappers of the r18h5 die views).
Output: <master>.split.json per distinct master + index.json.  Each split.json:
  status       RTL-UNBENCHED = cut + twin written, bench not completed;
               DONE (cut + every crossing register to register, RTL twin benched or no RTL change needed) |
               CUT-ONLY (cores measured, but some crossings are not register to register; fix named) | OPEN
  cores        [{master, core_label, members, module, cells, srams, pins_bits}]   (one entry per hard core)
  glue         cells left flat in the partition (< 20k pieces, pin / seam registers, top-level glue)
  crossings    [{between, bits, kind, note}]   kind: REG->REG | REG->LOGIC->REG | SRAM-BOUNDED | COMB (needs fix)
  rtl          twin modules (opt-in by module name; pinned files unchanged), cycle cost, bench + mutant
  splits_entry the cells_evidence.json `splits` format consumed by taps_cores_v2.py ({parts:[[name,n,each]], glue,
               stat, note, total}) so HBM-P4 can drop it in.
Every number is MEASURED unless the field says EST.  CORE_BUDGET 350k.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BUDGET = 350_000
S = json.load(open(os.path.join(HERE, 'stats_summary.json')))


def M(stat, mod):
    """total cells of a module (short name prefix match) in a stats_summary entry"""
    mods = S[stat]['modules']
    hits = [k for k in mods if k == mod] or [k for k in mods if k.startswith(mod)]
    assert hits, (stat, mod)
    return mods[hits[0]]['total']


def L(stat, mod):
    mods = S[stat]['modules']
    hits = [k for k in mods if k == mod] or [k for k in mods if k.startswith(mod)]
    return mods[hits[0]]['local']


def entry(master, plan_types, status, cores, glue, crossings, rtl, note, stat_key, total):
    mx = max(c['cells'] for c in cores)
    assert mx <= BUDGET or status != 'DONE', (master, mx)
    parts = {}
    for c in cores:
        k = (c['part'], c['cells'])
        parts[k] = parts.get(k, 0) + 1
    for c in cores:
        c.pop('part')
    return dict(master=master, plan_types=plan_types, status=status, measured_total=total, basis=S[stat_key]['basis'],
                n_cores=len(cores), max_core_cells=mx, cores_cells=sum(c['cells'] for c in cores), glue_cells=glue,
                cores=cores, crossings=crossings, rtl=rtl, note=note,
                splits_entry=dict(parts=[[n, cnt, each] for (n, each), cnt in parts.items()], glue=glue,
                                  stat=S[stat_key]['basis'].split(' ')[0], total=total, note=note))


out = {}

# ------------------------------------------------------------------ IDX score quarter (q_os2)
sq = 'ot_hbm_idx_score_quarter_static'
h0, h1 = M('SPLIT:ot_hbm_idx_chunk_rt_h', 'ot_hidx_score_hcol'), None
hc = sorted({v['total'] for k, v in S['SPLIT:ot_hbm_idx_chunk_rt_h']['modules'].items() if k.startswith('ot_hidx_score_hcol')})
h1, h0 = hc[0], hc[-1]                                  # HALF 1 (no seed head) is the smaller
tail = M(sq, 'ot_hbm_idx_tail_native')
d_leaf = M(sq, 'ot_hbm_idx_chunk_rt') - M('SPLIT:ot_hbm_idx_chunk_rt_h', 'ot_hbm_idx_chunk_rt_h')
tot_h = S[sq]['total'] - 8 * d_leaf
cores = []
for e in range(2):
    for c in range(4):
        for g in range(4):
            for h in range(2):
                cores.append(dict(part=f'hcol{h}', master=sq + '_h', core_label=f'r{e}c{c}_k{g}h{h}', module=f'ot_hidx_score_hcol #(HALF {h})',
                                  members=[f'ge[{e}].gc[{c}].leaf.core.g_col[{g}].g_half[{h}].u_hc'],
                                  cells=h0 if h == 0 else h1, srams=0,
                                  pins_bits=dict(inp=2 + 1 + 1 + 568 + 544 + 32 + 33, out=35)))
for e in range(2):
    cores.append(dict(part='tail', master=sq + '_h', core_label=f'tail{e}', module='ot_hbm_idx_tail_native (closed leaf)',
                      members=[f'ge[{e}].u_t'], cells=tail, srams=0, pins_bits=dict(inp=1 + 1 + 4 + 4 + 4 * 4 * 32 + 16, out=1 + 4 + 64 + 4)))
glue = tot_h - sum(c['cells'] for c in cores)
out[sq] = entry(sq, ['q_os2'], 'DONE', cores, glue, [
    dict(between='leaf glue (W pin regs rq/rkey/hid) -> hcol (each of 8 per leaf)', bits=569 + 544 + 32 + 1, kind='REG->REG',
         note='query broadcast {qv_b,q_b} 569 b + the column key 544 b + 4 head ids 32 b land in the hcol region pin regs (q_p/key_p/hid_p); rst_col = the column reset relay output'),
    dict(between='hcol HALF0 -> hcol HALF1 (same column)', bits=33, kind='REG->REG', note='running sum cs[4] + cf[4]: cs_o (head 3) -> csi_p (head 4)'),
    dict(between='hcol HALF1 -> leaf glue', bits=33, kind='REG->REG', note='cs[8]/cf[8] cs_o -> c_sum and the leaf sum-bus register b_w'),
    dict(between='hcol -> leaf glue (online)', bits=2, kind='REG->REG', note='region onl flops -> rdy1'),
    dict(between='leaf glue -> next leaf glue (W->E seam, flat glue)', bits=568 + 2176 + 30 + 1 + 4 + 1 + 552, kind='REG->REG', note='unchanged pinned seam chain (E pin regs -> next W pin regs)'),
    dict(between='leaf (e,3) glue -> tail e', bits=4 * 138, kind='REG->REG', note='sum bus e_bus reg -> tail input (unchanged)')],
    dict(twin='rtl/hbm_accel/index/quad_1017/ot_hbm_idx_score_quarter_static_h.sv (ot_hbm_idx_score_quarter_static_h / ot_hbm_idx_score_leaf_h, verbatim copies of the pinned modules with the leaf core -> ot_hbm_idx_chunk_rt_h)',
         split='rtl/hdc/v41x/ot_hbm_idx_chunk_rt_h.sv (ot_hidx_score_hcol HALF 0/1 = 2 masters x 64 instances)',
         cycle_cost_edges=0,
         bench='rtl/test/hbm_idx_static/run_chunk_rt_h_equiv.sh OUT pos|gap4|mut (lock-step vs pinned ot_hbm_idx_chunk_rt, every output every edge)',
         bench_result='ot-gold2 @bcc0334cd: pos PASS (GAPK 2: 2337 checks / 1063 nonzero sums; GAPK 4 PASS 2349; GAPK 2 SEED 7 PASS; GAPK 3 SEED 99 PASS), mutant MUT 1 FAIL (1245 errors) as required'),
    'leaf 1.55M (one key column ~383k > 350k): each key column cut at its head-pair region seam into two half-column cores '
    '(heads 0-3 / 4-7); every crossing was already a register pair (region pin regs, cs seam regs), so the twin is cycle-exact. '
    'Leaf W/E pin registers, chunk glue (input regs, head ids, valid line, online), quarter W glue, meta delays stay flat.',
    sq, S[sq]['total'])
out[sq]['measured_total_with_split'] = tot_h

# ------------------------------------------------------------------ TKM (c0)
tk = 'ot_hgi_coll_tkm_m_tp192'
tile = M(tk, 'ot_hgi_coll_tkm_tile_e86')
root = S[tk]['total'] - 32 * tile
cores = [dict(part='tile', master=tk, core_label=f'tile{t}', module='ot_hgi_coll_tkm_tile_e86 (-> ot_hgi_coll_tkm_tile_rg EW86 PT64)',
              members=[f'u.u.g_tiles[{t}].e86.u_tile'], cells=tile, srams=0,
              pins_bits=dict(inp=5 + 6 + 2 + 6 + 7 + 1 + 344 + 344, out=1 + 344 + 344 + 85 + 1)) for t in range(32)]
cores.append(dict(part='root', master=tk, core_label='root', module='ot_hgi_coll_tkm_static_p (own logic) + ot_hgi_coll_tkm_buffer',
                  members=['u.u (root logic: tick/calendar, decode + 4-sort, pass-1 capture, output lines)', 'u.u.u_buffer'],
                  cells=root, srams=2, pins_bits=dict(inp=2980 - 2 - 40 - 16 - 512 - 3 - 32 + 344 + 2, out=1 + 40 + 16 + 512 + 3 + 32 + 345 + 2)))
out[tk] = entry(tk, ['c0'], 'RTL-UNBENCHED', cores, 0, [
    dict(between='tile t -> tile t+1 (ins chain)', bits=345, kind='REG->REG', note='ovf_v/ovf_b output regs -> p_vg/p_bg input regs'),
    dict(between='tile t+1 -> tile t (up chain)', bits=344, kind='REG->LOGIC->REG', note='up_out reg -> X shift-register mux (conv) -> X regs: one 2:1 mux level, kept'),
    dict(between='root -> all 32 tiles (clr, conv broadcast)', bits=2, kind='COMB in pinned; REG->REG with PIPE 1',
         note='pinned root drives clr/conv from 32-bit tick comparators; PIPE 1 launches them from root flops (all tile inputs +1 edge). '
              'The 2-bit broadcast still spans the 32-tile row (~2 mm): repeaters only; a deeper registered tree = +1 edge per level on the same pattern'),
    dict(between='root -> tile 0 (entry)', bits=345, kind='REG->REG', note='entry/entry_v regs (PIPE 1: one more launch reg so it stays aligned with clr/conv)'),
    dict(between='tile 0 -> root (up[0])', bits=344, kind='REG->LOGIC->REG in pinned; REG->REG with PIPE 1', note='PIPE 1: up0_q pin register, consumers moved 2 edges later')],
    dict(twin='rtl/hbm_accel/generic/collective/tkm/ot_hgi_coll_tkm_static_p.sv (ot_hgi_coll_tkm_static_p #(PIPE 1); PIPE 0 = pinned)',
         cycle_cost_edges=2, cost_note='TKM finish/done/stat_cycles +2 edges (same words, same addresses, same order); compiler TKM latency +2',
         bench='rtl/hbm_accel/generic/collective/tkm/run_tp192_static_p.sh OUT (golden O/R vectors syn_sel/syn_cand/rank128_zeros + lock-step vs pinned root delayed 2 edges; PIPE 0 identity; mutant MUTP 1 must FAIL)',
         bench_result='NOT RUN TO COMPLETION: the TP192 lock-step tb (twin + pinned reference root, KMAX 2048, hier tiles) needs >290 GB in the top-level verilator_bin; memcg-OOM at 128 and 300 GB on ot-gold2. Next: drop the in-tb pinned reference (golden O/R vectors only) or run at TP 96 / KMAX 512; lint-clean only so far'),
    '32 x the TP192 tile (260k, already a hardened shape) + root (34k + 2 SRAM): the tile chain is the dataflow; tile pins are '
    'registered both ways; PIPE 1 registers the root side.  Root core 34k is small (could merge with its neighbouring tile: 294k).',
    tk, S[tk]['total'])

# ------------------------------------------------------------------ SFU core split3 (q_sfuc)
sf = 'ot_hgi_sfu_core_split3'
lane = M(sf, 'ot_su12_sfu__d4g_sfu'); lmap = M(sf, 'ot_hgi_sfu_lane_map__d4g_sfu')
lg = sorted({v['total'] for k, v in S[sf]['modules'].items() if k.startswith('ot_hgi_su_lgroup2__d4g_sfu')})
lg_out, lg_op = lg[0], lg[-1]
st_loc = L(sf, 'ot_hgi_sfu_static_operand_store__d4g_sfu')
bridge = M(sf, 'ot_hgi_sfu_vm_static_bridge__d4g_sfu')
G = 'u_core.u_engine.u_arithmetic.u_grid'
cores = [dict(part='lane', master=sf, core_label=f'lane{j}', module='ot_su12_sfu__d4g_sfu + ot_hgi_sfu_lane_map__d4g_sfu',
              members=[f'{G}.g_lane[{j}].*.u_sfu', f'{G}.g_lane[{j}].*.u_map'], cells=lane + lmap, srams=0,
              pins_bits=dict(inp=1022 + 32 + 4 * 32 + 2, out=1 + 24 + 96 + 4 + 8 + 57 + 57 + 33 + 2)) for j in range(16)]
cores.append(dict(part='opstore_a', master=sf, core_label='opstore_a', module='ot_hgi_su_lgroup2 x2 (operand groups 0,1) + operand-store glue',
                  members=['u_core.u_engine.u_memory.g_operand[0].u_group', 'u_core.u_engine.u_memory.g_operand[1].u_group', 'u_core.u_engine.u_memory (local)'],
                  cells=2 * lg_op + st_loc, srams=32, pins_bits=dict(inp=2 * 16 * 27 + 8 * (1 + 15 + 8 + 256), out=2 * 16 * 32 + 2)))
cores.append(dict(part='opstore_b', master=sf, core_label='opstore_b', module='ot_hgi_su_lgroup2 x2 (operand groups 2,3) + output group',
                  members=['u_core.u_engine.u_memory.g_operand[2].u_group', 'u_core.u_engine.u_memory.g_operand[3].u_group', 'u_core.u_engine.u_memory.u_output'],
                  cells=2 * lg_op + lg_out, srams=48, pins_bits=dict(inp=2 * 16 * 27 + 16 * 57 + 8 * (1 + 15 + 8 + 256) + 2 * 16, out=2 * 16 * 32 + 512 + 2 + 3)))
ctl = S[sf]['total'] - sum(c['cells'] for c in cores)
cores.append(dict(part='ctl', master=sf, core_label='ctl', module='ot_hgi_sfu_vm_static_bridge + split2/engine/quarter glue (control word register)',
                  members=['u_core.u_vm', 'u_core (local)', 'u_core.u_engine (local)', 'u_core.u_engine.u_arithmetic (control reg)'],
                  cells=ctl, srams=0, pins_bits=dict(inp=9090, out=16 * 1022)))
out[sf] = entry(sf, ['q_sfuc'], 'CUT-ONLY', cores, 0, [
    dict(between='ctl (quarter control register) -> lane j (lane_map)', bits=1022, kind='REG->REG', note='lane_map registers every input (terms0/ov0/..., u_pass ring)'),
    dict(between='lane j -> opstore (operand read request, per group)', bits=27, kind='SRAM-BOUNDED (REG->LOGIC->SRAM)',
         note='lane rd_addr/rd_re/rd_src are lane registers (c12); the store core feeds them through its bank crossbar (rsel, comb) into the SRAM macro inputs: no store-side pin flop'),
    dict(between='opstore -> lane j (operand data, per group)', bits=32, kind='SRAM-BOUNDED (SRAM->LOGIC->REG)',
         note='SRAM Q -> crossbar (lb_q select) -> scalar mux -> lane CAPR pin register cr_q: no store-side output flop'),
    dict(between='lane j -> opstore_b (output group lane write)', bits=57, kind='SRAM-BOUNDED (REG->LOGIC->SRAM)', note='vm_we/vm_waddr/vm_wdata'),
    dict(between='lanes <-> ctl (vi/kv/ro/fault)', bits=16 * (1 + 24 + 32 + 57 + 33 + 2), kind='REG on the lane side; ctl side NOT VERIFIED', note='lane: vi_q captured in the OPR (c12) register, ro_v/ro_x output registers; the VM bridge / reducer side was not analysed in this pass'),
    dict(between='ctl -> opstore (stage/drain/scalar)', bits=8 * (1 + 15 + 8 + 256) + 2 * 16 + 4 * 57, kind='NOT VERIFIED', note='bridge stage/drain sectors')],
    dict(twin=None, cycle_cost_edges=None,
         fix='pin-register the store side: lgroup2 request inputs (+1 edge) and read data output (+1 edge) = operand read latency +2 '
             'edges (lane FETCH latency is compiler-visible; RTL in ot_hgi_su_lgroup2 + the lane read-return constant). OPEN.'),
    '16 lane cores (su12_sfu 297k + its lane_map 10k = 307k each), 2 operand-store cores (80 SRAM 256x256), 1 control core '
    '(VM bridge 59k + control register/glue). The store is a 16-lane x 16-bank crossbar per operand group: the cut puts '
    'whole groups in a core (no crossbar split); lane<->store traffic is unavoidable (each lane talks to all 5 groups).',
    sf, S[sf]['total'])

# ------------------------------------------------------------------ SU pgslice (q_su0..q_su3)
for key, types in (('ot_hbm_su_static_pgslice_lg__pv0', ['q_su0', 'q_su1']), ('ot_hbm_su_static_pgslice_lg__pv8', ['q_su2', 'q_su3', 'q_su3_v1'])):
    st = S[key]['modules']
    lanes = sorted([(k, v) for k, v in st.items() if k.startswith('ot_hbm_su_static_lane__')], key=lambda a: a[1]['total'])
    bank = M(key, 'ot_hbm_su_static_pinned_bank')
    pt = M(key, 'ot_hbm_su_red_pretree_s')
    cores = []
    if key.endswith('pv0'):
        plain, expl = lanes[0][1]['total'] + bank, None
        lane_exp = [v['total'] for k, v in lanes if 200_000 < v['total'] < 220_000][0] + bank
        lane_exp_l = [v['total'] for k, v in lanes if v['total'] > 220_000][0] + bank
        side = M(key, 'ot_hbm_su_static_side__'); sp = M(key, 'ot_hbm_su_static_side_softplus')
        for n in range(15):
            cores.append(dict(part='lane_exp', master='ot_hbm_su_static_pgslice_lg (pv0..pv7)', core_label=f'lane_exp{n}', module='ot_hbm_su_static_lane (KIND exp) + its pinned VM bank (6 SRAM)',
                              members=[f'u_slice.g_lane[*].u_lane (exp lane {n})', 'its u_bank'], cells=lane_exp, srams=6, pins_bits=None))
        cores.append(dict(part='lane_exp_l', master='ot_hbm_su_static_pgslice_lg (pv0..pv7)', core_label='lane_exp_l', module='FULL lane (KIND 2, with ins 44k) + pinned bank',
                          members=['u_slice FULL lane', 'its u_bank'], cells=lane_exp_l, srams=6, pins_bits=None))
        for q in range(4):
            cores.append(dict(part='lane4', master='ot_hbm_su_static_pgslice_lg (pv0..pv7)', core_label=f'lanes_plain{4*q}_{4*q+3}', module='4 x ot_hbm_su_static_lane (plain) + 4 pinned banks',
                              members=[f'plain lanes {4*q}..{4*q+3} + banks'], cells=4 * plain, srams=24, pins_bits=None))
        cores.append(dict(part='side_sp', master='ot_hbm_su_static_pgslice_lg (pv0..pv7)', core_label='side_softplus', module='ot_hbm_su_static_side_softplus',
                          members=['u_slice.g_side_pipe.u_side.u_sp'], cells=sp, srams=0, pins_bits=dict(inp=3 + 1 + 1 + 32, out=32 + 32 + 1 + 1)))
        cores.append(dict(part='side_rest', master='ot_hbm_su_static_pgslice_lg (pv0..pv7)', core_label='side_rest', module='ot_hbm_su_static_side minus u_sp (rsqrt, sqrt, Engram gate exp/fdiv/sqrt, result mux)',
                          members=['u_slice.g_side_pipe.u_side (u_rsq, u_sq, u_egc, u_egs, u_exp, u_den, u_div, mux)'], cells=side - sp, srams=0,
                          pins_bits=dict(inp=6 + 1 + 1 + 3 + 32 + 3 + 33, out=33)))
        note = ('exp slices: 15 exp lanes + the FULL lane (each with its pinned VM bank: 6 SRAM 128x256), 16 plain lanes 4 per core, '
                'side split softplus | rest, reduction pretree.  Lanes need the EXISTING opt-in PIN_REG=1 (lane_pinreg leaf; the views use '
                'PIN_REG 0): +2 edges on store/RF requests, +4 on writes/reducer operands (su_top_compile --pin-reg).')
        sx = [dict(between='side_softplus -> side_rest (result mux)', bits=33, kind='COMB (needs fix)',
                   note='y_sp (fsqrt output) + the softplus fault OR (comb) feed side_rest\'s result mux y / fault OR: needs a y_sp/f_sp pin register in side_softplus and +1 edge on every side result (fn_out alignment) -> OPEN'),
              dict(between='FULL lane -> side (v, x) and fn/fn_out', bits=1 + 32 + 3 + 3, kind='REG->LOGIC->REG with PIN_REG 1', note='g_fn_pin registers fn/fn_out; v/x from the lane; units gate v with fn compare before their first stage')]
    else:
        plain = lanes[0][1]['total'] + bank
        for q in range(8):
            cores.append(dict(part='lane4', master='ot_hbm_su_static_pgslice_lg (pv8..pv15)', core_label=f'lanes{4*q}_{4*q+3}', module='4 x ot_hbm_su_static_lane (plain) + 4 pinned banks',
                              members=[f'lanes {4*q}..{4*q+3} + banks'], cells=4 * plain, srams=24, pins_bits=None))
        note = ('plain slices: 32 plain lanes 4 per core + pretree.  Lanes need the existing opt-in PIN_REG=1 (+2 / +4 edges, '
                'su_top_compile --pin-reg); with it every lane pin is registered.')
        sx = []
    cores.append(dict(part='pretree', master=key, core_label='pretree', module='ot_hbm_su_red_pretree_s #(LAT 6)', members=['u_slice.u_pt'],
                      cells=pt, srams=0, pins_bits=None))
    glue = S[key]['total'] - sum(c['cells'] for c in cores)
    out[key] = entry(key, types, 'CUT-ONLY', cores, glue, sx + [
        dict(between='lanes <-> pretree / VM banks / RF broadcast', bits=None, kind='REG->REG with PIN_REG 1', note='existing lane_pinreg leaf; not re-benched in this pass')],
        dict(twin=None, cycle_cost_edges='PIN_REG 1: +2 request / +4 write+reducer edges (existing opt-in)' + ('; side split +1 edge on side results (OPEN)' if key.endswith('pv0') else ''),
             bench='existing PIN_REG benches (not re-run here)'),
        note, key, S[key]['total'])

# ------------------------------------------------------------------ HC bank quarters (q_hc0..q_hc7)
for key, types in (('ot_hbm_hc_bankq0_static', ['q_hc0']), ('ot_hbm_hc_bankq_static', ['q_hc1', 'q_hc3', 'q_hc4', 'q_hc5']),
                   ('ot_hbm_hc_bankq_ft_static', ['q_hc2', 'q_hc6']), ('ot_hbm_hc_bankq_term_static', ['q_hc7'])):
    ln = [v['total'] for k, v in S[key]['modules'].items() if k.startswith('ot_hdc_v41x_hcp_lanes')][0]
    tot = S[key]['total']
    rest = tot - 8 * ln
    cores = [dict(part='lanes3', master=key, core_label='lanes0_2', module='3 x ot_hdc_v41x_hcp_lanes (pin-registered lane-group leaf, LG 8)',
                  members=['...u_stage.g_lg[0..2] (hcp_lanes)'], cells=3 * ln, srams=0, pins_bits=dict(inp=3 * (256 + 128 + 256 + 24), out=3 * (256 + 8 + 2))),
             dict(part='lanes3', master=key, core_label='lanes3_5', module='3 x ot_hdc_v41x_hcp_lanes', members=['...u_stage.g_lg[3..5]'], cells=3 * ln, srams=0,
                  pins_bits=dict(inp=3 * (256 + 128 + 256 + 24), out=3 * (256 + 8 + 2))),
             dict(part='lanes2_bank', master=key, core_label='lanes6_7_bank', module='2 x hcp_lanes + hcp_stage/bank/bankq glue + 12 SRAM',
                  members=['...u_stage.g_lg[6..7]', 'ot_hbm_hc_bank_static (+ SRAM 8 x 1024x256, 4 x 128x256)', 'bankq core/top glue'],
                  cells=2 * ln + rest, srams=12, pins_bits=None)]
    out[key] = entry(key, types, 'DONE', cores, 0, [
        dict(between='hcp_stage -> lane group (w_data, x_data, sum_in, ctl)', bits=256 + 128 + 256 + 24, kind='REG->REG',
             note='the LG 8 hcp_lanes leaf: "its pin flops ARE the old input registers (w_in, x_in, sum_q, lv_r/ss_r, gov, fst_q)" (ot_hdc_v41x_hcp.sv); stage side = SRAM / descriptor regs'),
        dict(between='lane group -> hcp_stage (sum_out, fault)', bits=256 + 1, kind='REG->REG', note='adder/seam output registers + registered group fault')],
        dict(twin=None, cycle_cost_edges=0, bench='no RTL change (cut along existing hard lane-group leaves)'),
        '8 lane-group leaves (hcp_lanes ~96k each, already pin-registered hard leaves) packed 3+3+2, the 2-group core carries the '
        'stage/bank glue and the 12 SRAM.  Cells from the r14 chainB hierarchical stats (same std area as the r18h5 views: 9.24e4 um2).',
        key, tot)

# ------------------------------------------------------------------ HC root (c0)
hr = 'ot_hbm_hc_root_static'
tailu = M(hr, 'ot_hbm_hc_tail_unit_static')
sk_old = M(hr, 'ot_hdc_sinkhorn__d4g_hc')
s0 = M('SPLIT:ot_hdc_sinkhorn_s', 'ot_hdc_sk_step0'); ss = M('SPLIT:ot_hdc_sinkhorn_s', 'ot_hdc_sk_steady')
trest = tailu - sk_old
sys1 = M(hr, 'ot_hdc_v41x_hcp_sys1_static')
cores = []
for t in range(2):
    cores += [dict(part='sk_step0', master=hr, core_label=f'tail{t}_sk_step0', module='ot_hdc_sk_step0 (ot_hdc_sinkhorn_s)', members=[f'tail {t}: sink.u_s0'],
                   cells=s0, srams=0, pins_bits=dict(inp=1 + 1 + 512 + 2, out=512 + 2)),
              dict(part='sk_steady', master=hr, core_label=f'tail{t}_sk_steady', module='ot_hdc_sk_steady (ot_hdc_sinkhorn_s)', members=[f'tail {t}: sink.u_ss'],
                   cells=ss, srams=0, pins_bits=dict(inp=1 + 1 + 1 + 512 + 2, out=1 + 3 + 1 + 512 + 1 + 1)),
              dict(part='tail_rest', master=hr, core_label=f'tail{t}_rest', module='ot_hgi_hc_tail_static minus the Sinkhorn (exp 66.5k, fdiv, calendar regs)',
                   members=[f'tail {t}: exp_, div_, tail registers'], cells=trest, srams=0, pins_bits=None)]
cores.append(dict(part='hcp_sys1', master=hr, core_label='hcp_sys1', module='ot_hdc_v41x_hcp_sys1_static', members=['hcp sys1'], cells=sys1, srams=0, pins_bits=None))
glue = S[hr]['total'] - 2 * tailu - sys1
out[hr] = entry(hr, ['c0'], 'CUT-ONLY', cores, glue, [
    dict(between='tail_rest -> sk_step0 (in_e)', bits=512, kind='REG->REG (assumed)', note='tail se registers -> er (load); verify the tail drives in_e from its t[] registers'),
    dict(between='sk_steady -> sk_step0 (load, pa, pb)', bits=3, kind='REG->LOGIC->REG', note='pa/pb are control flops; load = idle flop AND in_valid (1 gate)'),
    dict(between='sk_step0 -> sk_steady (b_q, bbad_q, abad_q)', bits=514, kind='REG->REG', note='NEW B output registers (pinned: B logic -> st directly = COMB crossing)'),
    dict(between='sk_steady -> tail_rest (y, fault, out_valid)', bits=514, kind='REG->LOGIC->REG', note='y = fault ? 0 : st (one AND level), captured by the tail at sink_capture')],
    dict(twin='rtl/hdc/v41/ot_hdc_sinkhorn_s.sv (ot_hdc_sinkhorn_s = ot_hdc_sk_step0 + ot_hdc_sk_steady; generated by gen_sinkhorn_s.py from the pinned unit)',
         cycle_cost_edges='+1 sink_clk edge per Sinkhorn (out_valid at 2 ITERS + 2 = 42, pinned 41): the tail calendar\'s sink_capture moves 1 sink edge',
         bench='rtl/test/run_sinkhorn_s_equiv.sh OUT pos|mut (lock-step vs pinned ot_hdc_sinkhorn: y/fault identical, out_valid exactly +1)',
         bench_result='ot-gold2 @bcc0334cd: pos PASS 300 cases (89 fault) and N 3000 SEED 7 PASS (962 fault), mutant MUT 1 FAIL (211/300 y mismatches) as required',
         open='integration twins ot_hgi_hc_tail_static_s / ot_hbm_hc_tail_unit_static_s / the scoped ot_hbm_hc_root_static (sink -> ot_hdc_sinkhorn_s, calendar +1) not written'),
    'Each tail (673k, never closed) = Sinkhorn 567k + exp/fdiv/regs.  The Sinkhorn is cut along its own dataflow: step-0 '
    'general datapath (cycles A, B: 16 SUBN quotients) | steady step + matrix state + control (16 lean quotients); the '
    'one-step-per-clock loop st -> step -> st stays inside sk_steady.  Root glue (95.7k incl. 2 SRAM) stays flat.',
    hr, S[hr]['total'])

# ------------------------------------------------------------------ coll q2 hard v8g (q_rc4)
ev = json.load(open(os.path.join(HERE, '..', 'inputs', 'cells_evidence.json')))['splits']['ot_hfd_coll_q2_hard_v8g']
cores = [dict(part=n, master='ot_hfd_coll_q2_hard_v8g', core_label=n, module=n, members=[n], cells=each, srams=None, pins_bits=None)
         for n, cnt, each in ev['parts']]
q2 = dict(master='ot_hfd_coll_q2_hard_v8g', plan_types=['q_rc4', 'q_rc4_v1'], status='CUT-ONLY', measured_total=ev['total'],
          basis='YOSYS ' + ev['stat'] + ' (stat file since deleted; numbers from inputs/cells_evidence.json)',
          n_cores=len(cores), max_core_cells=max(c['cells'] for c in cores), cores_cells=sum(c['cells'] for c in cores), glue_cells=ev['glue'],
          cores=[{k: v for k, v in c.items() if k != 'part'} for c in cores], crossings=[],
          rtl=dict(twin=None, cycle_cost_edges=None, open='crossings ring_ag / reduce / body not analysed in this pass'),
          note=ev['note'] + '; every part <= 350k already (HBM-P4 cells_evidence split)', splits_entry=ev)
out['ot_hfd_coll_q2_hard_v8g'] = q2

idx = {}
for k, v in out.items():
    fn = f'{k}.split.json'
    json.dump(v, open(os.path.join(HERE, fn), 'w'), indent=1)
    idx[k] = dict(file=fn, status=v['status'], plan_types=v['plan_types'], measured_total=v['measured_total'], n_cores=v['n_cores'],
                  max_core_cells=v['max_core_cells'], glue_cells=v['glue_cells'],
                  cycle_cost=v['rtl'].get('cycle_cost_edges'))
json.dump(dict(budget=BUDGET, masters=idx), open(os.path.join(HERE, 'index.json'), 'w'), indent=1)
for k, v in idx.items():
    print(f"{v['status']:9s} {k:40s} total {v['measured_total']:>9,} cores {v['n_cores']:3d} max {v['max_core_cells']:>8,} glue {v['glue_cells']:>8,} cost {v['cycle_cost']}")
