#!/usr/bin/env python3
"""Build the OpenTallas Chip Explorer (site/chip_explorer/index.html).

Reads committed records under results/ plus snapshots in site/chip_explorer/inputs/
(Qwen ROM r17b die geometry/IR/GRT and HBM-Qwen die files that were not yet on main
when the site was first built). Writes site/chip_explorer/build/data.json and the
single-file page. Every value in DATA carries {v, unit, status, src}; replace a
snapshot or a record and re-run to update the page.

Usage: python3 tools/chip_explorer_build.py
"""
#!/usr/bin/env python3
"""Assemble the explorer's DATA object from committed (and clearly labelled uncommitted) records.
Every leaf value is {v, unit, status, src}; status in measured | analytical | estimate | placeholder."""
import json, re, collections
from pathlib import Path

R = Path(__file__).resolve().parents[1]
X = R / 'site/chip_explorer/inputs'
BUILD = R / 'site/chip_explorer/build'
WT = X / 'qwen_r17b'


def V(v, unit, status, src, note=None):
    d = dict(v=v, unit=unit, status=status, src=src)
    if note:
        d['note'] = note
    return d


def J(p):
    return json.loads(Path(p).read_text())


CMP = 'results/arch/three_machine_compose/compose.json'
cmpj = J(R / CMP)
DSC = 'results/rtl/dsrom_recovery_20261004/composition.json'
dsc = J(R / DSC)
QT = 'results/rtl/qwen_plain_ar_stream4_P8191_20261005/terminal.json'
qt = J(R / QT)
HFP = 'results/rtl/hbm_accel_die_floorplan_20261005/floorplan.json'
hfp = J(R / HFP)
HWS = 'results/rtl/hbm_accel_die_floorplan_20261005/wire_stages.json'
hws = J(R / HWS)
QHB = 'origin/claude/qwen-hbm-die-fp-20261005:results/rtl/hbm_accel_qwen_die_floorplan_20261005'
qhfp = J(X / 'qhbm_floorplan.json')
qhws = J(X / 'qhbm_wire.json')
MREF = 'results/rtl/dshbm_matched_reference_20261005/composition.json'
mref = J(R / MREF)
DSM = 'results/uarch/dsrom_c_recheck_20261004/model.json'
dsm = J(R / DSM)
DRAFT = 'results/rtl/dsrom_recovery_20261004/levers/draft.json'
draft = J(R / DRAFT)
DSR = 'results/arch/dsrom_s81_rack_20261006/rack.json'      # S81 rack packing, hop classes, stacks, die counts (DS-RACK)
dsr = J(R / DSR)
LFF = 'results/rtl/dsrom_1m_allmeasured_20261004/links_full_fec.json'   # full-FEC links (RTL, owner 2026-10-06)
lff = J(R / LFF)
FEC_RULE = 'OWNER 2026-10-06: full RS(544,514) FEC on every off-package link (board, in-rack cable, rack to rack), both machines'

geo = J(X / 'geo.json')
irds = J(X / 'hbm_ds_ir.json')
QIR = 'wt-qwen-die (branch claude/qwen-die-rebuild-20261005, untracked): results/rtl/qwen_rom_die_r17_20261005/ir/ir_record.json'
qir = J(WT / 'ir_record.json')
QPS = 'branch claude/qwen-die-rebuild-20261005 @f76c3603b: results/rtl/qwen_rom_die_r17_20261005/path_sta/r17b_i5_skew19.json'
qps = J(WT / 'r17b_i5_skew19.json')
QGRT = 'branch claude/qwen-die-rebuild-20261005 @f76c3603b: results/rtl/qwen_rom_die_r17_20261005/grt/r17b_k16_banded_i5/summary.json'
qgrt = J(WT / 'grt_summary.json')
HINV = 'results/rtl/hbm_accel_fmax_inventory_20261004/inventory.json'
PLAN = 'docs/PROGRAM_PLAN_2026_10_05.md'
ATLAS = 'docs/ARCHITECTURE_ATLAS.html'
LEV = 'results/rtl/dsrom_recovery_20261004/levers/'

D = {}
D['meta'] = dict(
    date=V('2026-10-05', '', 'measured', 'build date of this page'),
    repo_head=V('06d98ba58', 'commit', 'measured', 'git rev-parse HEAD of /home/ubuntu/OpenTallas at build'),
    clock=V(1.2, 'GHz', 'analytical', 'every rate assumes 1.2 GHz; full-system SS/FF not qualified (' + PLAN + ' risk 2)'),
    period=V(833, 'ps', 'analytical', 'sign-off clock 0.833 ns, SS setup 60 ps / FF hold 25 ps uncertainty (' + PLAN + ' section 1)'),
    ss_unc=V(60, 'ps', 'analytical', PLAN + ' section 1'),
    ff_unc=V(25, 'ps', 'analytical', PLAN + ' section 1'),
    stage_pitch=V(430.56, 'um', 'measured', HWS + ' stage_pitch_um (one registered wire stage)'),
    ss_reach=V(504.0, 'um', 'measured', HWS + ' ss_reach_um'),
)

# ---------------------------------------------------------------- rates (compare)
q = cmpj['qwen_rom']; ds = cmpj['ds_rom']; hb = cmpj['hbm_ds']
hrow = hb['rows']['median']
qb = qhws['bases']
D['rates'] = dict(
    qwen=dict(
        AR=V(q['AR_tok_s'], 'tok/s', 'measured', CMP + ' qwen_rom.AR_tok_s (composed from measured: 193,955 measured cycles + 112 adopted core-context cycles at 1.2 GHz)'),
        MTP=V(q['MTP_tok_s'], 'tok/s', 'measured', CMP + ' qwen_rom.MTP_tok_s; operating mode AR (DSpark OFF)'),
        cycles=V(q['token_cycles'], 'cycles', 'measured', CMP + ' qwen_rom.token_cycles'),
        cycles_measured=V(q['token_cycles_measured'], 'cycles', 'measured', QT + ' total_cycles'),
        core_ctx=V(112, 'cycles', 'measured', CMP + ' qwen_rom.levers.core_context (r5b_f3ba, SS +0.87 / FF +7.12 ps, exact 5/5)'),
        AR_us=V(q['AR_us'], 'us', 'measured', CMP + ' qwen_rom.AR_us'),
        dspark=V(q['dspark_reference']['tok_s'], 'tok/s', 'analytical', 'results/rtl/qwen_rom_kv_fullbw_20261004/dspark_verdict.json (partial: tau third-party 3.1445)'),
        dspark_ratio=V(q['dspark_reference']['speedup_vs_ar'], 'x', 'analytical', 'results/rtl/qwen_rom_kv_fullbw_20261004/dspark_verdict.json'),
    ),
    ds=dict(
        AR=V(ds['AR_tok_s'], 'tok/s', 'measured', CMP + ' ds_rom.AR_tok_s (all-measured composition, recovery baseline + adopted levers, every off-package link on full RS(544,514) FEC; measured share ' + str(ds['measured_share']) + ')'),
        MTP=V(ds['MTP_tok_s'], 'tok/s', 'measured', CMP + ' ds_rom.MTP_tok_s (tau 4.159 owner blend; MTP physical_qualified=false)'),
        AR_us=V(ds['AR_us'], 'us', 'measured', CMP + ' ds_rom.AR_us'),
        MTP_step_us=V(ds['MTP_step_us'], 'us', 'measured', CMP + ' ds_rom.MTP_step_us'),
        II_us=V(ds['II_us'], 'us', 'measured', CMP + ' ds_rom.II_us (slowest stage busy + hop)'),
        tau=V(ds['tau'], 'tokens/step', 'analytical', ds['tau_source']),
        MTP_pub=V(ds['MTP_tok_s_tau_published'], 'tok/s', 'analytical', CMP + ' ds_rom.tau_sensitivity.published (tau 3.8879)'),
        AR_cond=V(ds['conditional_all']['composed']['AR_tok_s'], 'tok/s', 'analytical', CMP + ' ds_rom.conditional_all.composed (all PENDING_SSFF levers flipped; not a headline)'),
        MTP_cond=V(ds['conditional_all']['composed']['MTP_tok_s'], 'tok/s', 'analytical', CMP + ' ds_rom.conditional_all.composed'),
    ),
    hbm_ds=dict(
        AR=V(hrow['AR_tok_s'], 'tok/s', 'analytical', CMP + ' hbm_ds.rows.median (matched gate + exact levers + full-FEC switch crossings + die wire stages, median bundle; scoreboard status partial)'),
        MTP=V(hrow['MTP_tok_s'], 'tok/s', 'analytical', CMP + ' hbm_ds.rows.median'),
        AR_us=V(hrow['AR_us'], 'us', 'analytical', CMP + ' hbm_ds.rows.median.AR_us'),
        MTP_step_us=V(hrow['MTP_step_us'], 'us', 'analytical', CMP + ' hbm_ds.rows.median.MTP_step_us'),
        AR_floor=V(hb['rows']['floor']['AR_tok_s'], 'tok/s', 'analytical', CMP + ' hbm_ds.rows.floor (Manhattan wire)'),
        AR_bound=V(hb['rows']['bound']['AR_tok_s'], 'tok/s', 'analytical', CMP + ' hbm_ds.rows.bound (longest routed bundle)'),
        gate_AR=V(hb['basis']['gate_AR_tok_s'], 'tok/s', 'analytical', MREF + ' gate (matched reference, before die wire)'),
        gate_MTP=V(hb['basis']['gate_MTP_tok_s'], 'tok/s', 'analytical', MREF + ' gate'),
        wire_us=V(hrow['wire_added_us'], 'us', 'analytical', CMP + ' hbm_ds.rows.median.wire_added_us (from ' + HWS + ')'),
        levers_us=V(round(hb['basis']['gate_AR_us'] - hb['levers_AR_us'], 3), 'us', 'analytical', CMP + ' hbm_ds.levers (joint_PQ_XMAP -36.416 + paired_W2_PACK -6.133; exact on minimum components, SS/FF not admitted)'),
    ),
    hbm_qwen=dict(
        AR=V(qb['stages_430_median_bundle']['rows']['b_TP4_iso_silicon']['ar_tok_s_priced'], 'tok/s', 'analytical', QHB + '/wire_stages.json bases.stages_430_median_bundle.rows.b_TP4_iso_silicon.ar_tok_s_priced (measured 557,056-cycle token + 23,145 priced wire cycles)'),
        AR_tp2=V(qb['stages_430_median_bundle']['rows']['a_TP2_same_silicon']['ar_tok_s_priced'], 'tok/s', 'analytical', QHB + '/wire_stages.json ...a_TP2_same_silicon.ar_tok_s_priced'),
        AR_unpriced=V(2154.2, 'tok/s', 'measured', 'results/rtl/qwen_hbmacc_p8191_20261004/allmeasured.json (TP4 iso-silicon, exact, no die wire)'),
        MTP=V(None, 'tok/s', 'placeholder', 'no measured Qwen HBM MTP row at the same basis; DSpark about 5,055 on TP4 is cited in ' + PLAN + ' (not composed here)'),
    ),
)
D['ratios'] = dict(
    ds_ar=V(cmpj['ratios']['ds_rom_over_hbm_ar'], 'x', 'analytical', CMP + ' ratios.ds_rom_over_hbm_ar (vs wire median)'),
    ds_mtp=V(cmpj['ratios']['ds_rom_over_hbm_mtp'], 'x', 'analytical', CMP + ' ratios.ds_rom_over_hbm_mtp'),
)

# ---------------------------------------------------------------- Qwen per-layer timing
stages = [dict(name=s['stage'], cycles=s['cycles'], start=s['start_cycle']) for s in qt['stages']]
D['qwen_layers'] = V(stages, 'cycles', 'measured', QT + ' stages[] (full36 + RTL head, STREAM4, P8191, exact)')
# phase split inside a layer: measured on the isolated L0 trace (6,489 cycles incl. exposed KV fill)
D['qwen_phase_split'] = V(dict(attention=4404, mlp=1839, residual=246, total=6489, me_busy_attn=2245, me_busy_mlp=1008),
                          'cycles', 'measured',
                          'results/rtl/qwen_rom_kv_fullbw_20261004/dspark_step_stream4.json verify_segment_breakdown.ar (per-cycle sequencer trace, L0 isolated P8191)',
                          note='Applied to the 5,282-cycle chained layer by proportion; that scaling is analytical.')

# ---------------------------------------------------------------- DS critical path, by stage and category
def ds_cat(node):
    s = re.sub(r'^L\d+\.', '', node)
    if node.startswith('head') or node == 'embed' or node.startswith('token'):
        if 'hop' in s or 'return' in s:
            return 'hop'
        return 'head'
    if 'hop' in s or 'allgather' in s or 'allreduce' in s:
        return 'hop'
    if any(k in s for k in ('a_proj', 'wo_a', 'wo_b', 'experts_gu', 'ffn.down', 'ffn.router', 'wq_b', 'idx.q', 'eng.dot')) and 'router_' not in s:
        return 'field'
    if any(k in s for k in ('scores', '.max', '.exp', '.den', '.sink', 'normalize', 'own_row_write', 'window_load', 'idx.score', 'idx.topk', 'attn.gather')):
        return 'attn'
    return 'su'

cp = dsc['critical_path']
segs = []
cur = dict(nodes=[], cats=collections.Counter(), layers=[])
for n in cp:
    node, us = n['node'], n['us']
    if node == 'token':
        continue
    c = ds_cat(node)
    is_hop = node.endswith('substage_hop0') or node.endswith('substage_hop1') or node == 'head.hop'
    lay = node.split('.')[0]
    if lay not in cur['layers'] and not is_hop:
        cur['layers'].append(lay)
    if is_hop:
        cur['hop'] = round(us, 4)
        cur['hop_node'] = node
        segs.append(cur)
        cur = dict(nodes=[], cats=collections.Counter(), layers=[])
        continue
    cur['cats'][c] += us
    cur['nodes'].append([node, round(us, 4), n['cls']])
segs.append(cur)
seg_out = []
for i, s in enumerate(segs):
    first = s['nodes'][0][0] if s['nodes'] else ''
    seg_out.append(dict(i=i, layers=s['layers'], first=first, hop=s.get('hop', 0.0), hop_node=s.get('hop_node', ''),
                        cats={k: round(v, 4) for k, v in s['cats'].items()}, n=len(s['nodes']),
                        nodes=s['nodes']))
D['ds_stages'] = V(seg_out, 'us', 'measured', DSC + ' critical_path[] (1,762 nodes; 1,664 measured, 59 measured+vendor PHY budget, 38 inside-measured); split at each stage hop')
D['ds_extra_hops'] = V(dict(count=23, us_each=round(dsc['info']['hop_us'], 4), total=dsc['critical_path_us_by_class']['extra_S81_hops']), 'us', 'measured',
                       DSC + " critical_path_us_by_class.extra_S81_hops; tools/dsrom_1m_measure.py S81_EXTRA_HOPS = 81 - 58 (the S81 build adds 23 stage hops to the S58 graph)",
                       note='Where the 23 extra stage boundaries fall is not in the composition record; the ribbon draws them as unplaced hop-only stages.')
D['ds_by_class'] = V(dsc['critical_path_us_by_class'], 'us', 'measured', DSC + ' critical_path_us_by_class')
D['ds_mtp'] = V(dict(II=dsc['MTP']['II_us'], verify=dsc['MTP']['verify_us'], draft=dsc['MTP']['draft_us'], seed=dsc['MTP']['seed_commit_us'],
                     step=dsc['MTP']['step_us'], worst=dsc['MTP']['worst_stage'], rule=dsc['MTP']['rule'], top=dsc['MTP']['stage_busy_top']),
                'us', 'measured', DSC + ' MTP')
D['ds_hop'] = V(round(dsc['info']['hop_us'], 4), 'us', 'measured', DSC + " info.hop_us = " + LFF + " hop: ot_dsrom_link_rt RTL 652 cyc (40,976 B, 64-B flits) + full-KP4 RS(544,514) PHY vendor budget 209 ns + UCIe 10 ns + 2x45 routed wire stages (1,004 cyc)",
                note=FEC_RULE + '; was 0.7575 us on the superseded 130 ns light-FEC budget. Cable flight beyond 0.3 m is charged per hop class (' + DSR + ').')
sysm = dsm['priced']['S81_ragged_RD64_replicated']['system']
DBRP = 'results/rtl/dsrom_recovery_20261004/draft/draft_blocks_recovery.json'
DBR = J(R / DBRP)
D['ds_system'] = dict(
    stages=V(81, 'stages', 'analytical', DSM + ' decision.area.stages (S81)'),
    layer_dies=V(sysm['layer_dies'], 'dies', 'analytical', DSM + ' priced.S81_ragged_RD64_replicated.system.layer_dies (81 stages x TP4)'),
    head_dies=V(dsr['counts']['head'], 'dies', 'analytical', DSR + ' counts.head <- ' + dsr['counts']['src']['head']),
    table_dies=V(dsr['counts']['table'], 'dies', 'analytical', DSR + ' counts.table <- ' + dsr['counts']['src']['table']),
    total_dies_model=V(dsr['counts']['dies'], 'dies', 'analytical', DSR + ' counts.dies (324 layer + 12 head + 36 table + 52 draft)',
                       note='supersedes ' + DSM + ' system.total_dies 368 (8 head dies, no draft dies)'),
    packages=V(dsr['counts']['dies'] // 2, 'packages', 'analytical', DSR + ' counts.dies / 2 (two-die packages)'),
    stacks=V(dsr['stacks']['total'], 'HBM stacks', 'analytical', DSR + ' stacks.total: ' + dsr['stacks']['src'],
             note='4 on the 32 scan dies and the 12 head dies, 1 on the other 292 layer dies, 0 on table and draft dies; the power model\'s 452 = the same rule at 8 head dies'),
    scan_dies=V(dsr['stacks']['scan_dies'], 'dies', 'analytical', DSR + ' stacks.scan_stages ' + str(dsr['stacks']['scan_stages']) + ' x TP4'),
    die_mm2=V(dsm['decision']['area']['die_mm2'], 'mm2', 'analytical', DSM + ' decision.area.die_mm2 (priced S81 die)'),
    pairs=V(dsm['decision']['area']['pairs'], 'pairs/die', 'analytical', DSM + ' decision.area.pairs'),
    draft_primary=V(draft['placement']['dies']['primary'], 'dies', 'analytical', DRAFT + ' placement.dies.primary'),
    draft_replicas=V(draft['placement']['dies']['expert_replicas'], 'dies', 'analytical', DRAFT + ' placement.dies.expert_replicas (5 expert TP4 groups per DSpark block x 3 blocks)'),
    draft_added=V(draft['dies_added'], 'dies', 'analytical', DRAFT + ' dies_added (vs 12 baseline draft dies)'),
    draft_hop=V(round((DBR['rlinks']['x_row']['total_cycles'] + lff['hop']['delta_cycles'] + dsr['hop_summary']['draft_link_extra_cycles_each']) / 1.2e3, 4), 'us', 'measured',
                DBRP + ' rlinks.x_row (ot_dsrom_link_rt, 10,240 B primary -> replica, ' + str(DBR['rlinks']['x_row']['total_cycles']) + ' cyc on light FEC) + ' + LFF + ' hop.delta_cycles (full FEC) + ' + DSR + ' draft-link cable flight'),
    head_hop=V(f"{dsr['head_hop']['cls']}, {dsr['head_hop']['length_m']} m {dsr['head_hop']['medium']}, full FEC, +{dsr['head_hop']['extra_cycles']} cyc flight", '', 'analytical', DSR + ' head_hop'),
    token_return_us=V(next(n['us'] for n in dsc['critical_path'] if n['node'] == 'token.return'), 'us', 'measured',
                      DSC + " critical_path['token.return'] (8 traversals of ot_dsrom_link_rt on the full-KP4 channel, " + LFF + ' token_return, + cable flight)'),
    draft_blocks_us=V(draft['blocks_old_new_us']['new'], 'us', 'measured', DRAFT + ' blocks_old_new_us.new'),
)

# ---------------------------------------------------------------- DS levers (ladder)
lever_rows = []
for name, lv in ds['levers'].items():
    row = dict(name=name, cls=lv['cls'], verdict=lv['verdict'], record=lv['record'])
    if 'delta' in lv:
        row['dAR_tok_s'] = lv['delta']['AR_tok_s']; row['dMTP_tok_s'] = lv['delta']['MTP_tok_s']
        row['dAR_us'] = lv['delta']['AR_us']; row['dMTP_step_us'] = lv['delta']['MTP_step_us']
    row['note'] = lv.get('note', '')
    lever_rows.append(row)
LDESC = dict(draft='DP1-EP5 draft placement: DSpark blocks chained on one primary TP4 group; experts replicated on 5 groups (+52 dies)',
             head='LM head on bundled ROM4096 macros with a streaming tree (8,353 cycles go to last logit)',
             router='One select-tree pass picks and orders the top-6 experts (44 cycles)',
             su_hcpost='Fused hyper-connection post-mix (4 dependent mul-adds in one pipeline, 103 cycles)',
             su_routeract='Fused softplus + sqrt router activation in the 0.9 GHz serial domain',
             field_spine='Successor ROM-field spine at PQ=0 (registered stream-ROM reader, deeper beat assembly)',
             field_spine_pq='Closed PQ spine (pipelined field phases) on the successor spine',
             su_norm='Fused hc_pre, RMSNorm and FP8 quantise in one pipeline',
             su_softmax='Fused attention softmax (max, exp, denominator, sink, normalise)',
             su_swiglu='Fused SwiGLU, route-weight multiply and FP8 quantise',
             field='PQ field phases on the old spine (spine fails SS -722.8 ps)',
             hop='Cut-through stage hop ot_dsrom_link_ct (SS -500.4 ps)')
for r in lever_rows:
    r['what'] = LDESC.get(r['name'], '')
D['ds_levers'] = V(lever_rows, 'tok/s', 'measured', CMP + ' ds_rom.levers (adopted deltas = headline minus headline-without; conditional = if-adopted minus headline)')
D['ds_cond_steps'] = V({k: v['if_adopted'] for k, v in ds['levers'].items() if 'if_adopted' in v}, 'tok/s', 'analytical', CMP + ' ds_rom.levers.*.if_adopted')
D['hbm_levers'] = V([dict(name=k, cls=v['cls'], dAR_us=v['delta']['AR_us'], dMTP_step_us=v['delta']['MTP_step_us'], scope=v['scope'], note=v['note']) for k, v in hb['levers'].items()],
                    'us', 'analytical', CMP + ' hbm_ds.levers (exact on minimum components; SS/FF not admitted)')

# ---------------------------------------------------------------- HBM DS per-layer path by domain
hp = mref['path']
by_layer = collections.OrderedDict()
for n in hp:
    L = n['layer']
    key = 'pre' if L == -2 else ('head' if not isinstance(L, int) or L >= 43 else f'L{L}')
    if isinstance(L, str):
        key = L
    dom = n['domain'] or 'tail'
    by_layer.setdefault(key, collections.Counter())[dom] += n['us']
D['hbm_layers'] = V([dict(name=k, doms={d: round(u, 4) for d, u in v.items()}) for k, v in by_layer.items()], 'us', 'analytical',
                    MREF + ' path[] (2,291 nodes: 1,761 measured, 265 measured with TU vendor budget, 265 modelled striping tails); domains hbm/sm/su/coll/attn/du/tail',
                    note='Gate composition before the exact levers and the die-wire terms; those are added as separate rows.')
D['hbm_wire_terms'] = V(hws['compositions']['ds_matched']['terms'], 'us', 'analytical', HWS + ' compositions.ds_matched.terms (bound basis; headline uses median bundle)')
D['hbm_class_bounds'] = V(hws['class_bounds'], 'stages', 'measured', HWS + ' class_bounds (GRT routed lengths, r14b k16 i50; stage = 430.56 um)')
D['hbm_one_way'] = V(hws['bases']['stages_430_median_bundle']['one_way_cycles'], 'cycles', 'measured', HWS + ' bases.stages_430_median_bundle.one_way_cycles')
D['hbm_system'] = dict(
    dies=V(96, 'dies', 'analytical', 'results/rtl/dshbm_1m_allmeasured_20261004/composition.json design (TP-96, 32 SMs/die, Tomahawk-Ultra tier)'),
    switch=V('Tomahawk Ultra tier (~8 switch chips per striped crossing)', '', 'estimate', MREF + ' path tail nodes (Tomahawk striping tail 0.15 us, modelled) and inherited vendor terms'),
    tu_budget_share=V(0.3367, 'fraction of AR', 'analytical', 'results/arch/measured_scoreboard/README.md (TU vendor budget + striping tail share of DS HBM AR token, modelled)'),
    qwen_tp4=V(4, 'dies', 'analytical', QHB + '/floorplan.json die.tp4_dies'),
    qwen_tp2=V(2, 'dies', 'analytical', QHB + '/floorplan.json die.tp2_dies'),
)

# ---------------------------------------------------------------- dies (geometry + facts)
def gwrap(key, status, src, note=None):
    return V(geo[key], 'um', status, src, note)

D['dies'] = dict(
    hbm_ds=dict(
        title='HBM accelerator die, DeepSeek-V4.1 organisation (r14b)',
        geo=gwrap('hbm_ds', 'measured', 'tools/hbm_accel_die_fp.py build() ADOPTED = ' + 'results/rtl/hbm_accel_die_floorplan_20261005/floorplan.def (r14b: legality 0 overlaps, pin access PASS, GRT k16 i50 overflow 0)'),
        area=V(hfp['die']['mm2'], 'mm2', 'measured', HFP + ' die.mm2'),
        placed=V(hfp['placed_footprint_mm2'], 'mm2', 'measured', HFP + ' placed_footprint_mm2'),
        grt=V('overflow 0 (k16, 50 iterations)', '', 'measured', 'results/rtl/hbm_accel_die_floorplan_20261005/README.md r14b row'),
        ir_worst=V(25.41, 'mV', 'measured', 'results/rtl/hbm_accel_die_floorplan_20261005/feasibility.json ir_summary.ir14 (88 load windows pass, budget 35 mV)'),
        ir_windows=V(irds, 'mV', 'measured', 'results/rtl/hbm_accel_die_floorplan_20261005/feasibility.json cases[ir14/*] rail_to_rail_interior_mv; window rects from floorplan.json ir_windows_um'),
        clock_regions=V(hfp['clock_region_list'], 'um', 'measured', HFP + ' clock_region_list'),
        power=V(hfp['power']['peak_in_phase_w'], 'W', 'estimate', HFP + ' power.peak_in_phase_w (W/mm2 densities assumed)'),
    ),
    hbm_qwen=dict(
        title='HBM accelerator die, Qwen3-8B tile organisation',
        geo=gwrap('hbm_qwen', 'measured', QHB + ' (tools/hbm_accel_die_fp.py build_qwen() on that branch; floorplan.def)'),
        area=V(qhfp['die']['mm2'], 'mm2', 'measured', QHB + '/floorplan.json die.mm2'),
        placed=V(qhfp['placed_footprint_mm2'], 'mm2', 'measured', QHB + '/floorplan.json placed_footprint_mm2'),
        grt=V('GRT case q3a_b_k16_i50 (see feasibility.json)', '', 'measured', QHB + '/wire_stages.json grt_case'),
        power=V(qhfp['power'].get('peak_in_phase_w'), 'W', 'estimate', QHB + '/floorplan.json power.peak_in_phase_w'),
    ),
    ds_s81_layer=dict(
        title='DeepSeek-V4.1 ROM S81 layer die (L20 scan die)',
        geo=gwrap('ds_s81_layer', 'measured', 'tools/dsrom_s81_fulldie.py build() (layer) = results/rtl/dsrom_s81_fulldie_20261004/floorplan.def; the 16,919 cfg ROMs (7 per pair) are drawn as texture, not as rectangles',
                  note='Passed GRT/IR at 21fcf6469 before the recovery levers; full-die rerun pending (' + PLAN + ' risk 3).'),
        area=V(858.0, 'mm2', 'measured', 'tools/dsrom_s81_fulldie.py DIE = 33,000 x 26,000 um outline; priced die 839.2 mm2 in ' + DSM),
        grt=V('overflow 0; IR 28.6-32.2 mV (pre-recovery)', '', 'measured', PLAN + ' section 2 (S81 dies passed at 21fcf6469)'),
    ),
    qwen_rom=dict(
        title='Qwen3-8B ROM die (r17b)',
        geo=gwrap('qwen_rom', 'measured', 'r17b placement /tmp/qdie17/r17b_pdn/place.tcl + elements.lef (generator tools/qwen_rom_fulldie_b3r2.py on branch claude/qwen-die-rebuild-20261005 @f76c3603b; the placement files are scratch, not committed)',
                  note='Geometry from the r17b run directory; the r17b GRT and path-STA records are committed on the branch.'),
        area=V(823.78, 'mm2', 'measured', 'r17b manifest die 25,113.888 x 32,801.76 um (branch record ir_record.json meta.b3r2.die)'),
        grt=V('overflow %s (k16, 5 iterations)' % format(qgrt['layers']['Total']['overflow'], ','), '', 'measured', QGRT + ' layers.Total.overflow (M9 38 windows <= 1.036)'),
        ir=V({k: dict(win=v['meta']['window_um'], mv=v['rail_to_rail_interior_mv'], ok=v['pass_interior']) for k, v in qir.items() if k.startswith('r17b')},
             'mV', 'measured', QIR, note='uncommitted IR record (worktree, untracked); spine slab window fails 35 mV interior at 37.4 mV'),
        path=V(dict(bword_worst=qps['block_words']['stages_routed_max'], link_worst=qps['links']['stages_routed'], pitch=round(qps['pitch_um'], 1)),
               'stages', 'measured', QPS),
    ),
)

# ---------------------------------------------------------------- block catalogue: per die, per group
INV = HINV
def B(label, area, inst, rtl, closure, ss=None, ff=None, note='', src=''):
    return dict(label=label, area=area, inst=inst, rtl=rtl, closure=closure, ss=ss, ff=ff, note=note, src=src)

hl = hfp['block_ledger']
D['blocks'] = dict(
    hbm_ds=dict(
        phy=B('HBM3E PHY (one per stack)', V(10.006, 'mm2', 'measured', HFP + ' area_mm2_by_kind.phy / 4'), 4, 'ot_hbm3e_phy_v41x_aw30_e8p5 (real LEF view)', 'reservation', note='Vendor-style hard macro with real pins; content is a placeholder view.', src='results/rtl/die_top_lint_20261006/hbm_die_abstract_list.json'),
        svc=B('Stream service (32 pseudo-channels per stack)', V(hl['svc']['mm2'], 'mm2', 'estimate', HFP + ' block_ledger.svc'), 4, '32 x ot_hbm_accel_stream_pc_wb + cdc_fifo + expert fetch', 'open',
              ss=V(6.28, 'ps', 'measured', INV + ' ot_hbm_r14_stream_pc/stack r8b routed'), ff=V(5.11, 'ps', 'measured', INV), note='Stream stack closes routed; the pc_wb, cdc_fifo and expert-fetch parts have no closure record yet.'),
        sm=B('SM compute element (Tensor-Core-style matrix units)', V(hl['sm']['mm2'], 'mm2', 'measured', HFP + ' block_ledger.sm (measured-placed)'), 32, 'ot_hbm_accel_sm_v', 'open',
             ss=V(-102.66, 'ps', 'measured', INV + ' ot_gpu_tc_col routed'), ff=V(-0.91, 'ps', 'measured', INV), note='Worst routed on-SM part (tc_col); the whole element has never been routed at 1.2 GHz.'),
        su=B('SU quarter: serial vector unit (N1024 lanes) + fused chains', V(hl['su']['mm2'] / 4 + hl['su_fused']['mm2'] / 4, 'mm2', 'analytical', HFP + ' block_ledger.su (measured-placed) + su_fused (estimate), per quarter'), 4, 'ot_hdc_v41x_vec lane array + ot_dsrom_su_* fused chains', 'exact-not-closed',
             ss=V(-46, 'ps', 'measured', PLAN + ' section 2 (SU lane -4.8 / -46 ps)'), note='Runs in the 0.9 GHz serial domain by design.'),
        sfu=B('SFU quarter (transcendentals)', V(hl['sfu']['mm2'] / 4, 'mm2', 'analytical', HFP + ' block_ledger.sfu (model) / 4'), 4, 'SFU quarter (model ledger)', 'exact-not-closed',
              ss=V(-167, 'ps', 'measured', PLAN + ' section 2 (SFU tail -113 / -167 ps)')),
        hc=B('HC / mHC quarter (hyper-connection mix, Sinkhorn)', V(hl['hc']['mm2'] / 4, 'mm2', 'analytical', HFP + ' block_ledger.hc (model) / 4'), 4, 'HC quarter (model ledger only)', 'no-rtl'),
        index=B('Index path quarter (sparse-attention indexer)', V(1669.656 * 3080.136 / 1e6, 'mm2', 'measured', 'abstract size 1,669.7 x 3,080.1 um (abstract list)'), 4, 'ot_hbm_accel_index_path', 'open', note='No closure record.'),
        attn=B('Attention tile', V(hl['attn_tile']['mm2'], 'mm2', 'estimate', HFP + ' block_ledger.attn_tile'), 64, 'ot_attn_tile_registered_parent (leaf ot_attn_hgrp_m6h1b7p closed)', 'open', note='Tile about 881 MHz (' + PLAN + ').'),
        coll=B('Collective endpoint (TU)', V(hl['coll']['mm2'], 'mm2', 'estimate', HFP + ' block_ledger.coll'), 1, 'ot_hbm_accel_tu_endpoint', 'open',
               ss=V(-329, 'ps', 'measured', PLAN + ' section 2 (collective endpoint -329 ps)')),
        cmdproc=B('Command processor + pipelined issue', V(hl['cmdproc']['mm2'], 'mm2', 'estimate', HFP + ' block_ledger.cmdproc'), 1, 'ot_ds_hbm_cmdproc20 + ot_hbm_accel_issue', 'open',
                  ss=V(-136.7, 'ps', 'measured', INV + ' ot_hbm_accel_issue ENABLE=1 routed: r2r +27.94 ps but output ports -136.7 ps'), ff=V(8.4, 'ps', 'measured', INV)),
        vm=B('Vector memory / activation-multicast root', V(hl['vm']['mm2'], 'mm2', 'estimate', HFP + ' block_ledger.vm'), 1, 'no RTL top', 'no-rtl'),
        barrier=B('Barrier root (K32)', V(hl['barrier']['mm2'], 'mm2', 'measured', HFP + ' block_ledger.barrier (measured-routed)'), 1, 'ot_gpu_barrier_node K32', 'closed',
                  ss=V(384.3, 'ps', 'measured', 'results/rtl/hbm_accel_fmax_inventory_20261004/ctl_takeover_20261005/closure.json barrier_k32'), ff=V(39.39, 'ps', 'measured', 'same')),
        router=B('Router (top-k) + expert workgroup', V(hl['router']['mm2'], 'mm2', 'measured', HFP + ' block_ledger.router'), 1, 'ot_gpu_router_topk_f topk_f3', 'exact-not-closed', note='Registered-insert recipe exact on 2,000 vectors; no timing qualification yet (ctl_takeover closure.json blocked.router_topk).'),
        quant=B('Activation quantisers (FP4/FP8)', V(hl['quant']['mm2'], 'mm2', 'estimate', HFP + ' block_ledger.quant'), 1, 'ot_hdc_actquant', 'open', note='No closure record for this instance.'),
        loader=B('Weight loader (host side)', V(hl['loader']['mm2'], 'mm2', 'measured', HFP + ' block_ledger.loader (measured slot)'), 1, 'ot_hbm_accel_loader_host', 'open',
                 ss=V(-3672, 'ps', 'measured', HFP + ' block_ledger.loader (host SS -3,672 ps, not adopted)')),
        serdes=B('SerDes slab (switch links)', V(9.0, 'mm2', 'analytical', HFP + ' block_ledger.serdes 18 mm2 / 2 slabs (model)'), 2, 'reservation slab, no logic', 'reservation'),
        link=B('SerDes / UCIe pin macro', V(0.5626, 'mm2', 'measured', 'ot_pdie_serdes LEF 250 x 2,250 um'), 10, 'ot_pdie_serdes / ot_pdie_ucie (real pins, placeholder content)', 'reservation'),
        host=B('Host link slab', V(hl['host']['mm2'], 'mm2', 'analytical', HFP + ' block_ledger.host (model)'), 1, 'reservation slab', 'reservation'),
        waypoint=B('Wire station (registered wire stage)', V(round(hfp['area_mm2_by_kind']['waypoint'] / 208, 4), 'mm2', 'measured', HFP + ' area_mm2_by_kind.waypoint / 208'), 208, 'stations / multicast / gather / clock-distribution abstracts', 'no-rtl', note='One flop stage per 430.56 um of trunk.'),
    ),
    hbm_qwen=dict(
        tile=B('W12 ME tile (matrix engine + weight buffer)', V(round(669.077 / 1536, 4), 'mm2', 'measured', QHB + '/floorplan.json area_mm2_by_kind.tile / 1536'), 1536, 'ot_qwen_me_* W12 tile (HA8 vehicle)', 'open', note='ME spine / tile logic never routed at 1.2 GHz (' + INV + ').'),
        head=B('Column head', V(round(0.35 / 96, 4), 'mm2', 'measured', QHB + '/floorplan.json area_mm2_by_kind.head / 96'), 96, 'column head abstract', 'no-rtl'),
        phy=B('HBM3E PHY', V(10.006, 'mm2', 'measured', QHB + '/floorplan.json area_mm2_by_kind.phy / 4'), 4, 'ot_hbm3e_phy_v41x_aw30_e8p5', 'reservation'),
        svc=B('Stream service', V(round(8.813 / 4, 3), 'mm2', 'estimate', QHB + '/floorplan.json area_mm2_by_kind.svc / 4'), 4, 'stream service abstract', 'open'),
        spine=B('Spine: core, scale/port slices, loader', V(32.872, 'mm2', 'measured', QHB + '/floorplan.json area_mm2_by_kind.spine (all spine blocks)'), 10, 'qhd_core / qhd_scale* / qhd_port* / qhd_loader', 'open', note='Qwen-side core, collective and lane blocks open (' + PLAN + ').'),
        hub=B('Collective endpoint', V(3.6, 'mm2', 'measured', QHB + '/floorplan.json area_mm2_by_kind.hub'), 1, 'qhd_coll', 'open'),
        link=B('SerDes / UCIe pin macro', V(0.5626, 'mm2', 'measured', 'ot_pdie_serdes LEF'), 5, 'ot_pdie_serdes / ot_pdie_ucie', 'reservation'),
        serdes_slab=B('SerDes slab', V(4.0, 'mm2', 'measured', QHB + '/floorplan.json area_mm2_by_kind.serdes_slab'), 1, 'reservation', 'reservation'),
        host_slab=B('Host slab', V(10.003, 'mm2', 'measured', QHB + '/floorplan.json area_mm2_by_kind.host_slab'), 2, 'reservation', 'reservation'),
        waypoint=B('Wire station', V(round(0.216 / 78, 4), 'mm2', 'measured', QHB + '/floorplan.json area_mm2_by_kind.waypoint / 78'), 78, 'station abstracts', 'no-rtl'),
    ),
    ds_s81_layer=dict(
        q=B('ROM element pair, FP8/FP4 (q-element)', V(round(0.51084 * 0.1269, 4), 'mm2', 'measured', 'tools/dsrom_s81_fulldie.py docstring: routed abstract ot_v41_rom_elem_q_qp_w10 510.84 x 126.9 um'), 1898, 'ot_v41_rom_elem_q_qp_w10 (closure successor ot_v41_rom_elem_q_qx_w10)', 'exact-not-closed',
            note='Exact in the field composition (QX 8: -0.13% AR); the q-element is not yet closed (results/rtl/dsrom_field_qelem_20261005/README.md).'),
        bf=B('ROM element pair, BF16 (W10 pair)', V(round(1.0029 * 0.1577, 4), 'mm2', 'measured', LEV + 'head.json physical_cost.old_element (dsfd_bf 1,002.9 x 157.7 um)'), 519, 'ot_v41_rom_elem_w10', 'closed',
             ss=V(140.04, 'ps', 'measured', LEV + 'field.json ss_ff.ss_wns_ps.pair (per-pair hardware, routed)'), ff=V(5.04, 'ps', 'measured', LEV + 'field.json ss_ff.ff_hold_wns_ps.pair')),
        node=B('Ragged return-tree node', V(round(0.0864 * 0.07776, 5), 'mm2', 'measured', 'tools/dsrom_s81_fulldie.py NODE_FRAME 86.4 x 77.76 um'), 4706, 'ot_v41_retn_w17w10', 'open', note='No closure record located for the node at 1.2 GHz.'),
        hub=B('Spine slab (SU / gather / VM / collective / HC)', V(None, 'mm2', 'measured', 'per-instance rectangle'), 7, 'dsfd_sp_* slabs', 'exact-not-closed', note='Fused SU chains: hc_post closed (+0.23/+1.69 ps); norm, softmax and SwiGLU exact, PENDING_SSFF.'),
        phy=B('HBM3E PHY', V(10.006, 'mm2', 'measured', 'PHY LEF 8,500 x 1,177 um'), 4, 'ot_hbm3e_phy_v41x_aw30_e8p5', 'reservation'),
        ctrl=B('Streaming HBM controller', V(round(8.5 * 0.248, 3), 'mm2', 'measured', 'rectangle 8,500 x 248 um'), 4, 'dsfd_ctrl', 'open'),
        svc=B('Scan service (attention tiles + indexer ring reader)', V(round(8.5 * 1.577, 3), 'mm2', 'measured', 'rectangle 8,500 x 1,577 um'), 4, 'dsfd_svc', 'open'),
        band_blk=B('Selector (S) / banked collector (N)', V(None, 'mm2', 'measured', 'rectangles'), 2, 'dsfd_bk_selector / dsfd_bk_collector', 'open'),
        fifo_blk=B('Clock-region FIFO block (meso FIFOs)', V(round(0.38016 * 0.1296, 4), 'mm2', 'measured', 'FIFO_BLK 380.16 x 129.6 um'), 44, 'meso_d4_v3 FIFO slots', 'open', note='meso_d4_v3 signoff target not met (results/uarch/meso_fifo_20261004/physical/meso_d4_v3/physical.json).'),
        hub_fifo=B('Hub-side FIFO slot', V(round(0.12528 ** 2, 4), 'mm2', 'measured', 'MF 125.28 um square'), 24, 'meso / async FIFO', 'open'),
        link=B('UCIe / board SerDes macro', V(0.5626, 'mm2', 'measured', 'pdie LEFs'), 8, 'ot_pdie_ucie / ot_pdie_serdes', 'reservation', note='Stage hop endpoint ot_dsrom_link_rt; cut-through ot_dsrom_link_ct fails SS -500.4 ps (hop lever rejected).'),
        waypoint=B('Forwarded-link waypoint', V(None, 'mm2', 'measured', 'rectangles'), 216, 'station abstracts', 'no-rtl'),
    ),
    qwen_rom=dict(
        tile=B('ROM tile (code ROM beside the multipliers)', V(round(0.260904 * 1.291656, 4), 'mm2', 'measured', 'r17b elements.lef qfd_tile 260.9 x 1,291.7 um'), 1536, 'ot_qwen_rom_tile_* (W12 ME + ROM banks)', 'open', note='No routed tile closure record located; corridor stage at 430.56 um closes SS +11.9 ps.'),
        station=B('Corridor station (registered tap)', V(round(0.05268 * 0.103656, 5), 'mm2', 'measured', 'qfd_cst LEF'), 1536, 'corridor station', 'closed',
                  ss=V(11.9, 'ps', 'measured', 'results/rtl/qwen_corridor_gate_20261003 (D_tile_r2 430.56 um: SS60 +11.9 ps, FF25 met)'), note='FF hold met (value not recorded in the cited line).'),
        col_head=B('Column head', V(round(0.05268 * 0.103656, 5), 'mm2', 'measured', 'qfd_chead LEF'), 64, 'column head', 'no-rtl'),
        row_engine=B('Row engine (KV stream consumer)', V(round(0.328296 * 1.997976, 4), 'mm2', 'measured', 'qfd_reng LEF'), 24, 'row engine', 'open'),
        hbm_ctrl=B('HBM controller band', V(round(0.247512 * 12.141336, 3), 'mm2', 'measured', 'qfd_ctrl LEF'), 4, 'STREAM4 controller band (976.6 MHz)', 'open', note='Landing merge -0.75 ns open (' + PLAN + ').'),
        cdc=B('STREAM4 CDC frame (per pseudo-channel)', V(round(0.183048 ** 2, 4), 'mm2', 'measured', 'qfd_cdc LEF'), 128, 'per-PC async FIFO frame', 'open'),
        hub=B('Hub element', V(round(0.412536 ** 2, 4), 'mm2', 'measured', 'qfd_hub LEF'), 1, 'hub element', 'open'),
        spine=B('Spine slab (VM, SU64 + SFU, tree top, constants + sequencer)', V(None, 'mm2', 'measured', 'per-instance LEF'), 4, 'qfd_sp_*', 'exact-not-closed', note='Core decode adopted r5b_f3ba closes in context (SS +0.87 / FF +7.12 ps).'),
        band_slab=B('Band slab (port + scale groups)', V(None, 'mm2', 'measured', 'per-instance LEF'), 16, 'ot_qwen_slab_port_group x 8 per band', 'open', note='Port/scale slab share open (' + PLAN + ').'),
        link_fifo=B('Link FIFO', V(round(0.096744 * 0.153336, 4), 'mm2', 'measured', 'qfd_lfifo LEF'), 4, 'link FIFO', 'open'),
        link_station=B('Link station (registered wire stage)', V(None, 'mm2', 'measured', 'per-instance LEF'), 32, 'link stations', 'no-rtl'),
        io=B('IO block (collective, embedding ROM, UCIe, SerDes)', V(None, 'mm2', 'measured', 'per-instance LEF'), 4, 'qfd_io_*', 'reservation'),
        phy=B('HBM3E PHY (E/W edge)', V(round(0.833496 * 12.00012, 3), 'mm2', 'measured', 'phy_ew.lef 833.5 x 12,000 um'), 4, 'ot_hbm3e_phy (E/W variant)', 'reservation'),
    ),
)

# ---------------------------------------------------------------- closure board (SS / FF slack at 833 ps)
inv = J(R / HINV)
board = []
def C(design, block, ss, ff, closure, src, basis):
    board.append(dict(design=design, block=block, ss=ss, ff=ff, closure=closure, src=src, basis=basis))
# DS ROM
C('ds', 'BF16 W10 pair', 140.04, 5.04, 'closed', LEV + 'field.json', 'routed')
C('ds', 'LM head bundle element A', 24.43, 8.49, 'closed', LEV + 'head.json ss_ff.elements.A', 'routed')
C('ds', 'Router select tree', 65.6, 5.4, 'closed', LEV + 'router.json ss_ff', 'pre-layout screen')
C('ds', 'SU hc_post lane (fused)', 0.23, 1.69, 'closed', LEV + 'su_hcpost.json ss_ff', 'routed')
C('ds', 'SU softplus/sqrt lane (0.9 GHz)', 17.0, 3.74, 'closed', LEV + 'su_routeract.json ss_ff.route (1.111 ns)', 'routed at 0.9 GHz')
C('ds', 'Field spine successor PQ1 R16', 13.98, 0.61, 'exact-not-closed', LEV + 'field_spine_pq.json ss_ff (one max-slew pin; R128 pending)', 'routed')
C('ds', 'Field spine successor PQ0 R16', 18.74, -0.18, 'exact-not-closed', LEV + 'field_spine.json ss_ff (FAIL_HOLD)', 'routed')
C('ds', 'SU norm divider', 21.99, 7.7, 'exact-not-closed', LEV + 'su_norm.json ss_ff.routed.divc (parent boundary pending)', 'routed')
C('ds', 'SU SwiGLU lane', 19.37, 0.96, 'exact-not-closed', LEV + 'su_swiglu.json ss_ff.lane', 'routed')
C('ds', 'Actquant f12 quantiser', 11.51, 0.51, 'exact-not-closed', LEV + 'su_swiglu.json ss_ff.quantiser', 'routed')
C('ds', 'Old field spine PQ1 R16 (rejected)', -722.82, 3.37, 'open', LEV + 'field.json ss_ff', 'routed')
C('ds', 'Cut-through link ot_dsrom_link_ct (rejected)', -500.4, 4.2, 'open', LEV + 'hop.json ss_ff', 'pre-layout screen')
# Qwen ROM
C('qwen', 'Core decode r5b_f3ba (in die context)', 0.87, 7.12, 'closed', CMP + ' qwen_rom.levers.core_context', 'routed, context')
C('qwen', 'Corridor stage 430.56 um', 11.9, None, 'closed', 'results/rtl/qwen_corridor_gate_20261003', 'routed')
C('qwen', 'Landing merge', -750, None, 'open', PLAN + ' section 2', 'routed')
# HBM from inventory (blocks with both numbers or SS)
for b in inv['blocks']:
    if b.get('period_ns') == 0.833 and b.get('ss_reg_to_reg_slack_ps') is not None:
        st = {'closed': 'closed', 'closed_unit': 'closed', 'closed_variant': 'closed', 'screen_pass': 'closed'}.get(b['status'], 'open')
        C('hbm', b['module'][:60], b['ss_reg_to_reg_slack_ps'], b.get('ff_hold_slack_ps'), st, HINV + ' (' + b['evidence'][:90] + ')', b.get('evidence_kind') or '')
C('hbm', 'Barrier node K32', 384.3, 39.39, 'closed', 'results/rtl/hbm_accel_fmax_inventory_20261004/ctl_takeover_20261005/closure.json', 'routed')
C('hbm', 'Collective endpoint (TU)', -329, None, 'open', PLAN + ' section 2', 'routed')
C('hbm', 'SFU tail', -167, None, 'open', PLAN + ' section 2', 'routed')
D['closure_board'] = V(board, 'ps', 'measured', 'per-row src; slack at 0.833 ns with 60 ps SS / 25 ps FF uncertainty; inventory rows dated 2026-10-04')

# ---------------------------------------------------------------- principles (atlas Table 5-2) + fused chains (Table 8-14b)
D['principles'] = V([
    ['Stationary weights', 'Weights are stationary, in ROM beside the multipliers.', 'ROM words are laid out in the order the engine streams them; address generation is a counter; each lane group reads its own macro every cycle.'],
    ['Compiled schedule', 'The schedule is the program; control is compiled away.', 'A static list of macro-operations; hazards resolved at program generation; consumers chain on their producers’ progress, per vector.'],
    ['Fixed-latency pipelines', 'Every unit is a fixed-latency pipeline with initiation interval 1, registered at every port.', 'No iterative units and no combinational IEEE operations; irregular operators get dedicated pipelines (select, Sinkhorn, Engram); nothing stalls.'],
    ['Deterministic collectives', 'Collectives are deterministic, fixed-size and local.', 'Every transfer has the same size, destination and order for every token; routing selects ROM rows, not message paths; reductions sum in a fixed order.'],
    ['Bit-exact verification chain', 'Golden → ISA → program → RTL, against a golden whose reduction order is chosen for hardware.', 'Every sum is chunks of eight and a pairwise tree; the RTL must match in every logit, vector memory and KV cache.'],
    ['Streamed per-user state', 'Per-user state streams from attached HBM at close to raw bandwidth.', 'KV and index keys in HBM beside the ROM die, prefetched a layer ahead; refresh-aware controller with deep per-channel queues.'],
    ['Replicated hardened elements', 'Floorplan first, then one hardened array element sized to the full goal, replicated.', 'Each die is a symmetric array of one element with a real macro abstract, replicated to the count the budget requires.'],
    ['Fused dependent chains', 'A chain of small dependent vector operations runs as one streaming pipeline in the consumer’s clock domain.', 'Once weights are free, each dependent operation on a shared vector unit costs about 70 ns of overhead; fusing removes it.'],
    ['Established organisation for HBM comparators', 'HBM-weight comparators replicate a GPU organisation; only the ROM designs are novel.', 'SM-like elements with Tensor-Core-style matrix units, register files, shared memory and shoreline HBM controllers.'],
], '', 'measured', ATLAS + ' Table 5-2 (principles)', note='Text quoted or condensed from the atlas; status refers to the source being the adopted design document.')
D['fused_chains'] = V([
    ['Post-attention / post-FFN hyper-connection mix', 0.290, 0.086, 103, 'Adopted; routed SS +0.23 / FF +1.69 ps'],
    ['Attention pre-norm: hc_pre → RMSNorm → FP8 quantise', 0.755, 0.230, 276, 'At floor, exact; lane and RoPE routes pending'],
    ['FFN pre-norm: hc_pre → RMSNorm', 0.522, 0.215, 258, 'Exact, pending'],
    ['Query: q-norm → quantise', 0.489, 0.208, 250, 'Exact, pending'],
    ['Key/value: kv-norm → RoPE → quantise-dequantise', 0.510, 0.203, 244, 'Exact, pending'],
    ['SwiGLU → route-weight multiply → FP8 quantise', 0.483, 0.155, 186, 'Exact; re-staged quantiser routes closed'],
    ['Router activation: softplus → √', 0.152, 0.147, 132, 'Adopted at 0.9 GHz; routed SS +17.0 / FF +3.74 ps'],
], 'us', 'measured', ATLAS + ' Table 8-14b (fused chains, before/after per chain)')
D['spec_table'] = V([
    ['Qwen3-8B ROM, 8K, STREAM4', 'none: compute-bound, KV fill hidden', 5282, '17,197 (4)', 3.26, 0.70],
    ['Qwen3-8B HBM accelerator, TP4, 8K', 'weight stream', 17237, '16,044 (4)', 0.93, 2.28],
    ['DeepSeek-V4.1 ROM array, 1M', 'pipeline latency (wavefront)', '620.1 us/token', '748.9 us (6)', 1.21, 2.77],
], '', 'measured', ATLAS + ' Table 8-14a (section 8.6)', note='Atlas snapshot; DS row predates the current 592.9 us recovery composition.')

# ---------------------------------------------------------------- links (array views) and racks (rack view)
# Bandwidths set the drawn stroke width of each link; latencies feed the link-class tables.
RACK = 'results/arch/v41_rack.json'
rack = J(R / RACK)
PCK = rack['physical_constants']
LNK = 'results/rtl/dsrom_1m_allmeasured_20261004/links.json'
lnk = J(R / LNK)
TECH = 'configs/hardware/technology.json'
tech = J(R / TECH)['links']
ES = 'results/arch/energy_silicon_measured/energy_silicon.json'
es = J(R / ES)
S81FP = 'results/rtl/dsrom_s81_fulldie_20261004/floorplan.json'
s81p = J(R / S81FP)['scan_die_power']
HSL = 'results/uarch/hbm_switch_latency_authoritative_20261004/README.md'
UM = 'tools/uarch_model.py TU dict (Tomahawk Ultra protocol: 8 x 800G ports per 2-die package, payload efficiency 0.9 ASSUMED)'
HFPJ = J(R / HFP)
D['links'] = dict(
    ds_stage=V(round(lnk['hop']['phy_lane_rate_GBps'], 1), 'GB/s', 'analytical', LNK + ' hop.phy_lane_rate_GBps (13 lanes of 112G PAM4 net of FEC); the RTL endpoint measured ' + str(lnk['hop']['endpoint_rate_GBps']) + ' GB/s',
               note='per stage hop, one direction'),
    ds_tp=V(300.0, 'GB/s', 'analytical', TECH + ' links.rom_board_serdes: 0.30 TB/s per neighbour on a two-die package (lanes scale with sqrt(dies/4))'),
    ds_ucie=V(round(tech['rom_package_ucie']['bytes_s']['value'] / 1e9), 'GB/s', 'analytical', TECH + ' links.rom_package_ucie.bytes_s (one die-to-die neighbour in a package)'),
    ds_draft=V(round(lnk['hop']['phy_lane_rate_GBps'], 1), 'GB/s', 'analytical', DRAFT + ' placement.links (board + UCIe class, the stage-hop endpoint; full RS(544,514) FEC per ' + FEC_RULE + ') at the stage hop PHY rate'),
    hbm_uplink=V(400.0, 'GB/s', 'estimate', UM + ': 8 x 800G = 800 GB/s per package per direction, so 400 GB/s a die'),
    hbm_qwen=V(400.0, 'GB/s', 'placeholder', 'no record of the Qwen tile die link; drawn at the DS HBM die uplink (' + UM + ')'),
    qwen_ar=V(300.0, 'GB/s', 'analytical', TECH + ' links.rom_board_serdes per neighbour (two-die package class); results/uarch/economics.json qwen_rom.product (2 two-die packages, board link)'),
)
D['hbm_system']['switch_chips'] = V(es['deepseek_1m']['hbm_accel']['silicon']['switch_chips'], 'chips', 'estimate', ES + ' deepseek_1m.hbm_accel.silicon.switch_chips (one Tomahawk Ultra tier, ASSUMED)')

OU_MM = PCK['orv3_ou_mm']['value']; USABLE = PCK['orv3_usable_ou']['value']
WALL = rack['power']['wall_factor']; MARGIN = rack['power']['provision_margin']
SHELF_N1 = rack['power']['shelves']['n_plus_1_w']; STACK_W = PCK['hbm3e_stack_static_w']['value']
PKG_MM = PCK['package_mm']['value']; TRAY_KG = PCK['tray_mass_kg']['value']
src_rack = RACK + ' (legacy 28-stage rack study: ORv3 frame, 1 OU liquid stage tray of 4 two-die packages, power shelves, cable tiers)'


def shelves_for(w_prov):
    per_side = max(1, -(-int(w_prov) // int(SHELF_N1)))
    return 2 * per_side


def build_racks(trays, infra_top, die_w, label):
    """Pack trays (list of dicts with 'ou','kind','w') into ORv3 racks of USABLE OU. Each rack takes 2N power shelves
    sized to its provisioned wall power, a management switch, and (rack 0) the infra_top rows."""
    racks, cur = [], None
    def new_rack():
        return dict(rows=[], trays=[], w_chips=0.0)
    cur = new_rack(); racks.append(cur)
    for t in trays:
        extra = sum(r['h'] for r in infra_top) if len(racks) == 1 else 0
        trial_w = cur['w_chips'] + t['w']
        prov = trial_w * WALL * MARGIN + (sum(r.get('w', 0) for r in infra_top) if len(racks) == 1 else 100) * MARGIN
        used = sum(x['ou'] for x in cur['trays']) + t['ou'] + shelves_for(prov) + 1 + extra
        if used > USABLE:
            cur = new_rack(); racks.append(cur)
        cur['trays'].append(t); cur['w_chips'] += t['w']
    out = []
    for i, rk in enumerate(racks):
        infra = infra_top if i == 0 else []
        infra_w = sum(r.get('w', 0) for r in infra) + 100
        prov = rk['w_chips'] * WALL * MARGIN + infra_w * MARGIN
        ns = shelves_for(prov)
        rows, ou = [], 1
        for s in range(ns):
            rows.append(dict(ou=ou, h=1, kind='power', label=f"power shelf {'AB'[s % 2]}{s // 2 + 1} (33 kW, 6 x 5.5 kW PSU)")); ou += 1
        for t in rk['trays']:
            rows.append(dict(ou=ou, h=t['ou'], kind=t['kind'], label=t['label'], pk=t['pk'], w=round(t['w'], 1))); ou += t['ou']
        for r in infra:
            rows.append(dict(ou=ou, h=r['h'], kind=r['kind'], label=r['label'])); ou += r['h']
        rows.append(dict(ou=ou, h=1, kind='mgmt', label='management switch (1 GbE OOB) + leak detection')); ou += 1
        dies = sum(len(p['d']) for t in rk['trays'] for p in t['pk'])
        pk = sum(len(t['pk']) for t in rk['trays'])
        n_tray = len(rk['trays'])
        kg = 170 + 60 + n_tray * (TRAY_KG[0] + TRAY_KG[1]) / 2 + sum(r['h'] for r in infra) * 12 + ns * 8
        out.append(dict(name=f'{label}{i + 1}', rows=rows, used_ou=ou - 1, dies=dies, packages=pk, trays=n_tray,
                        chips_kw=round(rk['w_chips'] / 1e3, 2), wall_kw=round((rk['w_chips'] * WALL + infra_w) / 1e3, 2),
                        prov_kw=round(prov / 1e3, 2), shelves=ns, kg=round(kg)))
    return out


# --- DeepSeek ROM S81: 81 stages x TP4 (2 two-die packages a stage), 12 head, 36 Engram table, +52 draft dies.
# The packing, hop classes, die counts and HBM stacks come from the committed rack record (tools/dsrom_s81_rack.py).
def mkpk(role, dies, stage=None):
    global pid
    p = dict(id=pid, r=role, d=dies)
    if stage is not None:
        p['s'] = stage
    pid += 1
    return p
def tray(kind, pks, label, die_w, stacks_per_die):
    n = sum(len(p['d']) for p in pks)
    return dict(ou=1, kind=kind, pk=pks, label=label, w=n * die_w + n * stacks_per_die * STACK_W)
ds_racks = dsr['racks']
pid = 1 + max(p['id'] for rk in ds_racks for row in rk['rows'] for p in row.get('pk', []))
LAYER_W = dsr['die_w']['layer']
hs = dsr['hop_summary']['stage_hops']
hops = {'tray': hs.get('in-tray', 0), 'rack': hs.get('in-rack', 0), 'cross': hs.get('rack-to-rack', 0)}
dc = dsr['counts']
ds_dies = dc['dies']
RK_NOTE = ('Packing from ' + DSR + ' (tools/dsrom_s81_rack.py): two consecutive stages a tray, the chain as a U over two '
           'racks (down R1, across at the bottom, up R2 above the Engram tables), head trays beside S0, draft trays beside '
           'the head trays. Tray, power-shelf and cable template from the legacy rack study (' + RACK + '); not a '
           'mechanically qualified rack design.')
cls_ns = {c['cls']: c for c in dsr['link_classes']}
cross = dsr['packing']['rack_crossing']
D['racks'] = dict(
    frame=dict(
        ou_mm=V(OU_MM, 'mm', 'measured', RACK + ' physical_constants.orv3_ou_mm (Open Rack OpenU, published)'),
        usable_ou=V(USABLE, 'OU', 'measured', RACK + ' physical_constants.orv3_usable_ou (published)'),
        width_mm=V(PCK['orv3_it_width_mm']['value'], 'mm', 'measured', RACK + ' physical_constants.orv3_it_width_mm (published)'),
        depth_mm=V(PCK['orv3_tray_depth_mm']['value'], 'mm', 'estimate', RACK + ' physical_constants.orv3_tray_depth_mm'),
        package_mm=V(PKG_MM, 'mm', 'estimate', RACK + ' physical_constants.package_mm (two ~815 mm2 dies + 8 HBM3E on a ~3.3-reticle CoWoS-L interposer)'),
        die_mm=V(PCK['die_mm']['value'], 'mm', 'analytical', RACK + ' physical_constants.die_mm'),
        hbm_mm=V(PCK['hbm3e_footprint_mm']['value'], 'mm', 'measured', RACK + ' physical_constants.hbm3e_footprint_mm (Micron, published)'),
        wall_factor=V(round(WALL, 4), 'x', 'analytical', RACK + ' power.wall_factor (VR 0.87, PSU 0.96, fans 3%, CDU)'),
        margin=V(MARGIN, 'x', 'analytical', RACK + ' power.provision_margin'),
        shelf_kw=V(SHELF_N1 / 1e3, 'kW N+1', 'measured', RACK + ' power.shelves.n_plus_1_w (ORv3 HPR shelf, published)'),
        cooling_limit_w=V(s81p['cooling_limit_w'], 'W/die', 'analytical', S81FP + ' scan_die_power.cooling_limit_w (liquid, 2-die package: GB200 class package rating less the stacks)'),
    ),
    ds=dict(
        racks=V(ds_racks, 'racks', 'estimate', DSR + ' racks (' + dsr['packing']['rule'] + ')', note=RK_NOTE),
        counts=V(dict(stages=dc['stages'], layer=dc['layer'], head=dc['head'], table=dc['table'], draft=dc['draft'], dies=ds_dies,
                      packages=ds_dies // 2, stacks=dsr['stacks']['total'], scan_dies=dsr['stacks']['scan_dies']), 'dies', 'analytical',
                 DSR + ' counts: head ' + dc['src']['head'] + '; table ' + dc['src']['table'] + '; draft ' + dc['src']['draft'] + '; stacks ' + dsr['stacks']['src'],
                 note='Resolved 2026-10-06: 12 head + 36 Engram table dies (the 8 + 36 of the C1 ledger and the 12 + 32 this page showed earlier are both stale); '
                      'HBM stacks sized to need (scenario C): 4 on the 32 scan dies and the 12 head dies, 1 on the other 292 layer dies, none on table or draft dies = 468.'),
        die_w=V(dict(layer=LAYER_W, head_table=dsr['die_w']['head_table'], stack=STACK_W), 'W', 'analytical', DSR + ' die_w: ' + dsr['die_w']['src']),
        system_kw=V(dict(ar=round(es['deepseek_1m']['rom']['power']['ar_b1_icg']['system_w'] / 1e3, 2), mtp=round(es['deepseek_1m']['rom']['power']['mtp_b1_icg']['system_w'] / 1e3, 2)), 'kW', 'analytical',
                    ES + ' deepseek_1m.rom.power.{ar_b1_icg,mtp_b1_icg}.system_w (' + es['deepseek_1m']['rom']['design'] + ')'),
        hops=V(hops, 'stage hops', 'analytical', DSR + ' hop_summary.stage_hops (in-tray / in-rack / rack-to-rack); head hop ' + dsr['head_hop']['cls'] + ' ' + str(dsr['head_hop']['length_m']) + ' m, token return ' + dsr['token_return']['cls'], note=RK_NOTE),
        fec=V(dict(rule=FEC_RULE, hop_us=lff['hop']['us'], hop_light_us_was=round(lff['hop']['light_fec_cycles'] / 1.2e3, 4),
                   coll_delta_cycles=lff['collective_delta_cycles']['values'][0], cable_flight_us=dsc['info'].get('full_fec', {}).get('cable_flight_us'),
                   d_AR_tok_s=ds.get('link_fec', {}).get('delta_vs_light_fec', {}).get('AR_tok_s'), d_MTP_tok_s=ds.get('link_fec', {}).get('delta_vs_light_fec', {}).get('MTP_tok_s'),
                   d_AR_us=ds.get('link_fec', {}).get('delta_vs_light_fec', {}).get('AR_us'), hbm_d_us=hb.get('full_fec', {}).get('AR_us'), hbm_crossings=hb.get('full_fec', {}).get('crossings_AR')),
              'us', 'measured', LFF + ' (RTL: stage hop 1,004 cyc, token return, TP4 collectives +100 cyc each, bit-exact) + ' + DSR + ' cable flight per class; deltas ' + CMP + ' ds_rom.link_fec / hbm_ds.full_fec'),
        sat_tok_s=V(80833.5, 'tok/s', 'analytical', 'tools/dsrom_c_recheck.py SAT_TOK_S (head-bound saturated AR rate, all users)'),
        links=V([dict(cls=c['cls'], what=c['what'], medium=c['medium'] + ', ' + c['fec'], ns=c['ns'],
                      GBps=(D['links']['ds_ucie']['v'] if c['cls'] == 'in-package' else D['links']['ds_stage']['v']),
                      st=('analytical' if c['cls'] == 'in-package' else 'measured'), src=c['src']) for c in dsr['link_classes']],
                'ns per hop', 'analytical', DSR + ' link_classes; ' + FEC_RULE),
    ),
)
HBM_FEC_D = hb['full_fec']['per_crossing_ns']
# --- HBM accelerator: 96 dies in 48 two-die packages, one Tomahawk-Ultra tier of 8 chips (2 a switch tray)
H_DIES = 96; H_W = HFPJ['power']['peak_in_phase_w']
h_pk = [mkpk('hbm', [f'a{2 * i}', f'a{2 * i + 1}']) for i in range(H_DIES // 2)]
h_trays = [tray('compute', h_pk[i:i + 4], f'compute tray {i // 4}: dies {2 * i}-{2 * i + 7}', H_W, 4) for i in range(0, len(h_pk), 4)]
n_sw = D['hbm_system']['switch_chips']['v']
h_infra = [dict(h=1, kind='switch', label=f'Tomahawk Ultra switch tray {k} (2 x 51.2T chips)', w=1000.0) for k in range(-(-n_sw // 2))] + \
          [dict(h=2, kind='host', label='host: 2-socket CPU + NICs + BMC', w=900.0)]
h_racks = build_racks(h_trays, h_infra, H_W, 'H')
D['racks']['hbm'] = dict(
    racks=V(h_racks, 'racks', 'estimate', src_rack + '; 48 two-die packages and 8 TU chips per ' + UM, note='Tray density follows the ROM stage tray (4 packages a 1 OU liquid tray); 2 switch chips a 1 OU tray as in NVL72 switch trays.'),
    counts=V(dict(dies=H_DIES, packages=H_DIES // 2, stacks=4 * H_DIES, switch_chips=n_sw, ports_per_package=8), 'dies', 'analytical', ES + ' deepseek_1m.hbm_accel.silicon; ' + UM),
    die_w=V(dict(die=H_W, stack=STACK_W, switch_chip=500.0), 'W', 'estimate', HFP + ' power.peak_in_phase_w (assumed densities); switch 500 W ASSUMED (' + ES + ')'),
    system_kw=V(dict(ar=round(es['deepseek_1m']['hbm_accel']['power']['ar_b1']['system_w'] / 1e3, 2)), 'kW', 'estimate', ES + ' deepseek_1m.hbm_accel.power.ar_b1.system_w (incl. 8 x 500 W switches, ASSUMED)'),
    fabric_tbps=V(n_sw * 51.2, 'Tb/s', 'estimate', PCK['switch_capacity_tbps']['source'] + ' x ' + str(n_sw) + ' chips'),
    links=V([
        dict(cls='in-package', what='die to die inside a 2-die package', medium='package D2D (Blackwell class)', ns=None, GBps=round(tech['on_package']['bytes_s']['value'] / 1e9), st='placeholder', src=TECH + ' links.on_package (10 TB/s published); latency not in any record'),
        dict(cls='in-tray', what='none: every collective leaves the package for the switch', medium='—', ns=None, GBps=None, st='analytical', src=UM),
        dict(cls='in-rack', what='die to switch to die: one striped crossing (all-gather, reduce-scatter leg)', medium='SUE over twinax <= 3 m via Tomahawk Ultra, full RS(544,514) FEC', ns=round(477.6 + HBM_FEC_D, 1), GBps=720.0, st='estimate', src=HSL + ' (Broadcom SUE RM104 vendor budget: 100 bridge + 100 PHY + 250 switch + 2 x 3 m x 4.6 ns/m) with the endpoint PHY at the full-KP4 channel (+' + str(HBM_FEC_D) + ' ns, ' + CMP + ' hbm_ds.full_fec); 720 GB/s payload per package'),
        dict(cls='in-rack', what='32 KB all-reduce: two crossings + measured golden-order reducer', medium='same', ns=round(1214.6 + 2 * HBM_FEC_D, 1), GBps=720.0, st='estimate', src=HSL + ' (vendor crossings, full-FEC endpoint PHY, + measured HA2 reducer 18.3 ns)'),
        dict(cls='rack-to-rack', what='none: the 96-die machine fits one rack', medium='—', ns=None, GBps=None, st='estimate', src='this build'),
    ], 'ns per hop', 'estimate', HSL + '; ' + FEC_RULE),
)
# --- Qwen ROM: 4 dies in 2 two-die packages on one tray
q_pk = [mkpk('qwen', [f'q{2 * i}', f'q{2 * i + 1}']) for i in range(2)]
Q_W = es['qwen_8k']['rom']['power']['ar']['system_w'] / 4
q_trays = [tray('qtray', q_pk, 'Qwen ROM tray: TP4 = 2 two-die packages', Q_W, 4)]
q_racks = build_racks(q_trays, [dict(h=2, kind='host', label='host: CPU + NIC + BMC', w=900.0)], Q_W, 'Q')
D['racks']['qwen'] = dict(
    racks=V(q_racks, 'racks', 'estimate', src_rack + '; 2 two-die packages per results/uarch/economics.json qwen_rom.product', note='A Qwen TP4 group is one tray: a rack holds many independent groups; one is drawn.'),
    counts=V(dict(dies=4, packages=2, stacks=16), 'dies', 'analytical', 'results/uarch/economics.json qwen_rom.product.packages'),
    system_kw=V(dict(ar=round(es['qwen_8k']['rom']['power']['ar']['system_w'] / 1e3, 3)), 'kW', 'analytical', ES + ' qwen_8k.rom.power.ar.system_w (at 6,170 tok/s)'),
    links=V([
        dict(cls='in-package', what='die to die inside a 2-die package', medium='UCIe advanced package', ns=10.0, GBps=D['links']['ds_ucie']['v'], st='analytical', src=TECH + ' links.rom_package_ucie'),
        dict(cls='in-tray', what='TP4 all-reduce across the two packages (72 a token)', medium='112G PAM4 board trace, light FEC (as measured; the 2026-10-06 full-FEC rule names the DS ROM array and the HBM accelerator, Qwen not yet re-priced)', ns=406.6, GBps=300.0, st='measured', src='results/uarch/economics.json qwen_rom.product.exchange.per_allreduce_ns (measured on the DS TP4 board group, transferred)'),
    ], 'ns per hop', 'analytical', 'results/uarch/economics.json'),
)
D['racks']['nvl72'] = V(dict(kw=132, gpus=72, racks=1, switch_trays=9, compute_trays=18, kg=1360), 'rack', 'measured', ATLAS + ' section 6.9 Figure 6-9 (GB200 NVL72 published figures)')

BUILD.mkdir(parents=True, exist_ok=True)
(BUILD / 'data.json').write_text(json.dumps(D, separators=(',', ':')))
print('bytes', len(json.dumps(D, separators=(',', ':'))))
print('ds segments', len(seg_out), 'sum', round(sum(sum(s['cats'].values()) + s['hop'] for s in seg_out), 3))
print('hbm layers', len(D['hbm_layers']['v']), [x['name'] for x in D['hbm_layers']['v']][:4], [x['name'] for x in D['hbm_layers']['v']][-4:])

# ---------------------------------------------------------------- HBM DS layer-20 node list (for the animation)
l20 = [[n['node'], round(n['us'], 5), n['cls'], n['domain'] or 'tail'] for n in hp if n['layer'] == 20]
D['hbm_l20'] = V(l20, 'us', 'analytical', MREF + ' path[layer==20] (measured RTL nodes; coll nodes carry the TU vendor budget; tails modelled)')
(BUILD / 'data.json').write_text(json.dumps(D, separators=(',', ':')))
print('hbm l20 nodes', len(l20), round(sum(x[1] for x in l20), 3))
print(collections.Counter(x[3] for x in l20))


def assemble():
    S = R / 'site/chip_explorer/src'
    data = (BUILD / 'data.json').read_text()
    html = (S/'head.html').read_text() + (S/'body.html').read_text() + '\n<script>\nconst DATA = ' + data + ';\n</script>\n<script>\n' + (S/'app.js').read_text() + '\n</script>\n'
    out = R / 'site/chip_explorer/index.html'
    out.write_text(html)
    print(out, len(html))

assemble()
