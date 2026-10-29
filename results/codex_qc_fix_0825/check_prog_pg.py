"""Refuse a PG repair that changes cells, signal connectivity or routed geometry."""
import hashlib
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parent
proof = {}
for kind in ('cells', 'signal'):
    a, b = [(root / f'{x}.{kind}.tsv').read_bytes() for x in ('before', 'after')]
    assert a == b, f'{kind} changed'
    proof[kind + '_sha256'] = hashlib.sha256(a).hexdigest()
defs = [(root / f'{x}.def').read_text() for x in ('before', 'after')]
for section in ('COMPONENTS', 'NETS', 'SPECIALNETS'):
    chunks = [re.search(rf'(?m)^{section} \d+ ;\n.*?^END {section}\s*$', s, re.S | re.M).group() for s in defs]
    if section == 'SPECIALNETS':
        # global_connect reorders the supply-terminal list. Compare actual metal
        # separately and require exactly the known 216 missing connections added.
        supply_pin = r'\(\s+(\S+)\s+([A-Za-z_]\w*)\s+\)'
        endpoints = [set(re.findall(supply_pin, x)) for x in chunks]
        assert not endpoints[0] - endpoints[1], 'Supply endpoints removed'
        assert len(endpoints[1] - endpoints[0]) == 216, 'Unexpected supply additions'
        proof['added_supply_endpoints'] = 216
        chunks = [' '.join(re.sub(supply_pin, '', x).split()) for x in chunks]
    assert chunks[0] == chunks[1], f'DEF {section} changed'
    proof[section + '_sha256'] = hashlib.sha256(chunks[0].encode()).hexdigest()
proof['verdict'] = 'PG_ONLY_REPAIR'
(root / 'pg_only_receipt.json').write_text(json.dumps(proof, indent=2) + '\n')
print(json.dumps(proof))
