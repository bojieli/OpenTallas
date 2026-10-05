import sys,json,gzip,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_rom_bank5_control_gate import ROOT,OUT,NEW,bank_logic,validate_model


def test_sameedge_source_and_defaultoff_parent_parameter_binding():
    raw=(ROOT/NEW).read_bytes();logic=bank_logic(raw).decode()
    assert 'ROM_BANK5_CONTROL=0' in logic
    assert 'else read_q <= wrom_re;' in logic
    assert 'else if (code_rd_bank[b]) local_sel <= code_sel_q[b];' in logic
    assert 'code_sel_q2[rb] <= code_sel_q[rb]' in logic
    assert '.ROM_BANK5_CONTROL(ROM_BANK5_CONTROL)' in raw.decode()


def test_model_join_keeps_missing_context_and_exact_priced_dimensions():
    m=validate_model();assert m['fixed_candidate']['total_added_buffers']==76
    assert m['fixed_candidate']['new_FFs']==4
    context=json.loads((OUT/'provider_context_r1.json').read_text())
    assert context['actual_reset_owner']['physical_release_phase_ps'] is None
    assert context['actual_registered_producer']['address_clockQ_and_minmax_arrival_ps'] is None
    assert not any(context['contextual_STA_admission_required'].values())


def test_terminal_literal_proof_archive_and_nonvacuous_bank_mutant():
    gate=json.loads((OUT/'literal_r1.json').read_text());manifest=json.loads((OUT/'terminal_manifest_r1.json').read_text())
    assert gate['status']=='PASS_LITERAL_BANK5_SAMEEDGE_AND_FOURSTATE'
    assert gate['steps'][0]['returncode']==0 and gate['steps'][1]['returncode']!=0
    assert 'unknown_selected=7' in gate['steps'][-1]['output_tail']
    for name,pins in manifest['artifacts'].items():
        data=(OUT/'terminal_r1'/name).read_bytes()
        assert hashlib.sha256(data).hexdigest()==pins['sha256']
        assert hashlib.sha256(gzip.decompress(data)).hexdigest()==pins['uncompressed_sha256']
    for path,digest in gate['source_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest
