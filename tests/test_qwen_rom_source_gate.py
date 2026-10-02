"""Fail-closed independent replay gates for the real connected TP4 intake."""
import base64
import copy
import json
import sys
from pathlib import Path

import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import qwen_rom_source_gate as G


def put(p, name, data):
    if isinstance(data, str):
        data = data.encode()
    p['files'][name] = dict(base64=base64.b64encode(data).decode(), sha256=G.sha(data))


def fixture(tmp_path, full=False):
    p = dict(files={}, source_sha256_at_capture={'source.sv': G.sha(b'original')},
             binary_sha256='binary', generated_core_sha256='core', end_identity={'state': 'live'})
    (tmp_path / 'source.sv').write_bytes(b'original')
    names = G.FULL_STAGES if full else ['L0']
    put(p, 'token.log', ''.join(f'STAGE {n} done cycles=10 start_cyc={i*11+1} end_cyc={i*11+11} '
        'seq_fault=0 core_fault=0 coll_fault=0\n' for i,n in enumerate(names)))
    put(p, 'build_params.json', json.dumps(dict(die=['-GG=6144', '-GD=4', '-GSW=64', '-GSMIN=7', '-GTCUT=7'],
        tile=['-GGT=6144', '-GCODE_BANKS=5', '-GSMIN=7', '-GKV_LOCAL=0'],
        coll=['-GN=4', '-GLAT=339', '-GDEPTH=1024'])))
    put(p, 'stages.txt', ''.join(n+' dir0 dir1 dir2 dir3 1\n' for n in G.FULL_STAGES))
    put(p, 'oracle.json', '{"next_token": 42, "next_logit_bits": "3f800000"}')
    for n in names:
        if n == 'head':
            continue
        for d in range(4):
            for prefix in ('actual', 'expected'):
                put(p, f'{prefix}/{n}_die{d}_x.hex', '3f800000\n'*4096)
    if full:
        log = base64.b64decode(p['files']['token.log']['base64']).decode()
        put(p, 'token.log', log+'QWEN_ROM_TOKEN_TP2 PASS stages=37 token=42 val=3f800000 die1_token=42 cycles=407\n')
        p['end_identity']['state']='eligible_for_intake'
        put(p, 'terminal.json', json.dumps(dict(status='pass', source_stable=True,
            source_sha256=p['source_sha256_at_capture'], binary_sha256='binary', generated_core_sha256='core',
            oracle_sha256=p['files']['oracle.json']['sha256'], rtl_token=42, rtl_logit_bits='3f800000',
            stages_run=G.FULL_STAGES, total_cycles=407,
            design_point=dict(tp=4, groups_per_die=6144, tiles_per_die=1536,su_width=64,smin=7,tree_cut=7,collective_lat_cycles=339),
            layer_x_checks={f'L{i}_die{d}_x':dict(words=4096,mismatches=0,actual_sha256=G.sha(b'3f800000\n'*4096),expected_sha256=G.sha(b'3f800000\n'*4096)) for i in range(36) for d in range(4)})))
    return p


def test_live_prefix_exact_without_full_token_credit(tmp_path):
    r=G.replay(fixture(tmp_path),tmp_path)
    assert r['status']=='pending' and r['checkpoint_status']=='bit_exact'
    assert len(r['checks'])==4 and r['current_source_joined']
    assert not r['full_token_exact_at_runtime_scope'] and not r['adoption']


def test_complete_original_terminal_at_its_scope(tmp_path):
    r=G.replay(fixture(tmp_path,True),tmp_path)
    assert r['status']=='pass' and len(r['checks'])==144
    assert r['full_token_exact_at_runtime_scope'] and not r['adoption']


@pytest.mark.parametrize('name', ['actual/L0_die2_x.hex','expected/L0_die3_x.hex'])
def test_missing_rank_never_passes(tmp_path,name):
    p=fixture(tmp_path); del p['files'][name]
    with pytest.raises(KeyError): G.replay(p,tmp_path)


def test_last_rank_word_mismatch_rejected(tmp_path):
    p=fixture(tmp_path);put(p,'actual/L0_die3_x.hex','40000000\n'+'3f800000\n'*4095)
    with pytest.raises(ValueError,match='mismatches'): G.replay(p,tmp_path)


@pytest.mark.parametrize('words', [0,4095,4097])
def test_empty_or_truncated_or_extra_vector_rejected(tmp_path,words):
    p=fixture(tmp_path);put(p,'actual/L0_die0_x.hex','3f800000\n'*words)
    with pytest.raises(ValueError,match='4096'): G.replay(p,tmp_path)


@pytest.mark.parametrize('fault',G.FAULTS)
def test_rank3_fault_mask_rejected(tmp_path,fault):
    p=fixture(tmp_path); data=base64.b64decode(p['files']['token.log']['base64']).decode()
    put(p,'token.log',data.replace(fault+'=0',fault+'=8'))
    with pytest.raises(ValueError,match='fault mask'): G.replay(p,tmp_path)


def test_hash_tamper_rejected(tmp_path):
    p=fixture(tmp_path);p['files']['actual/L0_die0_x.hex']['sha256']='0'*64
    with pytest.raises(ValueError,match='hash mismatch'): G.replay(p,tmp_path)


def test_source_drift_does_not_transfer_current_qualification(tmp_path):
    p=fixture(tmp_path);(tmp_path/'source.sv').write_bytes(b'new-source')
    r=G.replay(p,tmp_path)
    assert not r['current_source_joined'] and r['checkpoint_status']=='bit_exact'


@pytest.mark.parametrize('change', ['fault_missing','reordered','duplicate','span'])
def test_malformed_stage_log_rejected(tmp_path,change):
    p=fixture(tmp_path);log=base64.b64decode(p['files']['token.log']['base64']).decode()
    if change=='fault_missing': log=log.replace('core_fault=0','')
    if change=='reordered': log=log.replace('L0','L1')
    if change=='duplicate': log+=log
    if change=='span': log=log.replace('cycles=10','cycles=9')
    put(p,'token.log',log)
    with pytest.raises(ValueError): G.replay(p,tmp_path)


@pytest.mark.parametrize('field,value', [('status','fail'),('source_stable',False),('binary_sha256','other'),
                                         ('total_cycles',408),('stages_run',['L0']),('source_sha256',{})])
def test_bad_original_terminal_is_retained_as_fail(tmp_path,field,value):
    p=fixture(tmp_path,True);t=json.loads(base64.b64decode(p['files']['terminal.json']['base64']));t[field]=value
    put(p,'terminal.json',json.dumps(t));r=G.replay(p,tmp_path)
    assert r['status']=='fail' and not r['full_token_exact_at_runtime_scope']


def test_live_child_prevents_terminal_qualification(tmp_path):
    p=fixture(tmp_path,True);p['end_identity']['state']='children_live'
    assert G.replay(p,tmp_path)['status']=='fail'


def test_duplicate_parameter_cannot_hide_override(tmp_path):
    p=fixture(tmp_path);params=json.loads(base64.b64decode(p['files']['build_params.json']['base64']))
    params['tile'].append('-GCODE_BANKS=10');put(p,'build_params.json',json.dumps(params))
    with pytest.raises(ValueError,match='parameters'):G.replay(p,tmp_path)
