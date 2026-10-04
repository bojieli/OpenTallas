#!/usr/bin/env python3
"""Compare a completed full-token RTL run with an existing TP4 oracle.

Consumes files only; does not require an earlier full-token RTL PASS and never
generates an oracle, runs inference, or computes a replacement head result.
"""
import argparse
import json
from pathlib import Path
import re

from qwen_rom_combined_readback import compare_hex, compare_kv, existing_e4m3, require, sha


def check(terminal, oracle_root, oracle_sha256, run_dir, runtime_log):
    terminal, oracle_root, run_dir, runtime_log = map(Path,
        (terminal, oracle_root, run_dir, runtime_log))
    receipt = json.loads(terminal.read_text())
    require(receipt.get('returncode') == 0 and receipt.get('status') == 'runtime_exit_zero',
            'completed zero-exit runtime required')
    require(receipt['layers'] == list(range(36)), 'all 36 decoder layers required')
    require(Path(receipt['command'][3]).resolve() == run_dir.resolve(), 'executed output directory differs')
    oracle_path = oracle_root/'oracle.json'
    require(sha(oracle_path) == oracle_sha256, 'selected oracle changed')
    oracle = json.loads(oracle_path.read_text())
    require(oracle.get('status') == 'ISA_golden_only' and oracle.get('tp') == 4
            and oracle.get('groups') == 6144 and oracle.get('kv_format') == 'fp8'
            and oracle.get('layers') == 36 and oracle.get('head') is True,
            'full TP4 oracle including head required')
    frame = oracle['per_position'][str(receipt['position'])]
    require(frame['token'] == receipt['token'], 'oracle input token differs')
    text = runtime_log.read_text()
    require(re.findall(r'QWEN_ROM_COMBINED PASS stages=(\d+)\b', text) == ['38'],
            'actual E plus 36 layers plus head completion required')
    require(re.findall(r'HEAD_RANK head die(\d) next_token=(\d+) next_val=([0-9a-fA-F]{8})', text)
            == [(str(r), str(frame['head']['next_token']), frame['head']['next_logit_bits']) for r in range(4)],
            'actual all-rank head token/logit differs')
    position_dir = oracle_root/('P'+str(receipt['position']))
    x_checks, kv_checks, head_checks, pins = {}, {}, {}, {}
    convert = existing_e4m3()
    for stage in ['E']+[f'L{l}' for l in range(36)]:
        for rank in range(4):
            key = f'{stage}_die{rank}'
            expected = position_dir/('x_preload.hex' if stage == 'E' else f'L{int(stage[1:]):02d}_die{rank}_x.hex')
            digest = frame['x_preload_sha256'] if stage == 'E' else frame['layer_x_sha256'][key]
            require(sha(expected) == digest, 'cached X identity differs: '+key)
            pins[str(expected.resolve())] = digest
            x_checks[key] = compare_hex(run_dir/(key+'_x.hex'), expected, embedding=stage == 'E')
            if stage != 'E':
                expected = position_dir/'kv_at_P'/(key+'.json')
                digest = frame['kv_at_P_sha256'][key]
                require(sha(expected) == digest, 'cached KV identity differs: '+key)
                pins[str(expected.resolve())] = digest
                kv_checks[key] = compare_kv(run_dir/(key+'_kvP.hex'), expected, convert)
    for rank in range(4):
        key = f'head_die{rank}'
        result = run_dir/(key+'_result.hex')
        words = result.read_text().split()
        require(len(words) == 2 and all(re.fullmatch(r'[0-9a-fA-F]{8}', w) for w in words),
                'malformed actual head result')
        expected = position_dir/(key+'_xnorm.hex')
        digest = frame['head'][key]['xnorm_sha256']
        require(sha(expected) == digest, 'cached normalized head input changed')
        pins[str(expected.resolve())] = digest
        head_checks[key] = dict(token_matches=int(words[0],16) == frame['head']['next_token'],
            logit_matches=words[1].lower() == frame['head']['next_logit_bits'].lower(),
            result_sha256=sha(result), normalized_input=compare_hex(run_dir/(key+'_xnorm.hex'), expected))
    require(sha(oracle_path) == oracle_sha256 and all(sha(p) == digest for p,digest in pins.items()),
            'cached inputs changed during comparison')
    good = (all(v['mismatches'] == 0 for v in x_checks.values())
            and all(v['k_mismatches'] == 0 and v['v_mismatches'] == 0 for v in kv_checks.values())
            and all(v['token_matches'] and v['logit_matches'] and v['normalized_input']['mismatches'] == 0
                    for v in head_checks.values()))
    return dict(schema='opentallas.qwen-rom-full-token-readback.v1', status='pass' if good else 'fail',
        scope='One complete E/L0..L35/head token, all four ranks, cached X/KV/head exactness; no rate or physical closure claim',
        position=receipt['position'], token=receipt['token'], layer_x_checks=x_checks,
        token_kv_writeback_checks=kv_checks, head_checks=head_checks, golden_sha256=pins,
        input_sha256={str(p.resolve()):sha(p) for p in (terminal,oracle_path,runtime_log)},
        checker_sha256=sha(__file__))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('terminal','oracle-root','run-dir','runtime-log','output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--oracle-sha256', required=True)
    args = parser.parse_args()
    try:
        record = check(args.terminal,args.oracle_root,args.oracle_sha256,args.run_dir,args.runtime_log)
    except (ValueError,KeyError,OSError,TypeError,IndexError) as error:
        record = dict(status='fail', error=str(error))
    with args.output.open('x') as stream:
        stream.write(json.dumps(record,indent=2)+'\n')
    return 0 if record['status'] == 'pass' else 2


if __name__ == '__main__':
    raise SystemExit(main())
