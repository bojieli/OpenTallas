"""File-transport/coverage contracts only; no numerical or RTL oracle fixtures."""
import json
from pathlib import Path

import numpy as np
import pytest

from tools.runtime.qwen_combined import frozen_history as history
from tools.runtime.qwen_combined import fulltoken_inputs as inputs


def fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(history, 'KV_WORDS', 4)
    monkeypatch.setattr(history, 'KV_BYTES', 16)
    monkeypatch.setattr(inputs, 'KV_BYTES', 16)
    cache = tmp_path/'cache'
    gold = cache/'gold/P255'
    (gold/'kv_pre').mkdir(parents=True)
    (cache/'prep').mkdir()
    images, kvpins, stages = [], {}, []
    for stage in inputs.STAGES:
        job = cache/f'runs/P255/{stage}'
        job.mkdir(parents=True)
        dirs, pins = [], {}
        for rank in range(4):
            directory = cache/f'images/{stage}-d{rank}'
            directory.mkdir(parents=True)
            dirs.append(str(directory))
            weightpins = {}
            for name in (*inputs.PAYLOADS, 'program.hex', 'segments.hex'):
                f = directory/name
                f.write_text(f'{rank:08x}\n')
                pin = inputs.sha(f)
                pins[f'{stage}/die{rank}/{name}'] = pin
                if name in inputs.PAYLOADS:
                    weightpins[name] = pin
            if stage != 'E':
                images.append(dict(kind='head' if stage == 'head' else 'layer',
                                   layer=-1 if stage == 'head' else int(stage[1:]),
                                   die=rank, src=str(directory), image_sha256=weightpins))
            if stage.startswith('L'):
                key = f'{stage}_die{rank}'
                bits = np.array([rank, 0x80000000, 0x3f800000, 0xffffffff], dtype='<u4')
                source = gold/'kv_pre'/f'{key}.npy'
                np.save(source, bits)
                kvpins[key] = inputs.sha(source)
                raw = job/f'w/kv_pre_bin/{key}.bin'
                raw.parent.mkdir(parents=True, exist_ok=True)
                raw.write_bytes(bits.tobytes())
        (job/'stages.txt').write_text(' '.join([stage, *dirs, '1' if stage.startswith('L') else '0'])+'\n')
        stages.append(pins)
    prep = cache/'prep/prep.json'
    prep.write_text(json.dumps({'images': images}))
    (gold/'x_preload.hex').write_text('@1000\n3f800000\n')
    (gold/'logits.npy').write_bytes(b'cached-logit-bits')
    codes = '80' * 4096
    (gold/'embedding_row.json').write_text(json.dumps(dict(token=6280, scale_bf16='3f80', codes_hex=codes)))
    embed = cache/'runs/P255/E/w/embedding_row.bin'
    embed.parent.mkdir(parents=True)
    embed.write_bytes((6280).to_bytes(4, 'little') + bytes.fromhex('803f') + bytes.fromhex(codes))
    oracle = cache/'gold/oracle.json'
    oracle.write_text(json.dumps(dict(schema='opentallas.qwen-rom-tp4-position-oracle-gpu.v1',
        status='ISA_golden_only', tp=4, groups=6144, kv_format='fp8', layers=36, head=True,
        positions=[255], prep_sha256=inputs.sha(prep), per_position={'255': dict(token=6280,
        kv_pre_sha256=kvpins, x_preload_sha256=inputs.sha(gold/'x_preload.hex'),
        head={'logits_sha256': inputs.sha(gold/'logits.npy')})})))
    family = {'rtl/example.sv': 'a'*64}
    (cache/'runs/P255/E/exit').write_text('0\n')
    (cache/'runs/P255/E/result.json').write_text(json.dumps(dict(status='pass', source_stable=True,
        configuration='REAL_MEM', hbm_layers=36, stages_run=['E'], position=255, token=6280,
        oracle_json_sha256=inputs.sha(oracle), source_sha256=family,
        stage_image_sha256=stages[0], kv_history_sha256={})))
    command = tmp_path/'Vdie__verFiles.dat'
    command.write_text('actual recorded command -GHBM_LAYERS=36\n')
    compiled = tmp_path/'compiled.json'
    compiled.write_text(json.dumps(dict(die=['-GD=4','-GG=6144','-GSW=64','-GNW=18',
        '-GREAL_MEM=1','-GHBM_LAYERS=36'], hbm=['-GMEM_WORDS=4718592','-GWR_ACK=1'],
        die_generated_command_provenance=dict(record_path=str(command),
                                             verfiles_sha256=inputs.sha(command)))))
    return cache, compiled, inputs.sha(oracle)


def test_full_cache_is_not_promoted_to_full_rtl_baseline(tmp_path, monkeypatch):
    cache, compiled, pin = fixture(tmp_path, monkeypatch)
    raw = cache/'runs/P255/L35/w/kv_pre_bin/L35_die3.bin'
    before = (raw.read_bytes(), raw.stat().st_mtime_ns)
    result = inputs.inspect(cache, oracle_sha256=pin, compiled_params=compiled)
    assert [s['name'] for s in result['stages']] == list(inputs.STAGES)
    assert len(result['history']) == 144
    assert result['baseline_pending'] == list(inputs.STAGES[1:])
    assert result['baselines']['E']['coverage'] == ['E']
    assert not result['fulltoken_rtl_pass'] and not result['launch_ready']
    assert any('head-stage support' in s for s in result['gaps'])
    assert inputs.history_from_inputs(result).source(35, 3)[2][1] == 0x80000000
    assert (raw.read_bytes(), raw.stat().st_mtime_ns) == before


def test_three_layer_baseline_cannot_supply_36_layer_history(tmp_path, monkeypatch):
    cache, compiled, pin = fixture(tmp_path, monkeypatch)
    f = cache/'runs/P255/E/result.json'
    rec = json.loads(f.read_text()); rec['hbm_layers'] = 3
    f.write_text(json.dumps(rec))
    result = inputs.inspect(cache, oracle_sha256=pin, compiled_params=compiled)
    assert result['baselines']['E']['status'] == 'incompatible_frozen_reference'
    assert 'three-layer baseline' in result['baselines']['E']['reason']
    assert not result['launch_ready'] and not result['fulltoken_rtl_pass']


def test_same_model_capacity_and_recorded_command_are_required(tmp_path, monkeypatch):
    cache, compiled, pin = fixture(tmp_path, monkeypatch)
    command = tmp_path/'Vdie__verFiles.dat'
    command.write_text('different command')
    with pytest.raises(ValueError, match='generated die command changed'):
        inputs.inspect(cache, oracle_sha256=pin, compiled_params=compiled)


def test_changed_raw_history_refuses_without_overwriting(tmp_path, monkeypatch):
    cache, compiled, pin = fixture(tmp_path, monkeypatch)
    raw = cache/'runs/P255/L35/w/kv_pre_bin/L35_die3.bin'
    raw.write_bytes(b'preserve old error')
    with pytest.raises(ValueError, match='existing raw history differs'):
        inputs.inspect(cache, oracle_sha256=pin, compiled_params=compiled)
    assert raw.read_bytes() == b'preserve old error'


def test_changed_oracle_manifest_is_not_substituted_into_frozen_baseline(tmp_path, monkeypatch):
    cache, compiled, pin = fixture(tmp_path, monkeypatch)
    f = cache/'runs/P255/E/result.json'
    rec = json.loads(f.read_text()); rec['oracle_json_sha256'] = '0' * 64
    f.write_text(json.dumps(rec))
    result = inputs.inspect(cache, oracle_sha256=pin, compiled_params=compiled)
    assert result['baselines']['E']['status'] == 'incompatible_frozen_reference'
    assert result['baselines']['E']['reason'] == 'baseline oracle/frame differs'
    assert 'E' in result['baseline_pending'] and not result['launch_ready']
    assert result['oracle']['sha256'] == pin
    assert json.loads(f.read_text())['oracle_json_sha256'] == '0' * 64
