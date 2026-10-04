#!/usr/bin/env python3
"""Bind existing Claude full-36 inputs; writes a handoff only, never executes."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.runtime.qwen_combined.fulltoken_inputs import inspect


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cache', type=Path, required=True)
    ap.add_argument('--position', type=int, default=255)
    ap.add_argument('--token', type=int, default=6280)
    ap.add_argument('--oracle-sha256', required=True)
    ap.add_argument('--compiled-params', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    result = inspect(a.cache, oracle_sha256=a.oracle_sha256, compiled_params=a.compiled_params,
                     position=a.position, token=a.token)
    a.output.mkdir(parents=True, exist_ok=False)
    lines = [' '.join([r['name'], *r['directories'], str(r['kv_reset'])]) for r in result['stages']]
    (a.output/'stages_E_L0_L35_head.txt').write_text('\n'.join(lines)+'\n')
    # Reuse all verified existing ABI files through links; no new image or
    # history bytes, and no mutation of Claude's live per-layer job trees.
    history_dir = a.output/'kv_history'
    history_dir.mkdir()
    for name, binding in result['history'].items():
        (history_dir/(name+'.bin')).symlink_to(binding['raw'])
    result['history_directory'] = str(history_dir.resolve())
    if 'sha256' in result['embedding']:
        (a.output/'embedding_row.bin').symlink_to(result['embedding']['raw'])
    (a.output/'x_preload.hex').symlink_to(result['preload']['path'])
    (a.output/'inputs.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print(json.dumps({'output': str(a.output), 'stages': len(lines),
                      'cached_history_ranks': len(result['history']), 'launch_ready': False,
                      'gaps': result['gaps']}))


if __name__ == '__main__':
    raise SystemExit(main())
