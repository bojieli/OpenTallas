#!/usr/bin/env python3
"""Remove legacy input hold waivers in a COPIED SDC for actual-model diagnostics.

The output is NOT a CLOSED leaf proof. No original source file is overwritten.
Clocks and reset exceptions are retained explicitly. All changed ports and the
exact original exception statement are recorded for audit. The physical ODB,
SPEF, and libraries must remain those of the original routed design.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--record', required=True, type=Path)
    p.add_argument('--retain', nargs='+', default=['ckv[0]', 'rst[0]', 'rsv[0]'])
    a = p.parse_args()
    if a.source.resolve() == a.out.resolve():
        p.error('diagnostic output must differ from the source')
    s = a.source.read_text()
    matches = list(re.finditer(r'^set_false_path -hold\\\n.*?(?=\nset_false_path|\n#)', s, re.S | re.M))
    if len(matches) != 1:
        raise ValueError('expected exactly one legacy port-list input hold exception')
    m = matches[0]
    pins = re.findall(r'get_ports \{([^}]+)\}', m[0])
    if not pins or len(pins) != len(set(pins)) or not set(a.retain) <= set(pins):
        raise ValueError('legacy exception needs an explicit unique actual port list and all retained ports')
    removed = [pin for pin in pins if pin not in a.retain]
    if not removed:
        raise ValueError('no normal data hold exceptions to remove')
    replacement = 'set_false_path -hold -from [get_ports {' + ' '.join(a.retain) + '}]'
    diag = s[:m.start()] + replacement + s[m.end():]
    a.out.write_text(diag)
    a.record.write_text(json.dumps({
        'scope': 'UNQUALIFIED diagnostic stricter constraints; actual unchanged routed geometry/libs/SPEF; no CLOSED assertion',
        'original_sdc_sha256': hashlib.sha256(a.source.read_bytes()).hexdigest(),
        'diagnostic_sdc_sha256': hashlib.sha256(diag.encode()).hexdigest(),
        'removed_normal_data_input_hold_exceptions': removed,
        'retained_clock_reset_hold_exceptions': a.retain,
        'removed_original_statement': m[0],
    }, indent=2) + '\n')
    print(f'removed {len(removed)} normal input hold exceptions; retained {a.retain}')


if __name__ == '__main__':
    main()
