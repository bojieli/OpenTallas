"""Project the existing proof-backed dead-input contract from exact HR pre-netlists."""
import hashlib
import json
from pathlib import Path
import re

FP_PASS = ['post', 'rc=0', 'mut', 'rc=1', 'emitted_v', 'rc=0']


def exact_dead_bits(pre, module, candidates):
    m = pre['modules'][module]
    connected = {b for c in m['cells'].values() for bits in c['connections'].values() for b in bits}
    outputs = {b for p in m['ports'].values() if p['direction'] != 'input' for b in p['bits']}
    result = []
    for name in sorted(set(candidates)):
        match = re.fullmatch(r'(.+)\[(\d+)\]', name)
        if not match:
            continue
        p = m['ports'].get(match[1])
        index = int(match[2])
        if p is None or p['direction'] != 'input':
            continue
        offset = int(p.get('offset', 0))
        position = index - offset
        if not 0 <= position < len(p['bits']):
            continue
        if p.get('upto', 0):
            position = len(p['bits']) - 1 - position
        bit = p['bits'][position]
        if isinstance(bit, int) and bit not in connected and bit not in outputs:
            result.append(name)
    return result


def emit(fp, module, kit, candidates):
    fp, kit = Path(fp), Path(kit)
    # Older published roots may omit the pre-netlist. No declaration without it.
    if not candidates or not (fp / 'pre.json').is_file():
        return []
    rc = (fp / 'eq_rc.txt').read_text().split()
    if rc != FP_PASS:
        raise ValueError('HR dead-input contract needs complete post/mutant/emitted proof')
    raw = (fp / 'pre.json').read_bytes()
    bits = exact_dead_bits(json.loads(raw), module, candidates)
    if not bits:
        return []
    receipt = dict(verdict='PASS', module=module, bits=bits, eq_rc=rc,
                   pre_sha256=hashlib.sha256(raw).hexdigest(),
                   method='Exact input bits have no cell connection or output alias in the original flattened pre-netlist; full transform and emitted-RTL equivalence passed. Mapped guard independently requires no load or driver.')
    (kit / 'hr_dead_inputs_proof.json').write_text(json.dumps(receipt, indent=1) + '\n')
    (kit / 'dead_inputs.json').write_text(json.dumps(dict(schema='opentallas.kit_dead_inputs.v1', bits=bits,
        proof=dict(verdict='PASS', method=receipt['method'], receipt='hr_dead_inputs_proof.json')), indent=1) + '\n')
    return bits
