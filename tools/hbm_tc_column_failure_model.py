#!/usr/bin/env python3
"""Read-only, source-pinned TC-column failure prerequisite. No hardware admission.

Run --output PATH to emit evidence, or --check PATH to reproduce it byte-for-byte.
Only RTL, reports, abstracts, configuration metadata and instruction graphs are read.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import qwen_hbm_complete_program as Q

ROOT = Path(__file__).resolve().parents[1]
BASE = 'e72abea5ae169d3167dddc89543013f0e6bb3a7a'
SOURCE = '000ba0898f5120a66d5905ccff333ebbbe28394d'
TERM = 'results/physical_abi3/asap7/gpu/w13_tc_col_terminal_20261001T2112Z'
RUN = 'results/physical_abi3/asap7/gpu/w13_tc_col_signoff_failure_20261001T2110Z/run'


def model():
    pins = {}
    def raw(path):
        b = (ROOT/path).read_bytes()
        pinned = subprocess.check_output(['git', 'show', BASE+':'+path], cwd=ROOT)
        if b != pinned:
            raise ValueError('base pin changed: '+path)
        pins[path] = hashlib.sha256(b).hexdigest()
        return b
    def record(path):
        return json.loads(raw(path))
    receipt = record(TERM+'/receipt.json')
    assert receipt['source_git'] == SOURCE and receipt['engineering_verdict'] == 'FAIL'
    main_source_differences = []
    for path, sha in receipt['files'].items():
        assert hashlib.sha256(raw(TERM+'/'+path)).hexdigest() == sha, path
        if path.startswith('source/'):
            original = path[len('source/'):]
            assert raw(TERM+'/'+path) == subprocess.check_output(['git', 'show', SOURCE+':'+original], cwd=ROOT)
            if raw(original) != raw(TERM+'/'+path):
                main_source_differences.append(original)
    ss = raw(RUN+'/corner_ss_max.rpt').decode()
    ff = raw(RUN+'/corner_ff_min.rpt').decode()
    assert 'v_q$_DFF_PN0_' in ss and 'g_lane[29].u_mul.s1_e[10]' in ss
    assert 'u_cc.g_r.r[43]' in ff and 'u.y[10]' in ff
    for p in ['constraint.sdc', 'corner_ss.tcl', 'corner_ff.tcl', 'reports/asap7/chip_ot_gpu_tc_col/base/5_route_drc.rpt']:
        raw(RUN+'/'+p)
    metrics = record(RUN+'/logs/asap7/chip_ot_gpu_tc_col/base/6_report.json')
    block = record(TERM+'/records/results/physical_abi3/asap7/chip/blocks/ot_gpu_tc_col.json')
    for p in ['tools/uarch_model.py', 'rtl/gpu/ot_gpu_sm_q.sv', 'rtl/gpu/ot_gpu_sm_v.sv',
              'tools/qwen_hbm_complete_program.py', 'compiler/models/qwen3-8b/config.json',
              'compiler/models/qwen3-8b/checkpoint_source.json', 'tools/deepseek_hbm_complete_program.py',
              'tools/deepseek_hbm_complete_calendar.py', 'tools/hbm_gpu_floorplan.py', 'tools/qwen_o4_floorplan.py',
              'results/physical_abi3/asap7/chip/budgets/gpu_sm_qwen.json',
              'results/physical_abi3/asap7/chip/budgets/gpu_sm_v41.json']:
        raw(p)
    admission = record('results/physical_abi3/asap7/gpu/w13_fullprogram_calendar_admission_20261001/admission.json')
    ds = record('results/rtl/w19_hbm_tp96_program_oreduce.json')
    raw('results/rtl/deepseek_hbm_complete_20261001/whole-program-calendar-r2.json')
    graph = Q.compile_program()  # reads configuration and checkpoint lock metadata, never tensor payloads
    qops = graph['instructions'] if 'instructions' in graph else graph['ops']
    qmatrix = [o for o in qops if o['opcode'] in ('MATRIX','SCORES','PV')]
    dmatrix = [(l['layer'], o) for l in ds['layers'] for o in l['ops'] if o['kind']=='mv' and o['fmt']=='bf16']
    ff_um2 = metrics['finish__design__instance__area__class:sequential_cell']/metrics['finish__design__instance__count__class:sequential_cell']
    configs = {}
    for name, lanes, cols in [('qwen',32,16),('deepseek_v41',16,8)]:
        reps = 4*cols
        extra = 40*lanes + 20  # two 18-bit dec bundles + sign/zero/nonfinite/valid; tag16/end/start/valid delay
        delta_area = extra*ff_um2
        configs[name] = {
            'lanes':lanes, 'IL':8, 'ALAT':7, 'tree_levels':int(math.log2(lanes)),
            'MACs_per_cycle_per_column':lanes, 'MACs_per_cycle_per_SM':lanes*reps,
            'tree_adders_per_column':lanes-1, 'circulating_adders_per_column':lanes,
            'control_loads_per_column':{'v_ingress_flops':lanes+1,'v_ingress_first_last_AND_gates':2,'bubble_gate_select_bits':16*lanes,'restart_mux_bits':32*lanes,'tree_valid_adder_ports_by_level':[lanes//(2**(i+1)) for i in range(int(math.log2(lanes)))],'fault_lane_reduce_inputs':lanes,'fault_tree_reduce_inputs':lanes-1},
            'columns_per_SM':reps, 'SMs_per_candidate_die':32, 'columns_per_candidate_die':32*reps,
            'ports_bytes_per_cycle':{'w_BF16':2*lanes,'x_BF16':2*lanes,'y_FP32':4,'tag_in':2,'tag_out':2,'shared_memory':0,'RF':0},
            'boundary_bits_per_cycle':{'input_payload_control':32*lanes+19,'output_payload_control':50,'clock_reset_pins':2,
                'new_lane_predecode_cut':40*lanes,'tree_leaves':32*lanes},
            'intensity_MACs_per_operand_byte':0.25,
            'parent_weight_read_bytes_per_cycle':128,
            'parent_x_read_bytes_per_cycle_TC_only':2*lanes*reps,
            'parent_weight_reuse_columns':cols,
            'old_column_cycles':1+5+7+7*int(math.log2(lanes))+1,
            'proposed_column_cycles':1+6+7+7*int(math.log2(lanes))+1,
            'delta_cycles':1,'delta_ps_per_exposed_drain':833,'II_cycles':1,
            'added_register_bits_per_column':extra,'added_register_bits_per_SM':extra*reps,
            'area_proxy_added_um2_per_column':delta_area,'area_proxy_added_um2_per_SM':delta_area*reps,
            'area_proxy_added_mm2_per_die':delta_area*reps*32/1e6,
            'Qwen_same_slot_FF_only_utilization_proxy':(37566.1+delta_area)/46586 if name=='qwen' else None,
            'area_basis':'Measured failed 32-lane column average sequential-cell area; incremental FF-only proxy, excludes decode replication/clock/hold repair/routing. No TC16 transfer of fit.',
            'routing':{'tracks_input_one_wire_per_bit':32*lanes+19,'tracks_output':50,
                'new_internal_cut_tracks_if_full_width_crossing':40*lanes,
                'capacity_assumption':'Reuse parent M5/M7/M9 vertical and M6/M8 horizontal, 50% signal share. Dedicated channel width inferred below; no layer admission.',
                'vertical_tracks_per_um':0.5*(1000/48+1000/64+1000/80),
                'horizontal_tracks_per_um':0.5*(1000/64+1000/80),
                'required_vertical_channel_um_input':(32*lanes+19)/(0.5*(1000/48+1000/64+1000/80)),
                'required_horizontal_channel_um_cut':40*lanes/(0.5*(1000/64+1000/80)),
                'actual_local_channel_capacity':None,'hub_layer_check':'REQUIRED; existing external wires unchanged, local cut must fit actual placement'},
            'floorplan_slot_fit':'UNQUALIFIED; Qwen old 220x220 um slot; TC16 own abstract required; parent packing must include clock/hold/routing overhead',
        }
    qevents = [{'op_id':o['id'],'opcode':o['opcode'],'participants':o['participants'],'delta_stream_cycles':1} for o in qmatrix]
    devents = [{'layer':layer,'op_id':o['id'],'fn':o['fn'],'weight':o['w'],'active_ranks':[i for i,(a,b) in enumerate(o['rows']) if b>a],'delta_stream_cycles':1} for layer,o in dmatrix]
    return {
        'schema':'opentallas.hbm-tc-column-failure-prerequisite.v1','model_tool_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'base_git':BASE,'failed_source_git':SOURCE,
        'status':'MODEL_EVIDENCE_ONLY_BUILD_ADMISSION_CLOSED', 'source_sha256':pins,
        'main_source_differences':{'paths':main_source_differences,'failed_multiplier':'ot_v41_bmul2, split 8x4 partial products, latency5','main_multiplier':'ot_hdc_bmul, single 8x8 stage','failed_ring':'combinational first-select fl[5], ALAT7 + FB1 delay = IL8','main_ring':'acc_q first-select fl[4], ALAT7 + acc register = IL8','transfer':'No qualification transfer between failed source and main; model successor is based on archived failed source only.'},
        'retained_model_search':{'result':'No complete failure-cone successor model found in base tools/results/uarch or retained owner worktree tools/results/uarch.',
            'owner_worktree':'/home/ubuntu/w13-physical-followup-20261001','existing_reused':['terminal owner receipt and 15 source files','parent SS/FF/terminal intake','W13 fullprogram calendar admission','existing Qwen graph compiler','DeepSeek TP96 compiled graph'],
            'not_a_microarchitecture_model':'tools/w13_chain_successor.py is a physical-job supervisor; not invoked'},
        'failure_unchanged':{'engineering_verdict':'FAIL','SS_setup_wns_ps':receipt['ss_setup_wns_ps'],'FF_hold_wns_ps':receipt['ff_hold_wns_ps'],
            'DRC':0,'period_ps':833,'setup_uncertainty_ps':60,'hold_uncertainty_ps':25,
            'complete_LEF_ETMs':True,'output_over_budget':block['budget_check']['over_budget'],
            'ov_budget_excess_ps':24.3,'fault_budget_excess_ps':64.7,
            'SS_setup_violation_count':metrics['finish__timing__drv__setup_violation_count'],
            'cell_area_um2':metrics['finish__design__instance__area'],'core_area_um2':46586,'die_area_um2':48400},
        'actual_path_model':{
            'SS':{'start':'v_q$_DFF_PN0_','end':'g_lane[29].u_mul.s1_e[10]$_DFF_P_',
                'clk_to_q_ps':130.2,'first_five_distribution_buffers_ps':263.8,
                'remaining_decode_add_and_repair_ps':448.7,'launch_to_data_ps':842.7,
                'available_launch_to_required_ps':740.0,
                'decode':'wg=v_ql[l]?w_q:0 -> BF16 dec exponent/nonzero/subnormal priority (7 bits) -> signed 10+10 to 11-bit exponent sum -> s1_e',
                'physical_fanout_sink_count':None,'fanout_limit':32,
                'fanout_evidence_limit':'Report has capacitance/slew and buffer chain, no complete netlist sink inventory. Shared v_q mapped path implies RTL per-lane v copies do not isolate this cone; synthesis merging is an inference, not proven sink count.'},
            'RTL_control':{'v_pin_register_loads':33,'v_ql_gate_bits':512,'v_q_multiplier_valid_ports':32,'v_q_delay_ports':1,
                'first_fanout_acc_mux_select_bits':1024,'last_delay_depth':12,'tree_valid_ports_by_level':[16,8,4,2,1],
                'tree_fault_reduce_inputs':31,'lane_fault_reduce_inputs':32,'tree_tag_delay_register_bits':560,
                'multiplexers':'32x16 bubble gate bits +32x32 restart mux bits; no lane data demux; tree fixed pairwise, no all-to-all crossbar',
                'reset_fanout':'All valid/resettable arithmetic and cut bundles; measured 45383 sequential cells is not an exact reset-sink count'},
            'FF':{'start':'u_tree.g_lv[1].g_add[5].u_add.g_w11.u.u_cc.g_r.r[43]',
                'end':'u_tree.g_lv[1].g_add[5].u_add.g_w11.u.y[10]',
                'source_bit':'WC=71; r[43] is bypass_code[10] (bundle bits 33..64)',
                'clk_to_q_ps':42.5,'OAI22_ps':14.3,'last_net_ps':2.3,'launch_clock_ps':237.4,'capture_clock_ps':262.6,
                'CRPR_ps':-2.8,'library_hold_ps':12.5,'minimum_delay_required_ps_rounded':59.9,
                'qualification':'Independent short bypass-code output path. Extra multiplier stage does not repair it; no FF closure credit.'}},
        'successor':{'kind':'smallest conservative one-cut proposal, opt-in off by default; no RTL written',
            'cut':'Insert one lane-local 40-bit predecode register after bubble-gated BF16 dec(a), dec(b), sign, zero, nonfinite, valid; archived ot_v41_bmul2 s1 exponent sum/mantissa latch becomes next stage; retain its split 8x4 partial products. All later arithmetic/rounding/reduction unchanged.',
            'why_one_cut':'Zero-cut buffered-valid retry has no proven gain and retains decode+exponent-add cone. One cut separates decode from addition without altering IL/ALAT or golden order; smallest conservative stage count, not an area-optimality proof.',
            'fanout_contract':'Input v still drives L+1 boundary registers; registered lane-valid controls 16 bubble bits and one local valid port. Equal copies may merge: successor must prove preserved physical locality, otherwise reject. Proposed local first copies L for 32-bit acc mux each; adds L-1 register bits beyond area proxy if needed.',
            'alignment':{'mul_latency':6,'first_acc_reset_tap':'archived combinational acc_in: fl[5] -> fl[6]','adder_valid_tap':'vl[5] -> vl[6]',
                'last_tag_delay_LL':'12 -> 13','tree_ALAT':7,'ring_IL':8,'feedback_FB':1,
                'fault':'Delay/match status with added stage; preserve sticky fault and invalid/bubble behavior'},
            'SS_budget':'Neither cut estimated delay nor all other paths qualified. Each must fit 833ps minus 60ps plus actual skew/setup; no fmax prediction.',
            'FF_and_output_gate':'Hold on all adders including bypass_code, and ov/fault 450ps budgets remain explicit gates. This model authorizes no hold tuning or boundary rebudgeting.'},
        'configurations':configs,
        'calendar_composition':{'qwen':{'events':qevents,'graph_operations':len(qops),'affected_rank_ops':len(qevents),
            'serialized_rank0_delta_cycles_upper_proxy':sum(0 in e['participants'] for e in qevents),
            'serialized_rank0_delta_ns_upper_proxy':sum(0 in e['participants'] for e in qevents)*0.833},
            'deepseek_v41':{'events':devents,'BF16_matrix_ops':len(devents),
                'serialized_rank0_delta_cycles_upper_proxy':sum(0 in e['active_ranks'] for e in devents),
                'serialized_rank0_delta_ns_upper_proxy':sum(0 in e['active_ranks'] for e in devents)*0.833,
                'nested_BF16_attention_and_compressor_dots':'Must additionally bind source local recipes to TC or qualified arithmetic; no zero-cost assumption'},
            'event_rule':'For every actual TC-backed final issue t, result/otag/ov earliest t+old_depth+1; shared/RF commit and all consumers/barriers follow actual write-visible. Keep service issue II=1 and shift slot identity with product. Parallel ranks/columns do not multiply token delta; recompute dependency max and finite port conflicts.',
            'parent_SM_rule':'Qwen four subparts x16 cols move together. DeepSeek four x8 BF16 cols move +1; block-dot unchanged: carry separate BF16/FP4/FP8 drain and fault epochs into comb/stack. No increase to common format latency without pricing it.',
            'prior_calendar_closed':[r['modeled_service_calendar_closed'] for r in admission['rows']],
            'complete_token_delta_ns':None,'per_user_rate_gain_percent':None,
            'limitations':'Serialized per-op sums are exposure proxies, not full-program latency. Missing finite controller/CDC/collective/SFU/local-dot mapping prevents token admission. No >=1% gain claim.'},
        'remaining_gates_in_order':['Bind all successor TC event delays and local nested dots in both complete-program calendars, parent SM drains, area and real channel capacities; compose token latency in owner unified model before build.',
            'Future separately authorized opt-in RTL exactness: special/subnormal/zero/nonfinite values, bubbles, first/last, tag wrap, IL slot recurrence, golden K and tree order; measure latency/II.',
            'Future separately authorized contextual SS setup and FF hold at unchanged 833/60/25ps; full violating-path inventory, preserved lane control locality, DRC0 and complete source-matched LEF/ETMs, ov/fault I/O budgets.',
            'Qualify complete SM plus both finite whole-program calendars before hardware/rate/power admission; rejected failed column never reused as qualified macro.'],
        'no_admission':{'RTL_edits':0,'new_builds':0,'PnR_jobs':0,'SM_dispatch':False,'retry_tuning':False,
            'constraints_changed':False,'checkpoint_payload_reads':0,'live_job_changes':0,'AGIdock_access':0,
            'hardware_admission':False,'full_program_qualification':False,'power_fit_credit':False}
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    g=parser.add_mutually_exclusive_group(required=True)
    g.add_argument('--output',type=Path);g.add_argument('--check',type=Path)
    a=parser.parse_args();data=json.dumps(model(),indent=2,sort_keys=True)+'\n'
    if a.check:
        if a.check.read_text()!=data:raise SystemExit('FAIL: evidence differs')
        print('PASS: source pins, immutable FAIL, structural accounting and calendar delta reproduce')
    else:
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(data)
        print('Wrote model evidence; build and hardware admission remain closed')

if __name__=='__main__':main()
