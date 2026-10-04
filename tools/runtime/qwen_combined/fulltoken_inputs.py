"""Existing full-36 cache binding only; no image, oracle, build or runtime work."""
import hashlib
import json
from pathlib import Path

from .frozen_history import FrozenHistory, KV_BYTES, require, sha

STAGES = ('E', *(f'L{i}' for i in range(36)), 'head')
PAYLOADS = ('matrix_int8.hex', 'matrix_scale_bf16.hex', 'crom.hex')


def history_from_inputs(inputs):
    """Use the explicitly pinned full GPU oracle, not a three-layer RTL record."""
    history = FrozenHistory(inputs['oracle']['root'],
                            oracle_sha256=inputs['oracle']['sha256'],
                            position=inputs['position'], token=inputs['token'])
    require(history.record['layers'] == 36 and history.record.get('head') is True,
            'full 36-layer plus head cached oracle required')
    return history


def compiled_extent(path):
    """Bind the existing generated die command and four-stack memory aperture.

    This is a compiled extent reference, not an executable/runtime PASS book.
    """
    path = Path(path)
    book = json.loads(path.read_text())
    def params(key):
        return {v[2:].split('=', 1)[0]: int(v.split('=', 1)[1])
                for v in book[key] if v.startswith('-G')}
    die, hbm = params('die'), params('hbm')
    require(all(die.get(k) == v for k, v in
                {'D': 4, 'G': 6144, 'SW': 64, 'NW': 18, 'REAL_MEM': 1,
                 'HBM_LAYERS': 36}.items()), 'same actual full-36 compiled die required')
    require(hbm.get('MEM_WORDS') == 36 * 131072 and hbm.get('WR_ACK') == 1,
            'same actual full-36 acknowledged HBM aperture required')
    provenance = book['die_generated_command_provenance']
    generated = Path(provenance['record_path'])
    require(sha(generated) == provenance['verfiles_sha256'], 'generated die command changed')
    require('-GHBM_LAYERS=36' in generated.read_text(), 'generated command lacks full-36 extent')
    return dict(path=str(path.resolve()), sha256=sha(path),
                die_generated_command=provenance, hbm_layers=36,
                memory_words_per_stack=hbm['MEM_WORDS'], runtime_verdict=None)


def baseline_reference(path, *, stage, history, pins, image_pins):
    """One actual single-stage result stays one stage, even after all finish."""
    path = Path(path)
    exit_path = path.parent / 'exit'
    reference = dict(path=str(path), exit_path=str(exit_path), stage=stage, status='pending')
    if not exit_path.exists():
        return reference
    reference['exit'] = int(exit_path.read_text())
    if not path.exists():
        reference['status'] = 'missing_terminal_result'
        return reference
    rec = json.loads(path.read_text())
    reference.update(status=rec.get('status'), sha256=sha(path))
    require(rec.get('status') == 'pass' and rec.get('source_stable') is True
            and rec.get('configuration') == 'REAL_MEM' and reference['exit'] == 0,
            'single-stage baseline is not stable REAL_MEM PASS: ' + stage)
    require(rec.get('stages_run') == [stage], 'single-stage coverage differs: ' + stage)
    require(rec.get('hbm_layers') == 36, 'three-layer baseline cannot bind full-36 inputs')
    require((rec['position'], rec['token'], rec['oracle_json_sha256']) ==
            (history.position, history.token, history.oracle_sha256), 'baseline oracle/frame differs')
    require(rec['source_sha256'] == pins, 'single-stage baseline source family differs')
    require(rec['stage_image_sha256'] == image_pins, 'single-stage baseline images differ')
    wanted = {k: v for k, v in history.frame['kv_pre_sha256'].items()
              if stage.startswith('L') and k.startswith(stage + '_die')}
    require(rec['kv_history_sha256'] == wanted, 'single-stage baseline KV coverage differs')
    reference['coverage'] = [stage]
    return reference


def inspect(cache, *, oracle_sha256, compiled_params, position=255, token=6280):
    """Return actual paths and pins; reuse existing raw histories without copying.

    Weight pins come from the GPU oracle's prep manifest and must resolve to
    the very same files. Only program/descriptor bytes and cached histories are
    read here. The owning combined launcher retains final payload validation.
    """
    cache = Path(cache).resolve(strict=True)
    result = dict(schema='opentallas.qwen-rom-full36-inputs.v1', position=position, token=token,
                  oracle=dict(root=str(cache/'gold'), sha256=oracle_sha256),
                  fulltoken_rtl_pass=False, launch_ready=False, gaps=[])
    history = history_from_inputs(result)
    prep_path = cache/'prep/prep.json'
    require(sha(prep_path) == history.record['prep_sha256'], 'oracle prep identity differs')
    prep = json.loads(prep_path.read_text())
    image_sources = {(('head' if p['kind'] == 'head' else f'L{p["layer"]}'), p['die']): p
                     for p in prep['images']}
    result['prep'] = dict(path=str(prep_path), sha256=sha(prep_path))
    result['compiled_extent'] = compiled_extent(compiled_params)
    result['stages'], result['history'], result['baselines'] = [], {}, {}
    first = cache/f'runs/P{position}/E/result.json'
    family = json.loads(first.read_text())['source_sha256'] if first.exists() else None
    result['baseline_source_sha256'] = family
    for stage in STAGES:
        stage_file = cache/f'runs/P{position}/{stage}/stages.txt'
        require(stage_file.is_file(), 'missing existing stage list: ' + str(stage_file))
        words = stage_file.read_text().split()
        require(len(words) == 6 and words[0] == stage and words[5] ==
                ('1' if stage.startswith('L') else '0'), 'existing stage ABI differs: ' + stage)
        row = dict(name=stage, source_stage_list=str(stage_file),
                   source_sha256=sha(stage_file), directories=words[1:5], kv_reset=int(words[5]),
                   image_sha256={})
        for rank, directory in enumerate(words[1:5]):
            directory = Path(directory)
            for filename in (*PAYLOADS, 'program.hex', 'segments.hex'):
                path = directory/filename
                key = f'{stage}/die{rank}/{filename}'
                if not path.is_file():
                    result['gaps'].append('missing cached image: ' + str(path))
                    continue
                if stage == 'E' or filename not in PAYLOADS:
                    pin = sha(path)
                else:
                    frozen = image_sources[(stage, rank)]
                    source = Path(frozen['src'])/filename
                    require(path.resolve() == source.resolve(), 'image outside oracle prep source: ' + key)
                    pin = frozen['image_sha256'][filename]
                row['image_sha256'][key] = pin
        result['stages'].append(row)
        if family is not None:
            baseline_path = cache/f'runs/P{position}/{stage}/result.json'
            try:
                result['baselines'][stage] = baseline_reference(
                    baseline_path, stage=stage, history=history,
                    pins=family, image_pins=row['image_sha256'])
            except ValueError as error:
                # Preserve the original reference and refusal. An inventory may
                # expose usable cache inputs, but cannot promote this baseline.
                result['baselines'][stage] = dict(
                    path=str(baseline_path), sha256=sha(baseline_path), stage=stage,
                    status='incompatible_frozen_reference', reason=str(error))
                result['gaps'].append(stage + ': ' + str(error))
    for layer in range(36):
        for rank in range(4):
            key = f'L{layer}_die{rank}'
            npy = history.position_dir/'kv_pre'/f'{key}.npy'
            raw = cache/f'runs/P{position}/L{layer}/w/kv_pre_bin/{key}.bin'
            if not npy.is_file() or not raw.is_file():
                result['gaps'].append('missing cached history: ' + str(npy if not npy.is_file() else raw))
                continue
            source, source_pin, words = history.source(layer, rank)
            raw_pin = hashlib.sha256(memoryview(words)).hexdigest()
            require(raw.stat().st_size == KV_BYTES and sha(raw) == raw_pin,
                    'existing raw history differs: ' + key)
            result['history'][key] = dict(source=str(source), source_sha256=source_pin,
                                         raw=str(raw), raw_sha256=raw_pin, bytes=KV_BYTES)
    result['preload'] = dict(path=str(history.position_dir/'x_preload.hex'),
                             sha256=history.frame['x_preload_sha256'])
    require(sha(result['preload']['path']) == result['preload']['sha256'], 'cached preload differs')
    result['embedding'] = dict(json=str(history.position_dir/'embedding_row.json'),
                              raw=str(cache/f'runs/P{position}/E/w/embedding_row.bin'))
    embedding = Path(result['embedding']['raw'])
    if not embedding.is_file():
        result['gaps'].append('missing cached embedding: ' + str(embedding))
    else:
        payload = embedding.read_bytes()
        frame = json.loads(Path(result['embedding']['json']).read_text())
        wanted = token.to_bytes(4, 'little') + int(frame['scale_bf16'], 16).to_bytes(2, 'little') + bytes.fromhex(frame['codes_hex'])
        require(payload == wanted and len(payload) == 4102, 'cached embedding row differs')
        result['embedding']['sha256'] = sha(embedding)
    result['head'] = dict(expected=history.frame['head'],
                          logits=str(history.position_dir/'logits.npy'))
    require(sha(result['head']['logits']) == history.frame['head']['logits_sha256'], 'cached logits differ')
    result['baseline_pending'] = [s for s in STAGES if result['baselines'].get(s, {}).get('status') != 'pass']
    if result['baseline_pending']:
        result['gaps'].append('Claude single-stage baseline pending: ' + ','.join(result['baseline_pending']))
    result['gaps'] += ['combined compiled executable/selection not enrolled by this input hook',
                       'combined launcher and pinned host require head-stage support',
                       'combined numerical helper requires head/argmax readback support']
    result['scope'] = 'cached full-36 input coverage and independent per-stage references; no composed RTL verdict'
    return result
