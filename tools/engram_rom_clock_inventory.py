"""Additive exact state/hold inventory for Confucius's typed power join."""
import hashlib
import json
from pathlib import Path

ROOT=Path('results/quality/w16_engram_rom_constructive_home_20261001')
raw=(ROOT/'final/candidate.json').read_bytes()
d=json.loads(raw)
v=d['variants']['planning_75Mbit']
tree=v['base_tree_FF_bits_per_home']+v['extra_wire_FF_bits_per_home']
rows=[]
for h in d['homes']:
    capture=h['actual_macros']*298
    storage=tree+capture+4864+64
    # Every state bit needs explicit held-state behavior under a stalled lease.
    # Plain flop with feedback MUX is a constructive choice; NOT free CE/ICG.
    hold_mux=storage
    selected_mux=v['response_mux2_bit_equivalents_per_home']
    demux=v['request_demux_gate_bit_equivalents_per_home']
    rows.append(dict(home_id=h['home_id'],actual_macros=h['actual_macros'],
        tree_wire_and_node_control_FF_bits=tree,macro_and_tag_capture_FF_bits=capture,
        double_packet_FIFO_FF_bits=4864,root_control_FF_bits=64,
        total_storage_FF_bits=storage,held_state_feedback_MUX2_bits=hold_mux,
        selected_response_MUX2_bits=selected_mux,request_demux_AND2_bits=demux,
        feedback_and_select_NAND2_if_four_per_MUX2=4*(hold_mux+selected_mux),
        request_demux_NAND2_if_two_per_AND2=2*demux,
        all_storage_clock_Hz=1200000000,all_macro_clock_Hz_without_qualified_stop=1200000000,
        clock_cell_type='Plain DFFHQNx1 as model0.2916um2 assumption; exact typed library area/power and any reset lowering owned by Confucius. Do not mix ASRHQN area with HQN characterization.',
        physical_clock_enable=False,idle_clock_credit=False,
        valid_active_macro_reads_per_layer=8,active_home_count_per_layer=24,
        payload_capture_beats_per_active_home=8,
        macro_capture_rate='Every macro capture FF clocked each fast cycle until a qualified stop/isolation provider exists; only selected macro data carries valid rows.',
        exact_clock_buffer_topology=None,clock_route_length_um=None,
        root_to_PHY_additional_stage_state=None,CRC_framing_arbitration_state=None))
out=dict(schema='opentallas.engram.clock-hold-inventory.v1',
    candidate_sha256=hashlib.sha256(raw).hexdigest(),candidate_path=str(ROOT/'final/candidate.json'),
    generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),homes=rows,
    aggregate_FF_bits=sum(r['total_storage_FF_bits'] for r in rows),
    aggregate_feedback_MUX2_bits=sum(r['held_state_feedback_MUX2_bits'] for r in rows),
    aggregate_response_MUX2_bits=sum(r['selected_response_MUX2_bits'] for r in rows),
    preliminary_area_screen_limit='329mm2 initial screen excludes held-state feedback mux, actual CTS/typed reset provider, endpoint PHY pipeline and PHY. It is NOT an accepted home budget.',
    preliminary_response_packet_limit='304B is proposed metadata packet, not actual frame/CRC/shared-port contract; serialize on actual link only after that binding.',
    preliminary_point_limit='Recursive-grid coordinates are complete constructive assignments and hashed, not legal fixed-cell floorplans or pin escape certificates.',
    power_authority='Confucius typed source budget -> Ram whole-placement and calendar join',
    power_W=None,composed_admission=False,L1_generated_source=None,checkpoint_reads=0,RTL_or_PnR_runs=False)
target=ROOT/'clock_hold_inventory.json'
assert not target.exists()
target.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(sha256=hashlib.sha256(target.read_bytes()).hexdigest(),aggregate_FF_bits=out['aggregate_FF_bits'],max_home_FF=max(r['total_storage_FF_bits'] for r in rows))))
