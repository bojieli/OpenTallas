#!/usr/bin/env python3
"""Fail-closed ROM operation coverage. Arithmetic matches never waive target RTL.

Program: JSON {ops:[...]} or an instruction .hex. Binding manifest must name
all required target components, exact elaborated instance paths, source pins,
per-op instruction digest, and real storage-to-operand/result-to-storage ports.
Only PHY/off-chip models and expected-only observers are permitted. This is an
operation/source gate, not a timing or numerical signoff.
"""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def operations(path):
    if path.suffix == '.json':
        obj = json.loads(path.read_text())
        ops = obj.get('ops', obj.get('program', []))
        if not isinstance(ops, list) or not ops:
            raise ValueError('emitted operation list absent')
        return [{'id': str(o.get('id', o.get('op_id', i))), 'opcode': str(o.get('eng', o.get('engine', o.get('opcode', 'unknown')))), 'instruction_sha256': digest(o)} for i, o in enumerate(ops)]
    words = []
    pc = 0
    for line in path.read_text().splitlines():
        for token in line.split('//')[0].split():
            if token.startswith('@'):
                pc = int(token[1:], 16)
                continue
            value = int(token, 16)
            words.append({'id': 'pc'+str(pc), 'opcode': 'unit'+str(value & 3), 'instruction_sha256': digest({'pc': pc, 'word': token.lower()})})
            pc += 1
    if not words:
        raise ValueError('instruction image empty')
    return words


class Target:
    def __init__(self, root, elaboration):
        path = root / elaboration['netlist']
        if sha(path) != elaboration['netlist_sha256']:
            raise ValueError('elaboration netlist digest differs')
        self.modules = json.loads(path.read_text())['modules']
        self.sources = elaboration['source_sha256']
        if not self.sources:
            raise ValueError('elaboration source pins absent')
        for name, pin in self.sources.items():
            if sha(root/name) != pin:
                raise ValueError('elaboration source differs: '+name)
        self.top = elaboration['top']
        self.instances = {}
        self.parent = {}
        self.visit(self.top, self.top, None, None)

    def canonical(self, bit):
        if bit not in self.parent:
            self.parent[bit] = bit
        if self.parent[bit] != bit:
            self.parent[bit] = self.canonical(self.parent[bit])
        return self.parent[bit]

    def union(self, a, b):
        self.parent[self.canonical(a)] = self.canonical(b)

    def bits(self, path, port):
        module = self.instances[path]
        return [self.canonical((path, b)) if isinstance(b, int) else b for b in module['ports'][port]['bits']]

    def visit(self, module_name, path, parent_path, connections):
        module = self.modules[module_name]
        self.instances[path] = module
        if connections is not None:
            for port, info in module['ports'].items():
                for inner, outer in zip(info['bits'], connections.get(port, [])):
                    if isinstance(inner, int):
                        self.union((path, inner), (parent_path, outer) if isinstance(outer, int) else outer)
        for cell_name, cell in module.get('cells', {}).items():
            if cell['type'] in self.modules:
                self.visit(cell['type'], path+'/'+cell_name, path, cell['connections'])

    def port(self, path, port, direction):
        module = self.instances[path]
        if module.get('attributes', {}).get('blackbox') in (1, '1', '00000000000000000000000000000001'):
            raise ValueError('blackbox target '+path)
        info = module['ports'][port]
        if info['direction'] != direction:
            raise ValueError('wrong target port direction '+path+'.'+port)
        bits = self.bits(path, port)
        if not bits or any(isinstance(bit, str) for bit in bits):
            raise ValueError('constant/open functional port '+path+'.'+port)
        src = module.get('attributes', {}).get('src', '')
        if not any(name in src for name in self.sources):
            raise ValueError('target source absent from source pins '+path)
        if not module.get('cells') and not module.get('memories'):
            raise ValueError('pin-only target '+path)
        return bits

    def storage(self, path):
        module = self.instances[path]
        if module.get('memories'):
            return True
        return any(c['type'].startswith('$mem') for c in module.get('cells', {}).values()) or any(self.storage(p) for p in self.instances if p.startswith(path+'/') and p.count('/') == path.count('/')+1)

    def seam(self, engine, port, memory, memory_port, role):
        direction, mdirection = ('input', 'output') if role == 'operand' else ('output', 'input')
        a = self.port(engine, port, direction)
        b = self.port(memory, memory_port, mdirection)
        if a != b:
            raise ValueError('operand/result is not bound to named real storage seam '+engine+'.'+port)
        if not self.storage(memory):
            raise ValueError('named memory has no actual storage '+memory)


def audit(root, program, manifest):
    errors = []
    ops = operations(program)
    if manifest.get('program_sha256') != sha(program):
        errors.append('PROGRAM_SOURCE_MISSING_OR_CHANGED')
    required = manifest.get('required_components', [])
    components = manifest.get('components', {})
    if not required:
        errors.append('TARGET_COMPONENT_REQUIREMENTS_MISSING')
    for name in sorted(set(required) | set(components)):
        c = components.get(name)
        if c is None:
            errors.append('REQUIRED_COMPONENT_ABSENT:'+name)
            continue
        if c.get('dut_output_override') or c.get('operand_provenance') in ('golden', 'oracle', 'reference'):
            errors.append('GOLDEN_SUPPLIES_DUT:'+name)
        if c.get('runtime_flow_control'):
            errors.append('RUNTIME_CREDIT_READY_WAIT_ON_CHIP:'+name)
        kind = c.get('implementation')
        allowed_model = c.get('role') in ('phy', 'off_chip_signal', 'off_chip_memory')
        expected_only = c.get('role') == 'expected_observer' and c.get('drives_dut') is False
        if kind not in ('rtl', 'macro') and not allowed_model and not expected_only:
            errors.append('MODELED_OR_ABSENT_ON_CHIP:'+name)
        if c.get('role') == 'expected_observer' and not expected_only:
            errors.append('EXPECTED_OBSERVER_DRIVES_DUT:'+name)
    target = None
    try:
        target = Target(root, manifest['elaboration'])
    except (KeyError, ValueError, OSError) as exc:
        errors.append('REAL_TARGET_ELABORATION_UNPROVEN:'+str(exc))
    if target is not None:
        classified = {c.get('instance') for c in components.values() if c.get('implementation') in ('rtl', 'macro')}
        for instance in sorted(set(target.instances) - classified):
            errors.append('TARGET_INSTANCE_NOT_IN_COMPONENT_INVENTORY:'+instance)
        for name, component in components.items():
            if component.get('implementation') in ('rtl', 'macro'):
                instance = component.get('instance')
                if instance not in target.instances:
                    errors.append('TARGET_COMPONENT_INSTANCE_ABSENT:'+name)
                else:
                    module = target.instances[instance]
                    src = module.get('attributes', {}).get('src', '')
                    if not any(f in src for f in target.sources):
                        errors.append('TARGET_COMPONENT_SOURCE_UNPINNED:'+name)
                    if module.get('attributes', {}).get('blackbox'):
                        errors.append('TARGET_COMPONENT_BLACKBOX:'+name)
    rows = []
    bindings = manifest.get('operations', {})
    for op in ops:
        reasons = []
        b = bindings.get(op['id'])
        if b is None:
            reasons.append('EMITTED_OPERATION_UNBOUND')
        else:
            if b.get('instruction_sha256') != op['instruction_sha256']:
                reasons.append('OPERATION_INSTRUCTION_SOURCE_DIFFERS')
            if b.get('opcode') != op['opcode']:
                reasons.append('OPCODE_DIFFERS')
            if b.get('dut_output_override') or b.get('output_provider') != 'target_rtl':
                reasons.append('REFERENCE_OR_BEHAVIORAL_COMPUTE_OUTPUT')
            ids = b.get('components', [])
            if not ids or any(c not in required for c in ids):
                reasons.append('OPERATION_COMPONENT_REQUIREMENTS_UNBOUND')
            if target is None:
                reasons.append('INSTANTIATED_TARGET_UNPROVEN')
            else:
                try:
                    engine = b['instance']
                    if engine not in target.instances:
                        raise ValueError('engine not instantiated in actual target')
                    operands, results = b['operands'], b['results']
                    if not operands or not results:
                        raise ValueError('real operand/result binding missing')
                    for role, ports in [('operand', operands), ('result', results)]:
                        for item in ports:
                            target.seam(engine, item['port'], item['memory_instance'], item['memory_port'], role)
                except (KeyError, ValueError) as exc:
                    reasons.append('REAL_OPERAND_MEMORY_PORT_BINDING_FAIL:'+str(exc))
        rows.append({**op, 'instance': b.get('instance') if b else None, 'native_operation_covered': not reasons, 'reasons': reasons})
    extra = set(bindings) - {o['id'] for o in ops}
    if extra:
        errors.append('BINDINGS_NOT_IN_EMITTED_PROGRAM:'+','.join(sorted(extra)))
    passed = not errors and all(row['native_operation_covered'] for row in rows)
    return {'schema': 'opentallas.native_operation_coverage.v1', 'scope': 'SOURCE_AND_OPERATION_COVERAGE_ONLY', 'program': str(program), 'program_sha256': sha(program), 'native_operation_coverage_pass': passed, 'native_qualified': False, 'native_qualified_reason': 'This gate is necessary; numerical, fixed-cycle schedule, complete target inventory and physical signoff remain independent requirements.', 'errors': errors, 'operations': rows, 'historical_arithmetic_verdict_preserved': True}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--program', type=Path, required=True)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    report = audit(a.root, a.program, json.loads(a.manifest.read_text()))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=2)+'\n')
    print(('PASS' if report['native_operation_coverage_pass'] else 'FAIL')+' native operation coverage: '+str(len(report['operations']))+' emitted operations, '+str(len(report['errors']))+' target defects')
    raise SystemExit(0 if report['native_operation_coverage_pass'] else 1)

if __name__ == '__main__':
    main()
