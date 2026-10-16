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


# ---------------------------------------------------------------------------------------------------------------
# v2 (s81-ctl-1011, 2026-10-11): engine-split shell dsfd_sp_ctrl_e (hop_tx retired) + per-engine slab endpoints
# (ot_s81_slab_ep inside each slab master).  Engine status: BOUND (slab master with the endpoint, real start / done),
# PENDING (owner named; the die gate fails while its ports are unbound), ROLE_ABSENT (no stage program of the role
# routes an op to the engine: checked against the compiled stage programs).
ENGINE_INDEX = {e: i for i, e in enumerate(ENGINES)}
V2_SHELL = {'layer': 'physical/s81_ctrl/rtl/dsfd_sp_ctrl_e.sv'}
ROLE_STAGES = {'layer': lambda s: s.startswith('S') and s not in ('S000', 'S058')}


def shell_ports_v2(root, role):
    src = (Path(root) / V2_SHELL[role]).read_text()
    header = re.sub(r'//[^\n]*', '', src).split(');', 1)[0]
    ports = {}
    for d, width, names in re.findall(r'\b(input|output)\s+(?:wire|reg)\s*(?:\[([^\]]+)\])?\s*([\w\s,]+?)(?=,\s*(?:input|output)\b|$)',
                                      header + ',', re.S):
        bits = 1 if not width else _number(width.split(':')[0]) - _number(width.split(':')[1]) + 1
        for n in re.findall(r'\w+', names):
            ports[n] = dict(direction=d, bits=bits)
    return src, ports


def program_ports(root, role, programs='results/rtl/s81_ctrl_20261008/programs'):
    used = {}
    for f in sorted((Path(root) / programs).glob('S*.json')):
        if not ROLE_STAGES[role](f.stem):
            continue
        for o in json.loads(f.read_text())['ops']:
            used.setdefault(o['eng'], set()).add(f.stem)
    return used


def validate_manifest_v2(path, root, role):
    """returns the manifest with 'qualification' recomputed; raises on a malformed / unpinned binding"""
    data = json.loads(Path(path).read_text())
    src, ports = shell_ports_v2(root, role)
    if data.get('schema') != 'opentallas.s81.ctrl-native-binding.v2' or data.get('role') != role:
        raise ValueError('ctrl binding v2: schema / role')
    if data.get('shell') != V2_SHELL[role] or data.get('shell_sha256') != hashlib.sha256(src.encode()).hexdigest():
        raise ValueError('ctrl binding v2 disagrees with the pinned shell')
    for k in ('adapter', 'endpoint'):
        rel = data[k + '_rtl']
        if data.get(k + '_sha256') != hashlib.sha256((Path(root) / rel).read_bytes()).hexdigest():
            raise ValueError('unpinned ' + k + ' RTL: ' + rel)
    eng_ports = {f'{p}{i}' for i in range(12) for p in 'cds'}
    other = set(ports) - eng_ports - {'ck', 'rs'}
    if set(data['ports']) != other:
        raise ValueError('ctrl binding v2 omits or invents shell ports: %s' % sorted(set(data['ports']) ^ other))
    for n, spec in data['ports'].items():
        ep = spec.get('endpoint')
        if not isinstance(ep, list) or len(ep) != 2 or any(str(x).lower() in ('tieoff', 'constant', 'unbound') for x in ep):
            raise ValueError('ctrl port has no native endpoint: ' + n)
    used = program_ports(root, role)
    if set(data['engines']) != set(ENGINES):
        raise ValueError('ctrl binding v2 must name all 12 engines')
    ready = True
    for e, spec in data['engines'].items():
        st = spec.get('status')
        if spec.get('index') != ENGINE_INDEX[e]:
            raise ValueError('engine index: ' + e)
        if st == 'BOUND':
            rel = spec.get('master_rtl')
            if not rel or not (Path(root) / rel).is_file() or not any(k in (Path(root) / rel).read_text() for k in ('ot_s81_slab_ep', 'ot_s81_done_word')):
                raise ValueError('BOUND engine without a slab master carrying ot_s81_slab_ep: ' + e)
            if spec.get('queue_depth') != 8 or spec.get('credit_return') != 'done':
                raise ValueError('engine lacks QD 8 / done credit: ' + e)
        elif st == 'ROLE_ABSENT':
            if e in used:
                raise ValueError('engine %s declared ROLE_ABSENT but %s route ops to it' % (e, sorted(used[e])[:3]))
        elif st == 'PENDING':
            if not spec.get('owner'):
                raise ValueError('PENDING engine without an owner: ' + e)
            ready = False
        else:
            raise ValueError('engine status: %s %s' % (e, st))
    data['qualification'] = 'NATIVE_BINDING_READY' if ready else 'PARTIAL'
    data['program_engines'] = {k: len(v) for k, v in sorted(used.items())}
    return data
