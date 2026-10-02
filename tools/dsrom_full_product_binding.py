#!/usr/bin/env python3
"""Metadata-only compiler/model bridge. Original emitters and model stay pinned.

prepare exports the actual complete descriptor demand. compose joins an allocator
and finite calendars; no synthetic latency defaults or image/payload reads.
"""
import argparse
import copy
from collections import deque
from fractions import Fraction
import hashlib
import gzip
import json
from pathlib import Path
import subprocess
import w11_dsrom_full_tp_program as F

ROOT = Path(__file__).resolve().parents[1]
PIN = '4c8b7f2d8e246bd09250051fc8f7cb3e3340f574'
CANDIDATE = 'DS4096-TP4-S58-PAIR1'
SOURCES = [F.CONFIG, 'tools/w11_dsrom_full_tp_program.py',
           'tools/hdc_replay_v41.py', 'tools/hdc_program_v41.py',
           'tools/hdc_isa_v41.py', 'tools/hdc_golden_v41.py',
           'tools/v41_program_constants.py', 'results/rtl/v41_program_constants.json',
           'tools/uarch_model.py']
ADDRESS_FIELDS = {'me_wbase', 'qe_wbase', 'he_wbase', 'c_base', 'sfu_cbase'}

def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(',', ':')).encode()

def digest(x):
    return hashlib.sha256(canonical(x)).hexdigest()

def source_pins():
    out = []
    for path in SOURCES:
        raw = (ROOT / path).read_bytes()
        pinned = subprocess.check_output(['git', 'show', PIN + ':' + path], cwd=ROOT)
        if raw != pinned:
            raise ValueError('source currency: ' + path)
        out.append({'commit': PIN, 'path': path, 'sha256': hashlib.sha256(raw).hexdigest()})
    return out

def encode_instruction(inst):
    # JSON turns the emitter's dynamic selector tuples into arrays. Restore
    # only actual ISA values; metadata sets/lists remain untouched.
    fields = {k: tuple(v) if isinstance(v, list) and not k.startswith("_") else v
              for k, v in inst.items()}
    return F.I.encode(full_shape=True, **fields)

def prepare():
    pins = source_pins()
    p = F.build_program(opt_in=True)
    F.validate_program(p)
    nodes = []
    for stage in p['stages'] + [dict(layer='head', instructions=p['head']['instructions'], runtime_actions=[])]:
        scope = stage['layer']
        actions = {}
        for ai, action in enumerate(stage['runtime_actions']):
            pos = action['before_instruction']
            if not 0 <= pos <= len(stage['instructions']):
                raise ValueError('action anchor')
            actions.setdefault(pos, []).append((ai, action))
        for i in range(len(stage['instructions']) + 1):
            for ai, action in actions.get(i, []):
                nodes.append({'id': f'L{scope}.A{ai}', 'scope': scope,
                              'kind': 'runtime_action', 'action': action})
            if i == len(stage['instructions']):
                continue
            inst = stage['instructions'][i]
            # Legality is checked here but these zero-address words are NOT images.
            word = encode_instruction(inst)
            nodes.append({'id': f'L{scope}.I{i}', 'scope': scope,
                          'kind': 'instruction', 'instruction_index': i,
                          'instruction': inst, 'template_word_sha256': hashlib.sha256(word.to_bytes(256, 'little')).hexdigest()})
        nodes.append({'id': f'L{scope}.fence', 'scope': scope, 'kind': 'consumer_done_fence',
                      'contract': 'END plus actual vector/collective/persistent publication/return consumers done'})
    # Embedding and global argmax are functional operations, not silently free ISA.
    nodes.insert(0, {'id': 'embedding', 'scope': 'embedding', 'kind': 'embedding_service'})
    nodes.append({'id': 'global_argmax', 'scope': 'head', 'kind': 'argmax_service'})
    return {'schema': 'opentallas.dsrom.full-product-demand.v1', 'source_pins': pins,
            'compiler_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'historical_review_candidate': CANDIDATE, 'historical_candidate_verdict': 'FAIL_CORRECTED_CAPACITY',
            'functional_program_sha256': digest(p), 'functional_program': p, 'nodes': nodes,
            'required_ranks': [0, 1, 2, 3], 'element': {'rows': 4096, 'NB': 2, 'PP': 1, 'physical_macros_per_pair': 4},
            'allocator_contract': {'schema': 'opentallas.dsrom.full-product-allocation.v1',
                'demand_sha256': 'digest of this complete demand record',
                'coverage': 'all40 layers, all384 routed experts, shared experts, constants, nonexpert, head/embed, table homes separately',
                'bindings': 'exact node ID x rank: provider, source_receipts, semantic_sha256, address_patches, owner_grain, calendar',
                'semantic_sha256': 'digest of complete original node; protects shapes, rounding, predicates, actions and order',
                'calendar': 'domain, accept_cycles, complete_cycles, issue_interval_cycles, completion_dependencies, acceptance_dependencies; finite and source-receipted',
                'resources': 'id -> global/rank scope, owner, domain, issue_interval_cycles, minimum_issue_cycles, optional capacity_bits_per_cycle, source_receipts; binding resource_claims give resource/order/release/demand_bits with resource_coverage_receipts',
                'rendezvous': 'id -> all4 exact original collective rank node IDs; same start after prior readiness, never mutual peer-completion dependencies',
                'ordered_grains': 'golden contiguous indivisible owners, area_um2_by_rank[4], q_pairs_by_rank[4], BF_pairs_by_rank[4], tensor_assignment evidence; footprint includes mandatory RNE/WAKE exactly once',
                'owner_groups': 'actual ordered assignment; candidate_id DS4096-TP4-S58-PAIR1 / TP4; exactly58 layer groups, other head/table roles explicitly priced, no automatic replacement count',
                'compiled_field': 'NP, NBF, physical_macros_per_pair=4, source_receipts; resident_site_groups must declare every compiled pair source-matched physicalclass/BF mask and shared immutable q/BF word intervals; dual q_on_BF requires actual dual-compute abstract proof, no overlapping capacity',
                'capacity_ledger': '26x33mm minus unique source-receipted service/routing_clock_PG/return debits; per-group service replication; compiled_NP/R/NBF/RD/ROOTD/RST defines declared return (not active mask), resizing requires full allocator padded topology binding; no native-area discount without native binding',
                'provider_ABI': 'explicit original HDC unit support; a 274-bit field cannot be called ME32/QE without a bound adapter',
                'coverage_receipts': 'provider contracts and independent allocator verification, never a bare boolean'},
            'readiness': {'ISA_execution': False, 'RTL_build': False, 'physical_admission': False, 'full_token_rate': False},
            'return_source': return_source_receipt(),
            'resource_compiler_sha256': hashlib.sha256((ROOT/'tools/dsrom_finite_resources.py').read_bytes()).hexdigest(),
            'resident_compiler_sha256': hashlib.sha256((ROOT/'tools/dsrom_resident_site_binding.py').read_bytes()).hexdigest(), 'jobs_launched': 0}

def pack_ordered(grains, capacity_um2):
    """Minimum contiguous groups for fixed ordered atoms and common rank capacity.

    Never partition an atom or reassociate a reduction. Other permutations/topology
    and native return-state resizing need separate authoritative owner input.
    """
    cap = Fraction(str(capacity_um2))
    if cap <= 0 or not grains:
        raise ValueError('positive capacity and owner grains required')
    groups, current, used, seen = [], [], [Fraction(0)] * 4, set()
    for atom in grains:
        if atom['id'] in seen or not atom.get('tensor_assignment_receipts'):
            raise ValueError('duplicate or unproved indivisible owner')
        seen.add(atom['id'])
        a = [Fraction(str(x)) for x in atom['area_um2_by_rank']]
        if len(a) != 4 or any(x < 0 or x > cap for x in a):
            raise ValueError('indivisible owner exceeds reticle field capacity: ' + atom['id'])
        if any(used[r] + a[r] > cap for r in range(4)):
            groups.append({'owners': current, 'area_um2_by_rank': [float(x) for x in used]})
            current, used = [], [Fraction(0)] * 4
        current.append(atom['id'])
        used = [used[r] + a[r] for r in range(4)]
    groups.append({'owners': current, 'area_um2_by_rank': [float(x) for x in used]})
    return groups

RETURN_PIN = '3995d7208'  # resolved and full SHA retained in output receipt
RETURN_PATH = 'results/uarch/dsrom_return_scaling_source_audit_20261002/model.json'

def return_source_receipt():
    commit = subprocess.check_output(['git', 'rev-parse', RETURN_PIN], cwd=ROOT, text=True).strip()
    raw = subprocess.check_output(['git', 'show', commit + ':' + RETURN_PATH], cwd=ROOT)
    record = json.loads(raw)
    old = return_dimensions({'compiled_NP':8192,'R':128,'NBF':1024,'RD':64,'ROOTD':128,'RST':1})
    if record['current_compiled']['declared_lower_bits'] != old['declared_lower_bits']:
        raise ValueError('return source equation currency')
    cases = record['preexisting_partition_parameter_cases_not_new_sweep']
    for case in cases:
        if case['compiled_NP'] == 4096:
            actual = return_dimensions({'compiled_NP':4096,'R':128,'NBF':1024,'RD':64,'ROOTD':128,'RST':1})
            if actual['declared_lower_bits'] != case['declared_lower_bits']:
                raise ValueError('compiled4096 source equation currency')
    return {'commit':commit,'path':RETURN_PATH,'sha256':hashlib.sha256(raw).hexdigest(),
            'status':record['status'],'source_pins':record['source_pins']}

def return_dimensions(topology):
    np, r, nbf = (topology[k] for k in ('compiled_NP', 'R', 'NBF'))
    rd, rootd, rst = (topology[k] for k in ('RD', 'ROOTD', 'RST'))
    if any(not isinstance(x, int) or isinstance(x, bool) for x in (np,r,nbf,rd,rootd,rst)):
        raise ValueError('integer compiled return topology')
    if min(np,r,nbf) < 1 or np < nbf or r > np or rst < 0 or min(rd,rootd) < 2:
        raise ValueError('illegal compiled return topology')
    if any(x & (x-1) for x in (np,r,rd,rootd)):
        raise ValueError('power-of-two source return topology')
    nodes = 2*np-r
    bits = nodes*(2*rd*65+rst*66)+r*rootd*(65+66)
    return {'compiled_NP':np,'R':r,'NBF':nbf,'return_nodes':nodes,
            'declared_lower_bits':bits,'physical_PP4096_banks':4*np,
            'conservative_FF_50pct_um2':float(Fraction(bits)*Fraction('0.37908')/Fraction('0.5')),
            'tree_levels':(2*np//r).bit_length()-1,
            'source_noqueue_tree_cycles':6*((2*np//r).bit_length()-1),
            'root_public_bits_per_cycle':r*69,
            'scope':'declared storage lower bound plus conservative FF50 proxy; occupancy/control/mux/adder/CTS/hold costs extra',
            'active_mask_changes_declarations':False}

def field_capacity(ledger):
    if ledger['width_um'] != 26000 or ledger['height_um'] != 33000:
        raise ValueError('selected 26x33mm manufacturing envelope')
    categories = {'service', 'routing_clock_PG', 'return'}
    terms = ledger['debits']; seen = set()
    for t in terms:
        if t['id'] in seen or t['category'] not in categories or not t.get('source_receipts'):
            raise ValueError('duplicate/unsourced reservation debit')
        seen.add(t['id'])
        if Fraction(str(t['area_um2'])) < 0:
            raise ValueError('negative reservation debit')
    if {t['category'] for t in terms} != categories:
        raise ValueError('service/corridor/clockPG/return composition required')
    topology = ledger.get('compiled_return_topology', {'compiled_NP':8192,'R':128,'NBF':1024,'RD':64,'ROOTD':128,'RST':1})
    dimensions = return_dimensions(topology)
    if dimensions['compiled_NP'] != 8192 and not ledger.get('compiled_topology_binding_receipts'):
        raise ValueError('resized NP requires allocator full padding/owner/topology binding')
    if ledger['full_return_storage_bits'] != dimensions['declared_lower_bits']:
        raise ValueError('full reachable compiled return contexts omitted')
    return_area = sum(Fraction(str(t['area_um2'])) for t in terms if t['category'] == 'return')
    if return_area < Fraction(str(dimensions['conservative_FF_50pct_um2'])) and not ledger.get('native_return_binding_receipts'):
        raise ValueError('unproved return reserve discount')
    if not ledger.get('service_replication_receipts'):
        raise ValueError('fixed hub/service replication per ownership group unpriced')
    return Fraction(858000000) - sum(Fraction(str(t['area_um2'])) for t in terms)

def validate_calendar(c):
    if c['domain'] not in ('streaming', 'serial'):
        raise ValueError('clock domain')
    for k in ('accept_cycles', 'complete_cycles', 'issue_interval_cycles'):
        if not isinstance(c[k], int) or isinstance(c[k], bool) or c[k] < 0:
            raise ValueError('finite integer calendar: ' + k)
    if c['complete_cycles'] < c['accept_cycles'] or c['issue_interval_cycles'] < 1:
        raise ValueError('acceptance/completion calendar')
    if not c.get('source_receipts'):
        raise ValueError('unsourced service calendar')
    return Fraction(5, 6) if c['domain'] == 'streaming' else Fraction(10, 9)

def validate_padding(allocation, groups, capacity):
    """Charge every compiled element, including unused q/BF physical sites."""
    topology = allocation['capacity_ledger'].get('compiled_return_topology',
        {'compiled_NP':8192,'R':128,'NBF':1024,'RD':64,'ROOTD':128,'RST':1})
    np, nbf = topology['compiled_NP'], topology['NBF']
    compiled = allocation['compiled_field']
    if compiled['NP'] != np or compiled['NBF'] != nbf or compiled['physical_macros_per_pair'] != 4:
        raise ValueError('allocator field / return compiled topology mismatch')
    if not compiled.get('source_receipts'):
        raise ValueError('compiled field site and BF mapping receipts required')
    if compiled.get('resident_site_groups') is not None:
        import dsrom_resident_site_binding as resident
        records=compiled['resident_site_groups']
        if len(records)!=4*len(groups):
            raise ValueError('resident site group/rank census')
        expected={(i,r) for i in range(len(groups)) for r in range(4)}
        if {(x['group_index'],x['rank']) for x in records}!=expected:
            raise ValueError('duplicate or missing resident group/rank')
        results=[]
        for record in records:
            priced=resident.validate(record['sites'],np,nbf)
            # Full site frames replace USED+UNUSED catalogue frames, never add
            # those same pair frames a second time. Extra repair/control must
            # be separately owned and charged once above this full-site floor.
            increment=Fraction(str(record['extra_nonoverlapping_repair_control_um2']))
            if increment<0 or not record.get('source_receipts'):
                raise ValueError('resident frame/repair reconciliation receipts')
            total=Fraction(str(priced['physical_frame_um2']))+increment
            if total>capacity:
                raise ValueError('resident full compiled field and mandatory growth exceed allowance')
            results.append(dict(priced,group_index=record['group_index'],rank=record['rank'],
                extra_nonoverlapping_repair_control_um2=float(increment),
                full_resident_reservation_um2=float(total)))
        return results
    atoms = {a['id']:a for a in allocation['ordered_grains']}
    results = []
    for group in groups:
        for r in range(4):
            q = sum(atoms[a]['q_pairs_by_rank'][r] for a in group['owners'])
            bf = sum(atoms[a]['BF_pairs_by_rank'][r] for a in group['owners'])
            if any(not isinstance(v,int) or isinstance(v,bool) or v<0 for a in group['owners']
                   for v in (atoms[a]['q_pairs_by_rank'][r],atoms[a]['BF_pairs_by_rank'][r])):
                raise ValueError('integer complete pair owner counts')
            if q > np-nbf or bf > nbf:
                raise ValueError('actual q/BF owner sites exceed compiled field')
            padding = (np-nbf-q)*Fraction('64825.596') + (nbf-bf)*Fraction('142971.9984')
            reserved = Fraction(str(group['area_um2_by_rank'][r])) + padding
            if reserved > capacity:
                raise ValueError('compiled unused-site padding exceeds corrected field allowance')
            results.append({'owners':group['owners'],'rank':r,'q_used':q,'BF_used':bf,
                            'q_padding':np-nbf-q,'BF_padding':nbf-bf,
                            'physical4096_macro_count':4*np,
                            'catalog_padding_frame_um2':float(padding),
                            'used_plus_padding_reservation_um2':float(reserved),
                            'scope':'catalog reservation, not hardabstract SSFF qualification'})
    return results

def verify_input_receipts(allocation):
    """Verify committed metadata/code references, never checkpoint payloads."""
    checked = {}
    def walk(x):
        if isinstance(x, dict):
            for key, value in x.items():
                if key.endswith('receipts') or key == 'native_ISA_provider_contract':
                    if not isinstance(value, list) or not value:
                        raise ValueError('nonempty committed source receipts: ' + key)
                    for ref in value:
                        if not isinstance(ref, dict) or set(('commit', 'path', 'sha256')) - set(ref):
                            raise ValueError('receipt needs commit/path/sha256: ' + key)
                        path = ref['path']
                        if '..' in Path(path).parts or Path(path).is_absolute() or Path(path).suffix not in ('.json', '.py', '.sv', '.v', '.tcl', '.sdc', '.lef', '.lib'):
                            raise ValueError('only bounded source/metadata receipts; no payload read')
                        identity = (ref['commit'], path)
                        if identity not in checked:
                            spec = ref['commit'] + ':' + path
                            size = int(subprocess.check_output(['git', 'cat-file', '-s', spec], cwd=ROOT))
                            if size > 64 * 1024 * 1024:
                                raise ValueError('receipt exceeds bounded metadata read')
                            raw = subprocess.check_output(['git', 'show', spec], cwd=ROOT)
                            checked[identity] = hashlib.sha256(raw).hexdigest()
                        if checked[identity] != ref['sha256']:
                            raise ValueError('receipt byte mismatch: ' + path)
                else:
                    walk(value)
        elif isinstance(x, list):
            for value in x:
                walk(value)
    walk(allocation)
    return [{'commit': k[0], 'path': k[1], 'sha256': v} for k, v in sorted(checked.items())]

def allocator_groups(allocation, capacity):
    if allocation.get('candidate_id') != CANDIDATE or allocation.get('TP') != 4:
        raise ValueError('single shared S58/TP4 candidate binding required')
    atoms = allocation['ordered_grains']; ids = [a['id'] for a in atoms]
    if len(set(ids)) != len(ids) or any(not a.get('tensor_assignment_receipts') for a in atoms):
        raise ValueError('duplicate/unproved full-product owner atom')
    assigned = allocation['owner_groups']
    if sum(g['role']=='layer' for g in assigned) != 58:
        raise ValueError('one shared candidate requires actual58 layer ownership groups, no independent count selection')
    if [a for g in assigned for a in g['owners']] != ids:
        raise ValueError('full ordered owner assignment missing/duplicated/reordered')
    lookup = {a['id']:a for a in atoms}; result=[]
    for g in assigned:
        if not g['owners'] or not g.get('source_receipts'):
            raise ValueError('empty or unsourced owner group')
        area = [sum(Fraction(str(lookup[a]['area_um2_by_rank'][r])) for a in g['owners']) for r in range(4)]
        if any(v<0 or v>capacity for v in area):
            raise ValueError('actual owner group exceeds corrected field capacity')
        result.append(dict(g,area_um2_by_rank=[float(x) for x in area]))
    return result

def compose(demand, allocation, *, fixture_only=False):
    if not fixture_only:
        if demand["source_pins"] != source_pins():
            raise ValueError("full product demand source currency")
        if demand.get("resource_compiler_sha256") != hashlib.sha256((ROOT/"tools/dsrom_finite_resources.py").read_bytes()).hexdigest():
            raise ValueError("shared resource compiler source currency")
        if demand.get("resident_compiler_sha256") != hashlib.sha256((ROOT/"tools/dsrom_resident_site_binding.py").read_bytes()).hexdigest():
            raise ValueError("resident site compiler source currency")
        F.validate_program(demand["functional_program"])
        if digest(demand["functional_program"]) != demand["functional_program_sha256"]:
            raise ValueError("functional emitter identity")
        receipts = verify_input_receipts(allocation)
    else:
        receipts = []
    if allocation.get('schema') != 'opentallas.dsrom.full-product-allocation.v1' or allocation.get('demand_sha256') != digest(demand):
        raise ValueError('allocator/demand identity')
    if not allocation.get('coverage_receipts'):
        raise ValueError('full tensor/format/constant coverage verification required')
    capacity = field_capacity(allocation['capacity_ledger'])
    groups = pack_ordered(allocation['ordered_grains'], capacity) if fixture_only else allocator_groups(allocation, capacity)
    if not fixture_only and allocation['compiled_field'].get('resident_site_groups') is None:
        raise ValueError('actual source bank/site residency required; exclusive q/BF count proxy is not product binding')
    padding = [] if fixture_only else validate_padding(allocation, groups, capacity)
    owner_group = {a: i for i, g in enumerate(groups) for a in g['owners']}
    bindings = allocation['bindings']
    expected = {f"{n['id']}.R{r}" for n in demand['nodes'] for r in range(4)}
    if set(bindings) != expected:
        raise ValueError('binding census missing/extra: ' + str(len(expected - set(bindings))) + '/' + str(len(set(bindings) - expected)))
    events, images = [], {str(r): [] for r in range(4)}
    specs = {}
    for r in range(4):
        previous, last_by_unit, prior_scope, scope_nodes = None, {}, None, []
        for node in demand['nodes']:
            nid = f"{node['id']}.R{r}"
            b = bindings[nid]
            if b['semantic_sha256'] != digest(node) or b['owner_grain'] not in owner_group:
                raise ValueError('semantic/owner binding: ' + nid)
            if not b.get('provider') or not b.get('source_receipts'):
                raise ValueError('provider source identity: ' + nid)
            c = b['calendar']; period = validate_calendar(c)
            deps = set(c['completion_dependencies'])
            if len(deps) != len(c['completion_dependencies']) or not deps <= expected:
                raise ValueError('unbound completion dependency: ' + nid)
            required = set()
            if node['scope'] != prior_scope:
                if previous:
                    required.add(previous)
                last_by_unit, scope_nodes = {}, []
                prior_scope = node['scope']
            if node['kind'] == 'instruction':
                inst = copy.deepcopy(node['instruction'])
                for u, last in last_by_unit.items():
                    if u in F.I.UNITS and inst.get('wait', 0) >> (u - 1) & 1:
                        required.add(last)
                # Complete drain at END and consumer-done fences, not free END.
                if inst['unit'] == F.I.UNIT_END:
                    required.update(scope_nodes)
                if not b.get('native_ISA_provider_contract'):
                    raise ValueError('274-bit field / legacy ISA provider adapter unbound: ' + nid)
                for name, patch in b.get('address_patches', {}).items():
                    if name not in ADDRESS_FIELDS or name not in inst or inst[name] != patch['old']:
                        raise ValueError('nonaddress/stale patch: ' + nid)
                    inst[name] = patch['new']
                word = encode_instruction(inst)
                images[str(r)].append({'node': nid, 'ownership_group': owner_group[b['owner_grain']],
                                       'word_hex': f'{word:0512x}', 'provider': b['provider']})
                last_by_unit[inst['unit']] = nid
            elif b.get('address_patches'):
                raise ValueError('runtime action is not an ISA opcode')
            if node['kind'] == 'consumer_done_fence':
                required.update(scope_nodes)
            if not required <= deps:
                raise ValueError('missing ISA wait/END/scope completion fence: ' + nid)
            specs[nid] = {'binding': b, 'period': period, 'previous': previous,
                          'dependencies': sorted(deps), 'owner_group': owner_group[b['owner_grain']],
                          'unit': node.get('instruction',{}).get('unit'),
                          'collective_input_bits': (node['instruction'].get('coll_n',0)*(64 if node['instruction'].get('coll_op')==2 else 32)) if node['kind']=='instruction' else 0}
            scope_nodes.append(nid)
            previous = nid
    resource_receipts=[]
    if not fixture_only or allocation.get('resources'):
        import dsrom_finite_resources
        completed,resource_receipts=dsrom_finite_resources.price(specs,allocation.get('resources',{}),allocation.get('rendezvous',{}))
    else:
        # Topological timing over all ranks supports causal peer collectives; rank0
        # is not evaluated as though the other three ranks were already free/ready.
        completed = {}
        prior_provider = {}
        for nid, spec in specs.items():
            key = (nid.rsplit('.R', 1)[1], spec['binding']['provider'])
            spec['prior_provider'] = prior_provider.get(key)
            prior_provider[key] = nid
        pending, users = {}, {nid: [] for nid in specs}
        for nid, spec in specs.items():
            deps = set(spec['dependencies'])
            deps.update(x for x in (spec['previous'], spec['prior_provider']) if x)
            pending[nid] = len(deps)
            for dep in deps:
                users[dep].append(nid)
        ready = deque(nid for nid in specs if pending[nid] == 0)
        while ready:
            nid = ready.popleft(); spec = specs[nid]
            c = spec['binding']['calendar']; period = spec['period']; times = [Fraction(0)]
            if spec['previous']:
                times.append(completed[spec['previous']][1])
            if spec['prior_provider']:
                prior = specs[spec['prior_provider']]
                times.append(completed[spec['prior_provider']][0] +
                             prior['binding']['calendar']['issue_interval_cycles'] * prior['period'])
            times.extend(completed[d][2] for d in spec['dependencies'])
            start = max(times)
            completed[nid] = (start, start + c['accept_cycles'] * period,
                              start + c['complete_cycles'] * period)
            for user in users[nid]:
                pending[user] -= 1
                if pending[user] == 0:
                    ready.append(user)
        if len(completed) != len(specs):
            raise ValueError('cyclic acceptance/completion dependencies')
    for nid, spec in specs.items():
        start, accept, complete = completed[nid]
        events.append({'id': nid, 'owner_group': spec['owner_group'],
                       'provider': spec['binding']['provider'], 'issue_after': spec['previous'],
                       'completion_dependencies': spec['dependencies'], 'start_ns': float(start),
                       'accepted_ns': float(accept), 'complete_ns': float(complete),
                       'domain': spec['binding']['calendar']['domain']})
    return {'schema': 'opentallas.dsrom.full-product-composed.v1',
            'demand_sha256': digest(demand), 'allocation_sha256': digest(allocation),
            'verified_input_receipts': receipts, 'synthetic_fixture_only': fixture_only,
            'resource_reservations': resource_receipts,
            'resource_coverage_bound': bool(resource_receipts),
            'groups': groups, 'contiguous_ownership_groups': len(groups),
            'packing_scope': 'fixed ordered atoms/common field capacity; padding must pass, no topology or count adopted',
            'compiled_padding': padding,
            'tp': 4, 'field_capacity_um2': float(capacity), 'capacity_ledger': allocation['capacity_ledger'],
            'events': events, 'ISA_images': images,
            'calendar_end_ns': float(max(x[2] for x in completed.values())),
            'historical_S58_corrected_capacity': 'FAIL unchanged',
            'compiled_return_dimensions': return_dimensions(allocation['capacity_ledger'].get('compiled_return_topology',
                {'compiled_NP':8192,'R':128,'NBF':1024,'RD':64,'ROOTD':128,'RST':1})),
            'scope': 'source-priced compiler calendar; numeric connected RTL and contextual SS/FF not implied',
            'readiness': {'physical_admission': False, 'full_token_rate': False, 'adopt': False},
            'jobs_launched': 0}

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--allocation', type=Path)
    ap.add_argument('--demand', type=Path)
    args = ap.parse_args()
    if args.out.exists():
        ap.error('refuse to overwrite retained evidence')
    d = json.loads(gzip.decompress(args.demand.read_bytes()) if args.demand and args.demand.suffix == '.gz' else args.demand.read_bytes()) if args.demand else prepare()
    result = compose(d, json.loads(args.allocation.read_text())) if args.allocation else d
    args.out.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(result, indent=2, sort_keys=True) + '\n').encode()
    if args.out.suffix == '.gz':
        raw = gzip.compress(raw, mtime=0)
    with args.out.open('xb') as out:
        out.write(raw)

if __name__ == '__main__':
    main()
