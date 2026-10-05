import importlib.util
import hashlib
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('inline_landing',ROOT/'tools/qwen_stream4_inline_landing.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def test_actual_mapping_not_uniform_twelve_sources():
    row=m.model()
    assert row['physical_cut']['aperture_histogram']=={'4':512,'10':64,'12':960}
    aps=m.tile_apertures()
    assert len(aps)==1536
    assert max(map(len,aps))==12
    assert all(0<=pc<128 and half in (0,1) for a in aps for pc,half in a)
    # Tile0 includes K+V sources; its actual aperture is ten, not twelve padded ports.
    assert aps[0]==[(0,0),(1,0),(2,0),(3,0),(16,0),(17,0),(18,0),(19,0),(32,0),(48,0)]


def test_source_copy_is_verbatim_and_manifest_replays(tmp_path):
    out=tmp_path/'extract';m.extract(out)
    src=(ROOT/m.SERVICE).read_text()
    for p in out.glob('*.svh'):
        assert p.read_text() in src
    for name,h in json.loads((out/'manifest.json').read_text()).items():
        assert hashlib.sha256((out/name).read_bytes()).hexdigest()==h
    assert 'ot_qwen_kv_land_merge #' not in (out/'arbitration.svh').read_text()


def test_pipe_and_macro_retirement_edges_not_service_or_writeback_ack():
    row=m.model();edges=row['acceptance']['edge_chain']
    assert edges['accepted_q0_edge']==0
    assert edges['service_kvw_output_edge']==8
    assert edges['tile_input_capture_edge']==9
    assert edges['macro_masked_write_edge']==10
    assert edges['original_inflight_clear_edge']==11
    assert not row['acceptance']['writeback_drain_is_SRAM_retirement']
    assert not row['acceptance']['physical_provider_ACK_added']
    assert not edges['physical_completion']
    with pytest.raises(ValueError):m.fixed_clock_edges(same_clock=False)
    with pytest.raises(ValueError):m.fixed_clock_edges(fill_lat=10)


def test_existing_state_counted_once_and_no_unpriced_slot_claim():
    row=m.model();st=row['existing_storage'];pr=row['prebuild_price']
    assert st['dense_network_entries']==320
    assert st['dense_network_register_bits']==8*320*(1+11+7+512+512)
    assert st['half_done_bits']==256
    assert st['added_state_bits']==st['removed_state_credit_bits']==0
    assert pr['period_ps']==833 and pr['setup_uncertainty_ps']==60 and pr['hold_uncertainty_ps']==25
    assert pr['SRAM_pins_loads_slot'] is None
    assert not pr['parent_slot_fit'] and not pr['physical_build_admitted']
    assert row['model_registration_owner']=='Maxwell'


def test_arbitration_retains_earlier_valid_quarter_and_partial_v_obligation():
    src=(ROOT/m.SERVICE).read_text()
    cut=m.section(src,'    // ---- arbitration:','    // ---- network pipe')
    assert "seen_q[tl] = seen_q[tl] | qv;" in cut
    assert "if ((seen_q[tl] & qv) == 4'd0)" in cut
    assert "if ((h_got[p] & need) == need) l_pop[p] = 1'b1;" in cut
    assert "h_got[ai] = hdone[ai]" in cut
    assert "p = (rr + pp_i) % NPC;" in cut
