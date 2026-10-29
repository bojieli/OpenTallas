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
        # Once every PG terminal is connected, write_def replaces its complete
        # enumerated endpoint list by (* VDD)/(* VSS). Compare actual metal;
        # the native master-terminal census in the repair log checks bindings.
        supply_pin = r'\(\s+(\S+)\s+([A-Za-z_]\w*)\s+\)'
        log = (root / 'pg_repair2.log').read_text()
        assert 'pg_terms=408482 open=0' in log
        assert 'open_before=216 repaired_instances=108' in log
        proof['supply_terms'] = 408482
        proof['repaired_supply_terms'] = 216
        chunks = [' '.join(re.sub(supply_pin, '', x).split()) for x in chunks]
    assert chunks[0] == chunks[1], f'DEF {section} changed'
    proof[section + '_sha256'] = hashlib.sha256(chunks[0].encode()).hexdigest()
proof['verdict'] = 'PG_ONLY_REPAIR'
(root / 'pg_only_receipt.json').write_text(json.dumps(proof, indent=2) + '\n')
print(json.dumps(proof))
