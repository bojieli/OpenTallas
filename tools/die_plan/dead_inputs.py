"""Fail-closed declarations for leaf inputs proved to have no fanout after Yosys opt.

A declaration is exact in partition type, RTL module, all evaluated parameters,
source bytes, port and bit. It never permits a live input or a generic pin regex.
"""
import hashlib
import json
from pathlib import Path


def dead_bits(module, port):
    """Conservative: blackbox child inputs count as loads; output aliases count as live."""
    p = module['ports'][port]
    if p['direction'] != 'input':
        raise ValueError('dead declaration is not an input')
    live = {b for p in module['ports'].values() if p['direction'] != 'input' for b in p['bits']}
    for cell in module.get('cells', {}).values():
        for pn, bits in cell['connections'].items():
            if cell.get('port_directions', {}).get(pn) != 'output':
                live.update(bits)
    return {i for i, b in enumerate(p['bits']) if isinstance(b, int) and b not in live}


def module_hash(path, module):
    import re
    text = Path(path).read_text()
    m = re.search(r'^module\s+' + re.escape(module) + r'\b.*?^endmodule', text, re.M | re.S)
    if not m:
        raise ValueError('proof source no longer defines ' + module)
    return hashlib.sha256(m.group().encode()).hexdigest()


class ProvenDead:
    def __init__(self, manifest, repo):
        self.rows = []
        repo = Path(repo).resolve()
        for rel in manifest.get('dead_input_proofs', []):
            path = (repo / rel).resolve()
            if not path.is_relative_to(repo) or Path(rel).is_absolute():
                raise ValueError('dead-input proof must be repository-relative')
            proof = json.loads(path.read_text())
            if proof.get('schema') != 'opentallas.dead_inputs.v1' or proof.get('verdict') != 'PASS':
                raise ValueError('invalid dead-input proof ' + rel)
            for row in proof['declarations']:
                source = (repo / row['source']).resolve()
                if not source.is_relative_to(repo) or Path(row['source']).is_absolute():
                    raise ValueError('dead-input source must be repository-relative')
                if module_hash(source, row['module']) != row['module_sha256']:
                    raise ValueError('stale dead-input source ' + row['source'])
                if row.get('method') != 'yosys.proc.opt.no_fanout' or row.get('remaining_loads') != 0:
                    raise ValueError('missing optimized no-fanout proof')
                self.rows.append(row)

    def allows(self, partition_type, cell, port, bit, defaults=()):
        params = dict(defaults)
        params.update(cell.params)
        for row in self.rows:
            if (row['partition_type'], row['module']) != (partition_type, cell.module):
                continue
            if params != row['parameters']:
                continue
            if any(lo <= bit <= hi for lo, hi in row['ports'].get(port, [])):
                return True
        return False
