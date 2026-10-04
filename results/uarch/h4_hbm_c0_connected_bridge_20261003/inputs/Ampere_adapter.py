#!/usr/bin/env python3
"""Default-off source operand adapter, not a native emitter or numerical VM.

The first C0-eligible recipe is Qwen SILU_GATE/exp/step0 FMAX. The RESIDUAL
views are retained broader source context, not V1-eligible C0 operations.
Storage homes and executor ownership are different coordinates. RF views have no HBM
address and no W2-derived parent55. No original compiler admission is changed.
"""
import argparse
import ast
import copy
import functools
import gzip
import hashlib
import json
import math
import struct
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'results/uarch/c0_source_operand_views_20261003'
MANIFEST_SHA = '2e9cc881491a441f65f14bd99419f1ada7e6334fa6234efcec59897386cfa833'
COSTS = ('RF_READ', 'RF_MIRRORED_ACK', 'FADD', 'NoC_PAGE', 'CDC', 'REVERSE_GRANT')


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


@functools.lru_cache(maxsize=1)
def sources():
    raw = (BASE / 'input_manifest.json').read_bytes()
    require(sha(raw) == MANIFEST_SHA, 'input manifest identity')
    inputs = {}
    for row in json.loads(raw):
        path = ROOT / row['archive']
        require(path.resolve().is_relative_to((BASE / 'inputs').resolve()), 'input scope')
        data = path.read_bytes()
        require(len(data) == row['bytes'] and sha(data) == row['sha256'], 'input identity')
        inputs[path.name] = data
    return inputs


@functools.lru_cache(maxsize=1)
def source_contract():
    """Extract metadata-only original methods; never instantiate a provider."""
    inputs = sources()
    tree = ast.parse(inputs['qwen_provider.py'])
    classes = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}
    tile = classes['TileWords']
    key = next(n for n in tile.body if isinstance(n, ast.FunctionDef) and n.name == 'key')
    ns = {}
    exec(compile(ast.Module(body=[key], type_ignores=[]), 'frozen-provider:TileWords.key', 'exec'), ns)
    # Prove arithmetic from the execution implementation, not inferred shapes.
    primitive = next(n for n in classes['NativePrimitiveVM'].body
                     if isinstance(n, ast.FunctionDef) and n.name == 'primitive')
    text = ast.unparse(primitive)
    require("z.astype(F, copy=False)" in text and "x[0] + x[1]" in text
            and "v = np.asarray(v, F)" in text and "at.get('canonical_zero', True)" in text,
            'actual binary32 execution contract')
    require(b'F = np.float32' in inputs['qwen_arithmetic.py'], 'source float32 definition')
    execute = next(n for n in classes['TiledMachine'].body
                   if isinstance(n, ast.FunctionDef) and n.name == 'execute')
    text = ast.unparse(execute)
    require("range(0, size, 128)" in text and "self.add(x, self.store.read(reads[1], start, n))" in text,
            'actual RESIDUAL execution recipe')
    init = ast.unparse(next(n for n in tile.body if isinstance(n, ast.FunctionDef) and n.name == '__init__'))
    require('self.worker_SM = 0' in init and 'self.worker_rank = 0' in init, 'source worker placement')
    native = json.loads(gzip.decompress(inputs['Qwen_tiled.json.gz']))
    require(native['microcode']['add'] == [{'dst': 'out', 'op': 'FADD', 'src': ['a', 'b']}], 'exact native leaf')
    require(native['tile_kernel_ABI']['add']['steps'][0]['round_point'] == 'binary32 RNE + canonical zero',
            'source arithmetic ABI')
    require(len(native['operations']) == 1737 and [o['pc'] for o in native['operations']] == list(range(1737)),
            'complete source PC order')
    return native, ns['key']


class OperandViews:
    """Bound source metadata consumed by the emitter owner; no alternate emitter."""
    def __init__(self, *, enabled=False):
        self.enabled = enabled
        self.native, self.key = source_contract()
        self.values = {v['version']: v for v in self.native['operands']}
        self.homes = {(v['version'], h['rank'], h['SM']): h for v in self.values.values()
                      for h in v['homes'] if 'home' in h}

    def view(self, version, start, words, rank, side, PC):
        value = self.values[version]
        require(type(rank) is int and rank in {h['rank'] for h in value['homes']}, 'source home rank')
        require(len(value['shape']) == 1 and all(type(n) is int and n > 0 for n in value['shape'])
                and 0 <= start and start+words <= value['shape'][0], 'explicit source extent')
        require(side == 'write' and value['birth_pc'] == PC or side == 'read' and PC in value['consumers'],
                'actual producer/consumer version')
        owner = SimpleNamespace(homes=self.homes)
        coordinates = [self.key(owner, version, start + i, rank) for i in range(words)]
        keys = {key for key, lane in coordinates}
        require(len(keys) == 1, 'one source storage page per view')
        key = coordinates[0][0]
        home = self.homes[version, rank, key[2]]
        require(key[0] == 'RF', 'this direct-RF enrollment does not invent HBM tickets')
        require(home['home']['first_word']['physical_mirrors'] == 2
                and home['home']['first_word']['width_bits'] == 32, 'RF source packing/mirrors')
        require(0 <= key[3] < 512 and coordinates[0][1] == 0 and coordinates[-1][1] == 127,
                'full source RF aperture')
        return dict(symbol=None, version=version, lease=value['lease'], side=side,
                    source_provider_ref=home['provider_ref'], storage_rank=rank, storage_SM=key[2],
                    storage_class='RF', RFslot9=key[3], word_start=start, word_count=words,
                    lanes=[lane for _, lane in coordinates], arithmetic_dtype='F32', bit_type='F32',
                    storage_dtype='U32', storage_word_bits=32, packing='F32 bitcast U32, 128 lanes per 512B vector',
                    mirrors=2, publication_event=home['publication_event'], release_event=home['release_event'],
                    release_requires=list(home['release_requires']), retire_pc=value['retire_pc'],
                    HBM_byte_address=None, parent55=None,
                    parent55_scope='NOT_APPLICABLE_DIRECT_RF: no W2 sector child or frame anchor',
                    remote_from_executor=(rank, key[2]) != (0, 0))

    def bind(self, PC, start, *, generation, owner_tag, response_stall_bound):
        require(self.enabled, 'operand adapter default off')
        require(type(PC) is int and 0 <= PC < 1737, 'source PC')
        op = self.native['operations'][PC]
        require(op['opcode'] == 'RESIDUAL', 'source recipe not enrolled')
        require(type(start) is int and 0 <= start <= 3968 and start % 128 == 0, 'source tile loop')
        for value, name in ((generation, 'generation'), (owner_tag, 'owner_tag')):
            require(type(value) is int and 0 < value < 2**64, 'actual parent ' + name)
        require(type(response_stall_bound) is int and response_stall_bound > 0, 'finite response bound')
        require(len(op['reads']) == 2 and len(op['writes']) == 1, 'exact RESIDUAL arity')
        require(op['calendar_export']['physical_primitives']['kernel_invocations']['add'] == 32,
                'actual source invocation count')
        views = [self.view(v, start, 128, min(h['rank'] for h in self.values[v]['homes']), 'read', PC)
                 for v in op['reads']]
        for symbol, view in zip(('a', 'b'), views):
            view['symbol'] = symbol
        version = op['writes'][0]
        outputs = [self.view(version, start, 128, rank, 'write', PC)
                   for rank in sorted({h['rank'] for h in self.values[version]['homes']})]
        for output in outputs:
            output['symbol'] = 'out'
        require(len(outputs) == 2, 'source output replication')
        command = dict(model='Qwen', family='RESIDUAL', source_PC=PC,
                       program_sha256=sha(sources()['Qwen_tiled.json.gz']), template_id='add', ordered_step_index=0,
                       owner_tag=owner_tag, generation=generation, rank=0, SM=0, opcode='FADD',
                       source_bittypes=[32, 32], destination_bittype=32,
                       source_version_home_refs=views, destination_version_home_ref=outputs[0],
                       predicate=None, active_lanes=128, source_attrs_rounding={},
                       response_stall_bound=response_stall_bound)
        return dict(schema='C0_SOURCE_OPERAND_VIEWS_R1', native_command=command,
                    source_step=copy.deepcopy(self.native['microcode']['add'][0]), source_output_replicas=outputs,
                    source_arithmetic_contract='binary32 RNE + canonical zero; VM nonfinite fault retained',
                    executor=dict(rank=0, SM=0, scope='actual serialized released executor'),
                    client_assignment=dict(client=0, scope='new opt-in direct-RF dispatch policy, not a released-provider observation'),
                    native_owner=[PC, op['writes'], 0, 0, generation],
                    workspace_slots=None, workspace_scope='exact emitter-owned allocation required; provider VM has no fixed a/b/out slot binding',
                    source_views_verified=True, payload_compared=False, hardware_admitted=False,
                    original_Popper_compile_admitted=False)

    def bind_eligible(self, PC, start, *, generation, owner_tag, response_stall_bound):
        """Actual SILU exp step0 FMAX: source neg(gate), broadcast f32(-87)."""
        require(self.enabled, 'operand adapter default off')
        require(type(PC) is int and 0 <= PC < 1737, 'source PC')
        op = self.native['operations'][PC]
        require(op['opcode'] == 'SILU_GATE', 'eligible source recipe not enrolled')
        size = self.native['source_program']['config']['intermediate_size']//2
        require(type(start) is int and 0 <= start <= size-128 and start%128 == 0, 'source SILU tile loop')
        require(all(type(v) is int and 0 < v < 2**64 for v in (generation,owner_tag)), 'source parent identity')
        require(type(response_stall_bound) is int and response_stall_bound > 0, 'finite response bound')
        require(self.native['microcode']['exp'][0] == dict(dst='ex',op='FMAX',src=['x','f32(-87)']),
                'literal exp step0')
        # Prove the caller chain and dtype from original execution/VM code.
        source = sources()['qwen_provider.py'].decode()
        require("ex=self.kernel('exp',x=self.kernel('neg',x=gate))" in source
                and "elif op=='FMAX': v=np.maximum(*a).astype(F)" in source,
                'actual SILU caller/FMAX dtype')
        gate = self.view(op['reads'][0], start,128,0,'read',PC)
        gate['symbol'] = 'gate'
        prefix = f"native:{sha(sources()['Qwen_tiled.json.gz'])}:PC{PC}:tile{start}:epoch{generation}"
        def transient(symbol,slot,expression,producer):
            return dict(version=prefix+':'+symbol,lease=prefix+':lease:'+symbol,
                        rank=0,SM=0,generation=generation,physical_RF_id='prospective.Qwen.rank0.SM0.RF',
                        connection_scope='prospective_source_only',RF_vectors=[slot],
                        arithmetic_dtype='F32',storage_dtype='U32',packing='binary32 bitcast U32',
                        source_expression=expression,source_producer=producer,parent55=None)
        negative = transient('neg.out',17,'neg(gate)',dict(template='neg',ordered_step_index=0,
                            source_step=copy.deepcopy(self.native['microcode']['neg'][0]),source_home=gate))
        constant = transient('exp.literal.minus87',18,'f32(-87)',dict(kind='literal_scalar_broadcast',
                             source_template='exp',source_step=0,source_operand=1,
                             literal_bits_U32=int.from_bytes(struct.pack('>f',-87),'big'),
                             scalar_words=1,broadcast_words=128,materialized_bytes=512))
        output = transient('exp.step0.ex',19,'FMAX(x,f32(-87))',dict(template='exp',ordered_step_index=0))
        command = dict(model='Qwen',family='SILU_GATE',source_PC=PC,
                       program_sha256=sha(sources()['Qwen_tiled.json.gz']),template_id='exp',ordered_step_index=0,
                       owner_tag=owner_tag,generation=generation,rank=0,SM=0,opcode='FMAX',
                       source_bittypes=[32,32],destination_bittype=32,
                       source_version_home_refs=[negative,constant],destination_version_home_ref=output,
                       predicate=None,active_lanes=128,source_attrs_rounding={},response_stall_bound=response_stall_bound)
        return dict(schema='C0_SOURCE_ELIGIBLE_OPERAND_VIEWS_R1',native_command=command,
                    source_step=copy.deepcopy(self.native['microcode']['exp'][0]),source_gate_home=gate,
                    client_assignment=dict(client=0,scope='new opt-in source-owned dispatch'),
                    native_owner=[PC,op['writes'],0,0,generation],
                    transient_enrollment=[negative,constant,output],
                    ordered_producer_actions=[
                        dict(action='read_source_home',home=gate,destination_slot=17),
                        dict(action='BITCAST_U',source_slot=17,destination_slot=17),
                        dict(action='broadcast_U32',bits=0x80000000,words=128,destination_slot=18),
                        dict(action='XOR',source_slots=[17,18],destination_slot=17),
                        dict(action='BITCAST_F',source_slot=17,destination_slot=17),
                        dict(action='broadcast_F32',bits=0xc2ae0000,words=128,destination_slot=18),
                        dict(action='FMAX',source_slots=[17,18],destination_slot=19)],
                    alias_fence='read/capture consumed before mirrored write and ACK; slot18 reused only after XOR consumption/reverse',
                    source_arithmetic_contract='FMAX numpy maximum then F32; source NaN propagation and signed-zero ties',
                    source_attrs_rounding={},parent55=None,parent55_scope='NOT_APPLICABLE_DIRECT_RF',
                    retained_caller_vectors=2,primitive_workspace_vectors=3,total_reserved_vectors=5,
                    caller_retention='gate and up remain live through reciprocal and final ordered gate*inverse*up',
                    source_dtype_verified=True,source_SSA_verified=True,payload_compared=False,
                    hardware_admitted=False,original_Popper_compile_admitted=False)


def price_eligible(plan, costs=None):
    c=plan['native_command']; gate=plan['source_gate_home']
    expected=verification_adapter().bind_eligible(c['source_PC'],gate['word_start'],generation=c['generation'],
                    owner_tag=c['owner_tag'],response_stall_bound=c['response_stall_bound'])
    require(plan == expected, 'eligible source packet identity changed')
    # NEG is the original BITCAST_U/XOR/BITCAST_F chain. Literal -87 is
    # broadcast explicitly to one RF vector, not treated as a free second port.
    counts=dict(RF_READ=1,RF_MIRRORED_ACK=1,NEG_BITCAST_U=1,NEG_XOR=1,NEG_BITCAST_F=1,
                CONST_BROADCAST=2,FMAX_READ_PAIR=1,FMAX=1,FMAX_MIRRORED_ACK=1,
                NoC_PAGE=int(gate['remote_from_executor']),CDC=2*int(gate['remote_from_executor']),
                REVERSE_GRANT=4)
    duration=None
    if costs is not None:
        require(set(costs)==set(counts) and all(type(v) in (int,float) and math.isfinite(v) and v>0
                                              for v in costs.values()), 'complete eligible finite positive ns costs')
        duration=sum(counts[k]*costs[k] for k in counts)
    return dict(service_counts=counts,latency_expression_ns=' + '.join(f'{v}*C_{k}' for k,v in counts.items()),
                latency_ns=duration,costs_ns=costs,RF_ports='2R1W mirrored, frozen owner across producer/native/consumer',
                cost_units='NEG_* are complete atomic source primitive RF read/capture/write/ACK services; CONST_BROADCAST includes materialization and mirrored ACK',
                source_gate_read_bytes=512,constant_broadcast_bytes=1024,new_HBM_bytes=0,new_RF_macros=0,
                total_reserved_vectors=5,MACs=0,FMAXs=128,
                collector_wire_bits=None,collector_tracks=None,incremental_control_area_mm2=None,
                unknowns=['actual source-owned C0 issuer wiring/collector and source SSA enrollment in emitter',
                          'finite positive source-matched service costs and cut capacity'],
                component_build_admitted=False,whole_die_required_for_source_adapter=False)


@functools.lru_cache(maxsize=1)
def verification_adapter():
    return OperandViews(enabled=True)


def price(plan, costs=None):
    """One serialized tile. Two reads use 2R; each output home uses mirrored 1W."""
    c = plan.get('source_command', plan['native_command'])
    expected = verification_adapter().bind(c['source_PC'], c['source_version_home_refs'][0]['word_start'],
                    generation=c['generation'], owner_tag=c['owner_tag'], response_stall_bound=c['response_stall_bound'])
    require(c == expected['native_command'] and plan['source_output_replicas'] == expected['source_output_replicas']
            and plan['source_step'] == expected['source_step'], 'source packet identity changed')
    if 'source_command' in plan:
        require(plan['native_command'] == workspace_command(expected), 'native workspace binding changed')
    reads = c['source_version_home_refs']
    writes = plan['source_output_replicas']
    remote = sum(v['remote_from_executor'] for v in reads + writes)
    # Both reads share the same source home and dual read ports.
    require(len({(v['storage_rank'], v['storage_SM']) for v in reads}) == 1, 'paired source read ports')
    # Home read (2R), native input read (2R), output workspace read; two
    # staging writes, one native result write, two source replicated writes.
    # The workspace also remains leased until all three reverse fences drain.
    counts = dict(RF_READ=3, RF_MIRRORED_ACK=3+len(writes), FADD=1,
                  NoC_PAGE=remote, CDC=2*remote, REVERSE_GRANT=3+len(reads)+len(writes))
    latency = None
    if costs is not None:
        require(set(costs) == set(COSTS) and all(type(v) in (int, float) and math.isfinite(v) and v > 0
                                               for v in costs.values()), 'all finite positive explicit ns costs')
        latency = sum(counts[k]*costs[k] for k in COSTS)
    return dict(service_counts=counts, home_payload_read_bits=8192, home_payload_write_bits=8192,
                workspace_payload_read_bits=12288, workspace_payload_write_bits=12288,
                physical_mirror_write_bits=40960, NoC_payload_bits=4096*remote,
                MACs=0, FADDs=128, RF_read_bits_per_service=8192, RF_write_bits_per_home_service=4096,
                RF_ports='2R1W, two mirrored copies, staging and outputs serialized across source homes',
                service_cost_unit='full 128-lane RF vector / full NoC page, not an assumed one-cycle access',
                max_outstanding_tiles=1, retained_input_vectors=2, retained_output_vectors=1,
                new_HBM_storage_bytes=0, new_RF_macros=0, workspace_vectors_reserved=3,
                workspace_allocation='three of existing primitive_scratch[17,30), exact slots not assigned by this adapter',
                latency_expression_ns=' + '.join(f'{counts[k]}*C_{k}' for k in COSTS), latency_ns=latency,
                costs_ns=costs, route_tracks=None, area_increment_mm2=None,
                physical_unknowns=['source-sized direct-RF collector/dispatcher', 'actual workspace allocation and alias fence',
                                   'route/cut capacity and finite PG/SS setup/FF hold'],
                component_build_admitted=False, whole_die_qualified=False)


def workspace_command(plan):
    """Explicit prospective source-owned connection; not an installed instance."""
    command = copy.deepcopy(plan['native_command'])
    def stage(view, slot):
        return dict(version=view['version'], lease=view['lease'], rank=0, SM=0,
                    generation=command['generation'], physical_RF_id='prospective.Qwen.rank0.SM0.RF',
                    connection_scope='prospective_source_only', RF_vectors=[slot],
                    arithmetic_dtype='F32', storage_dtype='U32', packing='binary32 bitcast U32',
                    source_storage_view=copy.deepcopy(view))
    command['source_version_home_refs'] = [stage(v, slot) for v, slot in
                                         zip(command['source_version_home_refs'], (17,18))]
    command['destination_version_home_ref'] = stage(command['destination_version_home_ref'],19)
    return command


class DirectRFDispatch:
    """New opt-in data-only enrollment; the native emitter remains Dewey's.

    This owns a bounded dispatch tag and a frozen prospective workspace. It
    supplies no arithmetic callback, accepted HBM child or physical receipt.
    Client0 is an explicit policy here, not inferred from a provider class.
    """
    def __init__(self, *, enabled=False):
        self.enabled = enabled
        self.adapter = OperandViews(enabled=enabled)
        self.next_tag = 1
        self.held = None

    def propose(self, PC, start, *, generation, response_stall_bound):
        require(self.held is None, 'one outstanding native tile')
        require(self.next_tag < 2**64, 'dispatch wrap requires epoch/all-copy fence')
        plan = self.adapter.bind(PC, start, generation=generation, owner_tag=self.next_tag,
                                 response_stall_bound=response_stall_bound)
        # Newly owned source contract, within the existing primitive scratch
        # reservation, and disjoint from all persistent operand homes.
        slots = dict(a=17, b=18, out=19)
        allviews = plan['native_command']['source_version_home_refs'] + plan['source_output_replicas']
        require(all(v['RFslot9'] >= 32 for v in allviews), 'workspace/persistent home alias')
        plan['workspace_slots'] = slots
        plan['workspace_scope'] = 'prospective source-owned direct-RF dispatcher allocation, not installed connection'
        plan['binding'] = dict(scope='prospective_source', operand_view_scope='source_derived_direct_RF',
                               RF_vectors=3, client=0, rank=0, SM=0,
                               parent55=None, parent55_reason='direct RF has no W2 frame anchor')
        # Source order: a then b, native add once, destination rank0 then rank1.
        plan['ordered_actions'] = [
            dict(action='read_home_into_workspace', symbol=v['symbol'], home=v, RFslot9=slots[v['symbol']])
            for v in plan['native_command']['source_version_home_refs']]
        plan['ordered_actions'].append(dict(action='native_leaf', source_step=plan['source_step'],
                                            source_slots=[17,18], destination_slot=19))
        plan['ordered_actions'].extend(dict(action='copy_output_to_source_home', home=v, RFslot9=19)
                                       for v in plan['source_output_replicas'])
        plan['source_command'] = copy.deepcopy(plan['native_command'])
        plan['native_command'] = workspace_command(plan)
        self.held = copy.deepcopy(plan)
        return copy.deepcopy(plan)

    def release(self, plan, *, provider_reverse_receipt):
        require(self.held is not None and plan == self.held, 'exact frozen source dispatch')
        require(provider_reverse_receipt.get('native_owner') == plan['native_owner'], 'matched actual parent owner')
        # Typed software-source seam, explicitly never an installed ACK claim.
        require(provider_reverse_receipt.get('scope') == 'source_provider_software', 'source provider receipt scope')
        require(provider_reverse_receipt.get('all_consumers_done') is True
                and provider_reverse_receipt.get('all_reverse_grants_accepted') is True,
                'actual source reverse retirement required')
        expected = [(v['source_provider_ref'], v['lease'], v['RFslot9'], 2)
                    for v in plan['source_output_replicas']]
        require(provider_reverse_receipt.get('mirrored_write_ACKs') == [list(x) for x in expected],
                'both actual source output homes and mirror ACKs')
        self.next_tag += 1
        self.held = None


def compose_context():
    adapter = OperandViews(enabled=True)
    PCs = [o['pc'] for o in adapter.native['operations'] if o['opcode'] == 'RESIDUAL']
    totals = {k: 0 for k in COSTS}
    home_counts = {}
    for pc in PCs:
        for start in range(0, 4096, 128):
            plan = adapter.bind(pc, start, generation=1, owner_tag=pc*32+start//128+1, response_stall_bound=1)
            for k, v in price(plan)['service_counts'].items():
                totals[k] += v
            for view in plan['native_command']['source_version_home_refs'] + plan['source_output_replicas']:
                key = f"r{view['storage_rank']}/SM{view['storage_SM']}"
                home_counts[key] = home_counts.get(key, 0)+1
    first = adapter.bind(35, 0, generation=1, owner_tag=1, response_stall_bound=1)
    dispatch = DirectRFDispatch(enabled=True).propose(35, 0, generation=1, response_stall_bound=1)
    eligible = adapter.bind_eligible(40,0,generation=1,owner_tag=1,response_stall_bound=1)
    return dict(schema='C0_SOURCE_OPERAND_VIEWS_MODEL_R1', default_enabled=False,
                scope='source metadata, constructor-free; replay owner values are fixtures, not live accepted commands',
                first_command=first, first_dispatch=dispatch, first_command_model=price(first),
                selected_C0_command=eligible,selected_C0_model=price_eligible(eligible),
                C0_eligible_coverage=dict(PC=40,template='exp',step=0,opcode='FMAX',calls_proved=1,
                    wider_RESIDUAL_context='source view coverage only; FADD excluded from original V1 set'),
                coverage=dict(source_PCs=1737, enrolled_PCs=PCs, enrolled_calls=len(PCs)*32,
                              family_complete='RESIDUAL', remaining_PCs=1737-len(PCs),
                              remaining_gate='per-family source SSA/tile recipe, arithmetic dtype and explicit runtime view enrollment'),
                service_counts=totals, home_view_counts=home_counts,
                complete_family_latency_expression_ns=' + '.join(f'{totals[k]}*C_{k}' for k in COSTS),
                source_views_gate='PASS', real_checkpoint_payload_gate='NOT_RUN',
                installed_connection_gate='NOT_RUN', production_component_admission='FAIL',
                preserved_original_guard=True, changed_original_sources=False,
                peer_handoff=dict(Popper='consume source views in owned direct-RF path; do not run RF views through HBM frame address()',
                                  Dewey='consume same ordered FADD recipe/replica list in existing native emitter; no new emitter here',
                                  parent55='only issuer-produced W2 frame owner46<<9|RFslot9 for HBM frames; absent for direct RF'),
                next_closure=['Popper/Dewey consume direct-RF dispatcher client0 slots17/18/19 in owned emitter',
                              'join actual caller generation/owner tag and publication/mirror/reverse receipts',
                              'price finite collector/cuts/latency; build only default-off component after prospective source/model admission'])


def compose():
    adapter = verification_adapter()
    packet = adapter.bind_eligible(40,0,generation=1,owner_tag=1,response_stall_bound=1)
    return dict(schema='C0_SELECTED_SOURCE_OPERAND_ADAPTER_MODEL_R1',default_enabled=False,
                scope='one actual source C0-eligible command; owner/epoch/stall values in replay are fixtures',
                selected_C0_command=packet,selected_C0_model=price_eligible(packet),
                source_metadata_gate='PASS',constructor_invoked=False,real_checkpoint_payload_gate='NOT_RUN',
                original_Popper_production_gate='FAIL_PROTOCOL_CONTROL_ONLY',hardware_admitted=False,
                prospective_component_build_admission='FAIL_UNPRICED_COLLECTOR_AND_EMITTER_ENROLLMENT',
                broader_context='RESIDUAL source views implemented separately in compose_context; FADD not V1 eligible',
                exact_enrollment_needed=dict(
                    Popper='add source-enrolled direct-RF operand consumer, retaining cdb NativeCompiler unchanged; no RF-to-HBM address fabrication',
                    Dewey='consume exact exp step0 FMAX plus ordered NEG/constant producers and transient SSA leases in owned native emitter',
                    source_rank_SM=[0,0],new_opt_in_client=0,prospective_workspace_slots=[17,18,19],
                    parent55='NOT_APPLICABLE: direct RF, no W2 frame child. HBM issuers alone may supply owner46<<9|RFslot9'),
                remaining_boundaries=['actual caller owner/epoch and software provider publication/mirror/reverse receipts',
                                      'priced direct-RF dispatch/collector ports, cuts and positive service ns',
                                      'actual checkpoint payload compare remains separate from metadata'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical(compose()))


if __name__ == '__main__':
    main()
