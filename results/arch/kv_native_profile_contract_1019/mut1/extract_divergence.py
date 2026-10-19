#!/usr/bin/env python3
"""Read preserved Yosys WaveJSON with its explicit name-escape adapter."""
import json
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parent

def read_wave(path):
    # Raw Yosys names contain unescaped Verilog backslashes. Preserve raw bytes.
    data = json.loads(path.read_text().replace(chr(92), chr(92) * 2))
    rows = {}
    for signal in data['signal']:
        values = iter(signal.get('data', []))
        previous = None
        decoded = []
        for code in signal['wave']:
            if code == '.':
                value = previous
            elif code == '=' or (code == '4' and 'data' in signal):
                value = next(values)
            else:
                value = code
            decoded.append(value)
            previous = value
        rows[signal['name']] = decoded
    return rows

def value(rows, expression, edge):
    match = re.fullmatch(r"(.+?)(?: \[(\d+)\])?", expression)
    name, bit = match.groups()
    name = name.lstrip(chr(92))
    bits = rows[name][edge]
    return bits[-1-int(bit)] if bit is not None else bits

rows = read_wave(ROOT / 'replay18_corrected_cex.json')
comparisons = json.loads((ROOT / 'replay_comparators.json').read_text())
failures = []
for comparison in comparisons:
    ys = rows[comparison['Y'].lstrip(chr(92))]
    for edge in range(7, len(ys)):
        if ys[edge] == '0':
            failures.append(dict(edge=edge, gold=value(rows, comparison['A'], edge),
                native=value(rows, comparison['B'], edge), comparison=comparison))
            break
failures.sort(key=lambda item: item['edge'])
result = dict(schema='opentallas.kv_pv_causal_divergence.v1',
    reset_low_edges=6, compared_from_edge=7, mutation='MUT1 arrival check +1',
    first_divergence_edge=failures[0]['edge'], differing_comparisons=len(failures),
    first_comparisons=[item for item in failures if item['edge']==failures[0]['edge']],
    all_first_differences=failures, qualification=False)
(ROOT / 'divergence.json').write_text(json.dumps(result, indent=1)+'\n')
print(result['first_divergence_edge'], result['differing_comparisons'])
