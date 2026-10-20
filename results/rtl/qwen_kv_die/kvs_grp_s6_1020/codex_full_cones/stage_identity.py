"""Private source-pinned placed sequential-cone audit; run inside exact ORFS image."""
import collections
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

import odb
sys.path.insert(0, '/audit_tools')
import native_census as NC

OUT = Path('/out')
OUT.mkdir(exist_ok=True)
errors = []
EXCLUDED_PORTS = {'ck', 'hck'}
MEMORIES = {'ot_sram_1r1w_4x32_m1_p192_grp_rsp',
            'ot_sram_1r1w_128x256_m1_r2c2_p192_mir'}
odb_path = next(Path('/gate/routes/gate/work/orfs/results/asap7').glob('*/base/4_1_cts.odb'))
log = Path('/gate/cts.log').read_text()
libs = sorted(set(re.findall(r'^read_liberty (\S+)', log, re.M)))
roles, receipts = NC.liberty_roles(libs)
memory_receipts = []
for master in sorted(MEMORIES):
    p = Path('/src/physical/asap7_memory_macros') / master / (master + '.v')
    text = p.read_text()
    if not re.search(r'always\s*@\(posedge clk\)', text) or not re.search(r'if\s*\(r_ce_in\)\s*rd_out\s*<=', text):
        errors.append('synchronous SRAM read not established:' + master)
    memory_receipts.append({'master': master, 'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                            'boundary': 'posedge clk registered rd_out, verified in exact behavioural source'})
db = odb.dbDatabase.create()
odb.read_db(db, str(odb_path))
block = db.getChip().getBlock()
dbu = block.getDbUnitsPerMicron()
nets = {n.getId(): n for n in block.getNets()}
roots, endpoints = {}, collections.defaultdict(list)
sequential_instances = {}
combinational_records = []
constant_descriptors = {}
back, forward = {}, collections.defaultdict(list)
constant_nets = set()
ring_inputs, ring_outputs, rings = {}, {}, {}
counts = collections.Counter()

def coordinate(t):
    if hasattr(t, 'getInst'):
        inst = t.getInst()
        if inst.getMaster().isBlock():
            ok, x, y = t.getAvgXY()
            if not ok:
                raise RuntimeError('missing actual macro pin geometry:' + inst.getName() + '/' + t.getMTerm().getName())
            return [x / dbu, y / dbu]
        z = inst.getBBox()
        return [(z.xMin() + z.xMax()) / (2 * dbu), (z.yMin() + z.yMax()) / (2 * dbu)]
    boxes = [z for pin in t.getBPins() for z in pin.getBoxes()]
    if not boxes:
        raise RuntimeError('missing port geometry:' + t.getName())
    z = boxes[0]
    return [(z.xMin() + z.xMax()) / (2 * dbu), (z.yMin() + z.yMax()) / (2 * dbu)]

def descriptor(t, kind):
    p = coordinate(t)
    net_info = {'net': t.getNet().getName(), 'net_id': t.getNet().getId()}
    if not hasattr(t, 'getInst'):
        return dict(net_info, name='port:' + t.getName(), pin=t.getName(), kind=kind, xy_um=p)
    i = t.getInst()
    r = {'name': i.getName() + '/' + t.getMTerm().getName(), 'instance': i.getName(),
         'master': i.getMaster().getName(), 'pin': t.getMTerm().getName(), 'kind': kind, 'xy_um': p}
    r.update(net_info)
    if i.getMaster().isBlock():
        x, y = i.getOrigin()
        r.update(macro_origin_um=[x / dbu, y / dbu], orientation=str(i.getOrient()),
                 pin_offset_from_origin_um=[p[0] - x / dbu, p[1] - y / dbu])
    return r

def role_pin(role, master, name):
    p = role['pins'].get(name)
    if p is None:
        m = re.fullmatch(r'(.*)\[(-?\d+)\]', name)
        if m and int(m[2]) in role['bus_order'].get(m[1], []):
            p = role['pins'].get(m[1])
    if p is None:
        errors.append('missing Liberty pin:' + master + '/' + name)
    return p

for inst in block.getInsts():
    if not any(t.getSigType() not in ('POWER', 'GROUND') for t in inst.getITerms()):
        counts['power_ground_only_instances'] += 1
        continue
    master = inst.getMaster().getName()
    role = roles.get(master)
    if role is None:
        errors.append('missing Liberty cell:' + master)
        continue
    seq = role['sequential'] or master in MEMORIES
    if inst.getMaster().isBlock() and master not in MEMORIES:
        errors.append('unclassified macro:' + master)
    ins, outs = {}, []
    for t in inst.getITerms():
        if t.getSigType() in ('POWER', 'GROUND'):
            continue
        pr = role_pin(role, master, t.getMTerm().getName())
        if not pr:
            continue
        if pr['clock']:
            counts['actual_liberty_clock_pins_excluded'] += 1
            continue
        if t.getNet() is None:
            # Unused outputs are legal; an unconnected data/control input is not.
            if pr['direction'] == 'input':
                errors.append('unconnected input:' + inst.getName() + '/' + t.getMTerm().getName())
            continue
        if pr['direction'] == 'input':
            ins[t.getMTerm().getName()] = t
        elif pr['direction'] == 'output':
            outs.append((t, pr))
        elif pr['direction'] != 'internal':
            errors.append('unsupported direction:' + master + '/' + t.getMTerm().getName())
    if seq:
        sequential_instances[inst.getName()] = inst
        kind = 'synchronous_sram' if master in MEMORIES else 'sequential'
        for t in ins.values():
            endpoints[t.getNet().getId()].append(descriptor(t, kind + '_input'))
        for t, pr in outs:
            n = t.getNet().getId()
            if n in roots or n in back:
                errors.append('multiple drivers:' + nets[n].getName())
            roots[n] = descriptor(t, kind + '_output')
        counts[kind + '_instances'] += 1
    else:
        for t, pr in outs:
            n = t.getNet().getId()
            f = re.sub(r'[\s()]', '', pr['function'] or '')
            if f in ('0', '1', "1'b0", "1'b1"):
                constant_nets.add(n)
                constant_descriptors[n] = dict(descriptor(t, 'constant_function_driver'), function=f)
                counts['constant_function_drivers'] += 1
                continue
            if not f:
                errors.append('missing combinational function:' + master + '/' + t.getMTerm().getName())
                continue
            tokens = set(re.findall(r'[A-Za-z_][A-Za-z0-9_]*(?:\[-?\d+\])?', f))
            unknown = tokens - set(ins)
            if unknown:
                errors.append('unknown function inputs:' + master + '/' + str(sorted(unknown)))
                continue
            deps = sorted({ins[x].getNet().getId() for x in tokens})
            if not deps:
                errors.append('empty nonconstant cone:' + inst.getName())
            if n in back or n in roots:
                errors.append('multiple drivers:' + nets[n].getName())
            cell = inst.getName() + '/' + t.getMTerm().getName()
            back[n] = (deps, cell)
            combinational_records.append({'instance':inst.getName(),'master':master,'output_pin':t.getMTerm().getName(),'output_net':t.getNet().getName(),'function':pr['function'],'input_pins':[{'pin':x,'net':ins[x].getNet().getName()} for x in sorted(tokens)]})
            for dep in deps:
                forward[dep].append((n, cell))
        counts['combinational_instances'] += 1
    if master == 'ot_sram_1r1w_4x32_m1_p192_grp_rsp':
        name = inst.getName()
        x, y = inst.getOrigin()
        z = inst.getBBox()
        rings[name] = {'instance': name, 'master': master, 'origin_um': [x / dbu, y / dbu],
                       'placement_lower_left_um': [z.xMin()/dbu, z.yMin()/dbu],
                       'bbox_um': [z.xMin()/dbu, z.yMin()/dbu, z.xMax()/dbu, z.yMax()/dbu],
                       'orientation': str(inst.getOrient()),
                       'master_size_um': [inst.getMaster().getWidth() / dbu, inst.getMaster().getHeight() / dbu],
                       'input_pin_count': len(ins), 'output_pin_count': len(outs)}
        ring_inputs[name] = list(ins.values())
        ring_outputs[name] = [t for t, _ in outs]

for t in block.getBTerms():
    if not t.getNet() or t.getSigType() in ('POWER', 'GROUND'):
        continue
    if t.getName() in EXCLUDED_PORTS:
        counts['declared_clock_ports_excluded'] += 1
        continue
    n = t.getNet().getId()
    if t.getIoType() == 'INPUT':
        if n in roots or n in back:
            errors.append('multiple drivers:' + nets[n].getName())
        roots[n] = descriptor(t, 'input_port')
    elif t.getIoType() == 'OUTPUT':
        endpoints[n].append(descriptor(t, 'output_port'))
    else:
        errors.append('unsupported port direction:' + t.getName())

# Memoized complete graph traversal: stop only on sequential/SRAM/port boundaries.
root_cache, end_cache = {}, {}
def cone(n, direction, active=None):
    cache = root_cache if direction == 'backward' else end_cache
    if n in cache:
        return cache[n]
    active = set() if active is None else active
    if n in active:
        errors.append('combinational cycle:' + nets[n].getName())
        return {}
    if direction == 'backward' and n in roots:
        cache[n] = {roots[n]['name']: roots[n]}
        return cache[n]
    active.add(n)
    result = {} if direction == 'backward' else {e['name']: e for e in endpoints.get(n, [])}
    if direction == 'backward':
        if n in back:
            for dep in back[n][0]:
                result.update(cone(dep, direction, active))
        elif n not in constant_nets:
            # A declared clock port feeding DATA is excluded only by the explicit task instruction.
            ports = [t.getName() for t in nets[n].getBTerms()]
            if not (ports and set(ports) <= EXCLUDED_PORTS):
                errors.append('undriven cone net:' + nets[n].getName())
    else:
        for dep, cell in forward.get(n, []):
            result.update(cone(dep, direction, active))
    active.remove(n)
    cache[n] = result
    return result

def reach(a, b):
    return abs(a['xy_um'][0] - b['xy_um'][0]) + abs(a['xy_um'][1] - b['xy_um'][1])

# Read actual Liberty sequential equations, not guessed D/CLK/reset pin names.
seq_equations = {}
for lib in libs:
    if '_SEQ_' not in lib:
        continue
    raw = Path(lib).read_bytes()
    text = (gzip.decompress(raw) if lib.endswith('.gz') else raw).decode()
    text = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
    for typ, _, body in NC.groups(text):
        if typ != 'library':continue
        for typ, master, body in NC.groups(body):
            if typ != 'cell' or master not in roles or not roles[master]['sequential']:continue
            eqs=[]
            for kind, name, group in NC.groups(body):
                if kind not in ('ff','latch','ff_bank','latch_bank'):continue
                eqs.append(dict(kind=kind,state_variables=name,**{a:NC.attr(group,a) for a in
                    ('next_state','clocked_on','enable','clear','preset','clear_preset_var1','clear_preset_var2')}))
            if master in seq_equations and seq_equations[master] != eqs:
                errors.append('conflicting sequential equations:' + master)
            seq_equations[master]=eqs

def expr_pins(expression, role):
    return sorted(set(re.findall(r'[A-Za-z_][A-Za-z0-9_]*(?:\[-?\d+\])?',expression or '')) & set(role['pins']))

constant_cache = {}
def constants(n, active=None):
    if n in constant_cache:return constant_cache[n]
    if n in constant_descriptors:return {constant_descriptors[n]['name']:constant_descriptors[n]}
    if n in roots:return {}
    active=set() if active is None else active
    if n in active:
        errors.append('constant cone cycle:'+nets[n].getName());return {}
    active.add(n);found={}
    for dep in back.get(n,([],None))[0]:found.update(constants(dep,active))
    active.remove(n);constant_cache[n]=found
    return found

clock_cache={}
def clock_sources(n, active=None):
    if n in clock_cache:return clock_cache[n]
    if n in roots:return {roots[n]['name']:roots[n]}
    ports=[t for t in nets[n].getBTerms() if t.getIoType()=='INPUT']
    if ports:return {'port:'+t.getName():descriptor(t,'clock_source_port') for t in ports}
    if n in constant_descriptors:return {constant_descriptors[n]['name']:constant_descriptors[n]}
    active=set() if active is None else active
    if n in active:
        errors.append('clock cone cycle:'+nets[n].getName());return {}
    active.add(n);found={}
    for dep in back.get(n,([],None))[0]:found.update(clock_sources(dep,active))
    active.remove(n)
    if not found:errors.append('unresolved clock source:'+nets[n].getName())
    clock_cache[n]=found
    return found

seq_records=[]
seq_data_edges=[]
port_membership=collections.defaultdict(lambda:{'data_input_flops':[],'data_output_flops':[]})
for name,inst in sorted(sequential_instances.items()):
    master=inst.getMaster().getName();role=roles[master]
    eqs=seq_equations.get(master,[])
    ismem=master in MEMORIES
    if not ismem and not eqs:errors.append('missing actual sequential equations:'+master)
    data_pins=set(p for eq in eqs for p in expr_pins(eq.get('next_state'),role))
    clear_pins=set(p for eq in eqs for p in expr_pins(eq.get('clear'),role))
    preset_pins=set(p for eq in eqs for p in expr_pins(eq.get('preset'),role))
    clocks=[];inputs=[];outputs=[];inports=set();outports=set()
    for t in inst.getITerms():
        if not t.getNet() or t.getSigType() in ('POWER','GROUND'):continue
        pin=t.getMTerm().getName();pr=role_pin(role,master,pin)
        if not pr:continue
        if pr['clock']:
            clocks.append(dict(descriptor(t,'clock_pin'),sources=list(clock_sources(t.getNet().getId()).values())))
        elif pr['direction']=='input':
            category='memory_data_control' if ismem else ('data_next_state' if pin in data_pins else
                'asynchronous_clear' if pin in clear_pins else 'asynchronous_preset' if pin in preset_pins else 'sequential_control')
            rr=list(cone(t.getNet().getId(),'backward').values())
            inputs.append(dict(descriptor(t,category),roots=rr,constant_sources=list(constants(t.getNet().getId()).values())))
            if category in ('data_next_state','memory_data_control'):
                for root in rr:
                    seq_data_edges.append({'root':root,'endpoint':descriptor(t,category)})
                    if root['kind']=='input_port':
                        inports.add(root['pin'])
                        port_membership[root['pin']]['data_input_flops'].append(name+'/'+pin)
        elif pr['direction']=='output':
            ee=[e for e in cone(t.getNet().getId(),'forward').values() if e['kind']=='output_port']
            outputs.append(dict(descriptor(t,'synchronous_sram_output' if ismem else 'sequential_output'),output_port_endpoints=ee))
            for e in ee:
                outports.add(e['pin']);port_membership[e['pin']]['data_output_flops'].append(name+'/'+pin)
    if inports and outports:classification='direct_port_data_input_and_output'
    elif inports:classification='direct_port_data_input'
    elif outports:classification='direct_port_data_output'
    else:classification='interior_or_multistage_landing_unresolved'
    seq_records.append({'instance':name,'master':master,'kind':'synchronous_sram' if ismem else 'liberty_sequential',
        'sequential_equations':eqs,'clock_pins':clocks,'input_pins':inputs,'output_pins':outputs,
        'direct_input_port_bits':sorted(inports),'direct_output_port_bits':sorted(outports),
        'boundary_classification':classification,
        'placement_policy':'Direct port-stage membership is a boundary obligation; absence of direct membership does not establish freedom to move a multistage landing.'})

import os
spec_path=Path('/src/physical/ref_tile')/os.environ['AUDIT_KIT']/'spec.json'
spec=json.loads(spec_path.read_text())
face_by_name={name:face for face,names in spec.get('pins',{}).items() for name in names}
die=block.getDieArea();die_um=[die.xMin()/dbu,die.yMin()/dbu,die.xMax()/dbu,die.yMax()/dbu]
port_bits=[]
for t in block.getBTerms():
    if not t.getNet() or t.getSigType() in ('POWER','GROUND'):continue
    d=descriptor(t,'port_bit');m=re.fullmatch(r'(.*)\[(-?\d+)\]',t.getName());base=m[1] if m else t.getName()
    x,y=d['xy_um'];dist={'W':abs(x-die_um[0]),'E':abs(x-die_um[2]),'S':abs(y-die_um[1]),'N':abs(y-die_um[3])}
    boxes=[z for pin in t.getBPins() for z in pin.getBoxes()]
    d.update(direction=str(t.getIoType()),base_port=base,bit=int(m[2]) if m else None,
        spec_face=face_by_name.get(base),actual_nearest_face=min(dist,key=dist.get),
        pin_boxes_um=[[z.xMin()/dbu,z.yMin()/dbu,z.xMax()/dbu,z.yMax()/dbu] for z in boxes],
        **port_membership.get(t.getName(),{'data_input_flops':[],'data_output_flops':[]}))
    port_bits.append(d)

result={'schema':'opentallas.grp_stage_pin_identity.v1','status':'ERROR' if errors else 'PASS',
    'scope':'Read-only ORIGINAL CTS pin/clock/reset/source-bit identity and complete Liberty-function combinational arc graph. This is not permission to move a boundary flop; interior-vs-multistage landing remains unresolved without a prospective source-bound floorplan.',
    'odb_path':str(odb_path),'odb_sha256':hashlib.sha256(odb_path.read_bytes()).hexdigest(),
    'audit_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'spec_path':str(spec_path),'spec_sha256':hashlib.sha256(spec_path.read_bytes()).hexdigest(),
    'liberty':receipts,'synchronous_memory_proof':memory_receipts,'die_um':die_um,
    'role_errors':sorted(set(errors)),'counts':dict(counts),'port_bits':port_bits,
    'constant_function_sources':list(constant_descriptors.values()),
    'output_port_sources':[
        {'port':t.getName(),'roots':list(cone(t.getNet().getId(),'backward').values()),
         'constant_sources':list(constants(t.getNet().getId()).values())}
        for t in block.getBTerms() if t.getNet() and t.getIoType()=='OUTPUT' and t.getSigType() not in ('POWER','GROUND')],
    'sequential_instances':seq_records,'data_stage_edges':seq_data_edges,
    'combinational_cells':combinational_records}
with gzip.open(OUT/'stage_identity.json.gz','wt') as f:json.dump(result,f,separators=(',',':'))
result['role_errors']=sorted(set(errors));result['status']='ERROR' if errors else 'PASS'
summary={k:v for k,v in result.items() if k not in ('port_bits','sequential_instances','data_stage_edges','combinational_cells','liberty','constant_function_sources','output_port_sources')}
summary.update(port_bit_count=len(port_bits),sequential_instance_count=len(seq_records),
    data_stage_edge_count=len(seq_data_edges),combinational_cell_count=len(combinational_records),
    boundary_classes=dict(collections.Counter(r['boundary_classification'] for r in seq_records)))
(OUT/'stage_identity_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(summary)
if errors:raise SystemExit(2)

