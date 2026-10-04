import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import rom_combined_source_pricing as p


def test_source_baseline_fifo_geometry_and_complete_state():
    d=p.build()['Qwen_baseline']
    assert (d['request_FIFO_replicas'],d['response_FIFO_replicas'])==(4,128)
    assert (d['request_depth'],d['response_depth'],d['coded_entry_bits'])==(16,8,360)
    assert d['payload_state_bits']==391680
    assert d['pointer_and_sync_bits']==4256
    assert d['reset_online_flags_fault_room_state_bits']==2110
    assert d['total_state_bits']==398046
    assert d['TP4_state_bits']==1592184
    assert d['FF50_reservation_mm2']==pytest.approx(.30178255536)
    assert d['NEAR_HBM']==0 and d['REAL_MEM']==1
    assert d['SECDED64_encoders']==660 and d['SECDED64_decoders']==660
    assert d['near_optional_added_area_or_latency_credit']==0


def test_tag_and_all_PC_bandwidth_not_one_serial_return():
    d=p.build()['Qwen_baseline']
    assert d['tag_bits']==13
    assert d['request_live_record_bits']==299
    assert d['response_live_record_bits']==274
    assert d['response_bytes_per_stack_per_hclk']==1024
    assert d['response_signal_bits_per_stack_including_valid_ready']==8832
    assert not d['FIFO_enqueue_is_write_completion']
    assert d['return_ACK_is_actual_service_acceptance']
    assert not d['reverse_free_space_same_edge_reuse']
    assert d['token_price_us'] is None and d['actual_slot_fit'] is False


@pytest.mark.parametrize('phase',[0,1,250,500,999])
def test_actual_empty_flag_and_receiving_edge_included(phase):
    accepted=p.crossing_accept_ps(0,1000,phase)
    assert 3000<accepted<=4000
    # A two-sync-only quotation would allow consumption before empty changes.
    assert accepted==((phase or 1000)+3000)


def test_source_phase_price_does_not_count_parallel_packets_or_credit_ACK():
    # Explicit one dependent transaction and explicit previous CDC charge.
    d=p.price_serial_crossings(100,1,833.3333333333,1024,already_charged_cdc_us=0)
    assert d['transport_lower_us']==pytest.approx(.005572)
    assert d['transport_upper_us']==pytest.approx(.007429333333333)
    assert d['combined_empty_FIFO_lower_us']==pytest.approx(100.005572)
    assert d['queue_ready_refresh_decoder_route_extra_us'] is None
    assert d['headline_rate'] is None and not d['measured']
    replaced=p.price_serial_crossings(100,1,1000,1000,already_charged_cdc_us=.006)
    assert replaced['combined_empty_FIFO_lower_us']==100
    with pytest.raises(ValueError):p.price_serial_crossings(100,1,1000,1000,already_charged_cdc_us=None)


def test_source_tampering_refused(tmp_path):
    src=ROOT/p.INPUTS
    dst=tmp_path/p.INPUTS
    dst.mkdir(parents=True)
    for f in src.iterdir():(dst/f.name).write_bytes(f.read_bytes())
    f=dst/'ot_qwen_combined_hbm_cdc.sv'
    f.write_text(f.read_text().replace('RSP_DEPTH=8','RSP_DEPTH=1'))
    with pytest.raises(ValueError,match='source changed'):p.build(tmp_path)


def test_unified_replay_preserves_selected_S81_debit(tmp_path):
    out=tmp_path/'combined.json'
    subprocess.run(['python3',str(ROOT/'tools/uarch_model.py'),'--rom-composed-source','--out',str(out)],check=True,stdout=subprocess.DEVNULL)
    expected=json.dumps(p.build(),indent=2,sort_keys=True)+'\n'
    assert out.read_text()==expected==(ROOT/p.OUT).read_text()
    d=json.loads(expected)
    assert d['selected_DS']['selected_return']['nodes']==5090
    assert d['selected_DS']['area']['prune_only_debit_vs_contracted_mm2']==pytest.approx(2.44144502784)
    assert d['selected_DS']['scenarios'][0]['conditional_AR_tokens_s']==pytest.approx(2466.176815147217)
