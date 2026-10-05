"""Selected S81 Q-boundary requirements; no inferred production input delays."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/rtl/dsrom_recovery_20261004/q_parent_boundary'


def build():
    paths=['rtl/common/ot_meso_fifo.sv','rtl/hdc/ot_hdc_delay.sv',
           'rtl/v41die/ot_v41_spine_pq_w17w10.sv',
           'rtl/v41rom/ot_v41_rom_stage_pg_cdc.sv','tools/dsrom_s81_fulldie.py']
    ports={}
    for name,hold,setup in [('xs_q0',112.19,204.96),('xs_q1',100.90,173.34)]:
        ports[name]=dict(earliest_data_arrival_ns=None,latest_data_arrival_ns=None,
            reference_clock_name=None,source_clock_insertion_min_ns=None,
            source_clock_insertion_max_ns=None,physicalrecord=None,
            current_E1_requirement=dict(min_arrival_ns=round(.360+hold/1000,5),
                max_arrival_ns=round(.727+setup/1000,5),
                declared_vehicle_min_ns=.360,declared_vehicle_max_ns=.727,
                production_constraint=False))
    return dict(schema='opentallas.s81.q-parent-boundary.v1',
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
        source_chain='spine BST final ot_hdc_delay register -> planned region meso FIFO/fanout -> element g_ir r_xs_q0/1',
        binding_status='Parent reservation abstracts exist; no selected routed launch/capture clock and Q-data path record. BST source is real but is not a substitute for FIFO output timing.',
        E1_basis='Noether corrected CTS owner terminal: Q0 FF-112.19/SS+204.96ps; Q1 FF-100.90/SS+173.34ps. Numbers are rounded owner report, not independently extracted raw STA.',
        ports=ports,
        equations=dict(earliest='launch insertion FF_min + clkQ FF_min + logic FF_min + wire FF_min + phase/reference offset',
            latest='launch insertion SS_max + clkQ SS_max + logic SS_max + wire SS_max + phase/reference offset',
            hold='earliest >= capture insertion FF_max + hold25ps + actual receiver hold - capture internal minimum data delay',
            setup='latest <= next capture edge + capture insertion SS_min - setup60ps - actual receiver setup - capture internal maximum data delay'),
        minimum_repair_model=dict(selection='Matched producer/receiver clock construction and real data path first; no speculative delay-chain or new capture cycle selected.',
            required_common_arrival_window_ns=[.47219,.90034],
            hold_deficit_if_and_only_if_vehicle_is_actual_ns=[.11219,.10090],
            hold_deficit_under_actual_parent_ns=None,
            launch_capture_skew_adjustment_ns=None,added_buffer_count=None,
            added_area_um2=None,added_cycles=0,
            candidate_cycle_policy='Retain existing source/FIFO/capture cycles while sizing matched clock paths. Additional cycles need separate actual dependency model if same-edge construction cannot close.',
            wire_or_clock_repair_acceptance='Both earliest and latest corners must pass with unchanged60/25 uncertainty; lowering capture insertion helps hold but consumes setup headroom and must use actual min/max clock paths.',
            route_admitted=False),
        physical_closes=False,production_IO_bound=False)

if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'model.json').write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
