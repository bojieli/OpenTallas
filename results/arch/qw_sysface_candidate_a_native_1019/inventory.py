#!/usr/bin/env python3
"""Finite source/netlist inventory only. Never invokes an EDA executable."""
import gzip, hashlib, json, pathlib, re
P = pathlib.Path(__file__).resolve().parent
load = lambda n: json.loads(gzip.decompress((P/'input'/n).read_bytes()))
m = load('original.json.gz')['modules']['qfd_sys_face']
s = gzip.decompress((P/'input/postcts.v.gz').read_bytes()).decode()
instances = {}
for match in re.finditer(r'^\s*(\w+)\s+(\\\S+|\w+)\s*\((.*?)\);', s, re.M | re.S):
    master, name, body = match.groups()
    if master == 'module':
        continue
    ports = {pin: net.strip().lstrip('\\') for pin, net in re.findall(r'\.(\w+)\(([^()]*)\)', body)}
    instances[name.lstrip('\\')] = {'master': master, 'ports': ports}
inputs = ['receive_slot','rx_v','rx_record','program_begin_v','program_ready','installed_fusedcap','program_epoch','program_digest','head_context_v','head_stage','head_token','head_position','native_active']
outputs = ['accepted_v','host_epoch_valid','host_epoch','host_tag','host_gen','host_fusedcap','host_image_epoch','host_image_digest','fault']
result = {'scope': 'Frozen parent direct connectivity inventory; not yet a separated external load model', 'inputs': [], 'outputs': []}
aliases = {}
for name, port in m['ports'].items():
    for index, bit in enumerate(port['bits']):
        aliases.setdefault(bit, []).extend([f'face_{name}[{index}]', f'core/{name}[{index}]'])
source_parent = gzip.decompress((P/'input/source_parent.sv.gz').read_bytes()).decode()
for direction, names in [('inputs', inputs), ('outputs', outputs)]:
    for name in names:
        bits = m['netnames']['u_record.u_context.'+name]['bits']
        for index, bit in enumerate(bits):
            net = f'core/n{bit}' if isinstance(bit, int) else str(bit)
            candidates = [net] + aliases.get(bit, [])
            # face aliases are only considered where the generated original wrapper
            # actually binds that port to face_<port>; no newer parent is assumed.
            candidates = [n for n in candidates if not n.startswith('face_') or re.search(r'\.\w+\('+re.escape(n.split('[')[0])+r'\)', source_parent)]
            connections = [{'instance': inst, 'master': item['master'], 'pin': pin, 'net': value}
                           for inst, item in instances.items() for pin, value in item['ports'].items() if value in candidates]
            result[direction].append({'port': name, 'index': index, 'generic_bit': bit, 'native_net_candidates': candidates, 'direct_connections': connections,
                                      'external_capacitance': None, 'external_input_drive': None,
                                      'hold': 'Separate component-internal feedback from external parent endpoints, then use actual corner pin capacitances; no unit-cap fallback'})
assert len(result['inputs']) == 677
assert len(result['outputs']) == 161
result['unique_output_bits'] = len({x['generic_bit'] for x in result['outputs']})
result['parsed_native_instances'] = len(instances)
result['sha256'] = {str(f.relative_to(P)): hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((P/'input').iterdir())}
(P/'boundary_inventory.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({'input_bits': 677, 'output_bits': 161, 'unique_output_bits': result['unique_output_bits'], 'native_instances': len(instances), 'external_load_status': 'HOLD; direct endpoints only'}))
