"""Project the existing proof-backed dead-input contract from exact HR pre-netlists."""
import hashlib
import json
from pathlib import Path
import re

FP_PASS = ['post', 'rc=0', 'mut', 'rc=1', 'emitted_v', 'rc=0']
FP_PASS_TEXT = 'equiv_make/equiv_simple -seq 2/equiv_induct/equiv_status -assert: post PASS, emitted .v PASS, mutant FAIL (caught)'
NAMED_SCHEMA = 'opentallas.hr_named_proof_legs.v1'
NAMED_LEGS = ('post', 'emitted_v')
NAMED_LIMIT = 'state outside zero init is not proved'
FP_TAIL = ['mut', 'rc=1', 'emitted_v', 'rc=0']   # the legs that prove the kit RTL itself, plus the mutant control


def stopped_post_only(rc):
    """Post-JSON leg stopped with no result: pending, never accepted."""
    return rc[:2] == ['post', 'stopped'] and rc[-4:] == FP_TAIL


def rc_tokens(rc):
    """eq_rc.txt words -> {leg: first word after its name}."""
    return {rc[i]: rc[i + 1] for i in range(len(rc) - 1) if rc[i] in ('post', 'mut', 'emitted_v')}


def named_legs(fp, module=None):
    """FP/named_legs.json (hr_named_leg.py): legs returned by another engine under their own name, {} when none.
    A record that does not match the proof dir refuses: it never falls back to anything."""
    f = Path(fp) / 'named_legs.json'
    if not f.is_file():
        return {}
    doc = json.loads(f.read_text())
    if doc.get('schema') != NAMED_SCHEMA or (module and doc.get('module') != module):
        raise ValueError(f'{f}: wrong schema or module')
    for name, leg in doc['legs'].items():
        if name not in NAMED_LEGS or leg.get('limit') != NAMED_LIMIT or leg.get('initial_state') != 'zero' \
                or leg.get('srams') != 'ports' or not leg.get('engine') or leg.get('result') != 'UNSATISFIABLE':
            raise ValueError(f'{f}: leg {name} does not carry engine, zero init, SRAMs as ports, limit and result')
        mut = leg.get('mutant') or {}
        if mut.get('result') != 'NOT_EQUIVALENT' or not isinstance(mut.get('frame'), int):
            raise ValueError(f'{f}: leg {name} has no caught mutant')
        for got, want in ((leg['gold'], leg['gold_sha256']), (leg['gate'], leg['gate_sha256']),
                          (mut['gate'], mut['gate_sha256'])):
            if hashlib.sha256((Path(fp) / got).read_bytes()).hexdigest() != want:
                raise ValueError(f'{f}: leg {name}: {got} is not the netlist the leg proved')
    return doc['legs']


def proof_state(fp, module=None):
    """'pass' (all yosys legs), 'named' (a stopped leg returned under its own name), 'pending' (a leg stopped or not
    returned, none failed) or 'fail'.  A leg that returned the wrong answer is never rescued by a named leg."""
    rc = (Path(fp) / 'eq_rc.txt').read_text().split()
    if rc == FP_PASS:
        return 'pass'
    tok, named = rc_tokens(rc), named_legs(fp, module)
    no_result = ('stopped', 'pending')
    if any(tok.get(k) not in ('rc=0',) + no_result for k in NAMED_LEGS) or tok.get('mut') not in ('rc=1',) + no_result:
        return 'fail'
    open_legs = [k for k in NAMED_LEGS if tok[k] != 'rc=0' and k not in named]
    # a mutant control that has not returned is covered only by the named legs' own mutants
    if tok['mut'] != 'rc=1' and not named:
        open_legs.append('mut')
    return 'pending' if open_legs else 'named'


def proof_text(fp, module=None):
    """the kit-side statement of a returned proof."""
    if proof_state(fp, module) == 'pass':
        return FP_PASS_TEXT
    parts = [f"{k}: {v['engine']}, flops zero init, SRAMs as ports, {v['result']}, own mutant caught at frame "
             f"{v['mutant']['frame']}; limit: {v['limit']}" for k, v in sorted(named_legs(fp, module).items())]
    return 'eq_rc.txt ' + ' '.join((Path(fp) / 'eq_rc.txt').read_text().split()) + '; named legs: ' + '; '.join(parts)


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
    state = proof_state(fp, module)
    if state == 'pending' and stopped_post_only(rc):
        # COORD 11-04: a stopped leg is no proof. Recorded as pending, nothing is declared dead.
        (kit / 'hr_dead_inputs_proof.json').write_text(json.dumps(dict(
            verdict='PENDING', module=module, candidates=candidates, eq_rc=rc,
            reason='post-JSON leg stopped with no result; no dead input declared until it returns'), indent=1) + '\n')
        return []
    if state not in ('pass', 'named'):
        raise ValueError('HR dead-input contract needs complete post/mutant/emitted proof')
    raw = (fp / 'pre.json').read_bytes()
    bits = exact_dead_bits(json.loads(raw), module, candidates)
    if not bits:
        return []
    method = 'Exact input bits have no cell connection or output alias in the original flattened pre-netlist; '
    method += ('full transform and emitted-RTL equivalence passed.' if state == 'pass' else proof_text(fp, module) + '.')
    method += ' Mapped guard independently requires no load or driver.'
    receipt = dict(verdict='PASS', module=module, bits=bits, eq_rc=rc,
                   pre_sha256=hashlib.sha256(raw).hexdigest(), method=method)
    if state == 'named':
        receipt['named_legs'] = named_legs(fp, module)
    (kit / 'hr_dead_inputs_proof.json').write_text(json.dumps(receipt, indent=1) + '\n')
    (kit / 'dead_inputs.json').write_text(json.dumps(dict(schema='opentallas.kit_dead_inputs.v1', bits=bits,
        proof=dict(verdict='PASS', method=receipt['method'], receipt='hr_dead_inputs_proof.json')), indent=1) + '\n')
    return bits
