import importlib.util
from pathlib import Path
s=importlib.util.spec_from_file_location('gate',Path(__file__).resolve().parents[1]/'tools/w13_gpu_calendar_gate.py');g=importlib.util.module_from_spec(s);s.loader.exec_module(g)


def lowering():
    return {'0':{k:True for k in ['ordinary_lowering_complete','issue_RF_calendar_complete','shared_bank_map_complete','fabric_edge_calendar_complete','SFU_lowering_complete']}}


def ins(**kw):
    e=dict(graph_op=0,sm=0,partition=0,opcode='FADD',rf_read_tick=0,issue_tick=8,finish_tick=36,RF_read_bits=2048,RF_write_bits=1024,peak_registers=32,producer_visible_ticks=[0]);e.update(kw);return e


def edge(**kw):
    e=dict(graph_op=0,quadrant=0,lane=0,launch_tick=0,accept_tick=159,consumer_done_tick=160,credit_return_tick=345,service_tick=0,payload_bytes=32,packet_bits=320,direction='read');e.update(kw);return e


def test_valid_candidate_has_no_hardware_or_speed_credit():
    l=lowering();l['0'].update(required_instruction_events=1,required_fabric_events=1,dependencies=[]);j=g.audit([0],[ins()],[edge()],l);assert j['modeled_service_calendar_closed'] and not j['physical_build_ready'] and j['speed_credit']==0


def test_missing_fullprogram_binding_and_SFU_failclosed():
    assert not g.audit([0,1],[ins()],[],lowering())['modeled_service_calendar_closed']
    assert 'unbound_opcode:EXP' in g.audit([0],[ins(opcode='EXP')],[],lowering())['issues']


def test_RF_dependency_writeback_and_DIV_contention():
    assert 'dependency_before_RF_visible' in g.audit([0],[ins(producer_visible_ticks=[4])],[],lowering())['issues']
    assert 'partition_writeback_overbooked' in g.audit([0],[ins(),ins(rf_read_tick=4,issue_tick=12)],[],lowering())['issues']
    events=[ins(opcode='DIV',partition=p,finish_tick=84,active_lanes=1) for p in (0,1)]
    assert 'single_scalar_DIV_overbooked' in g.audit([0],events,[],lowering())['issues']


def test_real_shared_bank_conflicts_and_combined_service_limit():
    j=g.audit([0],[ins(opcode='LOAD',finish_tick=16,shared_read_words=[0,32])],[],lowering())
    assert 'shared_bank_port_overbooked' in j['issues']
    events=[edge(lane=i) for i in range(24)]
    assert 'combined_service_750B_overbooked' in g.audit([0],[ins()],events,lowering())['issues']


def test_credit_may_not_return_before_consumer_done_or_exceed128():
    assert 'fabric_latency_or_consumer_credit_not_priced' in g.audit([0],[ins()],[edge(consumer_done_tick=400)],lowering())['issues']
    edges=[edge(launch_tick=i*3,accept_tick=i*3+159,consumer_done_tick=i*3+160,credit_return_tick=3000+i*3,service_tick=i*3) for i in range(129)]
    assert 'finite_credit_violation' in g.audit([0],[ins()],edges,lowering())['issues']
