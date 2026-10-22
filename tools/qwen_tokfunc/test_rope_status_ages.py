#!/usr/bin/env python3
"""Pure opt-in STATUS input checks; every case stops before generation."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    script = Path(__file__).with_name('compile_rope_pair.py')
    ages = ('kv_descriptor_to_kvn_expected_edges', 'status225_transport')
    paths = ('kv_descriptor_to_kvn_expected_path', 'status225_transport_path')
    base = dict.fromkeys(ages, 0)
    base.update(dict.fromkeys(paths, 'TEST_ONLY_NEVER_GENERATED'))
    cases = []
    for key in (*ages, *paths):
        for value in ('MISSING', None, -1 if key in ages else 'UNKNOWN'):
            row = dict(base)
            if value == 'MISSING':
                del row[key]
            else:
                row[key] = value
            expected = 'unknown required coherent STATUS age:' if key in ages else 'unknown required coherent STATUS GEN path:'
            cases.append((key, value, row, True, expected))
    # Both controls still refuse missing core GEN facts. The first proves that
    # STATUS requirements are opt-in; the second reaches the independent gate.
    cases += [('legacy_mode', None, {}, False, 'unknown required source/GEN fact: compute_source'),
              ('independent_core_gate', None, base, True, 'unknown required source/GEN fact: compute_source')]
    results = []
    for key, value, row, enabled, expected in cases:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            data = root / 'synthetic.json'
            data.write_text(json.dumps(row))
            out = root / 'must_not_exist'
            command = [sys.executable, str(script), '--source-dir', str(root),
                       '--ages', str(data), '--token-path', str(root / 'absent_token'),
                       '--link-handoff', str(root / 'absent_handoff'), '--out', str(out)]
            if enabled:
                command.append('--status-observers')
            run = subprocess.run(command, capture_output=True, text=True)
            assert run.returncode != 0 and expected in run.stderr and not out.exists(), run
            results.append(dict(field=key, value=value, status_observers=enabled,
                                refused=True, output_created=False))
    print(json.dumps(dict(verdict='PASS', scope='pure input refusals; no GEN/image/simulation',
                         cases=results), indent=1))


if __name__ == '__main__':
    main()
