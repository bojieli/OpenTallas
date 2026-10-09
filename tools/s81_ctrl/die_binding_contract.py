"""Native S81 control-plane binding and pre-build admission; never supplies tieoffs."""
import argparse
import ast
import hashlib
import json
import re
from pathlib import Path

ENGINES = ('fld', 'su', 'hc', 'coll', 'svc', 'sel', 'col', 'hop', 'head', 'emb', 'eng', 'spare')


def _number(expr):
    node = ast.parse(expr, mode='eval').body
    def calc(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, int):
            return n.value
        if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult)):
            a, b = calc(n.left), calc(n.right)
            return a+b if isinstance(n.op, ast.Add) else a-b if isinstance(n.op, ast.Sub) else a*b
        raise ValueError('unsupported port width expression')
    return calc(node)


def shell_contract(root, role):
    suffix = {'layer': '', 'source': '_src', 'head': '_h'}[role]
    rel = 'physical/s81_ctrl/rtl/dsfd_sp_ctrl' + suffix + '.sv'
    src = (Path(root) / rel).read_text()
    header = re.sub(r'//[^\n]*', '', src).split(');', 1)[0]
    ports = {}
    for d, width, name in re.findall(r'\b(input|output)\s+(?:wire|reg)\s*(?:\[([^\]]+)\])?\s*(\w+)', header):
        bits = 1 if not width else _number(width.split(':')[0]) - _number(width.split(':')[1]) + 1
        ports[name] = dict(direction=d, bits=bits, endpoint=None)
    if len(ports) != 45:
        raise ValueError('shell port parser coverage changed: %d' % len(ports))
    return dict(schema='opentallas.s81.ctrl-native-binding.v1', role=role, shell=rel,
                shell_sha256=hashlib.sha256(src.encode()).hexdigest(), ports=ports,
                qualification='UNBOUND', engines={}, vm_read_cycles=None,
                # IDs must be implemented in the pinned shell, not merely configured in a record.
                identity={k: int(v) for k, v in re.findall(r'\.(MY_ID|SRC_LO|SRC_HI)\((\d+)\)', src)},
                model=dict(area_mm2_nominal=0.15, clock_ghz=1.2, program_bits=128*28,
                           cmd_bits_each=85, done_bits_each=9, engine_queue_bits=12*8*84,
                           vm_write_bits=527, vm_read_request_bits=15, vm_read_response_bits=512,
                           message_data_bits_each=513, message_valid_ready_bits_each=2,
                           stage_handoff_extra_cycles=3, ar_stage_handoffs=121,
                           ar_extra_cycles=363, head_stop_extra_cycles=1 if role == 'head' else 0,
                           physical_closure='PENDING', endpoint_last_segment_um_max=100))


def validate_manifest(path, root, role):
    data = json.loads(Path(path).read_text())
    expected = shell_contract(root, role)
    for k in ('schema', 'role', 'shell', 'shell_sha256', 'identity'):
        if data.get(k) != expected[k]:
            raise ValueError('ctrl binding disagrees with pinned shell: ' + k)
    if set(data['ports']) != set(expected['ports']):
        raise ValueError('ctrl binding omits or invents native shell ports')
    for name, spec in data['ports'].items():
        for k in ('bits', 'direction'):
            if spec.get(k) != expected['ports'][name][k]:
                raise ValueError('ctrl port width/direction mismatch: ' + name)
        if name in ('ck', 'rs'):
            continue  # implemented by generator streaming clock/reset trees
        endpoint = spec.get('endpoint')
        if not isinstance(endpoint, list) or len(endpoint) != 2 or not all(isinstance(x, str) and x for x in endpoint):
            raise ValueError('ctrl port has no native endpoint: ' + name)
        if any(x.lower() in ('tieoff', 'constant', 'unbound') for x in endpoint):
            raise ValueError('ctrl functional tieoff forbidden: ' + name)
    if data.get('vm_read_cycles') != 1:
        raise ValueError('native controller requires one-cycle VM response; implement and price latency adapter')
    for engine in ENGINES:
        spec = data.get('engines', {}).get(engine, {})
        if spec.get('queue_depth') != 8 or spec.get('credit_return') != 'done':
            raise ValueError('ctrl engine lacks real queue8/done-credit adapter: ' + engine)
        if spec.get('clock_domain') not in ('stream_1p2', 'serial_0p9'):
            raise ValueError('unknown engine clock: ' + engine)
        if spec['clock_domain'] == 'serial_0p9' and not spec.get('cdc_rtl'):
            raise ValueError('serial engine lacks real descriptor/done CDC: ' + engine)
        rel = spec.get('adapter_rtl')
        if not rel or not (Path(root) / rel).is_file():
            raise ValueError('missing real engine adapter RTL: ' + engine)
        if spec.get('adapter_sha256') != hashlib.sha256((Path(root)/rel).read_bytes()).hexdigest():
            raise ValueError('unpinned engine adapter RTL: ' + engine)
    if data.get('qualification') != 'NATIVE_BINDING_READY':
        raise ValueError('ctrl binding is not eligible for implementation')
    return data


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument('--role', choices=['layer', 'source', 'head'], default='layer')
    ap.add_argument('--validate', type=Path)
    a = ap.parse_args()
    print(json.dumps(validate_manifest(a.validate, a.root, a.role) if a.validate else shell_contract(a.root, a.role), indent=2))


if __name__ == '__main__':
    main()
