#!/usr/bin/env python3
"""Small, read-only source/graph accounting. No simulator, synthesis or EDA."""
from pathlib import Path
import collections, gzip, hashlib, json, re, subprocess, sys, types
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ARCH = HERE.parent
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
# Use exactly the committed parser that originally enumerated c<index>.
raw = subprocess.check_output(['git','-C',str(ROOT),'show','4763bee5d:tools/textbook_lint.py'])
mod = types.ModuleType('attn_partition_pinned_lint'); sys.modules[mod.__name__] = mod
exec(compile(raw, '4763bee5d:tools/textbook_lint.py', 'exec'), mod.__dict__)
g, top = mod.flatten(mod.parse_verilog(gzip.open(ARCH/'attn_graph_audit_1019/original_source.v.gz','rt').read()), None)
assert len(g.cells) == 18862
frontiers = json.loads((ARCH/'attn_admission_model_1019/frontiers.json').read_text())
copies = {'cprs4/QN':'ufk_WS', 'cprs6/QN':'ufk_WN', 'cprs11/QN':'ufk_ES', 'cprs13/QN':'ufk_EN'}
def owner(name):
    if '.codec.l_pl[' in name: return 'landed_record_data'
    if '.codec.' in name: return 'landed_expectation_event_or_codec_fault'
    if name.startswith('ahs['): return 'old_context_hold_feedback'
    if '.ctl.at[' in name: return 'held_authority_position'
    if '.u_afr.' in name or name.startswith('ufk_'): return 'continuous_unit_health'
    if '.ctl.ls_' in name or '.ctl.slot_fault' in name: return 'landed_tx_slot_health'
    if '.producer.' in name or '.guard.' in name: return 'descriptor_producer_guard_health'
    if '.u_attn_face.' in name: return 'result_face_service_health'
    if '.boot_count[' in name or name.endswith('__running$_DFFE_PN0P_'): return 'live_root_ready'
    if '__io_fault' in name or '__local_fault' in name: return 'live_root_sticky_health'
    if '.ctl.local_fault' in name: return 'live_controller_sticky_health'
    return 'cut'
out = {}
for stage, data in frontiers.items():
    rows = []
    for pin in data['frontier']:
        if pin in copies:
            name = copies[pin]; master = 'DFFASRHQNx1_ASAP7_75t_R'
        else:
            m = re.fullmatch(r'c(\d+)/\w+', pin); assert m
            master, name, _ = g.cells[int(m[1])]
        rows.append(dict(native_pin=pin, original_instance=name, master=master, ownership=owner(name)))
    out[stage] = dict(rows=rows, counts=dict(collections.Counter(x['ownership'] for x in rows)))
(HERE/'frontier_ownership.json').write_text(json.dumps(out,indent=2)+'\n')
path = json.loads((HERE/'selected_producer_path.json').read_text())
assert path['die_sha256']=='18464a8b31042bea03b3fc5779d42803ab7b05bebbaab733a4d83d4a714c1ea6'
relay_lines = [x for x in path['lines'] if 'qkd_rlys_' in x]
assert len(relay_lines)==22  # 11 existing hops, each split528+20 payload bits.
producer = (HERE/'selected_d2d_producer.sv').read_text()
assert 'parameter integer PR = 1' in producer
assert 'always @(posedge ck) q_rx_payload <= c_rx_payload;' in producer
cases = []
for line in (HERE/'cases_stk.txt').read_text().splitlines():
    m = re.search(r'\+NSTEP=(\d+)',line); n = int(m[1])
    rel = [int(x) for x in re.findall(r'\+REL\d+=(\d+)',line)]
    assert len(rel)==n
    cases.append(dict(case=line.split()[0], attention_admissions=n, relative_run_edges=rel,
                      candidate_added_edges=0, two_stage_fallback_added_work_edges=2*n))
ff = 32*(1+11+1)
model = dict(verdict='MODEL_HOLD_NOT_RTL_OR_TIMING_QUALIFICATION',
    exact_native_source_sha256='ac6af21580867b0e1224c7cf7e6476309d5b036cd2ba558ad5014737fbfeddde',
    selected_producer_die_sha256=path['die_sha256'],
    producer_clock='n_clk_core_c[0]', producer_reset='none on q_rx_payload; preserve unreset flag cohort',
    producer_module='qkd_d2d_static PR=1; q_rx_payload <= c_rx_payload',
    candidate='32 upstream registered partial-zero flags; identical payload-age sideband',
    sideband=dict(bits=32, producer_ff=32, existing_relay_hops=11, relay_ff=352, receiver_landing_ff=32,
        plain_ff=ff, resettable_ff=0, clock_pins=ff, plain_master='DFFHQNx1_ASAP7_75t_R',
        ff_area_floor_um2=round(ff*1.080*.270,8), producer_output_pins=32, receiver_input_pins=32,
        per_hop_bus_bits=32, added_interface_bus_fraction=32/548,
        comb_area=None, buffer_area=None, extra_kept_copies=None, total_area=None,
        clock_capacitance=None, clock_tree_area=None, dynamic_power=None),
    qualification=dict(added_payload_edges=0, added_q_edges=0, added_request_edges=0,
        changed_fault_observation_edges=0, calendar_delta_edges=0,
        measured_tt_setup_ps=-569.32, measured_critical_arrival_ps=1294.07,
        new_native_timing=None, native_source_equivalence=None, four_state_equivalence=None,
        new_pg_contacts=None, new_clock_matching=None, new_all_driver_census=None),
    actual_selected_programmes=cases,
    actual_full_token_admissions=None, actual_production_mu_occupancy=None,
    manifest={x:sha(HERE/x) for x in ('cases_stk.txt','selected_driver.svh','selected_d2d_producer.sv','selected_producer_path.json')},
    pinned_parser_sha256=hashlib.sha256(raw).hexdigest(),
    holds=['actual GEN8 producer/relay identity and lifetime match',
           'sideband bit/cohort equality on every existing relay and reset transition',
           'producer c_rx_payload-to-predicate path depth/load/area and physical face grants',
           'entire receiver immediate observer and all side-cone timing after specialization',
           'full upstream D2D safe storage/contact/native qualification',
           'arbitrary first-use/reset and causal malformed-payload/cohort mutants'])
(HERE/'model.json').write_text(json.dumps(model,indent=2)+'\n')
print(json.dumps(dict(ff=ff,area_floor_um2=model['sideband']['ff_area_floor_um2'],cases=cases,
                     ownership={k:v['counts'] for k,v in out.items()}),indent=2))
