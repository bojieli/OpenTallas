import json
import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import dsrom_owner_cfg_interface_export as E
import dsrom_full_owner_compiler as C


def test_config_depth_boundaries():
    for p,w,logical,slice_,row in [(0,0,0,0,0),(163,20,4095,0,4095),(163,21,4096,1,0),(1023,24,25599,6,1023)]:
        a=E.config_address(p,w)
        assert (a['logical_address'],a['macro_depth_slice'],a['macro_address'])==(logical,slice_,row)
        assert a['ECC_layout_proposal_only'] and a['logical_address_bits']==15


@pytest.mark.parametrize('p,w',[(-1,0),(1024,0),(0,-1),(0,25)])
def test_bad_config_coordinates(p,w):
    with pytest.raises(ValueError):E.config_address(p,w)


def test_key_mode_and_overflow():
    assert E.key_word({'key':4096,'format':'fp4'})==0x80001000
    assert E.key_word({'key':4096,'format':'bf16'})==0xc0001000
    for key in (-1,1<<30):
        with pytest.raises(ValueError):E.key_word({'key':key,'format':'fp4'})


def test_cfg_active_inactive_and_row1_repair():
    m={'format':'fp4','segments':[[0,256]],'rows':1,'plans':[[0,0,0,1,128,0,36]]}
    assert E.config_word(m,0,8)&1
    assert E.config_word(m,0,17)==0x8000
    assert E.config_word(m,1,8)==0
    assert E.config_word(None,4095,24)==0
    for pair,word in [(4096,0),(-1,0),(0,25)]:
        with pytest.raises(ValueError):E.config_word(m,pair,word)


def test_sidecar_address_and_bad_provider():
    p={'kind':'ECC_FP4_SIDECAR','bits':16384*256*2,'pairs':[3,7],'stage':2}
    assert E.sidecar_address(p,0)['pair']==3
    a=E.sidecar_address(p,p['bits']-1)
    assert (a['pair'],a['mb'],a['parity'],a['physical_row'],a['data_bit'])==(7,1,1,4095,255)
    assert not a['decoder_or_port_implemented']
    for bit in (-1,p['bits']):
        with pytest.raises(ValueError):E.sidecar_address(p,bit)
    with pytest.raises(ValueError):E.sidecar_address({**p,'kind':'HE'},0)


def test_loader_has_no_invented_service_completion():
    xs=E.loader_journal(1023,4095)
    assert len(xs)==25 and [x['word'] for x in xs]==list(range(25))
    assert all(x['accept_cycle'] is None and x['return_cycle'] is None and x['actual_delivery_fence'] is None for x in xs)
    with pytest.raises(ValueError):E.loader_journal(0,4096)


def test_export_conserves_tables_and_rejects_wrong_mode_or_missing_phase():
    phases=list(C.readrows(E.OUT/'export_r1/phase_directory.jsonl.gz'))
    tables=list(C.readrows(E.OUT/'export_r1/key_tables.jsonl.gz'))
    assert len(phases)==46509 and len(tables)==58
    seen=set()
    for x in phases:
        identity=(x['stage'],x['phase'])
        assert identity not in seen;seen.add(identity)
        expected=x['source_key_word']
        assert tables[x['stage']]['words'][x['phase']]==expected
        assert (expected>>30)&1 == (x['format']=='bf16')
        assert (expected^(1<<30))!=tables[x['stage']]['words'][x['phase']]
    for t in tables:
        assert len(t['words'])==1024
        assert all(bool(w)==((t['stage'],p) in seen) for p,w in enumerate(t['words']))
    assert len(seen-{(phases[0]['stage'],phases[0]['phase'])})!=46509


def test_parent_provider_hash_and_corrected_charges():
    inputs=E.OUT/'inputs'
    parent=json.loads((inputs/'containment_model.json').read_text())
    receipt=json.loads((inputs/'source_receipt.json').read_text())
    check=json.loads((inputs/'containment_verification.json').read_text())
    assert C.sha((inputs/'containment_model.json').read_bytes())==check['model_sha256']
    for name,s in receipt['sources'].items():
        if (inputs/name).exists():assert C.sha((inputs/name).read_bytes())==s['sha256']
    x=parent['configuration_expansion']
    assert x['prospective_per_pair_4096x72_depth_slices']==7
    assert x['prospective_macro_instances']==4096*7
    assert x['expanded_physical_macro_pin_count']==4096*7*88
    out=json.loads((E.OUT/'export_r1/interface.json').read_text())
    assert out['PHW']==10 and out['compiled_NP']==4096 and out['NBF']==724
    assert not out['cfg_physical_timing_fault_ECC_admission']
    assert not out['full_descriptor_finite_calendar_bound']
    assert out['generic_source_loader']['hard_provider_or_cfg_ECC_or_cfg_fault_path_present'] is False


def test_actual_loader_and_admission_source_contract():
    pair=(E.OUT/'inputs/ot_v41_pair_w17w10_rne_wake_prepare.sv').read_text()
    adapt=(E.OUT/'inputs/ot_v41_rom_adapt.sv').read_text()
    for s in ['c_v <= ld_run;',"ld_a <= AW'(cfg_ph) * AW'(CW);",'wire go_e = go && act;']:
        assert s in pair
    for s in ["m_xks == AW'(1)","m_xcs == AW'(m_k)","m_xjs == '0", "m_ots == AW'(IL)", "m_ojs == AW'(1)",'m_round && !m_amax && !m_mmode']:
        assert s in adapt
