#!/usr/bin/env python3
"""Check one completed combined run against its existing frozen TP4 oracle.

File comparison only: no engine, model execution, oracle generation or inference.
Callable check() returns a scoped verdict; the CLI writes a new immutable receipt.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CONVERSION = ROOT/'tools/qwen_rom_rt_token_w12_rm.py'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def existing_e4m3():
    # Execute only the existing conversion function, not the owner's build/run
    # module imports or main. Its complete source is pinned in the receipt.
    tree = ast.parse(CONVERSION.read_text())
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'e4m3']
    require(len(nodes) == 1, 'existing E4M3 function missing or ambiguous')
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(CONVERSION), 'exec'), namespace)
    return namespace['e4m3']


def compare_hex(actual, expected, *, embedding=False):
    got = actual.read_text().split()
    want = expected.read_text().split()
    if embedding:
        want = [v for v in want if not v.startswith('@')]
    require(len(want) == 4096, 'frozen X must contain exactly 4096 words: '+str(expected))
    require(all(re.fullmatch(r'[0-9a-fA-F]{8}', w) for w in got + want), 'malformed X hex')
    mismatches = [i for i, (a, b) in enumerate(zip(got, want)) if a != b]
    return dict(words=len(got), mismatches=len(mismatches)+abs(len(got)-len(want)),
                first_mismatch=mismatches[0] if mismatches else None,
                actual_sha256=sha(actual), expected_sha256=sha(expected))


def compare_kv(actual, expected, convert):
    gold = json.loads(expected.read_text())
    wanted = {kind: [convert(int(v, 16)) for v in gold[key]]
              for kind, key in (('K', 'k_bits'), ('V', 'v_bits'))}
    require(all(len(v) == 256 for v in wanted.values()), 'frozen K/V must each contain 256 elements')
    rows = [line.split() for line in actual.read_text().splitlines()]
    require(len(rows) == 512, 'actual current-token K/V must contain 512 rows')
    got = {'K': [], 'V': []}
    for row in rows:
        require(len(row) == 4 and row[0] in got, 'malformed current-token K/V row')
        kind, head, dimension, value = row
        i = len(got[kind])
        require((int(head), int(dimension)) == (i//128, i%128) and i < 256,
                'duplicate, missing or reordered current-token K/V coordinate')
        require(re.fullmatch(r'[0-9a-fA-F]{2}', value) is not None, 'malformed E4M3 byte')
        got[kind].append(int(value, 16))
    require(all(len(v) == 256 for v in got.values()), 'missing K or V rows')
    return dict(k_codes=256, v_codes=256,
                k_mismatches=sum(a != b for a, b in zip(got['K'], wanted['K'])),
                v_mismatches=sum(a != b for a, b in zip(got['V'], wanted['V'])),
                actual_sha256=sha(actual), expected_sha256=sha(expected))


def check(terminal, baseline, oracle_root, run_dir, runtime_log):
    terminal, baseline, oracle_root, run_dir, runtime_log = map(Path,
        (terminal, baseline, oracle_root, run_dir, runtime_log))
    receipt = json.loads(terminal.read_text())
    require(receipt.get('returncode') == 0 and receipt.get('status') == 'runtime_exit_zero',
            'completed zero-exit owning runtime receipt required')
    require(receipt['input_sha256'].get(str(baseline.resolve())) == sha(baseline), 'frozen baseline pin differs')
    frozen = json.loads(baseline.read_text())
    require(frozen.get('status') == 'pass' and frozen.get('source_stable') is True
            and frozen.get('configuration') == 'REAL_MEM', 'passing REAL_MEM baseline required')
    require(receipt['position'] == frozen['position'] and receipt['token'] == frozen['token'], 'position/token differs')
    oracle_path = oracle_root/'oracle.json'
    require(sha(oracle_path) == frozen['oracle_json_sha256'], 'frozen oracle identity differs')
    oracle = json.loads(oracle_path.read_text())
    require(oracle.get('status') == 'ISA_golden_only' and oracle.get('tp') == 4
            and oracle.get('groups') == 6144 and oracle.get('kv_format') == 'fp8', 'frozen TP4 oracle required')
    layers = receipt['layers']
    require(layers and layers == list(range(len(layers))) and len(layers) <= oracle['layers'], 'selected layer coverage')
    require(frozen['stages_run'] == ['E']+['L'+str(l) for l in layers], 'selected stages differ from frozen baseline')
    require(Path(receipt['command'][3]).resolve() == run_dir.resolve(), 'readback directory differs from executed command')
    frame = oracle['per_position'][str(receipt['position'])]
    require(frame['token'] == receipt['token'], 'oracle token differs')
    position_dir = oracle_root/('P'+str(receipt['position']))
    text = runtime_log.read_text()
    final = re.findall(r'QWEN_ROM_COMBINED PASS stages=(\d+)\b', text)
    require(final == [str(len(layers)+1)], 'actual combined terminal marker/stage count missing')
    convert = existing_e4m3()
    x_checks, kv_checks, pins = {}, {}, {}
    for stage in ['E']+['L'+str(l) for l in layers]:
        for rank in range(4):
            key = stage+'_die'+str(rank)
            expected = position_dir/('x_preload.hex' if stage == 'E' else f'L{int(stage[1:]):02d}_die{rank}_x.hex')
            digest = frame['x_preload_sha256'] if stage == 'E' else frame['layer_x_sha256'][key]
            require(sha(expected) == digest, 'frozen X pin differs: '+key)
            pins[str(expected.resolve())] = digest
            x_checks[key+'_x'] = compare_hex(run_dir/(key+'_x.hex'), expected, embedding=stage == 'E')
            if stage != 'E':
                expected = position_dir/'kv_at_P'/(key+'.json')
                digest = frame['kv_at_P_sha256'][key]
                require(sha(expected) == digest, 'frozen current-token KV pin differs: '+key)
                pins[str(expected.resolve())] = digest
                kv_checks[key] = compare_kv(run_dir/(key+'_kvP.hex'), expected, convert)
    require(all(sha(p) == digest for p, digest in pins.items()), 'frozen comparison input changed')
    good = all(c['mismatches'] == 0 for c in x_checks.values()) and all(
        c['k_mismatches'] == 0 and c['v_mismatches'] == 0 for c in kv_checks.values())
    return dict(schema='opentallas.qwen-rom-combined-cached-readback.v1', status='pass' if good else 'fail',
                scope='Selected cached stages/all four ranks only; no unselected/full-token, rate or SS/FF qualification',
                position=receipt['position'], token=receipt['token'], layers=layers,
                layer_x_checks=x_checks, token_kv_writeback_checks=kv_checks,
                input_sha256={str(p.resolve()):sha(p) for p in (terminal, baseline, oracle_path, runtime_log)},
                golden_sha256=pins, comparison_source_sha256=sha(CONVERSION), checker_source_sha256=sha(__file__))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('terminal', 'baseline', 'oracle-root', 'run-dir', 'runtime-log', 'output'):
        parser.add_argument('--'+key, type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'immutable checker output exists')
    try:
        record = check(args.terminal, args.baseline, args.oracle_root, args.run_dir, args.runtime_log)
    except (ValueError, KeyError, OSError, TypeError, IndexError) as error:
        record = dict(status='fail', error=str(error), scope='cached readback refused; no numerical qualification')
    with args.output.open('x') as stream:
        stream.write(json.dumps(record, indent=2)+'\n')
    print(record['status'])
    return 0 if record['status'] == 'pass' else 2


if __name__ == '__main__':
    raise SystemExit(main())
