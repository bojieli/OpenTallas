#!/usr/bin/env python3
"""Launch Laplace's compiled full-shape combined top with frozen history.

This does not build an engine, generate an oracle or choose an optimization.
The selected enclosing driver must consume combined_driver.hpp and bind its
RankPins to actual RTL. Missing compiled clock/arm bindings fail before launch.
"""
import argparse
import importlib.util
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CORRECTED_SERVICE = 'rtl/hdc/nearhbm/ot_qwen_nearhbm_realmem_service.sv'
CORRECTED_SHA = 'a10a3d79240a8373c5a44ae187655b1a58beefbaa0ccd96b95b178cca16c7c3f'
DRIVER = 'tools/runtime/qwen_combined/combined_driver.hpp'
CONTEXT = 'tools/runtime/qwen_combined/fullshape_context.hpp'
CANONICAL_SERVICE = 'rtl/hdc/kv/ot_qwen_rt_kv_fill_service.sv'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def embedding_argument(path, expected_sha256, token):
    """Bind the cached 32-bit token, BF16 scale and 4096 INT8 ROM bytes."""
    path = Path(path).resolve(strict=True)
    require(sha(path) == expected_sha256, 'cached embedding row identity')
    payload = path.read_bytes()
    require(len(payload) == 4102, 'cached embedding ROM row extent')
    require(int.from_bytes(payload[:4], 'little') == token, 'embedding row token differs')
    return ['--embed-bin', str(path)]


def layers_from_stages(path):
    stages = []
    for line in Path(path).read_text().splitlines():
        words = line.split()
        if not words or words[0].startswith('#'):
            continue
        # Same stage-list ABI as qwen_rom_rt_w12_rm.cpp: kind then image dir.
        require(len(words) == 6, 'stage must name all four rank image directories and kv_reset')
        name, *directories, kv_reset = words
        require(kv_reset in ('0', '1'), 'invalid source stage kv_reset')
        require(name == 'E' or (name.startswith('L') and name[1:].isdigit()), 'unknown stage')
        require(all(Path(d).is_dir() for d in directories), 'missing actual rank stage image directory')
        stages.append(name)
    require(stages and stages[0] == 'E', 'embedding stage must be first')
    layers = [int(s[1:]) for s in stages[1:]]
    require(layers and layers == list(range(len(layers))) and len(layers) <= 36,
            'ordered contiguous decoder layers L0..L35 required')
    return layers


def validate_selection(book, root=ROOT):
    require(book.get('geometry') == {'tp': 4, 'groups': 6144, 'sw': 64, 'nw': 18},
            'actual fullshape TP4/G6144/SW64/NW18 required')
    require(book.get('real_mem') is True, 'actual REAL_MEM service required')
    pins = book['source_sha256']
    require(book.get('memory_service_source') in pins, 'actual selected REAL_MEM adapter source missing')
    require(CANONICAL_SERVICE in pins, 'canonical KV fill/write/ACK service source missing')
    require(book.get('crossing_sources') and all(p in pins for p in book['crossing_sources']),
            'actual request/response crossing sources missing')
    if book.get('near_hbm_enabled', False):
        require(pins.get(CORRECTED_SERVICE) == CORRECTED_SHA, 'selected near-HBM requires corrected 62ed service')
    require(pins.get(DRIVER) == sha(root / DRIVER) and pins.get(CONTEXT) == sha(root / CONTEXT),
            'selected clock/arm driver and fullshape context source required')
    for path, expected in pins.items():
        p = Path(path)
        require(not p.is_absolute() and '..' not in p.parts, 'repository relative source pin required')
        require(sha(root / p) == expected, 'selected source changed: ' + path)
    # A sourcebook must name the real enclosing driver and top, not substitute
    # the reduced component's PASS record or the standalone support test.
    require(book['top_source'] in pins and book['binding_source'] in pins,
            'actual enclosing top and pin-binding source missing')
    require(book['top_source'] != CORRECTED_SERVICE and book['binding_source'] not in (DRIVER, CONTEXT),
            'enclosing top/pin binding cannot be the component or helper')
    clocks = book['clocks']
    for domain in ('core', 'service'):
        c = clocks[domain]
        require(type(c['period_fs']) is int and c['period_fs'] > 0 and c['period_fs'] % 2 == 0,
                'explicit positive even clock period required')
        require(type(c['first_rise_fs']) is int and c['first_rise_fs'] > 0,
                'explicit positive clock phase required')
        require(type(c['port']) is str and bool(c['port']), 'actual clock port required')
    require(clocks['core']['port'] != clocks['service']['port'], 'core/service clocks aliased')
    require(type(book['memory_model_clk_ps']) is int and book['memory_model_clk_ps'] > 0
            and book['memory_model_clk_ps'] * 1000 == clocks['service']['period_fs'],
            'HBM timing model CLK_PS differs from driven service clock')
    binary = Path(book['executable']).resolve(strict=True)
    require(sha(binary) == book['executable_sha256'], 'compiled combined executable changed')
    if 'driver_abi' in book:
        require(book['driver_abi'] == 'combined-driver-v1', 'clock/arm consumer is not compiled')
    return binary


def prepare(book_path, stages, preload, oracle_root, baseline, output, root=ROOT):
    book = json.loads(Path(book_path).read_text())
    binary = validate_selection(book, root)
    selected_layers = layers_from_stages(stages)
    require(Path(preload).is_file(), 'missing actual vector preload')
    require(not Path(output).exists(), 'immutable output directory already exists')
    # Reuse Herschel's exact cached-source binding. Missing layer coverage is a
    # refusal, never a request for CPU inference or a synthetic KV fallback.
    spec = importlib.util.spec_from_file_location(
        '_qwen_combined_selected_history', root/'tools/runtime/qwen_combined/frozen_history.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    history = module.FrozenHistory.from_baseline(oracle_root, baseline)
    require(max(selected_layers) < history.record['layers'], 'frozen oracle does not cover selected layers')
    payload_pins = {}
    for line in Path(stages).read_text().splitlines():
        words = line.split()
        if not words or words[0].startswith('#'):
            continue
        for directory in words[1:5]:
            files = sorted(p for p in Path(directory).rglob('*') if p.is_file())
            require(files, 'empty rank stage image directory')
            for p in files:
                payload_pins[str(p.resolve())] = sha(p)
    output = Path(output)
    output.mkdir(parents=True)
    kv = history.export(output / 'kv_history', layers=selected_layers)
    (output / 'run').mkdir()
    # Canonical fscanf ABI has four rank paths and one reset integer. Resolve
    # every path before runtime; strip launcher-only comments without changing
    # the original immutable stage list.
    runtime_stages = output/'stages.txt'
    lines = []
    for line in Path(stages).read_text().splitlines():
        words = line.split()
        if words and not words[0].startswith('#'):
            lines.append(' '.join([words[0], *(str(Path(p).resolve()) for p in words[1:5]), words[5]]))
    runtime_stages.write_text('\n'.join(lines)+'\n')
    cmd = [str(binary), '--stages', str(runtime_stages.resolve()), str((output/'run').resolve()),
           str(Path(preload).resolve()), '--pos', str(history.position), '--token', str(history.token),
           '--kv-dir', str((output/'kv_history').resolve()), '--kv-ideal', '0']
    for domain in ('core', 'service'):
        for key in ('period_fs', 'first_rise_fs'):
            cmd += ['--' + domain + '-' + key.replace('_', '-'), str(book['clocks'][domain][key])]
    rec = {'schema': 'opentallas.qwen-rom-combined-launch.v1', 'status': 'prepared',
           'scope': 'actual selected layers; no fulltoken/SSFF/rate qualification from launch',
           'selection': book, 'layers': selected_layers, 'position': history.position, 'token': history.token,
           'kv_history': kv, 'command': cmd, 'stage_payload_sha256': payload_pins,
           'input_sha256': {str(Path(p).resolve()): sha(p) for p in (book_path, stages, preload, baseline)}}
    (output/'launch.json').write_text(json.dumps(rec, indent=2)+'\n')
    return cmd, rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for key in ('selection', 'stages', 'preload', 'oracle-root', 'baseline', 'output', 'embedding-bin'):
        ap.add_argument('--'+key, type=Path, required=True)
    ap.add_argument('--embedding-sha256', required=True)
    ap.add_argument('--prepare-only', action='store_true')
    a = ap.parse_args(argv)
    try:
        baseline_token = json.loads(a.baseline.read_text())['token']
        embedding = embedding_argument(a.embedding_bin, a.embedding_sha256, baseline_token)
        cmd, rec = prepare(a.selection, a.stages, a.preload, a.oracle_root, a.baseline, a.output)
        require(rec['token'] == baseline_token, 'prepared token differs from frozen baseline')
        cmd += embedding
        rec['command'] = cmd
        rec['embedding'] = {'path': embedding[1], 'sha256': a.embedding_sha256}
        rec['input_sha256'][embedding[1]] = a.embedding_sha256
        (a.output/'launch.json').write_text(json.dumps(rec, indent=2)+'\n')
        if a.prepare_only:
            print(json.dumps({'status': 'prepared', 'command': cmd}));return 0
        # Sole runtime owner launches this. No timeout, memory cap, new compiler,
        # second context gate or hidden golden callback is introduced.
        with (a.output/'runtime.log').open('x') as log:
            child = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
            (a.output/'runtime.pid').write_text(str(child.pid)+'\n')
            rc = child.wait()
        rec['returncode'] = rc
        rec['status'] = 'runtime_exit_zero' if rc == 0 else 'runtime_failed'
        require(all(sha(p) == expected for p, expected in rec['input_sha256'].items()), 'launch input changed')
        require(all(sha(p) == expected for p, expected in rec['stage_payload_sha256'].items()), 'stage image changed')
        require(all(sha(v['raw']) == v['raw_sha256'] for v in rec['kv_history'].values()), 'raw history changed')
        validate_selection(rec['selection'])
        (a.output/'terminal.json').write_text(json.dumps(rec, indent=2)+'\n')
        return rc
    except (ValueError, KeyError, OSError) as e:
        if 'rec' in locals():
            rec['status'] = 'failed';rec['error'] = str(e)
            with (a.output/'failure.json').open('x') as f:
                json.dump(rec, f, indent=2);f.write('\n')
        print('REFUSED: '+str(e), file=sys.stderr);return 2


if __name__ == '__main__':
    raise SystemExit(main())
