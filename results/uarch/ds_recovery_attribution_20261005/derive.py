#!/usr/bin/env python3
"""Bounded standard-library attribution of existing records; no model/build execution."""
import gzip, hashlib, json, re, subprocess, sys
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PINS = {}
SOURCE = sys.argv[1] if len(sys.argv) > 1 else '80d0e333ed01512d1bcc15fc0da5c1ebfcd92432'
def raw(p):
    b = subprocess.check_output(['git', '-c', 'gc.auto=0', 'show', SOURCE + ':' + p], cwd=ROOT)
    PINS[p] = hashlib.sha256(b).hexdigest()
    return b
def read(p):
    return json.loads(raw(p))
rev = subprocess.check_output(['git', 'rev-parse', SOURCE], cwd=ROOT, text=True).strip()
r = read('results/rtl/dsrom_recovery_20261004/composition.json')
h = read('results/rtl/dshbm_1m_allmeasured_20261004/composition.json')
f = read('results/rtl/dsrom_1m_allmeasured_20261004/field.json')
i = read('results/uarch/dsrom_s81_released_binding_20261004/canonical/inventory.json')
st = read('results/uarch/dsrom_s81_released_binding_20261004/canonical/stage_map.json')
e = read('results/arch/energy_silicon_measured/energy_silicon.json')
raw('results/arch/energy_silicon_measured/README.md')
raw('tools/energy_silicon_measured.py')
raw('tools/uarch_model.py')
raw('tools/dsrom_1m_allmeasured.py')
raw('rtl/v41rom/ot_v41_rom_elem_w10.sv')
pf = read('results/rtl/dsrom_s81_fulldie_20261004/floorplan.json')
hb = read('results/uarch/hbm_accelerator_integration_20261004/model.json')
streams = read('results/rtl/dshbm_1m_allmeasured_20261004/hbm_streams.json')
draft = read('results/rtl/dsrom_recovery_20261004/levers/draft.json')
head = read('results/rtl/dsrom_recovery_20261004/levers/head.json')
sm = read('results/rtl/dshbm_baseline_measured_20261004/sm_real_ops.json')
program = read('results/rtl/dshbm_baseline_measured_20261004/program.json')
read('results/rtl/dsrom_recovery_20261004/levers/router.json')
raw('results/arch/measured_scoreboard/scoreboard.json')
lef = raw('physical/asap7_memory_macros_v2/ot_rom_4096x274_m8/ot_rom_4096x274_m8.lef').decode()
w, ht = map(float, re.search(r'SIZE ([\d.]+) BY ([\d.]+)', lef).groups())
macro_area = w * ht / 1e6
wanted = {(p['layer'], p['die_stage'], m['alias']) for p in f['phases'] for m in p['matrices']}
mapbytes = raw('results/uarch/dsrom_s81_released_binding_20261004/canonical/matrix_map.jsonl.gz')
selected = {}
for line in gzip.decompress(mapbytes).splitlines():
    d = json.loads(line)
    key = (d['layer'], d['stage'], d['alias'])
    if key in wanted:
        if key in selected:
            raise ValueError('Ambiguous matrix key: ' + str(key))
        selected[key] = d
phases = []
for p in f['phases']:
    fmt_pairs = defaultdict(set)
    ms = []
    for m in p['matrices']:
        d = selected[(p['layer'], p['die_stage'], m['alias'])]
        pairs = {v[1] for v in d['plans']}
        fmt_pairs[d['format']].update(pairs)
        # The field record gives actual rank-0 rows/columns, including split rows/K.
        macs = (m['rows'][1]-m['rows'][0]) * (m['cols'][1]-m['cols'][0])
        ms.append(dict(alias=m['alias'], tensor=d['tensor'], rows=m['rows'], cols=m['cols'],
                       format=d['format'], rank0_MACs=macs, assigned_pairs=len(pairs),
                       read_words_max=m['t_read_words_max_s81'],
                       issue_cycles=m['issue_cycles_LAT8_condition_s81']))
    union = set().union(*fmt_pairs.values())
    cap = sum(len(v) * {'fp4':128,'fp8':64,'bf16':32}[k] for k,v in fmt_pairs.items())
    work = sum(m['rank0_MACs'] for m in ms)
    row = dict(phase=p['phase'], layer=p['layer'], node=p['node'], stage=p['die_stage'],
               K=p['K'], matrices=ms, rank0_active_assigned_pairs=len(union),
               rank0_pairs_by_format={k:len(v) for k,v in fmt_pairs.items()},
               pair_ids_rank0=sorted(union),
               fraction_installed_rank_die=len(union)/2417,
               fraction_installed_layer_system_rank0_assignment=len(union)/783108,
               rank0_MACs=work, optimistic_active_MACs_per_cycle=cap,
               active_compute_floor_cycles=work/cap,
               macro_read_floor_cycles=max(m['read_words_max'] for m in ms),
               configured_issue_floor_cycles=max(m['issue_cycles'] for m in ms),
               go_to_last_row_cycles=p['go_to_last_row_cycles'],
               go_to_idle_cycles=p['go_to_idle_cycles'],
               s81_wire_cycles_per_phase=80,
               worst_region_busy_pairs=p['worst_region_detail']['busy_pairs'],
               worst_region_installed_pairs=p['worst_region_detail']['pairs'],
               exact=p['exact'])
    phases.append(row)
(OUT/'rom_phase_capacity.json').write_text(json.dumps(dict(
    schema='opentallas.ds-recovery.phase-capacity.v1', source_revision=rev,
    scope='All 167 existing measured rank-0 field phases, representative layers 0,1,2,3,20,21,24; not all 40 layers newly measured.',
    definition='Active means assigned to this matrix phase, not simultaneous issue/activity on every edge. Pair IDs join actual canonical plans by layer, stage, alias. Installed denominator 783108 includes all 324 layer dies. Multiply rank-0 counts by TP4 only as a symmetric shape projection, not a measured four-rank trace.',
    ceiling_note='FAST1 PP1 BP0: each pair has 2 logical read ports, 4 physical ping-pong ROM4096; FP4/FP8/BF16 conditional ceilings 128/64/32 MACs per edge. Format ceilings are alternatives, not additive. Mixed-format summed ceiling is optimistic where a pair occurs in both sets.',
    phases=phases), separators=(',',':'))+'\n')
hbm_shapes = []
for layer in program['layers']:
    for op in layer['ops']:
        if op.get('unit') != 'SM':
            continue
        ranges = op.get('rows', [])
        counts = [max(0, a[1]-a[0]) for a in ranges]
        assigned = sum(min(32, n) for n in counts)
        cap = assigned * {'fp4':256,'fp8':128,'bf16':64}[op['fmt']]
        hbm_shapes.append(dict(layer=layer['layer'],id=op['id'],tag=op['tag'],fmt=op['fmt'],
          fn=op['fn'],tensor_or_expert_slot=op['w'],K=op['k'],global_n=op['n'],
          per_rank_row_counts=counts,nonempty_rank_SM_row_slots=assigned,
          one_column_shape_projected_MACs_per_cycle_upper=cap,
          claim='ISA rows mapped to32SMs/rank; nonempty row slots, not measured issue trace. K-split/replicated wo_a rows are contributor work, not extra output rows. Expert slot IDs are dynamic selection, not fixed expert tensors.'))
(OUT/'hbm_phase_shapes.json').write_text(json.dumps(dict(schema='opentallas.ds-recovery.hbm-phase-shapes.v1',
    source_revision=rev,scope='Existing TP96 ISA program shape inventory, not a newly composed current batch calendar.',
    measured_SM_cases=sm['cases']['ar'],measured_claim_boundary=sm['claim_boundary'],
    one_column_conditional_MACs_per_cycle={'fp4':256,'fp8':128,'bf16':64},
    installed_model_columns=8,
    caution='Real-operand AR SM cases use cols1 (4/8 blockdot lanes or64 BF16 lanes); eight installed model columns must not be charged as eight active AR columns. Current composed SM service durations can differ from older dump timing; no substitution made.',
    phases=hbm_shapes),separators=(',',':'))+'\n')
sources = {v['node']:v.get('source','') for v in r['base_patches']+r['patches']}
families = defaultdict(float)
for v in r['critical_path']:
    s = sources.get(v['node'],'')
    if s.startswith('ROM field:'): k='field'
    elif s.startswith('SU:'): k='SU'
    elif s.startswith('TP4 collective'): k='TP4_collectives'
    elif s.startswith('stage hop:') or s.startswith('token return:'): k='stage_hops_and_token_return'
    elif s.startswith('head:'): k='head'
    else: k='other'
    families[k] += v['us']
fetch = sum(v['us'] for v in h['path'] if v['node']=='hbm:expert_fetch')
old_rom = e['deepseek_1m']['rom']['silicon']
old_hbm = e['deepseek_1m']['hbm_accel']['silicon']
new_logic_delta = draft['dies_added'] * draft['placement']['dies']['die_mm2']
# Corrected retained-unary delta is reported separately; it may overlap later die pricing.
batch=[]
for B in [1,8,32,128]:
    U=128*(1-(1-6/128)**B)
    batch.append(dict(B=B, conditional_uniform_expected_union_experts=U,
                      expected_union_weight_bytes_per_token_over_one_user=U/(6*B),
                      total_expert_selections_over_expected_union=6*B/U,
                      probability_given_expert_selected=U/128,
                      union_experts_min=6, union_experts_max=min(128,6*B),
                      ideal_routed_weight_bytes_per_token_ratio_bounds=[1/B,min(128,6*B)/(6*B)]))
record = dict(
 schema='opentallas.ds-recovery.attribution.v1', status='BOUNDED_ATTRIBUTION_NOT_ADOPTION_OR_BATCH_VERDICT', source_revision=rev,
 owner='Rawls: attribution only; Maxwell owns composition, alternatives and overall gate',
 comparison=dict(context=1048576,position=1048575,ROM_TP=4,HBM_TP=96,
    ROM_AR_us=r['AR_us'],ROM_AR_tok_s=r['AR_tok_s'],ROM_MTP_tok_s=r['MTP']['MTP_tok_s'],
    HBM_AR_us=h['AR_us'],HBM_AR_tok_s=h['AR_tok_s'],gap_us=r['AR_us']-h['AR_us'],
    ROM_over_HBM_rate=r['AR_tok_s']/h['AR_tok_s'],
    target_clocks_hz={'stream':1200000000,'serial':900000000},
    qualification='Same released model/context/position and golden arithmetic contract; target-clock composed records, not a matched SS/FF full-system acceptance experiment. HBM includes vendor collectives and modelled striping tails. ROM regional field tests do not prove actual full-die admission.',
    HBM_AR_us_by_term=h['AR_by_term'], ROM_critical_path_us_by_source_family=dict(families),
    ROM_critical_path_sum_us=sum(families.values()),
    ROM_extra_S81_hops_us=23*r['info']['hop_us'],ROM_extra_S81_hops_count=23,
    ROM_path_plus_hops_rounding_residual_us=r['AR_us']-sum(families.values())-23*r['info']['hop_us'],
    ROM_rounding_bound_us=len(r['critical_path'])*0.00005+0.0005,
    ROM_extra_hops_authority='tools/dsrom_1m_allmeasured.py: ar=t+EXTRA_HOPS*hop_extra; extra23 hops added outside critical_path list',
    HBM_vendor_budget_us=h['AR']['tu_budget_us'],HBM_modelled_tail_us=h['AR']['modelled_us'],
    important_record_trap='ROM info.head.lm_head_us=73.571 is old metadata; actual recovery head.lm_head critical-path node is 6.9941 us (6.9892 service plus CDC). Attribution uses critical_path, not this stale field.'),
 installed_compute=dict(ROM_layer_dies=324,ROM_layer_pairs=783108,ROM_pairs_per_die=2417,
    ROM_BF_dual_pairs_per_die=519,ROM_physical4096_per_layer_die=9668,
    ROM_logical_word_read_ports_per_pair=2,ROM_physical_banks_per_pair=4,
    ROM_raw_read_bits_per_pair_per_cycle=548,
    ROM_conditional_MACs_per_cycle_per_pair={'fp4':128,'fp8':64,'bf16':32},
    ROM_conditional_layer_system_MACs_per_cycle={'fp4':783108*128,'fp8':783108*64,'bf16':324*519*32},
    HBM_dies=96,HBM_SMs_per_die=32,HBM_total_SMs=3072,HBM_columns_per_SM=8,HBM_measured_AR_columns_per_SM=1,
    HBM_measured_one_column_MACs_per_cycle_per_SM={'fp4':256,'fp8':128,'bf16':64},
    HBM_conditional_MACs_per_cycle_per_SM={'fp4':2048,'fp8':1024,'bf16':512},
    HBM_conditional_MACs_per_cycle_system={'fp4':3072*2048,'fp8':3072*1024,'bf16':3072*512},
    HBM_SM_ingest_bytes_per_cycle=128, HBM_peak_weight_ingest_TB_s_at_1p2GHz=3072*128*1.2e9/1e12,
    HBM_stack_peak_TB_s_system=384.0,
    caveat='Structural conditional ceilings from existing model; not achieved MAC/s. HBM real-operand AR cases use one column; hbm_phase_shapes.json gives nonempty rank/SM row assignments. Exact current composed per-phase issue trace is missing; 3072 SMs and8columns are installed upper bounds. ROM installed capacity cannot be pooled across resident weights/layers. No BF ceiling added to FP ceiling.'),
 weight_fetch=dict(exposed_expert_first_access_us=fetch,
    fraction_HBM_AR=fetch/h['AR_us'],all_explicit_HBM_path_us=h['AR_by_term']['hbm'],
    zero_expert_first_access_fixed_other_terms_AR_us=h['AR_us']-fetch,
    zero_all_explicit_HBM_terms_fixed_other_terms_AR_us=h['AR_us']-h['AR_by_term']['hbm'],
    ROM_gap_over_expert_first_access=(r['AR_us']-h['AR_us'])/fetch,
    qualification='5.2124 us is explicit expert first access, not total weight-read duration. HBM SM path can incorporate weight-ingest pacing/overlap; its weight-only removable part is not separately exposed. 10.757 us includes KV/embedding and is only a fixed-other-terms counterfactual, NOT an upper bound on all weight-service savings.',
    removable_stream_stall_formula='For each dependency/calendar: max(0,T_fetch-T_compute_or_available_overlap); account first access once. Do not subtract gross weight_bytes/bandwidth from a path that overlaps compute.',
    total_exposed_weight_service_saving_us=None),
 silicon=dict(basis='Raw summed die silicon, distinct from cost/packaging/yield. Logic includes on-die controllers and ROM/SRAM; HBM stack bound includes all 8 core DRAM layers plus one base/controller die, each <=121mm2. No extra base-die double charge.',
    old_368_die_ROM_inventory=old_rom, HBM_96_die_inventory=old_hbm,
    old_total_ROM_over_HBM=old_rom['total_mm2']/old_hbm['total_mm2'],
    old_logic_ROM_over_HBM=old_rom['logic_mm2']/old_hbm['logic_mm2'],
    DRAM_stack_area_bound_8hi_mm2=1089,DRAM_stack_area_bound_12hi_mm2=1573,
    switch_area_assumed_mm2=6400,
    recovery_draft_added_logic_dies=draft['dies_added'],recovery_draft_added_logic_mm2=new_logic_delta,
    old_plus_draft_known_inventory_mm2=old_rom['total_mm2']+new_logic_delta,
    old_plus_draft_total_ROM_over_HBM=(old_rom['total_mm2']+new_logic_delta)/old_hbm['total_mm2'],
    current_complete_total_mm2=None,
    unresolved='368-die ledger does not price the recovery draft +52 dies; additional stack/controller requirements, changed head implementation and current retained-unary/context pricing are not jointly inventoried. Old totals cannot label current complete system. A 5090-vs4706 return delta of 2.441445mm2/rank die is 791.02818mm2 across 324 dies, separate from full-die/context ledger; do not double-add without ledger join.',
    accounting_rule='A_total=sum logic dies + sum every HBM core die + every HBM base die + external switch dies; include KV HBM for ROM and weight+KV HBM for HBM accelerator, plus capacity growth with B. Packaging/interposer/substrate cost and yield are separate unknowns.',
    area_slices=dict(ROM4096_macro_body_mm2=macro_area,weight_ROM_macro_bodies_per_layer_die_mm2=9668*macro_area,
      cfg_ROM_storage_footprint_per_layer_die_mm2=pf['area_mm2_by_kind']['cfg'],
      q_BF_mixed_storage_compute_footprints_mm2=pf['area_mm2_by_kind']['q']+pf['area_mm2_by_kind']['bf'],
      return_legacy_4706_node_footprint_mm2=pf['area_mm2_by_kind']['node'],
      network_related_footprints_mm2={k:pf['area_mm2_by_kind'][k] for k in ['node','fifo_blk','phy','link','waypoint','hub_fifo']},
      pure_compute_area_mm2=None,pure_network_area_mm2=None,
      caveat='125.304x62.952um real ROM LEF body. q/BF abstracts combine storage+compute; control/hub/service contain mixed logic/storage/network. These are placed macro footprints within a858mm2 outline, not additive die-area ledger components; never call all839.239mm2 compute. No pure-compute/global routing split qualified.')),
 temporal_nonreuse=dict(layers=40,stages=81,experts_per_layer=128,experts_selected_per_user=6,
    routed_experts_selected_fraction=6/128,
    statement='Single-token dependencies activate successive resident layers/substages and only selected experts. Other resident ROM pairs cannot serve a different tensor merely because idle. HBM SM arithmetic is reused for successive tensors/layers, with weights streamed. This prices area/static occupancy but is not by itself a latency proof.',
    active_phase_capacity_evidence='rom_phase_capacity.json lists exact assigned pair sets, useful work, word-read/issue lower bounds and actual region timing for all167 recorded phases; compare active capacity, not whole-chip installed peak.',
    unresolved_cause='The observed field service times include read/issue, exact chunk recurrence, phase serialization, drain/return, VM and wire. Removing temporal nonreuse would require a priced valid schedule/mapping; neither low installed utilization nor area ratio proves that it is the AR root cause.'),
 batch=dict(status='NO_CURRENT_SATURATED_THROUGHPUT_OR_ENERGY_VERDICT',
    definitions={'aggregate_tokens_s':'B/T_batch_seconds (one next token per user); MTP = total actually accepted tokens/T_step, not B alone',
      'energy_J_per_token':'P_system_W/T_aggregate_tokens_s = integrated batch energy/accepted tokens',
      'equal_area_throughput':'floor(A_budget/A_system(B))*T_aggregate(B), only for feasible independent full replicas; fractional replica product is density, not executable schedule'},
    weight_reuse={'dense_weight_bytes_per_token_ideal':'W_dense/B',
      'MoE_weight_bytes_per_token_ideal':'sum_{e:B_e>0} W_e/B; sum B_e=6B; reuse per active expert = B_e',
      'equal_sized_routed_weight_bounds':'W_e*6/B <= W_union/B <= W_e*min(128,6B)/B (per layer)',
      'uniform_selection_example':'Conditional independent uniform 6-of128 users ONLY: E[U]=128*(1-(1-6/128)^B). Not actual token selection statistics.',
      'examples':batch,
      'limitations':'One-read-per-union assumes actual grouping/retention/storage/controller schedule. No such composed accelerator phase-II schedule is qualified. ROM pipeline overlap across users raises resident activity; it does not automatically give ROM one-read-for-B arithmetic or divide all energy by B.'},
    conditional_bounds={'service':'T_batch >= max(F_batch/C_active, W_union/BW_weight, B*KV_bytes_user/BW_KV, network/calendar/control bottleneck); only price overlap where source calendar allows it',
      'throughput':'T_aggregate <= min(B*C_active/F_batch, B*BW_weight/W_union, BW_KV/KV_bytes_user, actual phase/controller/network capacity)',
      'energy':'E_token = E_compute_user + E_KV_user + e_weight*W_union/B + E_network_user + P_static(B)/T_aggregate + wake/transition energy per accepted token',
      'monotonicity':'With fixed feasible capacity/clock and nested sets, union bytes nondecreasing and bounded; ideal best achievable throughput over B<=Bmax is nondecreasing by retaining smaller-batch fallback. Uniform-model union/B decreases with B. Actual arbitrary selections, schedule throughput and total energy need not be monotone; KV grows linearly and static active power can rise.',
      'static_amortization':'If fixed P_static and measured T increases by factor g, its J/token decreases by 1/g; no guarantee total P stays fixed. HBM reuse also reduces weight energy/token and can shift bottleneck to compute/KV/collectives.'},
    missing_measurement_contracts=[
      'Current accepted-token batch-phase-II/controller schedule at each B: actual expert IDs/B_e/union, retained weights, activation SRAM occupancy, credit limits and golden reduction identity/order.',
      'Per-phase compute/ROM/HBM read traces with valid issue widths, simultaneous active columns, stalls, first access, refresh/bank contention and committed outputs, tied to current shapes/clocks.',
      'KV/index bytes, capacity and per-user context at B; resident weights+KV fit, required stacks/base/controllers, die mapping and external switch count under same total-area budget.',
      'Current whole-system active/idle/wake power, controller/PHY/HBM/switch power and integration time divided by actual accepted tokens. TT pair power is not whole-die EM/power qualification.',
      'Current SS/FF setup/hold in context at unchanged uncertainty, producer/consumer acceptance, and complete source-pinned silicon inventory including draft/head/unary changes.'
    ],
    saturated_tokens_s=None,saturated_J_per_token=None,
    stale_energy_record=dict(source_scoreboard_commit=e['inputs']['scoreboard_commit'],
      old_ROM_AR_tok_s=e['deepseek_1m']['rom']['rates']['ar']['value'],old_ROM_MTP_tok_s=e['deepseek_1m']['rom']['rates']['mtp']['value'],
      old_Qwen_ROM_AR_tok_s=2274.2,current_Qwen_rate='STREAM4 authority; outside this DS sidecar, do not reuse2274.2',
      verdict='OLD rates invalidate current comparison. iso() multiplies replicas by batch-one rate only. All historical saturation rows and transferred power models remain historical; no regenerated energy verdict here. Noether notified via codex_notes.')),
 decision_support='Material evidence: installed peak/total area is not active-phase capacity; expert first-access saving is only5.2124us on this HBM path, while ROM field/SU and staged delivery dominate its serial critical path. Use phase read/issue/service attribution for Maxwell alternatives; withhold saturated equal-area/energy verdict until listed contracts exist.',
 input_sha256=PINS)
(OUT/'attribution.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(dict(phases=len(phases),matched_matrices=len(selected),rom_path_us=dict(families),representative_phases=[{k:p[k] for k in ['phase','rank0_active_assigned_pairs','rank0_MACs','optimistic_active_MACs_per_cycle','active_compute_floor_cycles','macro_read_floor_cycles','configured_issue_floor_cycles','go_to_last_row_cycles']} for p in phases[:3]],silicon_delta=new_logic_delta)))
