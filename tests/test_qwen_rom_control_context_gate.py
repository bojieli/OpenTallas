import sys,json,gzip,hashlib
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_rom_control_context_gate import ROOT,OUT,NEW,context_logic
from qwen_rom_reset_release_price_inputs import proposal


def test_explicit_bank_width_before_primitive_and_real_macro_address_binding():
    raw=(ROOT/NEW).read_bytes();s=context_logic(raw).decode()
    assert s.index('wire [CODE_BANKS-1:0] code_rd_bank')<s.index('.bank_read_n(~code_rd_bank)')
    assert 'ROM_CONTROL_DISTRIBUTION=0' in s
    bad=raw.replace(b'    wire [CODE_BANKS-1:0] code_rd_bank; // Explicit before primitive-port expression.\n',b'')
    with pytest.raises(ValueError):context_logic(bad)
    full=raw.decode()
    assert 'rom_distributed_addr[12*(p*5+b) +: 12]' in full
    assert '.MEM_EXTRA(MEM_EXTRA)' in full and '.KV_PREP(KV_PREP)' in full


def test_materialized76_real_buffers_survive_library_elaboration_with_finite_leaf_loads():
    d=json.loads((OUT/'distribution_r1.json').read_text())
    assert d['status']=='PASS_EXACT76BUF_SOURCE_AND_OWNERSHIP'
    assert sum(d['buffer_counts'].values())==76 and len(d['cell_topology'])==76
    for name,c in d['cell_topology'].items():
        assert c['type']=='BUFx4_ASAP7_75t_R'
        assert len(c['cell_input_sinks'])<=6 and c['output_sink_count']<=8
    assert not d['connected_to_actual_tile'] # component result retains its original scope


def test_integrated_source_terminal_induction_fourstate_and_address_mutant():
    g=json.loads((OUT/'integrated_literal_r2.json').read_text())
    assert g['status']=='PASS_INTEGRATED_BANK5_76BUF_LITERAL_AND_FOURSTATE'
    assert g['steps'][0]['returncode']==0 and g['steps'][1]['returncode']!=0
    assert not g['contextual_STA_admitted'] and not g['adoption']
    manifest=json.loads((OUT/'integrated_terminal_r2_manifest.json').read_text())
    for name,pin in manifest['artifacts'].items():
        raw=(OUT/'integrated_terminal_r2'/name).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==pin['sha256']
        assert hashlib.sha256(gzip.decompress(raw)).hexdigest()==pin['uncompressed_sha256']
    assert not gzip.decompress((OUT/'integrated_terminal_r2/fourstate_build.log.gz').read_bytes())
    negative=gzip.decompress((OUT/'integrated_terminal_r2/wrong_address_owner.log.gz').read_bytes()).decode()
    assert 'model found for base case: FAIL!' in negative
    for path,pin in g['source_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin


def test_root_producer_price_inputs_are_real_cell_costs_not_false_arrival_admission():
    r=proposal()
    for corner in ['ss','ff']:
        c=r['cell_liberty'][corner]
        assert r['actual_library_cell_area_um2']==pytest.approx(2*c['DFFASRHQNx1_ASAP7_75t_R']['area_um2']+2*c['INVx1_ASAP7_75t_R']['area_um2'])
        assert c['DFFASRHQNx1_ASAP7_75t_R']['nominal_pin_capacitance_fF']['CLK']>0
    assert r['startup_release_cycles']==2 and r['steady_per_token_added_cycles']==0
    assert all(value is None for value in r['unknown_model_context'].values())
    assert not r['Root_RTL_implemented'] and not r['new_mapping_admitted']
