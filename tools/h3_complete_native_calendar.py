#!/usr/bin/env python3
"""Full H3 finite SOFTWARE calendar; explicit provisional cycles, never an RTL oracle.

An interval with repeats is a lossless run-length schedule: repeat i owns the
listed credits on [start+i*stride,start+(i+1)*stride). Conservative batches
retain their ports through retirement. No traffic, admission, or ACK is free.
"""
import argparse
import ast
import math
import re
from collections import Counter, defaultdict
import gzip
import hashlib
import heapq
import json
import sys
import subprocess
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = 'results/uarch/h3_complete_native_calendar_20261002'
LOWERING = 'results/uarch/h3_versioned_lowering_20261002'
DISTRIBUTED = 'results/uarch/h3_distributed_norm_endpoint_20261002'
PINS = [f'{folder}/{target}.json.gz' for folder in (LOWERING, DISTRIBUTED)
        for target in ('Qwen', 'DeepSeek')] + [
    DISTRIBUTED + '/model.json', LOWERING + '/manifest.json',
    'results/uarch/qwen_hbm_connected_20261001/common_HBM_backend_provider_binding_r2.json',
    'results/uarch/qwen_hbm_resource_schedule_20261002/required_phase_provider_r7.json',
    'results/uarch/qwen_hbm_downstream_contract_20261002/provider_ports_r8.json',
    'rtl/gpu/ot_gpu_rf_service.sv', 'rtl/gpu/ot_gpu_full_sm_service.sv',
    'tools/deepseek_hbm_complete_memory.py',
    'tools/qwen_hbm_complete_service_provider.py',
    'tools/deepseek_hbm_complete_packed_index_provider.py',
    'tools/h3_complete_native_calendar.py']


def positive(n, label):
    if type(n) is not int or n < 1:
        raise ValueError('positive explicit integer required: ' + label)
    return n


def ceil(n, d):
    return (n + d - 1) // d


def read_json(path):
    if str(path).endswith('.gz'):
        with gzip.open(path, 'rt') as f:
            return json.load(f)
    return json.loads(Path(path).read_text())


def source_bytes(path, commit=None):
    """Read an immutable canonical blob without duplicating a producer artifact."""
    path=Path(path)
    if commit is None:return path.read_bytes()
    if not re.fullmatch('[0-9a-f]{7,40}',commit):raise ValueError('immutable source commit required')
    relative=path.relative_to(ROOT) if path.is_absolute() else path
    if relative.is_absolute() or '..' in relative.parts:raise ValueError('source blob path escape')
    raw=subprocess.check_output(['git','show',commit+':'+relative.as_posix()],cwd=ROOT)
    local=ROOT/relative
    if local.exists() and local.read_bytes()!=raw:raise ValueError('canonical source bytes differ from pinned commit')
    return raw


def native_value_specs(program, template_id):
    widths={};specs={}
    for definition,i in enumerate(program['templates'][template_id]['code']):
        op=i['op']
        if op in ('LOAD','CONST'):w=8 if i['attrs']['dtype']=='I64' else 4
        elif op=='F2I':w=8
        elif op in ('I2F','FADD','FMUL','DIV','SQRT','LDEXP','BITCAST_U','BITCAST_F') or op.startswith('FCMP'):w=4
        else:w=max((widths[v] for v in i['src']),default=8 if op=='IOTA' else 4)
        widths[i['dst']]=w;specs[i['dst']]={'bytes':max(1,math.prod(i['shape']))*w,'width':w,'definition':definition}
    return specs


def resolve_ds_movement_reference(program, template_id, ref, specs=None):
    """Resolve an exact retained SSA instruction and its typed operand."""
    if not isinstance(ref,dict) or ref.get('template')!=template_id:
        raise ValueError('structured retained native instruction reference required')
    index=ref.get('code_index');code=program['templates'][template_id]['code']
    if type(index)!=int or not 0<=index<len(code):raise ValueError('native instruction index out of range')
    node=code[index]
    specs=specs if specs is not None else native_value_specs(program,template_id)
    if ref.get('opcode')!=node['op'] or ref.get('attrs')!=node['attrs'] or ref.get('result_shape')!=node['shape']:
        raise ValueError('native instruction opcode attrs shape mismatch')
    operand=ref.get('operand')
    if operand=='dst':symbol=node['dst'];definition=index
    elif isinstance(operand,str) and re.fullmatch('src:[0-9]+',operand):
        j=int(operand[4:])
        if j>=len(node['src']):raise ValueError('native operand index out of range')
        symbol=node['src'][j];definition=specs.get(symbol,{}).get('definition')
        if definition is None or definition>=index:raise ValueError('native source definition missing')
    else:raise ValueError('native operand role required')
    if ref.get('value')!=symbol:raise ValueError('native operand value mismatch')
    size=specs[symbol]['bytes'];width=specs[symbol]['width']
    offset=ref.get('logical_byte_offset');payload=ref.get('payload_bytes')
    if type(offset)!=int or type(payload)!=int or offset<0 or payload<=0 or offset%width or payload%width or offset+payload>size:
        raise ValueError('native operand typed span out of range')
    return (index,operand),symbol,size,offset,payload


def reprice_h4_intervals(execution, *, costs=None):
    """Recompose retained execution, without arithmetic/provider rerun or r22.

    Producer128B shared transfers each require two actual64B transactions.
    C0 is an explicit provisional software service demand, never an RTL bridge.
    """
    costs = dict(costs or {'scratch64_transaction':8, 'C0_fetch':2,
        'C0_decode':2, 'C0_home_scoreboard':12, 'C0_accept':2,
        'C0_complete':2, 'C0_reverse_retire':2})
    required = {'scratch64_transaction','C0_fetch','C0_decode','C0_home_scoreboard',
                'C0_accept','C0_complete','C0_reverse_retire'}
    if set(costs) != required: raise ValueError('complete H4 cost table required')
    for key,value in costs.items(): positive(value,key)
    old_costs = execution['explicit_provisional_latency']
    rows=[]; shift=0; total_shared=total_commands=0
    for row in execution['ordered_PC_intervals']:
        units=row['cost_units']; commands=units['native_batch']
        if type(commands) is not int or commands<0: raise ValueError('native command repetitions')
        old_shared=units['shared_beat128']; shared64=2*old_shared
        if type(old_shared) is not int or old_shared<0: raise ValueError('shared repetitions')
        before=row['provider_service_ticks']+sum(units[k]*old_costs[k] for k in old_costs)
        if row['end']-row['start'] != before: raise ValueError('retained interval cost mismatch')
        if not row['all_provider_grants_before_PC_retire']: raise ValueError('unretired provider ownership')
        extra_shared=shared64*costs['scratch64_transaction']-old_shared*old_costs['shared_beat128']
        dispatch=commands*sum(v for k,v in costs.items() if k!='scratch64_transaction')
        changed=dict(row);changed.update(start=row['start']+shift,
            end=row['end']+shift+extra_shared+dispatch,
            scratch64_transactions=shared64, C0_command_repetitions=commands,
            C0_service_ticks=dispatch, scratch_reprice_delta=extra_shared,
            RF_service_credit='existing serialized provider/ACK charge retained once',
            native_RTL_bridge=False)
        rows.append(changed);shift+=extra_shared+dispatch
        total_shared+=shared64;total_commands+=commands
    return {'schema':'H4_REPRICED_RETAINED_SOFTWARE_INTERVALS_V1',
        'ordered_PC_intervals':rows, 'software_ticks':execution['ordered_PC_ticks']+shift,
        'baseline_software_ticks':execution['ordered_PC_ticks'], 'delta_software_ticks':shift,
        'scratch64_transactions':total_shared,'C0_commands':total_commands,
        'explicit_provisional_costs':costs,'hardware_clock_admission':False,
        'arithmetic_or_provider_rerun':False,'r22_augmentation_applied':False,
        'qualification':'CPU/native execution retained as software evidence only; all51 H1 family bridges absent',
        'traffic_scope':'existing reduced36layer fixtures; not fullshape checkpoint execution'}


class C0VersionScoreboard:
    """Finite software C0 ABI control; Sagan owns its actual command bridge.

    Immutable identity includes rank/SM/version/generation. Complete, visible,
    consumer accept, reverse grant and retirement are distinct transitions.
    One RF transaction credit stays held from accept through mirrored ACK.
    """
    def __init__(self, entries=512):
        self.capacity=positive(entries,'scoreboard entries');self.live={};self.commands={}
        self.last_generation={};self.RF_owner={}

    def publish(self, identity, home, *, visible=True, future_readers=()):
        if len(identity)!=4: raise ValueError('rank SM version generation identity')
        rank,sm,version,generation=identity
        if type(rank)!=int or rank<0 or type(sm)!=int or not 0<=sm<32 or not version:
            raise ValueError('rank SM version identity')
        positive(generation,'version generation')
        if len(home)!=3 or home[0] not in ('RF','scratch','HBM'):
            raise ValueError('concrete storage base extent required')
        kind,base,size=home;positive(size,'home bytes')
        if type(base)!=int or base<0: raise ValueError('concrete home base required')
        cap={'RF':262144,'scratch':65536,'HBM':1<<27}[kind]
        if base+size>cap: raise ValueError('home physical extent')
        if len(self.live)>=self.capacity: raise ValueError('finite scoreboard exhausted')
        if identity in self.live: raise ValueError('duplicate version identity')
        key=(rank,None if kind=='HBM' else sm,kind,base)
        if generation<=self.last_generation.get(key,0): raise ValueError('stale home generation')
        for ident,e in self.live.items():
            k,b,n=e['home']
            same_scope=ident[0]==rank and (kind=='HBM' or ident[1]==sm)
            if same_scope and k==kind and base<b+n and b<base+size:
                raise ValueError('premature write reuse live home alias')
        self.live[identity]={'home':home,'visible':visible,'readers':set(),
                             'future_readers':set(future_readers),'producer':None}
        self.last_generation[key]=generation

    def accept(self, command, sources, destination):
        if command in self.commands: raise ValueError('duplicate command')
        identities=list(sources)+[destination]
        if any(i not in self.live for i in identities): raise ValueError('unbound version/home')
        owner=destination[:2]
        if any(i[:2]!=owner for i in identities): raise ValueError('cross SM requires priced provider route')
        if owner in self.RF_owner: raise ValueError('RF transaction credit exhausted through ACK')
        if any(not self.live[i]['visible'] for i in sources): raise ValueError('premature read visibility')
        if self.live[destination]['visible'] or self.live[destination]['producer'] is not None:
            raise ValueError('destination already produced')
        self.RF_owner[owner]=command;self.live[destination]['producer']=command
        for i in sources:self.live[i]['readers'].add(command)
        self.commands[command]={'sources':list(sources),'destination':destination,'phase':'accepted'}

    def transition(self, command, phase):
        c=self.commands[command];expected={'accepted':'complete','complete':'mirrored_visible_ACK',
            'mirrored_visible_ACK':'consumer_accept','consumer_accept':'reverse_grant','reverse_grant':'retire'}
        if expected.get(c['phase'])!=phase: raise ValueError('C0 transition order')
        c['phase']=phase
        if phase=='mirrored_visible_ACK':
            self.live[c['destination']]['visible']=True;del self.RF_owner[c['destination'][:2]]
        if phase=='retire':
            for i in set(c['sources']):
                self.live[i]['readers'].remove(command);self.live[i]['future_readers'].discard(command)
            self.live[c['destination']]['producer']=None;del self.commands[command]

    def release(self, identity):
        e=self.live[identity]
        if e['readers'] or e['future_readers'] or e['producer'] is not None:
            raise ValueError('retained lease before reverse retirement or declared future consumer')
        del self.live[identity]


def reprice_h4_native_stages(calendar, program, costs):
    """Add ordered C0 service to the proved native trace, with no new payload run."""
    original_proof=verify_ssa_finite_sm_services(calendar,program)
    keys=['C0_fetch','C0_decode','C0_home_scoreboard','C0_accept','C0_complete','C0_reverse_retire']
    dispatch=[(k,positive(costs[k],k)) for k in keys]
    rows=[];now=0;delta=0
    for old in calendar['stages']:
        phases=[];cursor=0
        for key,value in dispatch[:4]:
            phases.append({'phase':key,'units':1,'start':cursor,'end':cursor+value,
                           'provisional_service_ticks':value})
            cursor+=value
        prefix=cursor
        for phase in old['phases']:
            if phase is old['phases'][-1]:
                for key,value in dispatch[4:]:
                    phases.append({'phase':key,'units':1,'start':phase['start']+cursor,
                        'end':phase['start']+cursor+value,'provisional_service_ticks':value})
                    cursor+=value
            p=dict(phase);p['start']+=cursor;p['end']+=cursor;phases.append(p)
        stride=old['batch_stride']+cursor
        row=dict(old);row.update(start=now,end=now+stride*old['repetitions'],batch_stride=stride,
            phases=phases,C0_command_repetitions=old['repetitions'],native_RTL_bridge=False,
            C0_RF_credit_scope='accept through existing two-mirror visible ACK; conservative batch ownership retained',
            C0_issue_prefix_ticks=prefix)
        now=row['end'];rows.append(row);delta+=cursor*old['repetitions']
    if now!=calendar['software_ticks']+delta:raise ValueError('C0 ordered stage composition')
    return {'schema':'H4_C0_REPRICED_ORDERED_DS_STAGE_SERVICES_V1','stages':rows,
        'software_ticks':now,'baseline_software_ticks':calendar['software_ticks'],
        'C0_added_software_ticks':delta,'C0_commands':sum(r['repetitions'] for r in rows),
        'baseline_native_port_and_lifetime_proof':original_proof,'workspace':calendar['workspace'],
        'workspace_peak_bytes':calendar['workspace_peak_bytes'],
        'constrained_extent_successor_demand':calendar['constrained_extent_successor_demand'],
        'scope':'PC127 rank0 native source-ordered conservative services only; no all2213 payload run',
        'scratch64_transaction_count':None,
        'scratch_count_unknown_reason':'DS relative32MiB workspace is not H1 local64KiB scratch; actual shared movement bridge not bound',
        'payload_executed':False,'hardware_clock_admission':False,
        'physical_workspace_admission':False,'r22_augmentation_applied':False}


def compose_h4_uarch(model_source, parameters, inventory):
    """Source-pinned unified model algorithms with actual H1 configurations.

    Pure unit-sum model excludes opportunistic physical record substitution.
    No executable opcode implementation is inferred from modeled area/rate.
    """
    names={'sm_area','sm_op_cycles','mma_drain_cycles'}
    parsed=ast.parse(model_source);selected=[n for n in parsed.body if isinstance(n,ast.FunctionDef) and n.name in names]
    if {n.name for n in selected}!=names: raise ValueError('unified model functions missing')
    namespace=dict(parameters,math=math,gpu_hardened_columns=lambda:{})
    exec(compile(ast.Module(body=selected,type_ignores=[]),'pinned_unified_model','exec'),namespace)
    result={}
    for target,key,ranks in [('Qwen','qwen',2),('DeepSeek','v41',96)]:
        old=dict(inventory['unified_model']['SM_ELEM'][key]);actual=dict(old)
        config=inventory['bindings']['Qwen_matrix' if key=='qwen' else 'DS_matrix']['config']
        actual['stack_levels']=config['LEV'];actual['group_slot']=False
        area=namespace['sm_area'](actual,64);rf_macros=4*16*2
        rf_area=rf_macros*parameters['SRAM_128X256_UM2']*parameters['GPU_MACRO_PACK']/1e6
        # ASSUMED finite C0 implementation:512 entries of200 bits and512bit command.
        control_bits=512*200+512; mux_bits=512*31
        control_area=(control_bits*parameters['DFF_UM2']+mux_bits*.2)/parameters['GPU_LOGIC_UTIL']/1e6
        per_sm=area['total_mm2']+rf_area+control_area
        result[target]={'actual_H1_config':config,'previous_model_element':old,'reconciled_model_element':actual,
            'ranks':ranks,'SMs_per_rank':32,'total_SM_replicas':ranks*32,
            'clock_policy':{'streaming_target_Hz':1200000000,'serial_chain_target_Hz':900000000,
                'setup_uncertainty_ps':60,'hold_uncertainty_ps':25,'SS_FF_qualification':False,
                'software_tick_to_hardware_clock_conversion':None},
            'RF':{'logical_bytes_per_SM':262144,'physical_mirrored_bytes_per_SM':524288,
                'logical_bytes_per_rank':8388608,'physical_bytes_per_rank':16777216,
                'logical_vectors':512,'workspace_reserved_vectors':32,'retained_source_vectors':480,
                'read_ports':2,'write_ports':1,'physical_write_copies':2,
                'transaction_credit':1,'credit_held_until':'mirrored_visible_ACK',
                'macros_per_SM':rf_macros,'footprint_mm2_per_SM':rf_area},
            'ports_bytes_per_accepted_transaction':{'RF_read_A':512,'RF_read_B':512,
                'RF_write_A':512,'RF_write_B':512,'scratch':64,'matrix_ingest':128},
            'boundary_bits_per_transaction':{'RF_operands':8192,'RF_mirrored_write':8192,
                'scratch':512,'matrix_ingest':1024,'C0_command':512},
            'port_peak_Bpc_is_not_achieved_rate':True,
            'finite_credits_per_SM':{'C0_command':1,'RF_transaction':1,'scratch_transaction':1,
                'scoreboard_entries':512,'provider_tag':1,'reverse_grant':1},
            'compute':{'matrix_macs_per_issue_clk':2048 if key=='qwen' else 512,
                'mode_rates_macs_per_issue_clk':{'INT8':2048} if key=='qwen' else {'BF16':512,'FP8':1024,'FP4':2048},
                'mode_rate_basis':'lane/column analytical peak, mutually exclusive formats; H1 DS exercises BF16 only',
                'unified_area_helper_sum_of_mode_lanes_not_an_issue_rate':area['macs_per_clk'],
                'native_hardware_bound_families':0,
                'actual_H1_opcode_exercised':['FADD'],'general_native_issue_rate':'UNKNOWN_POSITIVE_PROVISIONAL_REQUIRED',
                'communication_intensity_H1_macs_per_ingest_byte':(2048 if key=='qwen' else 512)/128},
            'area':{'matrix_and_SIMT_unit_sum':area,'RF_added_mm2_per_SM':rf_area,
                'C0_ASSUMED_mm2_per_SM':control_area,'modeled_lower_mm2_per_SM':per_sm,
                'modeled_lower_mm2_per_rank':32*per_sm,
                'excluded':'unimplemented generic SFU/reduction/movement/collective units; measured slot-fit UNKNOWN'},
            'routing':{'local_payload_tracks_lower':8192+8192+512+1024+512,
                'replicas':32,'command_mux_2to1_bit_equivalents':mux_bits,'command_demux_destinations':32,
                'broadcast_fanout':32,'channel_capacity_tracks':None,'slot_fit':None,
                'admission':'BLOCKED until actual floorplan channel/escape and complete endpoint areas'},
            'formula_drain_cycles_before':namespace['mma_drain_cycles'](old),
            'formula_drain_cycles_actual_config':namespace['mma_drain_cycles'](actual),
            'matvec_issue_comparison':[{'rows_per_rank':rows,'K':5120,'format':'fp8',
                'previous_group_slot_cycles':namespace['sm_op_cycles'](rows,5120,'fp8',1,True),
                'actual_row_slot_cycles':namespace['sm_op_cycles'](rows,5120,'fp8',1,False)}
                for rows in (32,64,256)] if key=='v41' else [],
            'hardware_admission':False}
    return {'schema':'H4_SOURCE_PINNED_ACTUAL_CONFIG_UNIFIED_COMPOSITION_V1','designs':result,
        'status':'MODELED_SOFTWARE_SERVICE_DEMAND_HARDWARE_UNQUALIFIED',
        'area_basis':'unified sm_area pure unit-sum; RF macro footprints + explicitly assumed C0 DFF/mux; lower bound',
        'measured_costs':'UNKNOWN; positive provisional calendar separate',
        'C0_bridge_owner':'Sagan','composed_model_owner':'Dewey'}


def verify_portable_producer(path, native):
    """Validate archived producer bytes without consulting another checkout."""
    pin_path = path.parent / 'producer_pins.json'
    if not pin_path.exists():
        return {}
    pins = read_json(pin_path)
    if pins.get('schema') != 'H3_PORTABLE_PRODUCER_PINS_V1':
        return {}  # Retained historical snapshot receipt, not this closure ABI.
    sources = {}; producer = {}
    for relative, pin in pins['files'].items():
        archived = (path.parent / relative).resolve()
        if not archived.is_relative_to(path.parent.resolve()):
            raise ValueError('producer archive path escape')
        raw = archived.read_bytes(); digest = hashlib.sha256(raw).hexdigest()
        if digest != pin['sha256']:
            raise ValueError('portable producer source pin mismatch: ' + relative)
        sources[str(archived)] = digest; producer[pin['path']] = digest
    if str(path.resolve()) not in sources:
        raise ValueError('portable producer lacks native input pin')
    for name, digest in native.get('source_sha256', {}).items():
        if producer.get(name) != digest:
            raise ValueError('portable producer source closure incomplete: ' + name)
    return sources


def split_i64_words(value):
    """Software R20 codec: preserve signed source bits in two LE words."""
    import numpy as np
    bits = np.asarray(value, dtype=np.int64).view(np.uint64)
    return (bits & np.uint64(0xffffffff)).astype('<u4'), (bits >> np.uint64(32)).astype('<u4')


def join_i64_words(low, high, low_identity, high_identity):
    import numpy as np
    if low_identity != high_identity or not low_identity:
        raise ValueError('I64 codec owner/definition/iteration mismatch')
    low = np.asarray(low, dtype='<u4'); high = np.asarray(high, dtype='<u4')
    if low.shape != high.shape:
        raise ValueError('I64 codec missing highword extent')
    return (low.astype(np.uint64) | (high.astype(np.uint64) << np.uint64(32))).view(np.int64)


def load_workspace_provider(path, native_sha256):
    join = read_json(path)
    if join['source_native_sha256'] != native_sha256:
        raise ValueError('workspace final native source mismatch')
    homes_path = path.parent / 'temporary_provider_homes.json.gz'
    if hashlib.sha256(homes_path.read_bytes()).hexdigest() != join['temporary_provider_homes_sha256']:
        raise ValueError('workspace home pin mismatch')
    homes = read_json(homes_path); index = {}
    for home in homes:
        key = home['pc'], home['rank'], home['symbol']
        if key in index:
            raise ValueError('duplicate workspace home')
        index[key] = home
    return {'join': join, 'homes': index, 'input_path': str(path),
            'sources': verify_portable_producer(path, {})}


def load_pinned_module(path, digest):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('executable provider source pin mismatch')
    name = 'h3_provider_' + digest[:16]
    module = types.ModuleType(name); module.__file__ = str(path)
    sys.modules[name] = module
    old = list(sys.path)
    try:
        sys.path.insert(0, str(ROOT / 'tools'))
        exec(compile(raw, str(path), 'exec'), module.__dict__)
    finally:
        sys.path[:] = old
    if hasattr(module, 'ROOT'):
        module.ROOT = ROOT
    return module


def audit_bounded_export(native, graph):
    """Count/binding audit of executable tile IR, not a fabricated macro trace."""
    if native['schema'] != 'opentallas.H3.qwen-bounded-tiled-native.v1':
        raise ValueError('bounded native schema required')
    if native['feasibility']['temporary_HBM_bytes'] != 0:
        raise ValueError('bounded native unexpectedly materializes HBM temporaries')
    provider=native['provider_binding']
    homes,reuse,releases,provider_ops=bind_provider_homes(provider,graph,{})
    check_homes(homes,graph)
    references={h['provider_ref']:h for h in provider['version_homes']}
    for operand in native['operands']:
        for h in operand['homes']:
            if 'home' in h and (h.get('provider_ref') not in references or h!=references[h['provider_ref']]):
                raise ValueError('bounded retained concrete home mismatch')
    abi = native['tile_kernel_ABI']; rows = []; totals = Counter()
    for name, kernel in abi.items():
        observed = Counter()
        for step in kernel['steps']:
            observed.update(step['native_steps'])
            if math.prod(step['write']['shape_max']) > 128 or step['write']['RF_vectors_max'] > 32:
                raise ValueError('bounded kernel RF/tile overcapacity')
            if not step['round_point']:
                raise ValueError('bounded arithmetic contract missing')
        if dict(observed) != kernel['native_counts_per_invocation']:
            raise ValueError('bounded kernel primitive count mismatch ' + name)
    if len(native['operations']) != len(graph['operations']):
        raise ValueError('bounded PC coverage mismatch')
    for op, source in zip(native['operations'], graph['operations']):
        if any(op[k] != source[k] for k in ('pc', 'opcode', 'reads', 'writes', 'dependencies')):
            raise ValueError('bounded source PC/version/dependency mismatch')
        export = op['calendar_export']; physical = export['physical_primitives']; counts = Counter()
        for name, repetitions in physical['kernel_invocations'].items():
            positive(repetitions, 'bounded kernel repetition')
            counts.update({k: v * repetitions for k, v in abi[name]['native_counts_per_invocation'].items()})
        if dict(counts) != physical['native_primitive_commands']:
            raise ValueError('bounded all-PC primitive count mismatch')
        if export['RF_workspace_vectors'] > 32 or export['shared_reserved_bytes'] > 65536 or export['temporary_HBM_bytes'] != 0:
            raise ValueError('bounded workspace capacity exhausted')
        totals.update(counts)
        rows.append({'pc': op['pc'], 'opcode': op['opcode'], 'primitive_commands': dict(counts),
            'kernel_invocations': physical['kernel_invocations'], 'providers': op['provider_binding']})
    return {'status': 'PASS_BOUNDED_ALL_PC_SOURCE_BINDINGS_AND_PRIMITIVE_COUNTS', 'PCs': len(rows),
        'classes': len({r['opcode'] for r in rows}), 'PCs_detail': rows, 'primitive_commands': dict(totals),
        'workspace': native['feasibility'], 'fullshape_ordered_runtime_trace_executed': False,
        'retained_source_home_proof':{'status':'PASS_CONCRETE_HOME_APERTURE_LIFETIME_AND_REUSE',
            'data_homes':len(provider['version_homes']),'control_homes':len(provider['control_homes']),
            'versions':len(native['operands']),'reuse_home_count':len(reuse),
            'RF_workspace_slots':list(range(32)),'RF_source_slots':'32..511, disjoint from native workspace'},
        'fullshape_companion_scope': 'conservative service reservation, not actual ordered instruction trace',
        'physical_or_clock_admission': False}


def load_bounded_provider_sources(directory):
    """Load the committed portable closure, including compiler imports."""
    base = Path(directory); pins = read_json(base / 'producer_pins.json')['files']
    for name, pin in pins.items():
        if hashlib.sha256((base / name).read_bytes()).hexdigest() != pin['sha256']:
            raise ValueError('bounded producer closure pin mismatch ' + name)
    for name in ('qwen_hbm_complete_program', 'h3_versioned_lowering', 'h3_distributed_norm_endpoint'):
        path = 'sources/tools/' + name + '.py'
        sys.modules[name] = load_pinned_module(base / path, pins[path]['sha256'])
    if 'bounded_entrypoint.py.source' not in pins or 'baseline.py.source' not in pins:
        raise ValueError('separate bounded entrypoint with preserved baseline required')
    sys.modules['h3_qwen_complete_native']=load_pinned_module(base/'baseline.py.source',pins['baseline.py.source']['sha256'])
    return (load_pinned_module(base / 'bounded_entrypoint.py.source', pins['bounded_entrypoint.py.source']['sha256']),
            load_pinned_module(base / 'provider.py.source', pins['provider.py.source']['sha256']))


def audit_ds_bounded_dispatch(dispatch, *, costs=None):
    """Finite conservative service reservations, with physical inadmission.

    This is deliberately an intermediate reservation of the pinned forward
    instruction executor, not an invented opcode-sorted native timeline.
    Every rank holds its32 SM services; execution is serialized within a rank
    and across PCs, so no bandwidth/parallel speedup is assumed. All costs are
    positive estimates. Actual workspace addresses and checkpoint descriptors
    remain required for addressed whole-program execution.
    """
    if dispatch['schema']!='H3_DS_FORWARD_BOUNDED_POLYNOMIAL_DISPATCH_V2':
        raise ValueError('DS bounded forward schema required')
    if dispatch['automatic_scalar_fallback_templates']!=0: raise ValueError('DS recursive fallback rejected')
    costs=dict(costs or {'primitive_scalar':32,'fragment512_read':16*108,'fragment512_write':16*128,
        'route512':64,'admit':2,'retire':2,'visibility_fence':4,'collective_rendezvous':2})
    required={'primitive_scalar','fragment512_read','fragment512_write','route512','admit','retire',
              'visibility_fence','collective_rendezvous'}
    if set(costs)!=required: raise ValueError('complete DS cost table required')
    for key,value in costs.items(): positive(value,key)
    cap=dispatch['workspace']['rank_cap_bytes']; templates=dispatch['templates']; count=Counter(); rows=[]
    demands={}; done=set(); tick=0; successor=[]
    for key,t in templates.items():
        p=t['plan']
        if t['reference_scalar_fallback_admitted'] or not t['no_recomputed_dependency_scalars']:
            raise ValueError('DS recursive fallback rejected')
        demand=p.get('workspace_upper_bytes',p.get('typed_live_workspace_upper_bytes_per_SM',0))
        if t['execution_path'].startswith('forward_'):
            demand+=p.get('quantized_input_provider_bytes_per_rank',p.get('retained_query_bytes',0))
        if demand<=0 or demand>cap: raise ValueError('DS finite workspace exhausted '+key)
        demands[key]=demand
    for op in dispatch['PC_dispatch']:
        if op['pc']!=len(rows) or not set(op['dependencies'])<=done: raise ValueError('DS bounded dependency deadlock')
        totals=Counter(); transfers=Counter(); ranks=defaultdict(lambda:{'work':Counter(),'read':0,'write':0,'templates':[]})
        for call in op['calls']:
            rank=call['rank']; key=call['template']; t=templates[key]
            if not 0<=rank<96 or 'block256%32' not in call['SM_partition']: raise ValueError('DS concrete32SM source binding required')
            totals.update(t['executed_primitive_scalar_projection'])
            transfer=t['provider_transfer_projection']
            transfers.update({k:v for k,v in transfer.items() if type(v) is int})
            ranks[rank]['work'].update(t['executed_primitive_scalar_projection'])
            ranks[rank]['read']+=transfer['read_512B_fragments_upper']
            ranks[rank]['write']+=transfer['write_512B_fragments_upper']
            ranks[rank]['templates'].append(key)
        if dict(totals)!=op['projected_executed_primitive_scalars'] or dict(transfers)!=op['provider_transfer_projection']:
            raise ValueError('DS all-PC primitive/transport count mismatch')
        rank_rows=[]
        for rank,record in sorted(ranks.items()):
            units={'primitive_scalar':sum(record['work'].values()),'fragment512_read':record['read'],
                'fragment512_write':record['write'],'route512':record['read']+record['write'],
                'admit':len(record['templates']),'retire':len(record['templates']),
                'visibility_fence':len(record['templates']),'collective_rendezvous':int(op['family']=='all_gather')}
            duration=sum(units[k]*costs[k] for k in costs)
            rank_rows.append({'rank':rank,'start':tick,'end':tick+duration,
                'cost_units':units,'workspace_peak_upper':max(demands[k] for k in record['templates']),
                'resources':{'SM_issue_leases_each_of_32':1,'source_fragment_credit':1,'write_residence':1,
                    'RF_vectors_per_SM':32,'rank_workspace_bytes':cap},'ordered_executor_templates':record['templates']})
        if not rank_rows: raise ValueError('DS PC has no admitted services')
        end=max(r['end'] for r in rank_rows)
        rows.append({'pc':op['pc'],'family':op['family'],'start':tick,'end':end,'dependencies':op['dependencies'],
            'ranks':rank_rows,'atomic_collective_participants':sorted(ranks) if op['family']=='all_gather' else [],
            'global_collective_credit':int(op['family']=='all_gather'),'writes_visible_before_retire':True,
            'scope':'conservative finite reservation; actual instruction order remains pinned forward executor'})
        count.update(totals); tick=end; done.add(op['pc'])
    for rank in range(96):
        successor.append({'rank':rank,'requested_bytes':cap,'alignment_bytes':512,'address_bits':27,
            'maximum_base_inclusive':(1<<27)-cap,'physical_base':dispatch['workspace']['base'],
            'must_be_disjoint_from':'all retained source homes, immutable checkpoint, persistent provider and every live lease',
            'release_guard':'accepted fragment return, consumer capture, matched reverse grant, source last use',
            'status':'UNBOUND_PHYSICAL_BASE_AND_PROVIDER_LEASE'})
    return {'status':'PASS_ALL_PC_BOUNDED_FINITE_SERVICE_RESERVATION_INTERMEDIATE','PCs':len(rows),
        'families':len({r['family'] for r in rows}),'primitive_scalars':dict(count),'estimated_service_ticks':tick,
        'explicit_provisional_costs':costs,'source_program_sha256':dispatch['source_program_sha256'],
        'PC_intervals':rows,'constrained_extent_successor_demand':successor,
        'ordered_full_native_trace':False,'full_token_numerical_execution':False,
        'checkpoint_scope':'producer fragment projection excludes physical checkpoint fetch; concrete provider range/route binding is required',
        'physical_admission':False,'clock_admission':False,'automatic_scalar_fallback':False}


def compose_ds_full_program_services(dispatch, *, bridge=None, native_program=None, costs=None):
    """All-PC finite service composition using retained producer projections.

    One dispatch per primitive scalar is an explicit conservative command upper,
    not an invented vector speedup. Bridge64B scratch demand is additive only
    when a pinned movement trace actually binds that template; absent is UNKNOWN.
    No numerical executor/provider payload or r22 augmentation runs here.
    """
    baseline=audit_ds_bounded_dispatch(dispatch)
    costs=dict(costs or {'C0_fetch':2,'C0_decode':2,'C0_home_scoreboard':12,
        'C0_accept':2,'C0_complete':2,'C0_reverse_retire':2,'scratch64_read':8,'scratch64_write_ACK':8,
        'atomic_collective_admit':2})
    required={'C0_fetch','C0_decode','C0_home_scoreboard','C0_accept','C0_complete',
              'C0_reverse_retire','scratch64_read','scratch64_write_ACK','atomic_collective_admit'}
    if set(costs)!=required:raise ValueError('complete all-PC service cost table required')
    for key,value in costs.items():positive(value,key)
    bridge_templates={}
    if bridge is not None:
        if native_program is None:raise ValueError('retained native code required for shared bridge validation')
        if bridge.get('schema')!='H4_DS_NATIVE_SHARED_MOVEMENT_BRIDGE_V1':raise ValueError('actual shared movement bridge schema')
        if bridge.get('source_program_sha256')!=dispatch['source_program_sha256']:
            raise ValueError('shared movement program source mismatch')
        if bridge.get('source_dispatch_sha256')!=hashlib.sha256(
                json.dumps(dispatch,sort_keys=True,separators=(',',':')).encode()).hexdigest():
            raise ValueError('shared movement dispatch content mismatch')
        if bridge.get('scratch_beat_bytes')!=64 or bridge.get('scratch_capacity_bytes')!=65536:
            raise ValueError('actual scratch64B/64KiB ABI required')
        if not re.fullmatch('[0-9a-f]{64}',bridge.get('bridge_source_sha256','')):
            raise ValueError('bridge producer source pin required')
        bridge_templates=bridge['templates']
        if not set(bridge_templates)<=set(dispatch['templates']):raise ValueError('unknown bridge native template')
    summaries={}
    for key,t in dispatch['templates'].items():
        r=bridge_templates.get(key)
        if r is None:
            summaries[key]={'status':'UNKNOWN_UNBOUND_SHARED_MOVEMENT','read64':None,'write64':None}
            continue
        if t['execution_path']!='source_order_live_range_stages':
            summaries[key]={'status':'UNKNOWN_FORWARD_LEAF_CONTINUATION_NOT_RESOLVED',
                'read64':None,'write64':None}
            continue
        if key not in native_program['templates']:raise ValueError('bridge retained template missing')
        code=native_program['templates'][key]['code']
        specs=native_value_specs(native_program,key)
        native_counts=Counter()
        for node in code:native_counts[node['op']]+=max(1,math.prod(node['shape']))
        if dict(native_counts)!=t['executed_primitive_scalar_projection']:
            raise ValueError('retained instruction projection mismatch')
        if r.get('execution_path')!=t['execution_path'] or r.get('native_primitive_scalars')!=t['executed_primitive_scalar_projection']:
            raise ValueError('bridge native instruction count/path mismatch')
        movements=r.get('ordered_movements');reads=writes=0;leases={};last_step=-1;covered=defaultdict(list)
        if not isinstance(movements,list):raise ValueError('ordered shared movement commands required')
        for m in movements:
            step=m['source_step'];kind=m['event'];identity=m['lease']
            if type(step)!=int or step<last_step or step<0:raise ValueError('shared source step order')
            last_step=step
            if kind=='acquire':
                base=m['base'];size=m['bytes']
                if identity in leases or type(base)!=int or type(size)!=int or base<0 or size<=0 or base%64 or size%64 or base+size>65536:
                    raise ValueError('finite shared concrete lease extent')
                if any(base<e['base']+e['bytes'] and e['base']<base+size for e in leases.values()):raise ValueError('shared live alias')
                value=m.get('value');offset=m.get('logical_byte_offset');payload=m.get('payload_bytes')
                if value not in specs or type(offset)!=int or type(payload)!=int or offset<0 or offset%64 or payload<=0 or offset+payload>specs[value]['bytes'] or size!=ceil(payload,64)*64:
                    raise ValueError('shared lease does not resolve retained value span')
                leases[identity]={'base':base,'bytes':size,'value':value,'offset':offset,'payload':payload,'written':[]}
            elif kind=='release_after_ACK_reverse':
                if identity not in leases:raise ValueError('unmatched shared retirement')
                del leases[identity]
            elif kind in ('read64','write64_ACK'):
                if identity not in leases:raise ValueError('shared movement missing live lease')
                count=positive(m['repetitions'],'actual shared instruction repetitions')
                lease=leases[identity];base,size=lease['base'],lease['bytes'];address=m['byte_address'];span=m['span_bytes']
                if type(address)!=int or type(span)!=int or address%64 or span<=0 or span%64 or address<base or address+span>base+size:
                    raise ValueError('shared instruction address extent')
                role,symbol,typed_bytes,offset,payload=resolve_ds_movement_reference(native_program,key,m.get('native_instruction_ref'),specs)
                if role[0]!=step or (kind=='read64')!=(role[1]!='dst'):
                    raise ValueError('native movement step/read-write role mismatch')
                if span!=ceil(payload,64)*64 or count!=1:
                    raise ValueError('native movement span/repetitions not resolved from source')
                if symbol!=lease['value'] or offset<lease['offset'] or offset+payload>lease['offset']+lease['payload'] or address!=base+offset-lease['offset']:
                    raise ValueError('shared movement does not match actual value/home slice')
                if kind=='read64' and not any(a<=offset and offset+payload<=b for a,b in lease['written']):
                    raise ValueError('shared read before source write visibility')
                if kind=='write64_ACK':lease['written'].append((offset,offset+payload))
                covered[role].append((offset,offset+payload))
                if kind=='read64':reads+=count*span//64
                else:writes+=count*span//64
            else:raise ValueError('unknown shared bridge movement event')
        if leases:raise ValueError('shared lease retained past template retirement')
        # RF alternatives must resolve the same complete operand obligations.
        # No exported proof string can suppress missing reads/writes.
        routes=r.get('RF_operand_routes',[])
        rf_homes=r.get('RF_value_homes',{});last={}
        for i,node in enumerate(code):
            for symbol in node['src']:last[symbol]=i
        for symbol in native_program['templates'][key]['outputs'].values():last[symbol]=len(code)
        for symbol,home in rf_homes.items():
            if symbol not in specs:raise ValueError('RF home unknown source value')
            slot=home.get('slot_first');vectors=home.get('vectors')
            if type(slot)!=int or type(vectors)!=int or slot<0 or slot+vectors>32 or vectors!=ceil(specs[symbol]['bytes'],512):
                raise ValueError('RF source value home capacity')
        for a,ha in rf_homes.items():
            for b,hb in rf_homes.items():
                if a>=b:continue
                simultaneous=specs[a]['definition']<=last.get(b,specs[b]['definition']) and specs[b]['definition']<=last.get(a,specs[a]['definition'])
                if simultaneous and ha['slot_first']<hb['slot_first']+hb['vectors'] and hb['slot_first']<ha['slot_first']+ha['vectors']:
                    raise ValueError('RF live source value home alias')
        for route in routes:
            role,symbol,size,offset,payload=resolve_ds_movement_reference(native_program,key,route.get('native_instruction_ref'),specs)
            slot=route.get('slot_first');vectors=route.get('vectors')
            if type(slot)!=int or type(vectors)!=int or slot<0 or vectors<1 or slot+vectors>32 or vectors!=ceil(payload,512):
                raise ValueError('finite source-resolved RF operand route')
            if route.get('visibility_guard')!='two-mirror visible_ACK':raise ValueError('RF route missing mirrored ACK')
            if rf_homes.get(symbol)!={'slot_first':slot,'vectors':vectors} or offset!=0 or payload!=size:
                raise ValueError('RF route does not match source value home')
            covered[role].append((offset,offset+payload))
        for i,node in enumerate(code):
            for operand in ['dst']+['src:'+str(j) for j in range(len(node['src']))]:
                spans=sorted(covered[(i,operand)]);cursor=0
                for start,end in spans:
                    if start!=cursor:raise ValueError('incomplete or duplicate native movement operand coverage')
                    cursor=end
                symbol=node['dst'] if operand=='dst' else node['src'][int(operand[4:])];size=specs[symbol]['bytes']
                if cursor!=size:raise ValueError('incomplete native movement operand coverage')
        summaries[key]={'status':'BOUND_SOFTWARE_MOVEMENT_TRACE','read64':reads,'write64':writes,
                        'bridge_source_sha256':bridge['bridge_source_sha256'],
                        'actual_source_instruction_operand_coverage':True}
    rows=[];tick=0;commands=shared_reads=shared_writes=0;unknown_calls=0;count=Counter()
    dispatch_cost=sum(v for k,v in costs.items() if k.startswith('C0_'))
    for op,old in zip(dispatch['PC_dispatch'],baseline['PC_intervals']):
        by_rank=defaultdict(lambda:{'native':Counter(),'read64':0,'write64':0,'unknown':[],'templates':[]})
        for call in op['calls']:
            key=call['template'];r=by_rank[call['rank']];r['native'].update(dispatch['templates'][key]['executed_primitive_scalar_projection'])
            r['templates'].append(key);s=summaries[key]
            if s['read64'] is None:r['unknown'].append(key);unknown_calls+=1
            else:r['read64']+=s['read64'];r['write64']+=s['write64'];shared_reads+=s['read64'];shared_writes+=s['write64']
        rank_rows=[]
        for old_rank in old['ranks']:
            rank=old_rank['rank'];r=by_rank[rank];n=sum(r['native'].values());commands+=n;count.update(r['native'])
            c0=n*dispatch_cost;shared=r['read64']*costs['scratch64_read']+r['write64']*costs['scratch64_write_ACK']
            duration=old_rank['end']-old_rank['start']+c0+shared
            rank_rows.append({'rank':rank,'start':tick,'end':tick+duration,
                'native_scalar_command_upper_by_opcode':dict(r['native']),'C0_command_upper':n,
                'C0_ticks':c0,'shared_known_ticks':shared,
                'scratch64_reads':None if r['unknown'] else r['read64'],
                'scratch64_writes_ACK':None if r['unknown'] else r['write64'],
                'bound_shared_read64_subtotal':r['read64'],'bound_shared_write64_subtotal':r['write64'],
                'unknown_shared_templates':r['unknown'],'baseline_provider_and_native_ticks_charged_once':old_rank['end']-old_rank['start'],
                'workspace_peak_upper':old_rank['workspace_peak_upper'],'resources':old_rank['resources'],
                'C0_and_scratch_transaction_credits_per_SM':1,'scoreboard_entries_per_SM':512,
                'RF_credit_held_until':'two-mirror visible_ACK','ordered_executor_templates':r['templates']})
        collective=op['family'] in ('all_gather','all_reduce','topk_merge')
        # all_gather's existing provisional admission is already in baseline.
        collective_delta=costs['atomic_collective_admit'] if collective and op['family']!='all_gather' else 0
        end=max(r['end'] for r in rank_rows)+collective_delta
        rows.append({'pc':op['pc'],'family':op['family'],'start':tick,'end':end,'ranks':rank_rows,
            'dependencies':op['dependencies'],'atomic_collective_participants':sorted(by_rank) if collective else [],
            'global_collective_credit':int(collective),'additional_atomic_admission_ticks':collective_delta,
            'actual_collective_payload_route_ticks':None if collective else 'not a collective PC',
            'shared_scope_complete':not any(r['unknown_shared_templates'] for r in rank_rows)})
        tick=end
    return {'schema':'H4_DS_ALL_PC_FINITE_KNOWN_SERVICE_COMPOSITION_V1','PCs':len(rows),
        'families':baseline['families'],'PC_intervals':rows,'source_program_sha256':dispatch['source_program_sha256'],
        'native_scalar_commands_upper_by_opcode':dict(count),'C0_scalar_command_upper':commands,
        'known_service_software_ticks':tick,'complete_service_software_ticks':None,
        'scratch64_read_transactions':None if unknown_calls else shared_reads,
        'scratch64_write_ACK_transactions':None if unknown_calls else shared_writes,
        'bound_scratch64_read_subtotal':shared_reads,'bound_scratch64_write_ACK_subtotal':shared_writes,
        'unknown_shared_template_calls':unknown_calls,'template_shared_bindings':summaries,
        'constrained_extent_successor_demand':baseline['constrained_extent_successor_demand'],
        'explicit_provisional_costs':costs,'retained_baseline_provisional_costs':baseline['explicit_provisional_costs'],
        'status':'PARTIAL_KNOWN_SERVICE_COST_WITH_EXPLICIT_SHARED_UNKNOWNS' if unknown_calls else 'PASS_ALL_PC_NATIVE_AND_SHARED_COST_JOIN_WITH_CHECKPOINT_GAP',
        'native_command_count_scope':'one command per scalar is conservative upper; actual vector/loop bridge needed',
        'checkpoint_traffic_cost':'UNKNOWN_NOT_INCLUDED_IN_KNOWN_SUBTOTAL',
        'ordered_full_native_trace':False,'arithmetic_or_provider_rerun':False,'r22_augmentation_applied':False,
        'hardware_full_native_claim':False,'clock_admission':False,'physical_admission':False}


def compile_ssa_finite_sm_services(program, *, rank, provider_bindings, workspace=None, costs=None):
    """Ordered native stage issue templates and bounded last-use allocation.

    Input is actual source SSA, never a macro callback or opcode histogram.
    Blocks are lossless128-lane repetitions. Source block256%32 selects the
    issuing SM; all services serialize, with no assumed32SM speedup. Operand
    transport deliberately reloads a whole source before each result batch,
    a positive conservative bound until actual indexed provider traffic exists.
    This compiler does not execute payloads or supply RTL implementations.
    """
    if type(rank) is not int or not 0<=rank<96: raise ValueError('DS rank extent')
    if set(provider_bindings)!=set(program['providers']): raise ValueError('exact native provider LOAD bindings required')
    cap=33554432; workspace=dict(workspace or {'AW':27,'base':None,'bytes':cap,'occupied_extents':[]})
    if workspace.get('AW')!=27 or workspace.get('bytes')!=cap: raise ValueError('AW27/32MiB provider workspace required')
    base=workspace.get('base')
    if base is not None:
        if type(base) is not int or base<0 or base%512 or base+cap>1<<27: raise ValueError('workspace aperture/alignment')
        if 'occupied_extents' not in workspace: raise ValueError('actual occupied provider extents required')
        for e in workspace['occupied_extents']:
            if type(e['base']) is not int or type(e['bytes']) is not int or e['base']<0 or e['bytes']<=0 or e['base']+e['bytes']>1<<27:
                raise ValueError('occupied provider extent aperture')
            if base<e['base']+e['bytes'] and e['base']<base+cap: raise ValueError('workspace/provider live alias')
    costs=dict(costs or {'native_batch':32,'RF_read_vector':3,'RF_mirrored_write_ACK':3,
        'HBM_sector_read':108,'HBM_sector_write':128,'RMW_merge':32,'route_fragment512':64,'admit':2,'consume':2,'retire':2})
    if set(costs)!={'native_batch','RF_read_vector','RF_mirrored_write_ACK','HBM_sector_read',
                   'HBM_sector_write','RMW_merge','route_fragment512','admit','consume','retire'}:
        raise ValueError('complete explicit SM/provider costs required')
    for key,value in costs.items():positive(value,key)
    code=program['code']; last={}; width={}; sizes={}; live={}; free=[(0,cap)]; stages=[]; released=[]
    tick=0; peak=0; generations=Counter(); counts=Counter(); batches=Counter()
    for index,node in enumerate(code):
        for ref in node['src']:last[ref]=index
    for ref in program['outputs'].values():last[ref]=len(code)
    def release(name,index):
        h=live.pop(name);free.append((h['offset'],h['reserved_bytes']));free.sort();merged=[]
        for address,size in free:
            if merged and merged[-1][0]+merged[-1][1]==address:merged[-1]=(merged[-1][0],merged[-1][1]+size)
            else:merged.append((address,size))
        free[:]=merged
        released.append({'symbol':name,'after_stage':index,'after_tick':tick,'generation':h['generation'],
                         'guard':'last source use and every accepted write/consumer/reverse grant retired'})
    for index,node in enumerate(code):
        for name in list(live):
            if last.get(name,-1)<index:release(name,index-1)
        op=node['op'];dst=node['dst'];args=node['src'];attrs=node.get('attrs',{})
        if dst in sizes or any(ref not in live for ref in args):raise ValueError('native SSA alias or premature source reuse')
        if any(type(d) is not int or d<0 for d in node['shape']):raise ValueError('native result shape extent')
        n=max(1,math.prod(node['shape']))
        w=(8 if attrs.get('dtype')=='I64' else 4) if op in ('LOAD','CONST') else 8 if op in ('F2I','IOTA') else (
            4 if op in ('I2F','FADD','FMUL','DIV','SQRT','LDEXP','BITCAST_U','BITCAST_F') or op.startswith('FCMP')
            else max((width[r] for r in args),default=4))
        length=max(512,ceil(n*w,512)*512)
        chosen=next((j for j,(_,size) in enumerate(free) if size>=length),None)
        if chosen is None:
            return {'status':'CONSTRAINED_NATIVE_WORKSPACE_SUCCESSOR_REQUIRED','failed_stage':index,'opcode':op,
                'requested_definition_bytes':length,'live_definitions':live,'live_bytes':sum(h['reserved_bytes'] for h in live.values()),
                'largest_free_span_bytes':max((size for _,size in free),default=0),'workspace_bytes':cap,
                'source_order_stages_completed':len(stages),'stages':stages,'hardware_or_clock_admission':False,
                'successor':'refine this exact stage/shape under source rounding and last-use order; do not wrap addresses or stop other templates'}
        address,room=free[chosen];free[chosen:chosen+1]=[(address+length,room-length)] if room>length else []
        generations[address]+=1
        home={'offset':address,'base':None if base is None else base+address,'reserved_bytes':length,
              'typed_bytes':n*w,'generation':generations[address],'release_after_stage':last.get(dst,index)}
        source_homes={ref:dict(live[ref]) for ref in args}
        live[dst]=home;width[dst]=w;sizes[dst]=n*w;peak=max(peak,sum(h['reserved_bytes'] for h in live.values()))
        repeats=ceil(n,128);frame_vectors=3+sum(ceil(min(128,n)*width[r],512) for r in args)+ceil(min(128,n)*w,512)
        if frame_vectors>32:raise ValueError('finite RF32 primitive frame exhausted')
        reads=sum(ceil(sizes[r],512) for r in args)
        external=None
        if op=='LOAD':
            name=attrs['name'];external=provider_bindings.get(name)
            if external is None or not external.get('kind'):raise ValueError('missing actual source provider reference')
            if external['kind']=='versioned_operand' and not external.get('version'):
                raise ValueError('versioned provider source identity required')
            spec=program['providers'][name]
            if spec['shape']!=node['shape'] or spec['dtype']!=attrs['dtype']:
                raise ValueError('exact native provider shape/dtype required')
            reads+=ceil(n*w,512)
        phases=[{'phase':'admit','units':1,'cost':'admit'},
            {'phase':'provider_read_capture_and_reverse_grant','units':reads*16,'cost':'HBM_sector_read'},
            {'phase':'provider_route','units':reads,'cost':'route_fragment512'},
            {'phase':'RF_operand_reads_2R','units':sum(ceil(min(128,n)*width[r],512) for r in args),'cost':'RF_read_vector'},
            {'phase':'consume','units':1,'cost':'consume'},
            {'phase':'native_issue','units':1,'cost':'native_batch'},
            {'phase':'RF_two_mirror_visible_ACK','units':ceil(min(128,n)*w,512),'cost':'RF_mirrored_write_ACK'},
            {'phase':'possible_partial_destination_sector_read','units':1,'cost':'HBM_sector_read'},
            {'phase':'possible_partial_destination_RMW_merge','units':1,'cost':'RMW_merge'},
            {'phase':'workspace_commit_visible_and_reverse_grant','units':ceil(min(128,n)*w,32),'cost':'HBM_sector_write'},
            {'phase':'retire','units':1,'cost':'retire'}]
        cursor=0
        for phase in phases:
            phase['start']=cursor;cursor+=phase['units']*costs[phase['cost']];phase['end']=cursor
        stages.append({'stage':index,'op':op,'src':list(args),'dst':dst,'shape':node['shape'],'attrs':attrs,
            'scalar_elements':n,'semantic_bits':w*8,'source_homes':source_homes,'destination_home':dict(home),
            'external_provider_binding':external,'start':tick,'end':tick+cursor*repeats,
            'repetitions':repeats,'batch_stride':cursor,'last_batch_lanes':n-(repeats-1)*128,
            'phases':phases,'SM_recipe':'((batch_index*128)//256)%32','RF_frame_vectors_upper':frame_vectors,
            'resources_per_batch':{'RF_read_ports':2,'RF_write_ports':1,'RF_mirrors':2,'provider_tag':1,
                'request_queue':1,'write_residence':1,'rank_route_credit':1,'SM_issue_credit':1},
            'native_implementation_binding':'UNKNOWN_PENDING_H4_OWNER; software estimate only',
            'rounding_and_movement_contract':{'op':op,'attrs':attrs,'source_stage_order':index},'payload_executed':False})
        counts[op]+=n;batches[op]+=repeats;tick+=cursor*repeats
    outputs={name:dict(live[ref],symbol=ref) for name,ref in program['outputs'].items()}
    for name in list(live):release(name,len(code))
    return {'status':'PASS_ORDERED_NATIVE_STAGE_FINITE_SM_SOFTWARE_RESERVATION','rank':rank,'stages':stages,
        'primitive_scalars':dict(counts),'primitive_batches128':dict(batches),'outputs':outputs,'release_events':released,
        'workspace_peak_bytes':peak,'workspace':workspace,'RF_vectors_per_SM':32,'SMs':32,'software_ticks':tick,
        'explicit_provisional_costs':costs,'hardware_cost_calibration':'UNKNOWN_NO_CPU_PRIMITIVE_AS_RTL_CREDIT',
        'concrete_software_address_binding':base is not None,'physical_workspace_admission':False,
        'hardware_or_clock_admission':False,'payload_executed':False,
        'RMW_scope':'one possible partial sector read+merge conservatively charged per batch; contiguous I64, no second r22 sidecar charge',
        'transport_scope':'whole operand reload per result128batch conservative upper; exact indexed traffic remains provider-bound',
        'constrained_extent_successor_demand':[] if base is not None else [{'rank':rank,'bytes':cap,'alignment':512,
            'AW':27,'maximum_base':(1<<27)-cap,'base':None,'release_guard':'source last use + actual backing/consumer/reverse grant drain'}]}


def verify_ssa_finite_sm_services(calendar, program):
    if len(calendar['stages'])!=len(program['code']):raise ValueError('native stage coverage incomplete')
    if calendar['hardware_or_clock_admission'] or calendar['hardware_cost_calibration']!='UNKNOWN_NO_CPU_PRIMITIVE_AS_RTL_CREDIT':
        raise ValueError('CPU/software primitive cannot qualify RTL cost')
    definitions={};groups=defaultdict(list);counts=Counter();batches=Counter();tick=0;last={};width={};sizes={};generations=Counter()
    for index,node in enumerate(program['code']):
        for ref in node['src']:last[ref]=index
    for ref in program['outputs'].values():last[ref]=len(program['code'])
    for index,(stage,node) in enumerate(zip(calendar['stages'],program['code'])):
        if any(stage[k]!=node[k] for k in ('op','src','dst','shape','attrs') if k in node):
            raise ValueError('native instruction/source mismatch')
        n=max(1,math.prod(node['shape']));repeats=ceil(n,128);cursor=0
        op=node['op'];at=node.get('attrs',{});args=node['src']
        w=(8 if at.get('dtype')=='I64' else 4) if op in ('LOAD','CONST') else 8 if op in ('F2I','IOTA') else (
            4 if op in ('I2F','FADD','FMUL','DIV','SQRT','LDEXP','BITCAST_U','BITCAST_F') or op.startswith('FCMP')
            else max((width[r] for r in args),default=4))
        reads=sum(ceil(sizes[r],512) for r in args)+(ceil(n*w,512) if op=='LOAD' else 0)
        expected_units=[1,reads*16,reads,sum(ceil(min(128,n)*width[r],512) for r in args),1,1,
                        ceil(min(128,n)*w,512),1,1,ceil(min(128,n)*w,32),1]
        expected_phases=['admit','provider_read_capture_and_reverse_grant','provider_route','RF_operand_reads_2R',
            'consume','native_issue','RF_two_mirror_visible_ACK','possible_partial_destination_sector_read',
            'possible_partial_destination_RMW_merge','workspace_commit_visible_and_reverse_grant','retire']
        if [p['units'] for p in stage['phases']]!=expected_units or [p['phase'] for p in stage['phases']]!=expected_phases:
            raise ValueError('native provider read/write/native repetition obligations mismatch')
        expected_costs=['admit','HBM_sector_read','route_fragment512','RF_read_vector','consume','native_batch',
            'RF_mirrored_write_ACK','HBM_sector_read','RMW_merge','HBM_sector_write','retire']
        if [p['cost'] for p in stage['phases']]!=expected_costs:raise ValueError('native service cost reference mismatch')
        if stage['start']!=tick or stage['stage']!=index or stage['repetitions']!=repeats or stage['scalar_elements']!=n:
            raise ValueError('native issue/repetition/source order mismatch')
        for ref in node['src']:
            if ref not in definitions or stage['source_homes'][ref]!=definitions[ref] or last[ref]<index:
                raise ValueError('native source lease/generation mismatch')
        for phase in stage['phases']:
            cost=positive(calendar['explicit_provisional_costs'][phase['cost']],phase['cost'])
            if type(phase['units']) is not int or phase['units']<0 or phase['start']!=cursor:
                raise ValueError('native service phase order/capacity')
            cursor+=phase['units']*cost
            if phase['end']!=cursor:raise ValueError('native service phase cost mismatch')
        if stage['batch_stride']!=cursor or stage['end']!=tick+cursor*repeats:
            raise ValueError('native repeated interval cost mismatch')
        if stage['RF_frame_vectors_upper']>32 or stage['resources_per_batch']!=dict(RF_read_ports=2,RF_write_ports=1,
            RF_mirrors=2,provider_tag=1,request_queue=1,write_residence=1,rank_route_credit=1,SM_issue_credit=1):
            raise ValueError('finite SM/provider capacity mismatch')
        home=stage['destination_home'];address=home['offset'];size=home['reserved_bytes']
        generations[address]+=1
        if home['generation']!=generations[address]:raise ValueError('native write reuse generation mismatch')
        if stage['semantic_bits']!=w*8 or home['typed_bytes']!=n*w:
            raise ValueError('native semantic word width/storage mismatch')
        if address<0 or address%512 or size%512 or size<=0 or address+size>calendar['workspace']['bytes']:
            raise ValueError('native workspace extent overrun')
        if home['release_after_stage']!=last.get(node['dst'],index):raise ValueError('premature source write reuse')
        for birth,retire,lo,hi in groups['workspace']:
            if retire>=index and address<hi and lo<address+size:raise ValueError('native live workspace alias')
        groups['workspace'].append((index,home['release_after_stage'],address,address+size))
        definitions[node['dst']]=home;width[node['dst']]=w;sizes[node['dst']]=n*w
        tick=stage['end'];counts[node['op']]+=n;batches[node['op']]+=repeats
    if dict(counts)!=calendar['primitive_scalars'] or dict(batches)!=calendar['primitive_batches128'] or tick!=calendar['software_ticks']:
        raise ValueError('native stage primitive count/total cost mismatch')
    return {'status':'PASS_ORDERED_SOURCE_STAGE_PORT_CREDIT_LIFETIME_AND_COST_PROOF','source_stages':len(calendar['stages']),
        'primitive_batches128':sum(batches.values()),'native_RTL_cost_credit':False,'physical_workspace_admission':False,
        'payload_executed':False,'transport_scope':calendar['transport_scope']}


class AddressedTileByteBackend:
    """Immutable byte requests use R21 real finite ownership and backing.

    Padding is explicitly loader initialized but never a valid logical byte
    range. No response ACK is invented: each ticket drains its reverse grant.
    """
    def __init__(self, K, native):
        self.K = K; self.pc = 0; self.serial = 0; self.loaded = set()
        self.epoch = 0
        self.extents = {e['provider_ref']: dict(e, rank=a['rank'])
            for a in native['provider_binding']['allocation'] for e in a['extents']}
        extents = defaultdict(list)
        for e in self.extents.values():
            extents['Qwen', e['rank']].append({'base': e['base'], 'bytes': ceil(e['bytes'], 32) * 32})
        for rank in range(2):
            for sm in range(32):
                for mirror in range(2):
                    extents[f'Qwen_RF_SM{sm}_copy{mirror}', rank].append({'base': 0, 'bytes': 512*512})
        self.events = Counter(); self.digest = hashlib.sha256()
        owner = self
        class Journal(K.SectorProvider):
            def log(self, event, ticket, **kw):
                super().log(event, ticket, **kw)
                record = self.events.pop(); owner.events[event] += 1
                owner.digest.update(encode(record) + b'\n')
        self.provider = Journal(dict(extents), tags=1, queue=1, write_residence=1)

    def transaction(self, target, rank, sector, payload=None):
        self.serial += 1
        identity = self.K.Identity(target, rank, self.epoch, self.pc, self.serial, sector)
        p = self.provider
        # Explicit RF service estimate, distinct from HBM64/80. All request,
        # owner lookup, CDC and reverse phases remain positive and recorded.
        read, write = (3, 3) if target.startswith('Qwen_RF_') else (64, 80)
        p.read_ticks, p.write_ticks = read, write
        p.costs['read_service'], p.costs['write_service'] = read, write
        t = p.submit(identity, payload is not None, payload or b'')
        value = p.wait(t); p.finish(t)
        return value

    def write_changes(self, target, rank, changes):
        parts = defaultdict(dict)
        for address, byte in changes.items(): parts[address//32][address%32] = int(byte)
        for sector, updates in sorted(parts.items()):
            if len(updates) == 32: data = bytearray(updates[i] for i in range(32))
            else:
                if (target, rank, sector) not in self.provider.backing:
                    self.provider.seed(target, rank, sector*32, bytes(32))
                data = bytearray(self.transaction(target, rank, sector))
                for offset, byte in updates.items(): data[offset] = byte
            self.transaction(target, rank, sector, bytes(data))

    def read_addresses(self, target, rank, addresses):
        captures = {}
        for sector in sorted({int(a)//32 for a in addresses}):
            captures[sector] = self.transaction(target, rank, sector)
        return bytes(captures[int(a)//32][int(a)%32] for a in addresses)

    def seed(self, ref, offset, payload):
        e = self.extents[ref]; address = e['base'] + offset
        if offset < 0 or offset + len(payload) > e['bytes']:
            raise ValueError('immutable loader logical extent')
        # Initialize only touched sector padding; retain an independent logical
        # loaded-byte set so missing checkpoint bytes never turn into zeros.
        for sector in range(address // 32, (address + len(payload) + 31) // 32):
            if ('Qwen', e['rank'], sector) not in self.provider.backing:
                self.provider.seed('Qwen', e['rank'], sector * 32, bytes(32))
        self.provider.seed('Qwen', e['rank'], address, payload)
        self.loaded.update((e['rank'], address + i) for i in range(len(payload)))

    def read_tile_bytes(self, request):
        e = self.extents.get(request.get('provider_ref'))
        if e is None or request.get('lease_state') != 'visible' or request.get('lease') != f'PC{self.pc}.{e["provider_ref"]}':
            raise ValueError('immutable provider lease/ref mismatch')
        payloads = []; captures = {}
        for r in request['byte_ranges']:
            address, size = r['address'], r['bytes']
            if size <= 0 or not e['base'] <= address or address + size > e['base'] + e['bytes']:
                raise ValueError('immutable request logical extent')
            if any((e['rank'], address + i) not in self.loaded for i in range(size)):
                raise ValueError('immutable checkpoint bytes missing')
            for sector in range(address // 32, (address + size + 31) // 32):
                if sector not in captures:
                    captures[sector] = self.transaction('Qwen', e['rank'], sector)
            payloads.append(bytes(captures[(address+i)//32][(address+i)%32] for i in range(size)))
        return {'provider_ref': request['provider_ref'], 'lease': request['lease'], 'state': 'visible',
                'reverse_grant_ACK': not self.provider.live, 'payloads': payloads}

    def proof(self):
        return {'events': dict(self.events), 'journal_sha256': self.digest.hexdigest(),
                'provisional_ticks': self.provider.now, 'all_owners_drained': not self.provider.live,
                'loader_bytes': len(self.loaded), 'hardware_or_clock_admission': False}


def seed_bounded_fixture(N, backend, native, positions):
    """Explicit small raw immutable image loader; excluded from execution costs."""
    import numpy as np
    p = native['source_program']; c = p['config']; raw = N.TileFixtureWeights(p)
    def put(rank, name, offset, data): backend.seed(f'Qwen.rank{rank}.extent.{name}', offset, data)
    for key, d in p['weight_descriptors'].items():
        prefix = 'head' if d['layer'] is None else f'L{d["layer"]}.{d["name"]}'
        for start in range(0, d['rows'], 128):
            n = min(128, d['rows'] - start)
            for col in range(0, d['K'], 32):
                k = min(32, d['K'] - col); codes = raw.matrix_tile(key, start, n, col, k)
                for row in range(n): put(d['die'], prefix+'.codes', (start+row)*d['K']+col, codes[row].tobytes())
            put(d['die'], prefix+'.scales', 2*start,
                (raw.scale_tile(key, start, n).view(np.uint32)>>16).astype('<u2').tobytes())
    h = c['hidden_size']; hd = c['head_dim']
    for rank in range(2):
        for token in range(c['vocab_size']):
            for start in range(0, h, 128):
                codes, scale = raw.embedding_tile(token, start, min(128, h-start))
                put(rank, 'embedding', token*h+start, codes.tobytes())
            put(rank, 'embedding', c['vocab_size']*h+2*token,
                np.array([int(scale.view(np.uint32))>>16], '<u2').tobytes())
        for layer in range(c['num_hidden_layers']):
            put(rank, f'L{layer}.qk_norm', 0, np.full(2*hd, 0x3f80, '<u2').tobytes())
        put(rank, 'final_norm', 0, np.full(h, 0x3f80, '<u2').tobytes())
        for position in positions:
            for start in range(0, hd//2, 128):
                n = min(128, hd//2-start)
                co, si = raw.rope_tile(position, c['rope_theta'], start, n)
                put(rank, 'rope_table', 4*(position*hd+start), co.astype('<f4').tobytes())
                put(rank, 'rope_table', 4*(position*hd+hd//2+start), si.astype('<f4').tobytes())


def execute_bounded_provider_program(N, K, native, backend, *, positions, sidecars=None, observer=None,
                                     latency=None):
    """All-PC tiled execution with R21 addressed microVM arithmetic/transport.

    N and K must be source-pinned producer modules. Immutable bytes come only
    from the caller backend. A finite16KiB RF shadow holds primitive operands;
    optional R20 sidecars use their real low/high addresses, not new extents.
    The shadow and event journals are software models, not physical RF hardware.
    No materialized fullshape calendar or r22 cost augmentation executes here.
    """
    import numpy as np
    latency = dict(latency or {'native_batch':32, 'scratch64_transaction':8, 'NoC_page512':64,
                               'PC_admit':2, 'PC_retire':2, 'visibility_fence':4, 'collective_rendezvous':2})
    required = {'native_batch','scratch64_transaction','NoC_page512','PC_admit','PC_retire','visibility_fence','collective_rendezvous'}
    if set(latency)!=required: raise ValueError('complete explicit latency table required')
    for key,value in latency.items(): positive(value,key)
    if not hasattr(backend, 'read_tile_bytes'):
        raise ValueError('actual raw provider byte backend required')
    sidecars = sidecars or []
    bypc = defaultdict(list)
    for h in sidecars:
        if h.get('semantic_bits') == 64 and h['class_'] == 'HBM_native_workspace':
            bypc[h['pc']].append(h)
    frame_extents = {('Qwen_RF_shadow', 0): [{'base': 0, 'bytes': 16384}]}
    for homes in bypc.values():
        for h in homes:
            es = frame_extents.setdefault(('Qwen', h['rank']), [])
            for base, size in [(h['base'], h['reserved_bytes']), (h['highword_base'], h['highword_reserved_bytes'])]:
                e = {'base': base, 'bytes': size}
                if e not in es: es.append(e)
    # Different PCs reuse arenas: union their address ranges before provider
    # construction. Per-definition ownership still uses immutable generations.
    for key, es in frame_extents.items():
        merged = []
        for e in sorted(es, key=lambda e: e['base']):
            end = e['base'] + e['bytes']
            if merged and e['base'] <= merged[-1]['base'] + merged[-1]['bytes']:
                merged[-1]['bytes'] = max(end, merged[-1]['base'] + merged[-1]['bytes']) - merged[-1]['base']
            else: merged.append(dict(e))
        frame_extents[key] = merged
    journal_counts = Counter(); journal_hash = hashlib.sha256()
    class JournalProvider(K.SectorProvider):
        def log(self, event, ticket, **kw):
            super().log(event, ticket, **kw)
            record = self.events.pop(); journal_counts[event] += 1
            journal_hash.update(encode(record) + b'\n')
    provider = JournalProvider(frame_extents, tags=1, queue=1, write_residence=1)
    frame = K.Storage(provider, 'Qwen_RF_shadow', 0, 0, 16384)
    codec = {rank: K.Storage(provider, 'Qwen', rank, es[0]['base'], es[0]['bytes'])
             for (target, rank), es in frame_extents.items() if target == 'Qwen'}
    pc = [-1]; physical_batches = Counter(); primitive_journal = hashlib.sha256(); step_number = [0]
    pc_rows = []; tick = [0]; position_now = [0]
    sidecar_uses = Counter()
    class Router:
        def __init__(self): self.provider = provider; self.tile = 128; self._epoch = 0; self._pc = 0
        @property
        def epoch(self): return self._epoch
        @epoch.setter
        def epoch(self, value):
            self._epoch = value; frame.epoch = value
            for s in codec.values(): s.epoch = value
        @property
        def pc(self): return self._pc
        @pc.setter
        def pc(self, value):
            self._pc = value; frame.pc = value
            for s in codec.values(): s.pc = value
        def read(self, t, indexes): return (frame if t.target == frame.target else codec[t.rank]).read(t, indexes)
        def write(self, t, start, data): return (frame if t.target == frame.target else codec[t.rank]).write(t, start, data)
        def allocate(self, shape, dtype):
            if dtype == 'I64' and available:
                h = available.pop(0); sidecar_uses[pc[0]] += 1
                return K.tensor_from_native_binding(h, shape)
            return frame.allocate(shape, dtype)
        def free(self, t):
            if t.target == frame.target: frame.free(t)
    router = Router(); available = []
    class AddressedVM(N.NativePrimitiveVM):
        def primitive(self, op, args, attrs=None, shape=None):
            at = dict(attrs or {}); values = [np.asarray(v) for v in args]
            if any(v.size > 128 for v in values): raise ValueError('native operand needs outer tile')
            if at.get('dtype') in ('U32', 'I64'):
                values = [v.astype(np.uint32 if at['dtype'] == 'U32' else np.int64) for v in values]
            if op == 'COPY': operation = 'PACKET_COMMIT'
            else: operation = op
            if operation not in K.MicroVM.SUPPORTED:
                raise ValueError('provider microVM unsupported primitive ' + op)
            if shape is None: shape = list(np.broadcast_shapes(*(v.shape for v in values))) if values else []
            if math.prod(shape) > 128: raise ValueError('native result needs outer tile')
            if provider.live or frame.allocations: raise ValueError('primitive frame reused before reverse grant')
            available[:] = sorted(bypc.get(pc[0], []), key=lambda h: (h['rank'], h['symbol']))
            router.pc = pc[0]; router.epoch += 1; inputs = {}; code = []
            for j, value in enumerate(values):
                dtype = ('F32' if value.dtype.kind == 'f' else 'I8' if value.dtype == np.int8 else
                         'U8' if value.dtype == np.uint8 else 'I64' if value.dtype == np.int64 else 'U32')
                t = router.allocate(tuple(value.shape), dtype); router.write(t, 0, value.reshape(-1))
                inputs[str(j)] = t
                code.append({'op': 'LOAD', 'dst': 'a' + str(j), 'src': [], 'shape': list(value.shape),
                             'attrs': {'name': str(j), 'dtype': dtype}})
            code.append({'op': operation, 'dst': 'out', 'src': ['a' + str(j) for j in range(len(values))],
                         'shape': list(shape), 'attrs': at})
            vm = K.MicroVM(router)
            result_tensor = vm.run({'code': code, 'outputs': {'out': 'out'}, 'source_pc': pc[0]}, inputs)['out']
            result = router.read(result_tensor, np.arange(result_tensor.count)).reshape(shape)
            for entry in vm.journal:
                physical_batches[entry['op']] += 1; primitive_journal.update(encode(entry) + b'\n')
                if entry['staging_payload_bytes'] > 1536: raise ValueError('provider staging capacity exhausted')
            for t in list(inputs.values()) + list(vm.registers.values()): router.free(t)
            if provider.live or provider.queue or provider.resident or frame.allocations:
                raise ValueError('primitive ownership not drained')
            self.counts[op] += 1; self.word_counts[op] += result.size
            self.fault |= vm.fault; step_number[0] += 1
            self.peak_vectors = max(self.peak_vectors, ceil(frame.peak_live_bytes, 512))
            return result
    class TransportWords(N.TileWords):
        def location(self, key, mirror=0):
            kind, rank, sm, page = key
            return (f'Qwen_RF_SM{sm}_copy{mirror}', rank, page*512) if kind == 'RF' else ('Qwen', rank, page)
        def write(self, version, start, values):
            super().write(version, start, values)
            touched = {self.key(version,start+i,rank)[0]
                for rank in {h['rank'] for h in self.values[version]['homes']} for i in range(np.size(values))}
            for key in sorted(touched):
                for mirror, data in enumerate(self.pages[key]):
                    target, rank, base = self.location(key, mirror)
                    raw = data.astype('<u4').tobytes()
                    backend.write_changes(target, rank, {base+i:b for i,b in enumerate(raw)})
        def read_indices(self, version, indices):
            if version not in self.published: raise ValueError('unpublished source')
            ids = np.asarray(indices,np.int64).reshape(-1)
            shape, kind = self.shapes[version]; total = 2 if kind == 'winner' else math.prod(shape)
            if len(ids)>128 or np.any(ids<0) or np.any(ids>=total): raise ValueError('source read aperture')
            result = np.empty(len(ids),np.uint32); rank = self.rank(version)
            for i, word in enumerate(ids):
                key,lane = self.key(version,int(word),rank)
                if self.owners.get(key)!=version or key not in self.pages: raise ValueError('source provider lease identity')
                if self.cache is None or self.cache[0]!=key:
                    copies = []
                    for mirror in range(len(self.pages[key])):
                        target,r,base = self.location(key,mirror)
                        copies.append(np.frombuffer(backend.read_addresses(target,r,range(base,base+512)), '<u4').copy())
                    if len(copies)==2 and not np.array_equal(*copies): raise ValueError('RF mirror disagreement')
                    self.cache = (key,copies[0])
                    self.counters['RF_read' if key[0]=='RF' else 'HBM_read_sectors32'] += 1 if key[0]=='RF' else 16
                    self.counters['source_read_payload_bits'] += 4096
                    if (key[1],key[2])!=(self.worker_rank,self.worker_SM): self.counters['NoC_source_read_bits'] += 4096
                result[i] = self.cache[1][lane]
            self.counters['source_word_reads'] += len(ids)
            return result if kind in ('U32','winner') else result.view(np.float32)
    class TransportKV(N.BoundKVStorage):
        def state_write(self, rank, offset, data):
            super().state_write(rank,offset,data)
            base = self.state[rank]['base']+offset
            backend.write_changes('Qwen',rank,{base+i:b for i,b in enumerate(data)})
        def state_read(self, rank, offset, count):
            e=self.state[rank]
            if offset<0 or offset+count>e['bytes']: raise ValueError('KV state byte aperture')
            # State has an explicit cold zero initialization, unlike checkpoint bytes.
            self.counters['state_read_sectors32'] += len(set((e['base']+offset+i)//32 for i in range(count)))
            return backend.read_addresses('Qwen',rank,range(e['base']+offset,e['base']+offset+count))
        def commit(self, tag):
            state=self.pending[int(tag)]; rank=state['key'][1]
            backend.write_changes('Qwen',rank,state['payload'])
            return super().commit(tag) # publication follows all actual backing grants
        def read(self, lease, addresses):
            super().read(lease,addresses) # validate source producer generation and two-reader lease
            rank=self.leases[int(lease)]['key'][1]
            raw=backend.read_addresses('Qwen',rank,np.asarray(addresses).reshape(-1))
            return np.frombuffer(raw,np.uint8).copy().reshape(np.shape(addresses))
    for e in backend.extents.values():
        if e['name']=='KV_provider_state':
            backend.provider.seed('Qwen',e['rank'],e['base'],bytes(ceil(e['bytes'],32)*32))
    machine = N.TiledMachine(native, N.HBMByteTileProvider(backend)); machine.vm = AddressedVM()
    machine.store = TransportWords(native); machine.memory = TransportKV(native['source_program'])
    original_execute = machine.execute
    def execute(op):
        pc[0] = op['pc']; backend.pc = op['pc']
        before = Counter(machine.vm.counts); batches = Counter(physical_batches)
        begin_provider = provider.now + backend.provider.now
        before_transfer = Counter(machine.store.counters); before_tiles = Counter(machine.counters)
        original_execute(op)
        counts = Counter(machine.vm.counts)-before
        source = native['source_program']['instructions'][op['pc']]
        expected = N.physical_tile_export(source,native['source_program'],position_now[0])['native_primitive_commands']
        if dict(counts)!=expected: raise ValueError('executed PC native primitive count mismatch '+str(op['pc']))
        transfers = Counter(machine.store.counters)-before_transfer; tiles = Counter(machine.counters)-before_tiles
        cost_units = {'native_batch':sum((Counter(physical_batches)-batches).values()),
            'scratch64_transaction':2*(tiles['shared_read_beats128']+tiles['shared_write_beats128']),
            'NoC_page512':(transfers['NoC_source_read_bits']+transfers['NoC_source_write_bits'])//4096,
            'PC_admit':1,'PC_retire':1,'visibility_fence':int(op['opcode']=='KV_FENCE'),
            'collective_rendezvous':int(op['opcode'] in ('ALL_REDUCE','ARGMAX_REDUCE'))}
        extra = sum(latency[k]*v for k,v in cost_units.items())
        elapsed = provider.now + backend.provider.now - begin_provider + extra
        if provider.live or backend.provider.live: raise ValueError('PC retires with retained provider ownership')
        start = begin_provider+tick[0]
        pc_rows.append({'pc':op['pc'],'position':position_now[0],'opcode':op['opcode'],'start':start,
            'end':start+elapsed,'dependencies':op['dependencies'],'native_commands':dict(counts),
            'provider_service_ticks':provider.now+backend.provider.now-begin_provider,
            'cost_units':cost_units,'reads':op['reads'],'writes':op['writes'],
            'all_provider_grants_before_PC_retire':True,'temporary_HBM_bytes':0})
        tick[0] += extra
    machine.execute = execute
    results = []; observer_ticks = [0]
    def observe(op, store):
        before = backend.provider.now+provider.now
        if observer: observer(op,store)
        observer_ticks[0] += backend.provider.now+provider.now-before
    for token, position in positions:
        backend.pc=0; position_now[0]=position
        backend.epoch = position
        results.append(machine.run(token, position, observe if observer else None))
        # Per-PC intervals price only their own transport; cold initialized
        # input publication is reported separately by the total provider ledger.
    result = {'status': 'PASS_ALL_PC_BOUNDED_PROVIDER_MICROVM_EXECUTION', 'executions': results,
        'provider_events': dict(journal_counts), 'provider_journal_sha256': journal_hash.hexdigest(),
        'primitive_journal_sha256': primitive_journal.hexdigest(), 'provider_native_batches': dict(physical_batches),
        'primitive_calls': step_number[0], 'RF_shadow_peak_bytes': frame.peak_live_bytes,
        'R20_sidecar_PC_uses': dict(sidecar_uses), 'all_provider_owners_drained': not provider.live,
        'codec_leases_drained': all(not s.codec_leases and not s.codec_locks for s in codec.values()),
        'provider_ticks': provider.now, 'cost_scope': 'positive provisional provider ticks, separate from existing calendar',
        'source_transport': backend.proof(),
        'native_service_ticks': sum(physical_batches.values())*latency['native_batch'],
        'explicit_provisional_latency':latency,'ordered_PC_intervals':pc_rows,
        'ordered_PC_ticks':tick[0]+provider.now+backend.provider.now,
        'post_commit_test_observer_service_ticks':observer_ticks[0],
        'initial_source_publication_ticks':provider.now+backend.provider.now-sum(r['provider_service_ticks'] for r in pc_rows)-observer_ticks[0],
        'calibration':'UNKNOWN_UNCALIBRATED; all software service estimates explicit and positive',
        'r22_augmentation_applied': False, 'existing_calendar_cost_mutated': False,
        'provider_sector_admission_ticks': 2, 'parent_sector_cost_admission_separately_accounted': True,
        'physical_or_clock_admission': False,
        'sidecar_scope': 'Optional addressed R20 staging experiment; not the zero-temporary-HBM bounded layout' if sidecars else
                         'I64 occupies two32bit words in finite RF shadow; zero additional temporary HBM'}
    result['interval_proof']=verify_bounded_provider_execution(result,native)
    return result


def verify_bounded_provider_execution(result, native):
    rows=result['ordered_PC_intervals'];n=len(native['operations']);done=set();previous=0;position=None
    if len(rows)!=n*len(result['executions']): raise ValueError('bounded executable PC coverage incomplete')
    latency=result['explicit_provisional_latency']
    for key,value in latency.items():positive(value,key)
    for index,row in enumerate(rows):
        if row['position']!=position: done=set();position=row['position']
        op=native['operations'][index%n]
        if row['pc']!=op['pc'] or row['dependencies']!=op['dependencies'] or not set(row['dependencies'])<=done:
            raise ValueError('bounded executable dependency deadlock')
        if row['reads']!=op['reads'] or row['writes']!=op['writes']:raise ValueError('bounded operand version alias')
        duration=row['provider_service_ticks']+sum(latency[k]*v for k,v in row['cost_units'].items())
        if row['start']<previous or row['end']-row['start']!=duration or duration<=0:
            raise ValueError('bounded executable interval overlap/cost mismatch')
        if not row['all_provider_grants_before_PC_retire'] or row['temporary_HBM_bytes']!=0:
            raise ValueError('bounded premature write reuse')
        done.add(row['pc']);previous=row['end']
    for events in (result['provider_events'],result['source_transport']['events']):
        if events['request_accept']!=events['validated_reverse_grant'] or events.get('reverse_quarantine',0):
            raise ValueError('bounded provider credit not drained')
    if not result['all_provider_owners_drained'] or not result['source_transport']['all_owners_drained']:
        raise ValueError('bounded retained provider ownership')
    if result['RF_shadow_peak_bytes']>16384 or any(e['RF_workspace_peak_vectors']>32 or e['shared_tile_peak_bytes']>17408 for e in result['executions']):
        raise ValueError('bounded finite capacity exhausted')
    return {'status':'PASS_ORDERED_PC_DEPENDENCY_COST_AND_FINITE_PROVIDER_PROOF',
        'PC_intervals':len(rows),'source_and_scratch_tags_each':1,'queues_each':1,'write_residence_each':1,
        'physical_or_clock_admission':False}


def execute_primitive_vm(target, program, payloads, *, snapshot, source_sha256,
                         scratch_bytes, instruction_limit, weights=None, storage=None, div=None):
    """Execute producer instructions, with explicit finite software admission.

    DS accepts an SSA template; Qwen accepts a recipe and an expression environment.
    Payloads are caller-supplied arrays, never an opcode/golden callback. This is
    a primitive numerical adapter, not a complete DS provider orchestrator.
    Scratch bounds cover resident tensor values; NumPy process/transient memory
    and hardware residence remain separate gates. No numerical runtime is used
    as a calendar latency. DIV requires an explicit primitive provider.
    """
    import numpy as np
    positive(scratch_bytes, 'VM scratch bytes')
    positive(instruction_limit, 'VM instruction limit')
    raw = Path(snapshot).read_bytes()
    if hashlib.sha256(raw).hexdigest() != source_sha256:
        raise ValueError('primitive VM source pin mismatch')
    tree = ast.parse(raw)
    namespace = {'np': np, '__name__': 'h3_pinned_primitive_vm', '__file__': str(snapshot)}
    if target == 'DeepSeek':
        # Only the producer's primitive machine is loaded; no compiler/module
        # side effects or high-level source operator dispatch can execute.
        machine = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Machine')
        exec(compile(ast.Module(body=[machine], type_ignores=[]), str(snapshot), 'exec'), namespace)
        code = program['code']
        if len(code) > instruction_limit:
            raise ValueError('finite VM instruction capacity exhausted')
        live = {}; last = {}; peak = 0
        for pc, ins in enumerate(code):
            for name in ins['src']: last[name] = pc
        for name in program['outputs'].values(): last[name] = len(code)
        for pc, ins in enumerate(code):
            if ins['dst'] in live or any(name not in live for name in ins['src']):
                raise ValueError('VM SSA alias or premature version consumption')
            # Eight bytes accommodates every producer scalar type, including
            # integer addressing, before any payload execution/allocation.
            live[ins['dst']] = math.prod(ins['shape']) * 8
            peak = max(peak, sum(live.values()))
            if peak > scratch_bytes:
                raise ValueError('finite VM scratch capacity exhausted')
            live = {name: size for name, size in live.items() if last.get(name, -1) > pc}
        vm = namespace['Machine'](program, payloads, div=div)
        outputs = vm.run()
        return {'outputs': outputs, 'events': vm.events, 'fault': vm.fault,
                'resident_tensor_bound_bytes': peak, 'source_sha256': source_sha256}
    if target != 'Qwen':
        raise ValueError('unsupported primitive VM target')
    # Qwen's module defines primitive helpers and its addressed storage class;
    # its __main__ compile/run path is never executed here.
    old_path = list(sys.path)
    try:
        sys.path.insert(0, str(ROOT / 'tools'))
        exec(compile(tree, str(snapshot), 'exec'), namespace)
    finally:
        sys.path[:] = old_path
    base = namespace['Machine']
    class BoundedMachine(base):
        def nodes(self, nodes, env, operation):
            for node in nodes:
                self.executed += 1
                if self.executed > instruction_limit:
                    raise ValueError('finite VM instruction capacity exhausted')
                if node['op'] == 'FOR':
                    start, stop, step = (int(self.value(node[k], env)) for k in ('start', 'stop', 'step'))
                    if start < 0 or stop < 0 or step <= 0:
                        raise ValueError('loop aperture')
                    if len(range(start, stop, step)) > instruction_limit - self.executed:
                        raise ValueError('finite VM loop capacity exhausted')
                    for index in range(start, stop, step):
                        env[node['var']] = index
                        self.nodes(node['body'], env, operation)
                else:
                    super().nodes([node], env, operation)
                size = sum(value.nbytes for value in env.values() if isinstance(value, np.ndarray))
                self.peak = max(self.peak, size)
                if size > scratch_bytes:
                    raise ValueError('finite VM scratch capacity exhausted')
    vm = BoundedMachine.__new__(BoundedMachine)
    vm.weights = weights; vm.storage = storage
    vm.lease_by_version = {}; vm.expression_cache = {}; vm.primitive_counts = Counter()
    vm.executed = 0; vm.peak = 0
    env = dict(payloads)
    if sum(v.nbytes for v in env.values() if isinstance(v, np.ndarray)) > scratch_bytes:
        raise ValueError('finite VM scratch capacity exhausted')
    # Loads/publication require explicit provider objects. Missing bindings
    # fail before instruction dispatch rather than silently installing fixtures.
    def check(nodes):
        for node in nodes:
            if node['op'] == 'FOR': check(node['body'])
            elif node['op'].startswith('LOAD_') and weights is None:
                raise ValueError('unbound native weight provider')
            elif node['op'] in {'BEGIN_WRITE', 'WRITE_BYTES', 'COMMIT_PUBLISH', 'ACQUIRE', 'READ_BYTES', 'CONSUMER_DONE'} and storage is None:
                raise ValueError('unbound native storage provider')
    check(program['recipe'])
    vm.nodes(program['recipe'], env, program)
    return {'outputs': {name: env[name] for name in program['outputs']},
            'primitive_counts': dict(vm.primitive_counts), 'executed_instructions': vm.executed,
            'resident_tensor_bound_bytes': vm.peak, 'source_sha256': source_sha256}


class Calendar:
    """Deterministic earliest-ready DAG scheduler, atomic all-resource admission.

    Slots are concrete finite credit identities. Each reservation holds them
    through final consumption/reverse-credit. Atomic admission removes circular
    hold-and-wait; DAG cycles and impossible requests are rejected, not timed out.
    """
    def __init__(self, capacities):
        self.capacities = {k: positive(v, k) for k, v in capacities.items()}
        self.slots = {k: [0] * v for k, v in self.capacities.items()}
        self.events = []
        self.ends = {}

    def add(self, name, deps, duration, resources, *, ready=0, **attrs):
        if name in self.ends:
            raise ValueError('duplicate event identity ' + name)
        positive(duration, name)
        if type(ready) is not int or ready < 0:
            raise ValueError('invalid ready cycle')
        if len(deps) != len(set(deps)) or any(d not in self.ends for d in deps):
            raise ValueError('unresolved dependency/deadlock ' + name)
        start = max([ready] + [self.ends[d] for d in deps])
        selected = {}
        for key, count in sorted(resources.items()):
            positive(count, key)
            if key not in self.slots or count > self.capacities[key]:
                raise ValueError('finite capacity exhausted: ' + key)
            choices = sorted(range(len(self.slots[key])), key=lambda i: (self.slots[key][i], i))[:count]
            selected[key] = choices
            start = max(start, *(self.slots[key][i] for i in choices))
        end = start + duration
        for key, slots in selected.items():
            for slot in slots:
                self.slots[key][slot] = end
        event = dict(id=name, deps=list(deps), start=start, end=end,
                     resources=selected, **attrs)
        self.events.append(event)
        self.ends[name] = end
        return name

    def dag(self, tasks):
        tasks = list(tasks)
        byid = {t['id']: t for t in tasks}
        if len(byid) != len(tasks):
            raise ValueError('duplicate task')
        indegree = {}; successors = defaultdict(list)
        for t in tasks:
            if len(t['deps']) != len(set(t['deps'])):
                raise ValueError('duplicate dependency')
            indegree[t['id']] = len(t['deps'])
            for dep in t['deps']:
                if dep not in byid:
                    raise ValueError('unknown dependency')
                successors[dep].append(t['id'])
        queue = [k for k, v in indegree.items() if not v]
        heapq.heapify(queue)
        while queue:
            key = heapq.heappop(queue); t = byid[key]
            self.add(key, t['deps'], t['duration'], t['resources'])
            for nxt in successors[key]:
                indegree[nxt] -= 1
                if not indegree[nxt]:
                    heapq.heappush(queue, nxt)
        if len(self.ends) != len(tasks):
            raise ValueError('dependency cycle/deadlock')
        return self.events


def verify_calendar(events, capacities):
    """Independent interval/credit and dependency proof; handles parallel events."""
    seen = {}; owners = defaultdict(list)
    for e in events:
        if e['id'] in seen or type(e['start']) is not int or e['start'] < 0 or e['end'] <= e['start']:
            raise ValueError('event identity/time')
        for dep in e['deps']:
            if dep not in seen or seen[dep]['end'] > e['start']:
                raise ValueError('premature consume/dependency')
        for key, slots in e['resources'].items():
            if key not in capacities or len(slots) != len(set(slots)):
                raise ValueError('unknown/duplicate resource')
            for slot in slots:
                if type(slot) is not int or not 0 <= slot < capacities[key]:
                    raise ValueError('finite capacity exhausted')
                owners[key, slot].append((e['start'], e['end'], e['id']))
        if 'repeats' in e:
            if positive(e['repeats'], 'repeats') * positive(e['stride'], 'stride') != e['end'] - e['start']:
                raise ValueError('batch interval inconsistent')
        if 'native_program' in e:
            verify_native_program(e['native_program'])
            if e['end'] - e['start'] != e['native_program']['duration']:
                raise ValueError('native enclosing reservation mismatch')
        seen[e['id']] = e
    for intervals in owners.values():
        ordered = sorted(intervals)
        if any(a[1] > b[0] for a, b in zip(ordered, ordered[1:])):
            raise ValueError('overlapping credit/port ownership')
    return {'events': len(events), 'resource_slots_used': len(owners),
            'dependency_edges': sum(len(e['deps']) for e in events),
            'status': 'PASS_FINITE_INTERVAL_PROOF'}


def verify_native_program(program):
    """Replay compressed primitive timing and finite scratch, independently."""
    def walk(nodes):
        offset = 0; counts = Counter()
        for node in nodes:
            if node['offset'] != offset:
                raise ValueError('native primitive ordering/offset')
            if node['kind'] == 'primitive':
                for name, value in node['stage_cycles'].items():
                    positive(value, name)
                if node['duration'] != sum(node['stage_cycles'].values()):
                    raise ValueError('native stage composition')
                credit = node['storage_credit']
                if credit['sector_credit'] != 1 or credit['read_ports'] > 2 or credit['write_ports'] != 1:
                    raise ValueError('native primitive finite capacity')
                if not node['rounding'] or not node['source_instruction'].get('op'):
                    raise ValueError('native arithmetic provenance')
                counts[node['op']] += node['batches128']
            elif node['kind'] == 'loop':
                if node['count'] < 0:
                    raise ValueError('negative loop trip count')
                duration, body_counts = walk(node['body'])
                expected = duration * node['count'] + node.get('control_cycles', node.get('explicit_empty_loop_control_cycles', 0))
                if node['duration'] != expected:
                    raise ValueError('native loop repetition/stride')
                counts.update({op: n * node['count'] for op, n in body_counts.items()})
            else:
                raise ValueError('native calendar node kind')
            positive(node['duration'], 'native duration'); offset += node['duration']
        return offset, counts
    duration, counts = walk(program['primitive_tree'])
    duration += program.get('empty_owned_extent_control_cycles', 0)
    if duration != program['duration']:
        raise ValueError('native recipe duration')
    live = []
    for home in program['scratch_homes'].values():
        lo = home['byte_offset']; size = home['buffer_bytes'] * home['buffers']
        if lo < 0 or lo % 512 or size % 512 or lo + size > program['finite_scratch_bytes']:
            raise ValueError('native scratch capacity')
        live.append((lo, lo + size))
    live.sort()
    if any(a[1] > b[0] for a, b in zip(live, live[1:])):
        raise ValueError('native scratch alias')
    return dict(counts)


def cycle_table(graphs, layouts):
    endpoints = {'admit', 'RF_read', 'RF_write_ACK', 'consume', 'retire',
                 'visibility_fence', 'HBM_read_sector', 'HBM_write_sector',
                 'forward_CDC', 'reverse_CDC', 'collective_sector', 'PACK_BF16',
                 'root_delivery', 'scalar_broadcast', 'matrix_stage', 'matrix_weight_sector',
                 'norm_collector_tail', 'norm_output_scale', 'external_stage', 'native:STAGE_OPERAND', 'owner_lookup', 'owner_held_accept', 'validated_reverse_grant'}
    for g in graphs.values():
        for o in g['operations']:
            endpoints.add('operator:' + o['opcode'])
            endpoints.update('provider:' + p for p in o['missing_native_endpoints'])
    for layout in layouts.values():
        for template in layout['selected_command_bindings']['command_templates'].values():
            endpoints.update('native:' + c['op'] for c in template)
    # These are deliberately explicit SOFTWARE estimates in abstract scheduler ticks.
    # Users may replace every value with calibrated endpoint inputs via --cycles.
    estimates = {'admit': 2, 'RF_read': 3, 'RF_write_ACK': 3, 'consume': 2,
                 'retire': 2, 'visibility_fence': 4, 'HBM_read_sector': 64,
                 'HBM_write_sector': 80, 'forward_CDC': 4, 'reverse_CDC': 4,
                 'collective_sector': 32, 'PACK_BF16': 8, 'root_delivery': 12,
                 'scalar_broadcast': 12, 'matrix_stage': 8, 'matrix_weight_sector': 64,
                 'owner_lookup': 12, 'owner_held_accept': 1, 'validated_reverse_grant': 4,
                 'norm_collector_tail': 512, 'norm_output_scale': 32, 'external_stage': 16}
    return {'schema': 'H3_EXPLICIT_ENDPOINT_CYCLES_V1', 'unit': 'abstract_software_tick',
            'calibration': 'PROVISIONAL_UNCALIBRATED', 'hardware_clock_claim': False,
            'values': {key: estimates.get(key, 32) for key in sorted(endpoints)},
            'basis': 'Explicit conservative software service estimates; provider/operator cost per 128-word tile; memory/collective per sector32; native per command; no CPU numerical oracle.'}


def validate_cycles(table, required):
    if table.get('unit') != 'abstract_software_tick' or table.get('hardware_clock_claim') is not False:
        raise ValueError('software cycle unit/clock scope')
    if table.get('calibration') not in ('PROVISIONAL_UNCALIBRATED', 'MEASURED_ENDPOINT_INPUTS'):
        raise ValueError('latency provenance missing')
    if table['calibration'] == 'MEASURED_ENDPOINT_INPUTS' and not table.get('measurement_pins'):
        raise ValueError('measured inputs require separate source pins')
    for key in required:
        positive(table.get('values', {}).get(key), key)


def version_homes(graph, layout, ranks):
    """Expand real rank groups; add finite persistent object/opaque homes explicitly."""
    homes = defaultdict(list)
    for h in layout['homes']:
        for rank in h['rank_group']:
            homes[h['version'], rank].append({k: v for k, v in h.items() if k != 'rank_group'})
    for v in graph['operands']:
        for rank in range(ranks):
            n = v['elements_per_rank'][rank]
            if not n or homes[v['id'], rank]:
                continue
            if v['bits_per_element'] == 0:
                home = {'class': 'publication', 'object': v['id'], 'bytes': 1}
            elif v['name'].startswith(('window.', 'compressed.', 'index_keys.', 'selected.')):
                home = {'class': 'persistent', 'object': v['name'],
                        'bytes': ceil(n * v['bits_per_element'], 8), 'byte_offset': 0}
            else:
                raise ValueError('unmapped version ' + v['id'])
            homes[v['id'], rank].append({'version': v['id'], 'name': v['name'], 'SM': 0,
                'birth_pc': v['birth_pc'], 'retire_pc': v['retire_pc'], 'home': home})
    return homes


def bind_provider_homes(provider, graph, fallback):
    if provider.get('schema') != 'opentallas.Qwen.provider-binding.v1':
        raise ValueError('provider binding schema')
    coverage = provider['coverage']
    if coverage['PCs'] != len(graph['operations']) or coverage['versions'] != len(graph['operands']) or coverage['unbound_versions']:
        raise ValueError('provider coverage')
    homes = defaultdict(list); refs = {}; release_at = defaultdict(list)
    versions = {v['id']: v for v in graph['operands']}
    for h in provider['version_homes']:
        if h['version'] not in versions or h['provider_ref'] in refs:
            raise ValueError('provider home/version identity')
        if h['birth_pc'] != versions[h['version']]['birth_pc'] or h['retire_pc'] != versions[h['version']]['retire_pc']:
            raise ValueError('provider lifetime mismatch')
        record = dict(h); record['name'] = versions[h['version']]['name']
        homes[h['version'], h['rank']].append(record); refs[h['provider_ref']] = h
        release_at[h['retire_pc']].append(h)
    for h in provider['control_homes']:
        if h['version'] not in versions or h['provider_ref'] in refs:
            raise ValueError('control provider identity')
        record = {'version': h['version'], 'name': versions[h['version']]['name'],
            'SM': 0, 'home': {'class': 'publication', 'object': h['version'], 'bytes': 1,
                'provider_extent': h['state_extent']}, 'provider_ref': h['provider_ref']}
        homes[h['version'], h['rank']].append(record); refs[h['provider_ref']] = h
    for key, entries in fallback.items():
        if entries and not homes[key]:
            raise ValueError('unbound provider version/rank')
    reuse = defaultdict(list); release_refs = {h['release_event']: h for h in provider['version_homes']}
    for edge in provider['reuse_dependencies']:
        if edge['new_home'] not in refs or edge['wait_release'] not in release_refs:
            raise ValueError('provider reuse dependency identity')
        new, old = refs[edge['new_home']], release_refs[edge['wait_release']]
        if old['retire_pc'] >= new['birth_pc']:
            raise ValueError('provider premature reuse')
        reuse[edge['new_home']].append(edge['wait_release'])
    operations = {}
    for p, op in zip(provider['operations'], graph['operations']):
        if p['pc'] != op['pc'] or p['opcode'] != op['opcode'] or p['source_dependencies'] != op['dependencies']:
            raise ValueError('provider PC/dependency mismatch')
        if set(p['inputs']) != set(op['reads']) or set(p['outputs']) != set(op['writes']):
            raise ValueError('provider PC operand mismatch')
        if any(ref not in refs for group in (p['inputs'], p['outputs']) for ids in group.values() for ref in ids):
            raise ValueError('unknown concrete provider reference')
        operations[p['pc']] = p
    if len(operations) != len(graph['operations']):
        raise ValueError('provider operation coverage')
    return homes, reuse, release_at, operations


def check_homes(homes, graph):
    values = {v['id']: v for v in graph['operands']}
    groups = defaultdict(list); persistent = defaultdict(list)
    for (vid, rank), entries in homes.items():
        if vid not in values:
            raise ValueError('unknown version home')
        for h in entries:
            p = h['home']; cls = p['class']
            if cls not in ('RF', 'spill', 'persistent', 'publication'):
                raise ValueError('home class')
            if cls == 'RF':
                lo, size = p['slot_first'], positive(p['vectors'], 'vectors')
                if lo < 32 or lo + size > 512:
                    raise ValueError('RF aperture/workspace capacity')
            elif cls == 'spill':
                lo, size = p['byte_offset'], positive(p['bytes'], 'spill bytes')
                if lo < 0 or lo % 512 or size % 512:
                    raise ValueError('spill alignment')
            elif cls == 'persistent':
                persistent[rank, p['object']].append((values[vid]['birth_pc'], values[vid]['retire_pc'], vid))
                continue
            else:
                continue
            groups[rank, h['SM'], cls].append((values[vid]['birth_pc'], values[vid]['retire_pc'], lo, lo + size, vid))
    for entries in groups.values():
        live = []
        for birth, retire, lo, hi, vid in sorted(entries):
            live = [x for x in live if x[0] >= birth]
            if any(lo < x[2] and x[1] < hi for x in live):
                raise ValueError('live home alias/premature write reuse ' + vid)
            live.append((retire, lo, hi, vid))
    for entries in persistent.values():
        ordered = sorted(entries)
        if any(a[1] > b[0] for a, b in zip(ordered, ordered[1:])):
            raise ValueError('persistent generation reused with future readers')
    return True


def extent_demands(layout):
    demands = []
    for binding in layout['spill_resident_bindings']:
        if not binding.get('fits', True):
            extent = binding['source_extent']; required = binding['required_bytes']
            demands.append({'rank_group': binding['rank_group'], 'class': 'activation_spill',
                'source_extent': extent, 'required_bytes': required,
                'additional_bytes': required - extent['bytes'], 'alignment_bytes': 512,
                'AW': binding['provider_ABI']['AW'],
                'status': 'CONSTRAINED_SUCCESSOR_EXTENT_REQUIRED',
                'constraints': ['nonalias with all checkpoint/KV/source extents',
                    'fulladdress end <= 2**AW', 'one distinct arena per rank; explicit SM subranges',
                    'all readers retired and reverse credit returned before address reuse'],
                'calendar_binding': 'logical successor arena; NOT an allocated source address'})
    return demands


class Shape:
    """Shape-only expressions. Never stores or evaluates numerical tensor data."""
    def __init__(self, shape=()):
        self.shape = tuple(int(n) for n in shape)
        if any(n < 0 for n in self.shape):
            raise ValueError('negative tensor extent')
    def __getitem__(self, key):
        keys = key if isinstance(key, tuple) else (key,)
        if Ellipsis in keys:
            missing = len(self.shape) - sum(k is not None and k is not Ellipsis for k in keys)
            keys = tuple(x for k in keys for x in ([slice(None)] * missing if k is Ellipsis else [k]))
        out = []; axis = 0
        for item in keys:
            if item is None:
                out.append(1); continue
            n = self.shape[axis]; axis += 1
            if isinstance(item, slice):
                out.append(len(range(*item.indices(n))))
            elif isinstance(item, Shape):
                out.extend(item.shape)
            elif not -n <= int(item) < n:
                raise ValueError('shape index aperture')
        return Shape(out + list(self.shape[axis:]))
    def binary(self, other):
        return Shape(broadcast(self.shape, other.shape if isinstance(other, Shape) else ()))
    __add__ = __radd__ = __sub__ = __rsub__ = __mul__ = __rmul__ = binary
    __truediv__ = __rtruediv__ = __floordiv__ = __rfloordiv__ = __mod__ = __rmod__ = binary


def broadcast(*shapes):
    result = []
    for axis in range(1, max(map(len, shapes), default=0) + 1):
        sizes = {s[-axis] for s in shapes if len(s) >= axis} - {1}
        if len(sizes) > 1:
            raise ValueError('incompatible broadcast extents')
        result.append(next(iter(sizes), 1))
    return tuple(reversed(result))


def shape_reshape(value, shape):
    shape = list(shape); size = math.prod(value.shape)
    if shape.count(-1) > 1:
        raise ValueError('reshape inferred dimension')
    if -1 in shape:
        known = math.prod(n for n in shape if n != -1)
        if not known or size % known:
            raise ValueError('reshape extent')
        shape[shape.index(-1)] = size // known
    if math.prod(shape) != size:
        raise ValueError('reshape element count')
    return Shape(shape)


def shape_concat(values, axis=0):
    shapes = [as_shape(v).shape for v in values]; out = list(shapes[0]); axis %= len(out)
    for shape in shapes[1:]:
        if len(shape) != len(out) or any(a != b for i, (a, b) in enumerate(zip(out, shape)) if i != axis):
            raise ValueError('concat extent')
        out[axis] += shape[axis]
    return Shape(out)


def as_shape(value):
    if isinstance(value, Shape):
        return value
    if isinstance(value, (tuple, list)):
        return Shape((len(value),))
    return Shape()


def shape_expression(expr, env):
    expr = re.sub(r'np\.float64\(([-+0-9.eE]+)\)', r'\1', str(expr))
    tree = ast.parse(expr, mode='eval')
    allowed = (ast.Expression, ast.Name, ast.Load, ast.Constant, ast.Tuple, ast.List,
        ast.Subscript, ast.Slice, ast.Attribute, ast.Call, ast.BinOp, ast.UnaryOp,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.USub)
    for node in ast.walk(tree):
        if not isinstance(node, allowed):
            raise ValueError('non-shape expression ' + expr)
        if isinstance(node, ast.Attribute) and node.attr != 'shape':
            raise ValueError('shape expression attribute')
        if isinstance(node, ast.Call) and (not isinstance(node.func, ast.Name) or node.func.id not in
                ('reshape', 'transpose', 'concat', 'zeros', 'arange', 'f32', 'int', 'min', 'max', 'pow2ceil', 'log2ceil', 'bitlength')):
            raise ValueError('non-shape call: ' + expr)
    helpers = {'reshape': shape_reshape,
        'transpose': lambda v: Shape(tuple(reversed(v.shape))), 'concat': shape_concat,
        'zeros': lambda s: Shape(s), 'arange': lambda n: Shape((n,)),
        'f32': lambda n: Shape(), 'int': lambda n: n if isinstance(n, int) else Shape(),
        'min': min, 'max': max, 'pow2ceil': lambda n: 1 << (max(1,int(n))-1).bit_length(),
        'log2ceil': lambda n: (max(1,int(n))-1).bit_length(), 'bitlength': lambda n: int(n).bit_length()}
    return eval(compile(tree, '<shape-only-native-index>', 'eval'), {'__builtins__': {}, **helpers}, env)


def normalize_bundle(data):
    if data.get('schema') == 'opentallas.H3.qwen-complete-native-software.v1':
        return {**data, 'target': 'Qwen'}
    if data.get('schema') == 'H3_DEEPSEEK_COMPLETE_NATIVE_V1':
        operations = []; sequences = {}
        for op in data['instructions']:
            groups = defaultdict(list)
            for binding in op['rank_bindings']:
                if not binding.get('empty_owned_extent'):
                    # Final DS exports one actual recipe per gathered buffer.
                    # The primary recipe is an extent preview, not an additional
                    # executable buffer when explicit buffer_programs are present.
                    keys = tuple(b['template'] for b in binding.get('buffer_programs', [])) or (binding['template'],)
                    groups[keys].append(binding['rank'])
            programs = []
            for keys, ranks in groups.items():
                if keys not in sequences:
                    code = []; counts = Counter(); outputs = {}
                    for index, key in enumerate(keys):
                        template = data['templates'][key]
                        prefix = f'buffer{index}_' if len(keys) > 1 else ''
                        for instruction in template['code']:
                            code.append({**instruction, 'dst': prefix + instruction['dst'],
                                'src': [prefix + v for v in instruction['src']]})
                        outputs.update({prefix + name: prefix + symbol for name, symbol in template['outputs'].items()})
                        counts.update(template['resources'].get('instruction_batches128_by_opcode', {}))
                    sequences[keys] = {'instructions': code, 'outputs': outputs,
                        'expected_primitive_batches': dict(counts),
                        'source_template': hashlib.sha256(encode(keys)).hexdigest()}
                programs.append({**sequences[keys], 'rank_group': ranks,
                    'source_templates': list(keys),
                    'providers': {key: op['provider_bindings'][key] for key in keys},
                    'resources': {key: data['templates'][key]['resources'] for key in keys}})
            operations.append({**op, 'opcode': op['family'], 'programs': programs,
                'reads': [v['version'] for v in op['reads']], 'writes': [v['version'] for v in op['writes']]})
        return {**data, 'target': 'DeepSeek', 'operations': operations}
    return data


def bundle_primitives(data):
    if data.get('schema') == 'H3_ORDERED_NATIVE_LOWERING_V1':
        return {step['op'] for op in data['operations'] for step in op['steps']}
    result = set()
    def walk(nodes):
        for node in nodes:
            result.add(node['op'])
            walk(node.get('body', [])); walk(node.get('exact_template', []))
    for op in data['operations']:
        if 'recipe' in op:
            walk(op['recipe'])
        else:
            for program in op.get('programs', []):
                walk(program['instructions'])
    return result


def validate_bundle(native, graph):
    if len(native['operations']) != len(graph['operations']):
        raise ValueError('native bundle PC coverage')
    for plan, op in zip(native['operations'], graph['operations']):
        if plan['pc'] != op['pc'] or plan.get('opcode', plan.get('family')) != op['opcode']:
            raise ValueError('native bundle PC identity')
        if plan['reads'] != op['reads'] or plan['writes'] != op['writes']:
            raise ValueError('native bundle version mismatch')
        if 'recipe' not in plan and 'programs' not in plan:
            raise ValueError('native bundle instructions missing')


def bind_recipe(native, plan, macro, rank, table, workspace=None):
    """Instruction-dependent ordered nested calendar; loops remain lossless RLE.

    Every primitive serially consumes at most two RF read ports, one write port,
    one finite sector credit and one of 32 lane engines. Source temporaries use
    a finite double-buffered logical scratch arena, sized by this binding. It is
    a constrained successor allocation if the existing scratch extent is short.
    """
    costs = table['values']; env = {}; buffers = {}; stats = Counter(); serial = [0]
    source = native.get('source_program', {})
    version_shapes = {v['version']: v['shape'] for v in native.get('operands', []) if 'version' in v and 'shape' in v}
    version_names = {v['version']: v.get('name', '') for v in native.get('operands', []) if 'version' in v}
    context = source.get('context_capacity', 8192)
    env['position'] = context - 1
    for i, vid in enumerate(macro['reads']):
        shape = version_shapes.get(vid)
        if shape is not None:
            env[f'input{i}'] = Shape([context if n == 'position+1' else n for n in shape])
            if version_names.get(vid) == 'position':
                env[f'input{i}'] = context - 1
            if macro['opcode'] == 'ARGMAX_REDUCE':
                env[f'input{i}'] = Shape((2,))
    exported_allocations = plan.get('temporary_storage', {}).get('allocations')
    workspace_homes = ({symbol: workspace['homes'][plan['pc'], rank, symbol]
                        for symbol in exported_allocations} if workspace and exported_allocations else {})
    highword_symbols = {symbol for symbol, home in workspace_homes.items() if home.get('semantic_bits') == 64}
    element_bytes = 4 if exported_allocations else 8
    def register(name, shape):
        if name:
            name = name.split('[')[0]
            size = max(element_bytes, element_bytes * math.prod(shape))
            buffers[name] = max(buffers.get(name, 0), ceil(size, 512) * 512)
    for key, val in env.items():
        if isinstance(val, Shape):
            register(key, val.shape)
    def primitive(node, local_env, path):
        op = node['op']; src = node.get('src', []); dst = node.get('dst')
        rounding = node.get('round_point', node.get('rounding'))
        if not rounding:
            rounding = 'FP32_RNE_then_positive_zero' if op in ('FADD', 'FMUL') else 'explicit native instruction contract'
        if any(k in node for k in ('callback', 'handler', 'golden_callback')):
            raise ValueError('native callback forbidden')
        args = [shape_expression(x, local_env) for x in src]
        if 'shape' in node:
            result = Shape(node['shape'])
        elif op == 'LOAD_WEIGHT':
            d = source['weight_descriptors'][node['key']]; result = Shape((d['rows'], d['K']))
        elif op == 'LOAD_EMBED_CODES':
            result = Shape((source['config']['hidden_size'],))
        elif op == 'LOAD_EMBED_SCALE':
            result = Shape()
        elif op == 'LOAD_GAMMA':
            result = Shape((source['config']['head_dim'] if node.get('kind') != 'final' else source['config']['hidden_size'],))
        elif op in ('LOAD_ROPE_COS', 'LOAD_ROPE_SIN'):
            result = Shape((source['config']['head_dim'] // 2,))
        elif op == 'LOAD_SCALE':
            d = source['weight_descriptors'][node['key']]; result = Shape((d['rows'],))
        elif op == 'READ_BYTES':
            result = as_shape(args[-1])
        elif op in ('BEGIN_WRITE', 'ACQUIRE', 'BIND_LEASE', 'COMMIT_PUBLISH', 'CONSUMER_DONE'):
            result = Shape()
        else:
            result = Shape(broadcast(*(as_shape(a).shape for a in args))) if args else Shape()
        if op == 'MOV' and args:
            result = as_shape(args[0])
        name = dst.split('[')[0] if dst else None
        if name:
            if '[' in dst:
                # Destination scatter is a costed materialization under its full lease.
                if name not in local_env:
                    raise ValueError('scatter destination uninitialized')
                register(name, as_shape(local_env[name]).shape)
            else:
                if op != 'STAGE_OPERAND' or not isinstance(local_env.get(name), int):
                    local_env[name] = result
                register(name, result.shape)
        batches = max(1, ceil(math.prod(result.shape), 128))
        read_batches = sum(max(1, ceil(math.prod(as_shape(a).shape) * element_bytes, 512)) for a in args)
        write_batches = max(1, ceil(math.prod(result.shape) * element_bytes, 512)) if dst else 1
        # A source recipe may have three-input SELECT or CONCAT. Decompose RF
        # operand reads into serial pairs, retaining values in the finite arena.
        operand_pairs = max(1, ceil(len(args), 2))
        stages = {'admit': costs['admit'], 'RF_read': costs['RF_read'] * max(read_batches, operand_pairs),
            'execute': costs['native:' + op] * batches,
            'RF_write_ACK': costs['RF_write_ACK'] * write_batches,
            'consume': costs['consume'], 'retire': costs['retire']}
        # All temporaries are explicitly scratch-backed. No invisible limitless RF.
        sectors = 16 * (read_batches + write_batches)
        ownership = 2 * (costs['owner_lookup'] + costs['owner_held_accept'])
        read_sectors, write_sectors = 16 * read_batches, 16 * write_batches
        stages['scratch_read'] = max(1, read_sectors) * (costs['HBM_read_sector'] + ownership +
            costs['forward_CDC'] + costs['consume'] + costs['reverse_CDC'] + costs['validated_reverse_grant'] + costs['retire'])
        stages['scratch_write'] = write_sectors * (costs['HBM_write_sector'] + ownership +
            costs['visibility_fence'] + costs['forward_CDC'] + costs['consume'] + costs['reverse_CDC'] +
            costs['validated_reverse_grant'] + costs['retire'])
        high_reads = []
        for text, arg in zip(src, args):
            names = {n.id for n in ast.walk(ast.parse(text, mode='eval')) if isinstance(n, ast.Name)}
            touched = sorted(names & highword_symbols)
            if touched:
                high_reads.append({'symbols': touched, 'sectors32': max(1, ceil(math.prod(as_shape(arg).shape) * 4, 32))})
        high_write = max(1, ceil(math.prod(result.shape) * 4, 32)) if name in highword_symbols else 0
        if high_reads:
            stages['I64_highword_read'] = sum(r['sectors32'] for r in high_reads) * costs['I64_highword_read_sector']
            stages['I64_join'] = costs['I64_split_join'] * sum(max(1, ceil(r['sectors32'], 16)) for r in high_reads)
        if high_write:
            stages['I64_split'] = costs['I64_split_join'] * max(1, ceil(high_write, 16))
            # Conservative sector RMW for every upper-word write, including
            # partial words/scatters. Adjacent packed owners are never clobbered.
            stages['I64_RMW_read'] = high_write * costs['I64_highword_read_sector']
            stages['I64_RMW_merge'] = costs['I64_RMW_merge'] * max(1, ceil(high_write, 16))
            stages['I64_highword_write_visible'] = high_write * costs['I64_highword_write_sector']
        if op.startswith('LOAD') or op in ('WRITE_BYTES', 'READ_BYTES', 'PACKET_COMMIT'):
            stages['provider_visibility'] = max(1, ceil(math.prod(result.shape) * element_bytes, 32)) * (
                costs['HBM_write_sector' if op in ('WRITE_BYTES', 'PACKET_COMMIT') else 'HBM_read_sector'] +
                costs['visibility_fence'] + ownership + costs['validated_reverse_grant'])
        index = serial[0]; serial[0] += 1; stats[op] += batches
        return {'kind': 'primitive', 'index': index, 'op': op, 'source_instruction': node,
            'rounding': rounding, 'shape': list(result.shape), 'batches128': batches, 'scratch_element_bytes': element_bytes,
            'RF_read_batches': read_batches, 'RF_write_batches': write_batches,
            'operand_pair_reads': operand_pairs, 'storage_sectors32': sectors, 'scratch_read_sectors32': read_sectors, 'scratch_write_sectors32': write_sectors,
            'owner_lookup_edges_per_sector': 2 * costs['owner_lookup'],
            'owner_accept_edges_per_sector': 2 * costs['owner_held_accept'],
            'validated_reverse_grant_cycles': costs['validated_reverse_grant'],
            'stage_cycles': stages, 'duration': sum(stages.values()),
            'version_identity': ['event.target', 'event.pc', 'event.rank', path, index, 'loop_iteration_tuple'],
            'read_symbols': src, 'write_symbol': dst,
            'I64_highword_reads': high_reads, 'I64_highword_write_sectors32': high_write,
            'I64_conservative_RMW_sectors32': high_write,
            'storage_credit': {'sector_credit': 1, 'read_ports': 2, 'write_ports': 1,
                               'lanes': 128, 'double_buffer_versions': 2}}
    def walk(nodes, local_env, path=()):
        out = []; offset = 0
        for i, node in enumerate(nodes):
            if node['op'] in ('FOR', 'SUM_TEMPLATE'):
                if node['op'] == 'FOR':
                    start = shape_expression(node['start'], local_env); stop = shape_expression(node['stop'], local_env)
                    step = shape_expression(node['step'], local_env); count = len(range(start, stop, step))
                    local_env[node['var']] = start; body = node['body']
                else:
                    start = 0; step = 1; count = 1; body = node['exact_template']
                if count == 0:
                    record = {'kind': 'loop', 'count': 0, 'body': [], 'duration': costs['admit'],
                              'explicit_empty_loop_control_cycles': costs['admit']}
                else:
                    groups = [(start, count)]
                    if node['op'] == 'FOR' and node['var'] == 'tree_level':
                        groups = [(index, 1) for index in range(start, stop, step)]
                    elif node['op'] == 'FOR' and node['var'] == 'g' and count > 1:
                        groups = [(start, count - 1), (start + step * (count - 1), 1)]
                    elif node['op'] == 'FOR' and node['var'] == 's':
                        knode = next((n for n in body if n['op'] == 'FOR' and n['var'] == 'k'), None)
                        if knode:
                            groups = []; last_trip = None
                            for index in range(start, stop, step):
                                local_env[node['var']] = index
                                bounds = [shape_expression(knode[k], local_env) for k in ('start', 'stop', 'step')]
                                trip = len(range(*bounds))
                                if trip != last_trip:
                                    groups.append([index, 1]); last_trip = trip
                                else:
                                    groups[-1][1] += 1
                    segments = []; total = 0
                    for index, repeat in groups:
                        if node['op'] == 'FOR':
                            local_env[node['var']] = index
                        children, duration = walk(body, local_env, path + (i, index))
                        segment = {'kind': 'loop', 'count': repeat, 'iteration_start': index,
                            'iteration_step': step, 'iteration_stride': duration, 'body': children,
                            'duration': duration * repeat + costs['admit'], 'control_cycles': costs['admit'],
                            'offset': total, 'ordering': 'iteration-major exact body order'}
                        segments.append(segment); total += segment['duration']
                    record = {'kind': 'loop', 'count': 1, 'body': segments, 'duration': total + costs['admit'],
                        'control_cycles': costs['admit'], 'source_loop_count': count,
                        'ordering': 'contiguous source iteration groups; shrinking trees and tail extents explicit'}
                    if node['op'] == 'FOR':
                        local_env[node['var']] = start + step * (count - 1)
            else:
                record = primitive(node, local_env, path + (i,))
            record['offset'] = offset; offset += record['duration']; out.append(record)
        return out, offset
    if 'recipe' in plan:
        nodes = plan['recipe']
    else:
        programs = plan['programs']; program = next((p for p in programs if rank in p['rank_group']), None)
        if program is None:
            return {'schema': 'H3_ORDERED_PRIMITIVE_CALENDAR_V1', 'duration': costs['admit'],
                'primitive_tree': [], 'finite_scratch_bytes': 0, 'scratch_homes': {},
                'empty_owned_extent_control_cycles': costs['admit'], 'no_tensor_value_evaluation': True}
        nodes = program['instructions']
        definitions = set()
        for node in nodes:
            if any(v not in definitions for v in node['src']):
                raise ValueError('Peirce SSA premature consume')
            if node['dst'] in definitions:
                raise ValueError('Peirce SSA duplicate write')
            definitions.add(node['dst'])
        for node in nodes:
            # DS instructions use SSA symbol references, not expression callbacks.
            if node['op'] == 'LOAD':
                env[node['dst']] = Shape(node['shape'])
    prefix = [{'op': 'STAGE_OPERAND', 'dst': name, 'src': [name],
        'round_point': 'bit-exact source version movement; no arithmetic',
        'version': macro['reads'][int(name[5:])], 'source': 'macro RF/persistent read landing'}
        for name in list(env) if name.startswith('input') and name[5:].isdigit()]
    tree, duration = walk(prefix + nodes, env)
    arena = {}; cursor = 0; producer_homes = {}
    if exported_allocations:
        for name, allocation in exported_allocations.items():
            home = allocation['home']; producer_homes[name] = allocation
            if home['class_'] == 'spill':
                size = ceil(allocation['bytes'], 512) * 512
                arena[name] = {'byte_offset': home['byte_offset'], 'buffer_bytes': size, 'buffers': 1,
                    'base_by_rank': home['base_by_rank'], 'version': allocation['version'],
                    'lease': allocation['lease'], 'release_after': allocation['release_after']}
                cursor = max(cursor, home['byte_offset'] + size)
            elif home['class_'] == 'RF':
                if any(not 3 <= slot < 32 for slot in home['vector_slots']):
                    raise ValueError('producer native workspace RF aperture')
            else:
                raise ValueError('producer native temporary home class')
        if cursor != plan['temporary_storage']['spill_bytes']:
            raise ValueError('producer native scratch extent mismatch')
    else:
        for name, size in sorted(buffers.items()):
            arena[name] = {'byte_offset': cursor, 'buffer_bytes': size, 'buffers': 2,
                           'version_buffer': 'iteration-local producer parity; read old parity before mirrored ACK switch'}
            cursor += 2 * size
    result = {'schema': 'H3_ORDERED_PRIMITIVE_CALENDAR_V1', 'duration': duration,
        'primitive_tree': tree, 'finite_scratch_bytes': cursor, 'scratch_homes': arena,
        'producer_temporary_homes': producer_homes,
        'workspace_provider_homes': workspace_homes,
        'producer_counts_full_context': plan.get('calendar_counts_full_context'),
        'producer_native_finite_export': plan.get('calendar_export', {}).get('schema'),
        'source_arithmetic': macro['golden_contract'], 'source_recipe_sha256': hashlib.sha256(encode(nodes)).hexdigest(),
        'provider_refs': native.get('provider_requirements', 'Peirce LOAD/provider program descriptors'),
        'storage_scope': 'finite logical successor arena per rank; does not alias source scratch',
        'scratch_layout': ('producer finite RF/refill/spill allocations consumed exactly; no independently sized double buffers' if exported_allocations else
            '8 bytes per logical element: F32/U32 lowword plus padded highword; I64 retains both32bit words; two RF staging vectors per128 logical values'),
        'no_tensor_value_evaluation': True}
    if 'programs' in plan and program.get('expected_primitive_batches'):
        expected = program['expected_primitive_batches']
        observed = verify_native_program(result)
        if observed != expected:
            raise ValueError('DS producer primitive count mismatch at PC' + str(plan['pc']))
        result['producer_vector_count_gate'] = 'PASS_EXACT_EXPORTED_NATIVE_COUNTS'
        result['producer_expected_primitive_batches'] = expected
        result['producer_source_templates'] = program['source_templates']
    if plan.get('calendar_counts_full_context'):
        expected = {op: counts['native_vector_beats'] for op, counts in
                    plan['calendar_counts_full_context']['by_primitive'].items()}
        observed = verify_native_program(result)
        if any(observed.get(op, 0) != count for op, count in expected.items()):
            raise ValueError('producer native vector count mismatch at PC' + str(plan['pc']))
        result['producer_vector_count_gate'] = 'PASS_EXACT_EXPORTED_NATIVE_COUNTS'
    return result



def validate_native_lowering(native, graph, homes, ranks):
    """Worker interchange: every PC and concrete ordered two-source native steps.

    Each step has rank, SM, op, repeats, reads=[{version,slot}],
    writes=[{version,slot}], rounding, provider_refs, and source_arithmetic.
    Macro inputs initialize their concrete slots. Constants need explicit
    provider descriptors, which create costed staging steps. Local versions may
    reuse a slot only after their last listed read. No callback is executable.
    """
    if native.get('schema') != 'H3_ORDERED_NATIVE_LOWERING_V1':
        raise ValueError('native lowering schema')
    operations = native.get('operations', [])
    if len(operations) != len(graph['operations']):
        raise ValueError('native lowering must cover every PC')
    plans = {}
    for plan, macro in zip(operations, graph['operations']):
        if plan.get('pc') != macro['pc'] or plan.get('opcode') != macro['opcode']:
            raise ValueError('native PC identity/order')
        if plan.get('operand_versions') != {'reads': macro['reads'], 'writes': macro['writes']}:
            raise ValueError('native operand version mismatch')
        if not plan.get('source_arithmetic') or not plan.get('rounding') or not plan.get('provider_refs'):
            raise ValueError('native arithmetic/provider contract missing')
        steps = plan.get('steps', [])
        if not steps:
            raise ValueError('native steps missing')
        state = {}; last = {}; definitions = set()
        for i, step in enumerate(steps):
            for ref in step.get('reads', []):
                last[step['rank'], step['SM'], ref['version']] = i
        for rank in macro['participants']:
            for vid in macro['reads']:
                for h in homes[vid, rank]:
                    if h['home']['class'] == 'RF':
                        p = h['home']
                        for slot in range(p['slot_first'], p['slot_first'] + p['vectors']):
                            state[rank, h['SM'], slot] = vid
        for i, step in enumerate(steps):
            rank, sm = step['rank'], step['SM']
            if rank not in macro['participants'] or not 0 <= sm < 32:
                raise ValueError('native step owner')
            if not step.get('op') or any(k in step for k in ('callback', 'golden', 'handler')):
                raise ValueError('native callback/opcode forbidden')
            positive(step['repeats'], 'native repeats')
            if not step.get('rounding') or not step.get('provider_refs') or not step.get('source_arithmetic'):
                raise ValueError('native step provenance')
            if len(step['reads']) > 2 or len(step['writes']) > 1:
                raise ValueError('native two-source port capacity')
            for ref in step['reads'] + step['writes']:
                if type(ref['slot']) is not int or not 0 <= ref['slot'] < 512:
                    raise ValueError('native slot aperture')
            for ref in step['reads']:
                key = rank, sm, ref['slot']
                if state.get(key) != ref['version']:
                    raise ValueError('native stale/unpublished input')
            for ref in step['writes']:
                key = rank, sm, ref['slot']; old = state.get(key)
                if old is not None and last.get((rank, sm, old), -1) > i:
                    raise ValueError('native premature write reuse')
                ident = rank, sm, ref['version']
                if ident in definitions:
                    raise ValueError('native duplicate version')
                definitions.add(ident); state[key] = ref['version']
        plans[plan['pc']] = plan
    return plans


def bind_workspace_intervals(workspace, events, pcs, native_plans):
    """Bind R20 addresses to actual admission/retirement fence intervals.

    An entire PC holds the finite workspace lease. All native primitive traffic,
    including upper-word transactions, occurs inside the ordered nested program.
    No source mismatch, review arena, or physical ACK is silently adopted.
    """
    byid = {e['id']: e for e in events}
    allocations = {r['rank']: r for r in workspace['join']['rank_allocation']}
    intervals = []; rank_leases = defaultdict(list); seen = set()
    for pc in pcs:
        plan = native_plans[pc['pc']]
        for rank in pc['participants']:
            start = byid[pc['admit']]['start']; end = byid[pc['retire']]['end']
            rank_leases[rank].append((start, end, pc['pc']))
            regions = []; slots = []
            for symbol, allocation in plan['temporary_storage']['allocations'].items():
                key = pc['pc'], rank, symbol; seen.add(key)
                home = workspace['homes'][key]; source = allocation['home']
                if (home['version'] != allocation['version'] or home['lease'] != allocation['lease'] or
                        home['bytes'] != allocation['bytes'] or home['release_after'] != f"PC{pc['pc']}.retire"):
                    raise ValueError('workspace version/lease/retire binding mismatch')
                if home['class_'] == 'RF_workspace':
                    if source['class_'] != 'RF' or home['slots'] != source['vector_slots']:
                        raise ValueError('workspace RF source mismatch')
                    slots.extend(home['slots'])
                else:
                    expected = source['base_by_rank'][str(rank)] + source['byte_offset']
                    if source['class_'] != 'spill' or home['base'] != expected:
                        raise ValueError('workspace physical base source mismatch')
                    regions.append((home['base'], home['end_exclusive']))
                    extent = next(e for e in allocations[rank]['extents'] if e['name'] == 'native_workspace')
                    if not extent['base'] <= home['base'] < home['end_exclusive'] <= extent['base'] + extent['bytes']:
                        raise ValueError('workspace finite extent exhausted')
                if home.get('semantic_bits') == 64:
                    extent = next(e for e in allocations[rank]['extents'] if e['name'] == 'native_I64_highword_codec_sidecar')
                    lo = home['highword_base']; hi = lo + home['highword_reserved_bytes']
                    if not extent['base'] <= lo < hi <= extent['base'] + extent['bytes']:
                        raise ValueError('workspace I64 sidecar extent exhausted')
                    regions.append((lo, hi))
                intervals.append({'pc': pc['pc'], 'rank': rank, 'symbol': symbol,
                    'home': home, 'start': start, 'end': end, 'admit_event': pc['admit'],
                    'retire_event': pc['retire'], 'release_guard': home['release_guard'],
                    'I64_software_codec_implemented': home.get('semantic_bits') == 64,
                    'physical_codec_admitted': False,
                    'iteration_identity': ['session64', 'PC', 'rank', 'symbol', 'definition', 'loop_iteration_tuple'],
                    'write_visibility': 'priced provisional causal fence; actual physical event is unqualified'})
            regions.sort()
            if any(a[1] > b[0] for a, b in zip(regions, regions[1:])) or len(slots) != len(set(slots)):
                raise ValueError('workspace alias within live PC lease')
    if seen != set(workspace['homes']):
        raise ValueError('workspace provider coverage mismatch')
    for leases in rank_leases.values():
        leases.sort()
        if any(a[1] > b[0] for a, b in zip(leases, leases[1:])):
            raise ValueError('premature workspace lease reuse')
    return intervals, {'status': 'PASS_CONCRETE_SOFTWARE_WORKSPACE_INTERVALS',
        'temporary_home_count': len(intervals), 'rank_PC_leases': sum(map(len, rank_leases.values())),
        'final_native_source_match': True,
        'older_calendar_source_mismatch_preserved': not workspace['join']['final_native_calendar_source_match'],
        'review_candidate_arena_adopted': False, 'physical_or_clock_admission': False,
        'I64_software_codec': 'LE lower/upper32; equal owner/definition/iteration; two visible writes before publication',
        'I64_physical_codec_implemented': False}


def compile_target(target, graph, layout, table, native=None, providers=None, workspace=None):
    ranks = 2 if target == 'Qwen' else 96
    homes = version_homes(graph, layout, ranks); check_homes(homes, graph)
    values = {v['id']: v for v in graph['operands']}
    reuse = defaultdict(list); release_at = defaultdict(list); provider_ops = {}
    if providers:
        homes, reuse, release_at, provider_ops = bind_provider_homes(providers, graph, homes)
        check_homes(homes, graph)
    bundled = native and native.get('schema') != 'H3_ORDERED_NATIVE_LOWERING_V1'
    native_plans = ({o['pc']: o for o in native['operations']} if bundled else
                    validate_native_lowering(native, graph, homes, ranks) if native else {})
    if bundled:
        validate_bundle(native, graph)
    selected = {b['pc']: b for b in layout['selected_command_bindings']['bindings']}
    caps = {'global.collective': 1}
    for r in range(ranks):
        caps.update({f'r{r}.{k}': n for k, n in [('issue', 1), ('collective', 1), ('HBM', 1),
            ('sector_credit', 4), ('ACK_capture', 4), ('forward_CDC', 4), ('reverse_CDC', 4),
            ('RMW_lock', 4), ('opcode_context', 4), ('owner_lookup', 1), ('owner_context', 4)]})
        for sm in range(32):
            caps.update({f'r{r}.s{sm}.{k}': n for k, n in [('RF', 1), ('read_port', 2),
                ('write_port', 1), ('execute', 1), ('packing_queue', 2), ('root_FIFO', 2),
                ('shared_workspace', 1)]})
    scratch_peaks = Counter(); primitive_counts = Counter(); programs = {}; recipe_cache = {}
    cal = Calendar(caps); cost = table['values']; pcs = []; visible = {}; last_reader = {}; terminal = {}; last_pc = None
    persistent_owner = {}

    def stage(name, deps, endpoint, resources, units=1, **attrs):
        units = positive(units, name + '.units')
        return cal.add(name, list(dict.fromkeys(deps)), cost[endpoint] * units, resources,
                       endpoint=endpoint, repeats=units, stride=cost[endpoint], **attrs)

    def transfer(name, deps, h, rank, write):
        p = h['home']; sm = h['SM']; rr = f'r{rank}'; ss = rr + f'.s{sm}'
        if write and providers:
            deps = list(deps) + reuse.get(h.get('provider_ref'), [])
            if any(d not in cal.ends for d in deps):
                raise ValueError('provider home reuse before release')
        if p['class'] == 'RF':
            resources = {ss + '.RF': 1, ss + ('.write_port' if write else '.read_port'): 1}
            endpoint = 'RF_write_ACK' if write else 'RF_read'; units = p['vectors']
        elif p['class'] in ('spill', 'persistent'):
            resources = {rr + '.HBM': 1, rr + '.sector_credit': 1, rr + '.forward_CDC': 1,
                         rr + '.ACK_capture': 1, rr + '.RMW_lock': 1, rr + '.reverse_CDC': 1,
                         rr + '.owner_lookup': 1, rr + '.owner_context': 1}
            endpoint = 'HBM_write_sector' if write else 'HBM_read_sector'; units = ceil(p['bytes'], 32)
        else:
            resources = {rr + '.opcode_context': 1}; endpoint = 'consume'; units = 1
        event = stage(name, deps, endpoint, resources, units, version=h['version'], rank=rank,
                      SM=sm, home=p, provider_ref=h.get('provider_ref'),
                      request_identity={'version': h['version'], 'rank': rank, 'SM': sm, 'serial': name,
                          'repeat_sector_ordinal': 'repeat_index', 'epoch': 'token_session',
                          'quarantine': 'compound consumer+reverse+validated grant retirement'},
                      direction='write' if write else 'read')
        # HBM transport slots above stay owned across the full compound sequence.
        # Repeat stride explicitly includes backing visibility, consumer completion
        # and reverse CDC. It never purports to be an actual DUT completion event.
        if p['class'] in ('spill', 'persistent'):
            e = cal.events[-1]
            owner_cycles = 2 * (cost['owner_lookup'] + cost['owner_held_accept'])
            extra = owner_cycles + sum(cost[k] for k in ('forward_CDC', 'consume', 'reverse_CDC', 'validated_reverse_grant', 'retire'))
            if write:
                extra += cost['visibility_fence']
            e['stride'] += extra; e['end'] += extra * units
            e['phases_per_repeat'] = {'service': cost[endpoint], 'forward_CDC': cost['forward_CDC'],
                'consume': cost['consume'], 'reverse_CDC': cost['reverse_CDC'], 'retire': cost['retire'],
                'owner_lookup': 2 * cost['owner_lookup'], 'owner_held_accept': 2 * cost['owner_held_accept'],
                'validated_reverse_grant': cost['validated_reverse_grant']}
            if write:
                e['phases_per_repeat']['backing_visibility_fence'] = cost['visibility_fence']
            cal.ends[event] = e['end']
            for key, slots in e['resources'].items():
                for slot in slots:
                    cal.slots[key][slot] = e['end']
        return event

    # External values are scheduled provider inputs, never magically visible.
    for v in graph['operands']:
        if not v['external_source']:
            continue
        for rank in range(ranks):
            entries = homes[v['id'], rank]
            if not entries:
                continue
            prev = stage(f'input.{v["id"]}.r{rank}', [], 'external_stage', {f'r{rank}.issue': 1}, version=v['id'])
            ends = [transfer(f'{prev}.h{i}', [prev], h, rank, True) for i, h in enumerate(entries)]
            visible[v['id'], rank] = stage(prev + '.visible', ends, 'visibility_fence', {f'r{rank}.issue': 1})
            for h in entries:
                if h['home']['class'] == 'persistent':
                    persistent_owner[rank, h['home']['object']] = visible[v['id'], rank]

    # Source ordering is retained: macro dependencies include previous-PC retire.
    # Independent SM chains inside each macro overlap only on disjoint resources.
    for op in graph['operations']:
        pc = op['pc']; prefix = f'pc{pc}'; participants = op['participants']
        if not participants or len(participants) != len(set(participants)) or any(r not in range(ranks) for r in participants):
            raise ValueError('participant/rendezvous identity')
        deps = []
        for dep in op['dependencies']:
            if dep not in terminal:
                raise ValueError('PC dependency deadlock')
            deps.append(terminal[dep])
        if last_pc:
            deps.append(last_pc)
        admitted = stage(prefix + '.admit', deps, 'admit', {f'r{r}.issue': 1 for r in participants}, pc=pc)
        reads = []; read_by_rank = defaultdict(list)
        for vid in op['reads']:
            if vid not in values:
                raise ValueError('unknown read version')
            for rank in participants:
                for i, h in enumerate(homes[vid, rank]):
                    if (vid, rank) not in visible:
                        raise ValueError('unpublished/premature read ' + vid)
                    e = transfer(f'{prefix}.read.{vid}.r{rank}.h{i}', [admitted, visible[vid, rank]], h, rank, False)
                    reads.append(e); read_by_rank[rank].append(e); last_reader[vid, rank] = e
        collective = op['opcode'] in ('ALL_REDUCE', 'ARGMAX_REDUCE', 'all_gather', 'all_reduce', 'topk_merge', 'kv_gather')
        executions = []; collective_ready = admitted
        if collective and pc in native_plans:
            resources = {'global.collective': 1, **{f'r{r}.collective': 1 for r in participants}}
            collective_ready = stage(prefix + '.collective_admit', reads + [admitted], 'collective_sector',
                resources, max(1, ceil(sum(ceil(values[v]['elements_per_rank'][r] * values[v]['bits_per_element'], 8)
                    for v in op['reads'] for r in participants), 32)),
                atomic_rendezvous=True, participants=participants, phase='ordered source delivery before native consumption',
                golden_contract=op['golden_contract'])
        if pc in native_plans and bundled:
            for rank in participants:
                plan = native_plans[pc]
                if 'programs' in plan:
                    template = next((p for p in plan['programs'] if rank in p['rank_group']), None)
                    cache_key = template['source_template'] if template else 'empty_extent'
                else:
                    cache_key = f'Qwen.pc{pc}' + (f'.rank{rank}' if workspace else '')
                if cache_key not in recipe_cache:
                    recipe = bind_recipe(native, plan, op, rank, table, workspace)
                    counts = verify_native_program(recipe)
                    key = hashlib.sha256(cache_key.encode()).hexdigest()[:24]
                    programs[key] = recipe
                    recipe_cache[cache_key] = key, counts
                key, counts = recipe_cache[cache_key]; recipe = programs[key]
                primitive_counts.update(counts)
                scratch_peaks[rank] = max(scratch_peaks[rank], recipe['finite_scratch_bytes'])
                rr = f'r{rank}'
                resources = {rr + '.HBM': 1, rr + '.sector_credit': 1, rr + '.ACK_capture': 1,
                    rr + '.forward_CDC': 1, rr + '.reverse_CDC': 1, rr + '.opcode_context': 1,
                    rr + '.owner_lookup': 1, rr + '.owner_context': 1}
                for sm in range(32):
                    resources.update({rr + f'.s{sm}.RF': 1, rr + f'.s{sm}.execute': 1,
                        rr + f'.s{sm}.read_port': 2, rr + f'.s{sm}.write_port': 1,
                        rr + f'.s{sm}.shared_workspace': 1})
                executions.append(cal.add(f'{prefix}.r{rank}.native_recipe',
                    list(dict.fromkeys(read_by_rank[rank] + [collective_ready])), recipe['duration'], resources,
                    native_program_ref=key, native_source_PC=pc, pc=pc, rank=rank,
                    operand_versions={'reads': op['reads'], 'writes': op['writes']},
                    concrete_provider_operation=provider_ops.get(pc),
                    native_provider_bindings_ref=str(pc) if target == 'DeepSeek' else None,
                    policy='exclusive finite rank lease; ordered primitive calendar below; no internal ideal overlap'))
        elif pc in native_plans:
            plan = native_plans[pc]; chains = {}
            for index, step in enumerate(plan['steps']):
                rank, sm = step['rank'], step['SM']; ss = f'r{rank}.s{sm}'
                previous = [chains[rank, sm]] if (rank, sm) in chains else read_by_rank[rank] + [collective_ready]
                stem = f'{prefix}.native{index}'
                issued = stage(stem + '.issue', previous, 'admit', {ss + '.execute': 1}, native_step=step)
                read = stage(stem + '.consume', [issued], 'RF_read', {ss + '.RF': 1, ss + '.read_port': max(1, len(step['reads']))}, step['repeats'])
                execute = stage(stem + '.execute', [read], 'native:' + step['op'], {ss + '.execute': 1}, step['repeats'])
                write = stage(stem + '.commit', [execute], 'RF_write_ACK', {ss + '.RF': 1, ss + '.write_port': 1}, step['repeats'])
                chains[rank, sm] = stage(stem + '.retire', [write], 'retire', {ss + '.execute': 1})
            executions.extend(chains.values())
        elif pc in selected:
            b = selected[pc]; templates = layout['selected_command_bindings']['command_templates']; roots = defaultdict(list)
            for binding in b['participant_commands']:
                for rank in binding['rank_group']:
                    if rank not in participants:
                        raise ValueError('native participant outside macro')
                    sm = binding['SM']; ss = f'r{rank}.s{sm}'; previous = list(read_by_rank[rank]) + [admitted]
                    previous = [stage(f'{prefix}.r{rank}.s{sm}.constants', previous, 'external_stage',
                        {ss + '.RF': 1, ss + '.write_port': 1},
                        max(1, len(binding['coefficient_constant_provider_preconditions'])),
                        provider_preconditions=binding['coefficient_constant_provider_preconditions'])]
                    template = templates[binding['command_template']]
                    for command in template:
                        ci = command['command_index']; stem = f'{prefix}.r{rank}.s{sm}.cmd{ci}'
                        issued = stage(stem + '.issue', previous, 'admit', {ss + '.execute': 1}, command=command)
                        consumed = stage(stem + '.consume', [issued], 'RF_read', {ss + '.RF': 1, ss + '.read_port': 2})
                        ran = stage(stem + '.execute', [consumed], 'native:' + command['op'], {ss + '.execute': 1})
                        committed = stage(stem + '.commit', [ran], 'RF_write_ACK', {ss + '.RF': 1, ss + '.write_port': 1})
                        previous = [stage(stem + '.retire', [committed], 'retire', {ss + '.execute': 1})]
                    roots[rank].append(stage(f'{prefix}.r{rank}.s{sm}.root', previous, 'root_delivery',
                        {ss + '.root_FIFO': 1, f'r{rank}.s0.RF': 1, f'r{rank}.s0.write_port': 1},
                        source_RF_slot=binding['root_RF_slot'], root_version=binding['root_version'],
                        collector_lane=sm, closed_delivery_fence=True))
            for rank in participants:
                if not roots[rank]:
                    raise ValueError('missing root participant')
                tail = stage(f'{prefix}.r{rank}.collector', roots[rank], 'norm_collector_tail',
                    {f'r{rank}.s0.RF': 1, f'r{rank}.s0.execute': 1},
                    golden_contract=op['golden_contract'], root_order=sorted(x['SM'] for x in b['participant_commands'] if rank in x['rank_group']))
                for sm in sorted({h['SM'] for vid in op['writes'] for h in homes[vid, rank]}):
                    delivered = stage(f'{prefix}.r{rank}.s{sm}.scalar', [tail], 'scalar_broadcast',
                        {f'r{rank}.s{sm}.root_FIFO': 1, f'r{rank}.s{sm}.RF': 1})
                    executions.append(stage(f'{prefix}.r{rank}.s{sm}.scale', [delivered], 'norm_output_scale',
                        {f'r{rank}.s{sm}.execute': 1}))
        elif collective:
            resources = {'global.collective': 1}
            resources.update({f'r{r}.collective': 1 for r in participants})
            bytes_ = sum(ceil(values[v]['elements_per_rank'][r] * values[v]['bits_per_element'], 8)
                         for v in op['reads'] for r in participants)
            executions.append(stage(prefix + '.rendezvous', reads + [admitted], 'collective_sector',
                resources, max(1, ceil(bytes_, 32)), participants=participants,
                atomic_rendezvous=True, golden_contract=op['golden_contract'],
                ordered_source_ranks=participants, payload_bytes=bytes_))
        else:
            for rank in participants:
                previous = list(read_by_rank[rank]) + [admitted]
                units = max(1, ceil(max(sum(values[v]['elements_per_rank'][rank] for v in op['reads']),
                                       sum(values[v]['elements_per_rank'][rank] for v in op['writes'])), 128))
                for index, endpoint in enumerate(op['missing_native_endpoints']):
                    is_memory = any(s in endpoint.lower() for s in ('hbm', 'provider', 'packed', 'fetch', 'visible'))
                    resources = {f'r{rank}.opcode_context': 1,
                                 f'r{rank}.HBM' if is_memory else f'r{rank}.s0.execute': 1}
                    previous = [stage(f'{prefix}.r{rank}.provider{index}', previous, 'provider:' + endpoint,
                        resources, units, golden_contract=op['golden_contract'],
                        source_binding=op.get('external_bindings', op['source']))]
                executions.append(stage(f'{prefix}.r{rank}.execute', previous, 'operator:' + op['opcode'],
                    {f'r{rank}.s0.execute': 1, f'r{rank}.opcode_context': 1}, units,
                    source_operation=op['source'], golden_contract=op['golden_contract'],
                    implementation='parameterized software endpoint; numerical execution separate'))
        if collective and pc in native_plans:
            resources = {'global.collective': 1, **{f'r{r}.collective': 1 for r in participants}}
            executions = [stage(prefix + '.rendezvous', executions + reads + [admitted],
                'collective_sector', resources, max(1, ceil(sum(
                    ceil(values[v]['elements_per_rank'][r] * values[v]['bits_per_element'], 8)
                    for v in op['reads'] for r in participants), 32)),
                atomic_rendezvous=True, participants=participants, golden_contract=op['golden_contract'])]
        consumed = stage(prefix + '.consume', executions + reads + [admitted], 'consume',
                         {f'r{r}.issue': 1 for r in participants}, pc=pc)
        commits = []
        for vid in op['writes']:
            if vid not in values or values[vid]['birth_pc'] != pc:
                raise ValueError('wrong write version producer')
            for rank in range(ranks):
                entries = homes[vid, rank]
                destination_admit = consumed
                if entries and rank not in participants:
                    destination_admit = stage(f'{prefix}.delivery.r{rank}.{vid}', [consumed], 'admit', {f'r{rank}.issue': 1},
                        source_ranks=participants, destination_rank=rank)
                for i, h in enumerate(entries):
                    p = h['home']; extra = []
                    if p['class'] == 'persistent' and (rank, p['object']) in persistent_owner:
                        extra.append(persistent_owner[rank, p['object']])
                    # RF/spill reuse obeys inclusive static lifetime check and previous
                    # macro retirement; old consumer and reverse credits have drained.
                    event = transfer(f'{prefix}.write.{vid}.r{rank}.h{i}', [destination_admit] + extra, h, rank, True)
                    commits.append(event)
                if entries:
                    fence = stage(f'{prefix}.visible.{vid}.r{rank}', commits[-len(entries):],
                        'visibility_fence', {f'r{rank}.issue': 1}, version=vid, rank=rank)
                    visible[vid, rank] = fence; commits.append(fence)
                    for h in entries:
                        if h['home']['class'] == 'persistent':
                            persistent_owner[rank, h['home']['object']] = fence
        last_pc = stage(prefix + '.retire', commits + [consumed], 'retire',
                        {f'r{r}.issue': 1 for r in participants}, pc=pc)
        terminal[pc] = last_pc
        for h in release_at.get(pc, []):
            stage(h['release_event'], [last_pc, visible[h['version'], h['rank']]], 'validated_reverse_grant',
                {f'r{h["rank"]}.issue': 1}, provider_ref=h['provider_ref'],
                requires=h['release_requires'], source_consumers=h['consumers'])
        pcs.append({'pc': pc, 'opcode': op['opcode'], 'participants': participants,
                    'admit': admitted, 'consume': consumed, 'commit_fences':
                    [e for e in commits if '.visible.' in e], 'retire': last_pc,
                    'read_versions': op['reads'], 'write_versions': op['writes'],
                    'native_commands': pc in selected or pc in native_plans, 'atomic_collective': collective})
    proof = verify_calendar(cal.events, caps)
    for e in cal.events:
        if 'native_program_ref' in e and e['end'] - e['start'] != programs[e['native_program_ref']]['duration']:
            raise ValueError('native enclosing reservation duration')
    demands = [] if providers else extent_demands(layout)
    workspace_layout = {p['rank']: p for p in (native or {}).get('storage', {}).get('software_provider_layout', [])}
    for rank, size in sorted(scratch_peaks.items()):
        if size:
            demands.append({'rank_group': [rank], 'class': 'native_temporary_scratch',
                'required_bytes': size, 'alignment_bytes': 512, 'additional_bytes': size,
                'required_minimum_AW': max(1, (size - 1).bit_length()),
                'source_provider_AW': 34 if target == 'Qwen' else 27,
                'source_provider_address_width_fits': size <= 2**(34 if target == 'Qwen' else 27),
                'status': 'CONSTRAINED_SUCCESSOR_EXTENT_REQUIRED',
                'constraints': ['distinct from all version spill, checkpoint and persistent extents',
                    'capacity >= maximum bound recipe arena; no modulo alias',
                    'producer allocation leases retire before workspace reuse; conservative fallback buffers drain before reuse'],
                'calendar_binding': ('producer concrete software base and lease; physical residence unqualified' if rank in workspace_layout else
                                     'finite logical arena; resident physical base needs provider binding'),
                'producer_workspace_layout': workspace_layout.get(rank),
                'bounded_tiled_allocation': False,
                'admission_scope': 'outside retained source spill extent; software workspace reservation only'})
    persistent_caps = {}
    for (vid, rank), entries in homes.items():
        for h in entries:
            if h['home']['class'] == 'persistent':
                key = f'r{rank}:' + h['home']['object']
                persistent_caps[key] = max(persistent_caps.get(key, 0), h['home']['bytes'])
    workspace_intervals = []; workspace_proof = None
    if workspace:
        workspace_intervals, workspace_proof = bind_workspace_intervals(workspace, cal.events, pcs, native_plans)
    return {'schema': 'H3_COMPLETE_NATIVE_SOFTWARE_CALENDAR_V1', 'target': target,
        'status': ('PASS_COMPLETE_NATIVE_SOFTWARE_CALENDAR' if len(native_plans) == len(pcs) else
                   'PASS_MACRO_RESERVATION_INTERMEDIATE'), 'PC_count': len(pcs), 'PCs': pcs,
        'native_lowering_PC_count': len(native_plans),
        'native_operator_lowering_complete': len(native_plans) == len(pcs),
        'ordinary_native_lowering_gap_PCs': [p['pc'] for p in pcs if p['pc'] not in native_plans and not p['native_commands']],
        'events': cal.events, 'resources': caps, 'proof': proof,
        'native_primitive_batch_counts': dict(sorted(primitive_counts.items())),
        'native_programs': programs,
        'native_provider_bindings_by_PC': {str(pc): plan['provider_bindings'] for pc, plan in native_plans.items()
                                           if 'provider_bindings' in plan},
        'native_primitive_count_gate': ('PASS_ALL_PC_EXPORTED_COUNTS' if native_plans and
            all(p.get('producer_vector_count_gate') == 'PASS_EXACT_EXPORTED_NATIVE_COUNTS'
                for p in programs.values() if p['primitive_tree']) else 'NOT_ALL_EXPORTED_COUNT_CHECKS_AVAILABLE'),
        'workspace_provider_intervals': workspace_intervals, 'workspace_provider_proof': workspace_proof,
        'version_home_archive': ('Qwen_provider_binding.json.gz' if providers else DISTRIBUTED + '/' + target + '.json.gz'),
        'provider_binding_coverage': providers['coverage'] if providers else None,
        'provider_resource_contract': providers['resource_contract'] if providers else None,
        'cycles': cal.ends[last_pc], 'cycle_unit': table['unit'],
        'latency_calibration': table['calibration'], 'hardware_clock_claim': False,
        'physical_base_and_lease_bindings_complete': False,
        'software_schedule_coverage_scope': 'all source PCs and actual instruction expansions; physical bases/leases remain separate admission',
        'RTL_or_physical_admission': False, 'CPU_numerical_oracle_cycles': False,
        'source_backed_extent_admission': not bool(demands), 'constrained_extent_successors': demands,
        'home_binding': 'actual provider lookup when supplied; otherwise exact distributed RF/spill homes; persistent finite logical objects, physical bases separate gate',
        'persistent_object_capacities': persistent_caps,
        'provisional_endpoint_scope': 'All macro providers and ordinary operators have explicit tile service reservations. Selected native templates expand command-by-command. Generic endpoints are parameterized software providers, not hardware implementation claims.'}


def load_inputs():
    manifest = read_json(ROOT / LOWERING / 'manifest.json')
    for path, digest in manifest['outputs'].items():
        if hashlib.sha256((ROOT / LOWERING / path).read_bytes()).hexdigest() != digest:
            raise ValueError('lowering input pin mismatch: ' + path)
    graphs = {t: read_json(ROOT / LOWERING / (t + '.json.gz')) for t in ('Qwen', 'DeepSeek')}
    layouts = {t: read_json(ROOT / DISTRIBUTED / (t + '.json.gz')) for t in graphs}
    return graphs, layouts


def encode(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()


def run_bounded_provider_join(directory, out, *, layers=36, verify=False):
    """Portable executable milestone; no old large-calendar regeneration."""
    import numpy as np
    base=Path(directory); out=Path(out); N,K=load_bounded_provider_sources(base)
    original=read_json(base/'Qwen_tiled.json.gz')
    graph=read_json(base/'sources/results/uarch/h3_versioned_lowering_20261002/Qwen.json.gz')
    full=audit_bounded_export(original,graph)
    ds=read_json(base/'ds/forward_dispatch_milestone.json.gz'); dsproof=audit_ds_bounded_dispatch(ds)
    dsprogram=ROOT/OUT/'final_ds_bed325f89/program_final.json.gz'
    if hashlib.sha256(dsprogram.read_bytes()).hexdigest()!=ds['source_program_sha256']:
        raise ValueError('DS bounded source program pin mismatch')
    config=dict(hidden_size=8,head_dim=4,num_attention_heads=2,num_key_value_heads=2,
        intermediate_size=16,vocab_size=16,num_hidden_layers=layers,rms_norm_eps=1e-6,rope_theta=1000000)
    native=N.compile_tiled(N.compile_program(config,context=32,groups=16)); positions=[(3,0),(5,1)]
    def bits(value):
        if isinstance(value,dict): return {k:bits(v) for k,v in value.items()}
        if isinstance(value,tuple): return [bits(v) for v in value]
        a=np.asarray(value)
        return {'shape':list(a.shape),'dtype':a.dtype.str,'bits':a.tobytes().hex()}
    expected=N.TiledMachine(native); references={}; reference_results=[]; pos=[0]
    def record(op,store):
        references[pos[0],op['pc']]={v:bits(store.debug_snapshot(v)) for v in op['writes']}
    for token,position in positions:
        pos[0]=position; reference_results.append(expected.run(token,position,record))
    backend=AddressedTileByteBackend(K,native);seed_bounded_fixture(N,backend,native,[p for _,p in positions])
    snapshots=[]; seen=[0]
    def compare(op,store):
        position=positions[seen[0]//len(native['operations'])][1]
        observed={v:bits(store.debug_snapshot(v)) for v in op['writes']}
        if observed!=references[position,op['pc']]: raise ValueError('post-commit output bits mismatch PC'+str(op['pc']))
        snapshots.append({'pc':op['pc'],'position':position,'sha256':hashlib.sha256(encode(observed)).hexdigest()})
        seen[0]+=1
    execution=execute_bounded_provider_program(N,K,native,backend,positions=positions,observer=compare)
    if [e['next_token'] for e in execution['executions']]!=[e['next_token'] for e in reference_results]:
        raise ValueError('bounded provider token mismatch')
    execution['post_commit_all_output_bits']='PASS_EXACT_PINNED_NATIVE_EXECUTOR_REFERENCE'
    execution['post_commit_output_snapshots']=snapshots
    execution['reference_scope']='test-only native primitive executor, no golden callback or numerical CPU time in costs'
    old=ROOT/OUT/'workspace_r20_33b741b4e/calendar_r1/manifest.json'
    oldmanifest=read_json(old)
    existing={'manifest_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),
        'I64_highword_read_sector':oldmanifest['endpoint_cycles']['values']['I64_highword_read_sector'],
        'I64_highword_write_sector':oldmanifest['endpoint_cycles']['values']['I64_highword_write_sector'],
        'I64_split_join':oldmanifest['endpoint_cycles']['values']['I64_split_join'],
        'I64_RMW_merge':oldmanifest['endpoint_cycles']['values']['I64_RMW_merge'],
        'r22_augmentation_applied':False,'existing_calendar_mutated':False,
        'bounded_Qwen_additional_temporary_HBM_bytes':0,
        'old_2801511424_byte_workspace_scope':'retained baseline only; not inherited by bounded export',
        'R21_read_sector_ticks':108,'R21_write_sector_ticks':128,
        'difference_to_parent_sector_cost':'2 admission ticks, explicit in R21 service; no additive second codec charge',
        'R20_intervals':'retained baseline allocation proof; bounded RF I64 uses two32bit words, optional realPC14 codec tested separately',
        'source_interval_join':'same actual graph versions and PC dependencies; old macro times do not qualify the new instruction counts'}
    outputs={'Qwen_all_PC_bindings.json.gz':full,'Qwen_provider_execution.json.gz':execution,
             'DS_bounded_reservation.json.gz':dsproof,'cost_reconciliation.json':existing}
    if not verify: out.mkdir(parents=True,exist_ok=False)
    hashes={}
    for name,value in outputs.items():
        raw=encode(value); data=gzip.compress(raw,mtime=0) if name.endswith('.gz') else raw+b'\n'
        path=out/name
        if verify:
            if path.read_bytes()!=data: raise ValueError('bounded join replay mismatch '+name)
        else: path.write_bytes(data)
        hashes[name]=hashlib.sha256(data).hexdigest()
    pins=read_json(base/'producer_pins.json')['files']
    manifest={'schema':'H3_BOUNDED_PROVIDER_JOIN_MILESTONE_V1','source_pins':pins,
        'consumer_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'output_sha256':hashes,'Qwen_fullshape_PCs':full['PCs'],'Qwen_families':full['classes'],
        'Qwen_executed_fixture_PCs_per_token':len(native['operations']),'Qwen_fixture_layers':layers,
        'Qwen_executed_tokens':len(positions),'Qwen_fixture_next_tokens':[e['next_token'] for e in execution['executions']],
        'DS_bounded_PCs':dsproof['PCs'],'DS_families':dsproof['families'],
        'DS_scope':dsproof['status'],'full_token_checkpoint_quality':False,'hardware_clock_admission':False,
        'existing_cost_reconciliation':existing,
        'remaining_gaps':['DS rank workspace physical bases/leases and checkpoint routes unbound',
            'DS ordered wholeprogram addressed microVM execution pending; bounded dispatch service reservation intermediate',
            'Qwen fullshape checkpoint token execution not demonstrated by reduced36layer raw fixtures',
            'Measured RF/HBM/NoC/shared/native/collective costs separate calibration gate',
            'KeplerR21 lacks IOTA; DS complete generic addressed microVM requires bounded IOTA binding'],
        'replay':f'python tools/h3_complete_native_calendar.py --bounded-provider-join {directory} --bounded-layers {layers} --out {out} --verify'}
    path=out/'manifest.json'; raw=encode(manifest)+b'\n'
    if verify:
        if path.read_bytes()!=raw: raise ValueError('bounded join manifest replay mismatch')
    else: path.write_bytes(raw)
    print(json.dumps({k:manifest[k] for k in ('Qwen_fullshape_PCs','Qwen_executed_fixture_PCs_per_token',
        'Qwen_fixture_next_tokens','DS_bounded_PCs','DS_families','hardware_clock_admission')}))
    print('PASS_BOUNDED_SOURCE_PINNED_PROVIDER_JOIN_REPLAY' if verify else 'PASS_BOUNDED_PROVIDER_JOIN_MILESTONE')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, default=ROOT / OUT)
    ap.add_argument('--cycles', type=Path)
    ap.add_argument('--verify', action='store_true')
    ap.add_argument('--native-lowering', type=Path, action='append', default=[])
    ap.add_argument('--qwen-providers', type=Path)
    ap.add_argument('--qwen-workspace', type=Path)
    ap.add_argument('--target', choices=('Qwen', 'DeepSeek'), action='append')
    ap.add_argument('--bounded-provider-join', type=Path)
    ap.add_argument('--bounded-layers', type=int, default=36)
    ap.add_argument('--ds-native-stage-calendar', type=Path)
    ap.add_argument('--ds-stage-bindings', type=Path)
    ap.add_argument('--ds-stage-workspace', type=Path)
    ap.add_argument('--ds-stage-rank', type=int, default=0)
    ap.add_argument('--h4-cost-join', type=Path)
    ap.add_argument('--ds-full-program-cost',type=Path)
    ap.add_argument('--ds-full-native-source',type=Path)
    ap.add_argument('--ds-shared-bridge',type=Path)
    ap.add_argument('--ds-shared-bridge-source',type=Path)
    ap.add_argument('--ds-native-source-commit')
    args = ap.parse_args()
    if args.ds_full_program_cost:
        dispatch=read_json(args.ds_full_program_cost)
        if args.ds_full_native_source is None:raise ValueError('actual source native artifact required')
        native_raw=source_bytes(args.ds_full_native_source,args.ds_native_source_commit)
        digest=hashlib.sha256(native_raw).hexdigest()
        if digest!=dispatch['source_program_sha256']:raise ValueError('full native source pin mismatch')
        bridge=read_json(args.ds_shared_bridge) if args.ds_shared_bridge else None
        if bridge is not None:
            if args.ds_shared_bridge_source is None:raise ValueError('bridge producer source bytes required')
            if hashlib.sha256(args.ds_shared_bridge_source.read_bytes()).hexdigest()!=bridge.get('bridge_source_sha256'):
                raise ValueError('bridge producer source bytes pin mismatch')
        native_program=json.loads(gzip.decompress(native_raw)) if bridge is not None else None
        result=compose_ds_full_program_services(dispatch,bridge=bridge,native_program=native_program)
        inputs=[args.ds_full_program_cost,args.ds_full_native_source,Path(__file__)]
        if args.ds_shared_bridge:inputs.extend([args.ds_shared_bridge,args.ds_shared_bridge_source])
        manifest={'schema':'H4_DS_FULL_PROGRAM_COST_MANIFEST_V1','PCs':result['PCs'],'families':result['families'],
            'source_sha256':{str(p.relative_to(ROOT)) if p.is_absolute() and p.is_relative_to(ROOT) else str(p):
                hashlib.sha256(native_raw if p==args.ds_full_native_source else p.read_bytes()).hexdigest() for p in inputs},
            'native_source_commit':args.ds_native_source_commit,
            'status':result['status'],'unknown_shared_template_calls':result['unknown_shared_template_calls'],
            'complete_service_software_ticks':None,'hardware_full_native_claim':False,
            'scope':'all-PC instruction-dependent scalar upper, retained provider projections and optional actual shared bridge; no arithmetic/provider replay'}
        summary={k:v for k,v in result.items() if k not in ('PC_intervals','template_shared_bindings','constrained_extent_successor_demand')}
        summary['unbound_physical_workspace_ranks']=len(result['constrained_extent_successor_demand'])
        artifacts={'manifest.json':manifest,'summary.json':summary,'full_program_costs.json.gz':result}
        if args.verify:
            for name,value in artifacts.items():
                if read_json(args.out/name)!=value:raise ValueError('DS full cost replay mismatch: '+name)
        else:
            args.out.mkdir(parents=True,exist_ok=False)
            for name,value in artifacts.items():
                raw=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
                (args.out/name).write_bytes(gzip.compress(raw,mtime=0) if name.endswith('.gz') else raw)
        print(json.dumps({'PCs':result['PCs'],'families':result['families'],'status':result['status'],
            'known_service_software_ticks':result['known_service_software_ticks'],
            'unknown_shared_template_calls':result['unknown_shared_template_calls'],'hardware_full_native_claim':False}))
        print('PASS_DS_FULL_SOURCE_PINNED_COST_REPLAY' if args.verify else 'PASS_DS_FULL_KNOWN_SERVICE_COMPOSITION')
        return
    if args.h4_cost_join:
        folder=args.h4_cost_join
        pins=read_json(folder/'inputs.json')
        for name,digest in pins['sha256'].items():
            if hashlib.sha256((folder/name).read_bytes()).hexdigest()!=digest:
                raise ValueError('H4 source pin mismatch: '+name)
        model=compose_h4_uarch((folder/'uarch_model.py.source').read_text(),
            read_json(folder/'uarch_parameters.json'),read_json(folder/'hardware_inventory.json'))
        execution=read_json(folder/'Qwen_provider_execution.json.gz')
        repriced=reprice_h4_intervals(execution)
        ds=reprice_h4_native_stages(read_json(folder/'DS_PC127_calendar.json.gz'),
            read_json(folder/'DS_PC127_template.json.gz'),repriced['explicit_provisional_costs'])
        summary={'schema':'H4_FINITE_MODEL_COST_JOIN_V1','source_sha256':pins['sha256'],
            'consumer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'Qwen_fixture_PC_intervals':len(repriced['ordered_PC_intervals']),
            'Qwen_software_ticks_before':repriced['baseline_software_ticks'],
            'Qwen_software_ticks_after':repriced['software_ticks'],
            'scratch64_transactions':repriced['scratch64_transactions'],
            'C0_command_repetitions':repriced['C0_commands'],
            'DS_PC127_C0_commands':ds['C0_commands'],'DS_PC127_added_software_ticks':ds['C0_added_software_ticks'],
            'DS_PC127_source_stages':len(ds['stages']),
            'H1_bridge_family_coverage':read_json(folder/'family_coverage.json'),
            'hardware_clock_admission':False,'no_provider_or_arithmetic_repeat':True,
            'RF_ACK_service_charged_once':True,'r22_augmentation_applied':False}
        artifacts={'model.json':model,'summary.json':summary,'repriced_intervals.json.gz':repriced,
                   'DS_PC127_repriced_stages.json.gz':ds}
        if args.verify:
            for name,value in artifacts.items():
                if read_json(args.out/name)!=value:raise ValueError('H4 cost replay mismatch: '+name)
        else:
            args.out.mkdir(parents=True,exist_ok=False)
            for name,value in artifacts.items():
                raw=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
                (args.out/name).write_bytes(gzip.compress(raw,mtime=0) if name.endswith('.gz') else raw)
        print(json.dumps(summary,sort_keys=True))
        print('PASS_H4_SOURCE_PINNED_COST_REPLAY' if args.verify else 'PASS_H4_FINITE_MODEL_COST_JOIN')
        return
    if args.ds_native_stage_calendar:
        if args.ds_stage_bindings is None:raise ValueError('native source provider bindings required')
        program=read_json(args.ds_native_stage_calendar);bindings=read_json(args.ds_stage_bindings)
        workspace=read_json(args.ds_stage_workspace) if args.ds_stage_workspace else None
        result=compile_ssa_finite_sm_services(program,rank=args.ds_stage_rank,provider_bindings=bindings,workspace=workspace)
        proof=verify_ssa_finite_sm_services(result,program) if result['status'].startswith('PASS') else {'status':result['status']}
        manifest={'schema':'H3_ORDERED_NATIVE_SM_STAGE_CALENDAR_V1',
            'source_sha256':{str(p.relative_to(ROOT)) if p.is_absolute() and p.is_relative_to(ROOT) else str(p):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in [args.ds_native_stage_calendar,args.ds_stage_bindings,Path(__file__)]},
            'status':result['status'],'proof':proof,'CPU_primitive_as_RTL_credit':False,'hardware_clock_admission':False,
            'scope':'ordered native stage/relative workspace/finite issue template; no payload or hardware execution'}
        if args.ds_stage_workspace:
            path=args.ds_stage_workspace
            name=str(path.relative_to(ROOT)) if path.is_absolute() and path.is_relative_to(ROOT) else str(path)
            manifest['source_sha256'][name]=hashlib.sha256(path.read_bytes()).hexdigest()
        raw=gzip.compress(encode(result),mtime=0);manifest['calendar_sha256']=hashlib.sha256(raw).hexdigest()
        if args.verify:
            if (args.out/'native_stage_calendar.json.gz').read_bytes()!=raw or read_json(args.out/'manifest.json')!=manifest or read_json(args.out/'proof.json')!=proof:
                raise ValueError('native stage/source-pin calendar replay mismatch')
        else:
            args.out.mkdir(parents=True,exist_ok=False)
            (args.out/'native_stage_calendar.json.gz').write_bytes(raw)
            (args.out/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
            (args.out/'proof.json').write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n')
        print(json.dumps({'status':'PASS_SOURCE_PINNED_NATIVE_SM_STAGE_REPLAY' if args.verify else result['status'],
                          'proof':proof,'hardware_clock_admission':False}))
        return
    if args.bounded_provider_join:
        return run_bounded_provider_join(args.bounded_provider_join,args.out,layers=args.bounded_layers,verify=args.verify)
    providers = read_json(args.qwen_providers) if args.qwen_providers else None
    native = {}
    producer_sources = {}
    native_hashes = {}
    for path in args.native_lowering:
        original = read_json(path)
        producer_sources.update(verify_portable_producer(path, original))
        data = normalize_bundle(original)
        if data['target'] in native:
            raise ValueError('duplicate target lowering')
        native[data['target']] = data
        native_hashes[data['target']] = hashlib.sha256(path.read_bytes()).hexdigest()
    workspace = load_workspace_provider(args.qwen_workspace, native_hashes['Qwen']) if args.qwen_workspace else None
    graphs, layouts = load_inputs(); default = cycle_table(graphs, layouts)
    table = read_json(args.cycles) if args.cycles else default
    required = set(default['values'])
    if workspace:
        provider_cost = workspace['join']['service_cost']
        for key, source in [('I64_highword_read_sector', 'highword_sidecar_extra_full_sector_read_ticks'),
                            ('I64_highword_write_sector', 'highword_sidecar_extra_full_sector_write_ticks'),
                            ('I64_split_join', 'codec_split_join_ticks_per128word_tile')]:
            if not args.cycles:
                table['values'][key] = positive(provider_cost[source], key)
            required.add(key)
        if not args.cycles:
            table['values']['I64_RMW_merge'] = 32
        required.add('I64_RMW_merge')
        table['workspace_cost_scope'] = 'R20 positive provisional inputs, unmeasured; sidecar sectors and split/join priced explicitly'
    for data in native.values():
        for primitive in bundle_primitives(data):
            key = 'native:' + primitive
            if not args.cycles:
                table['values'][key] = 32
            required.add(key)
    validate_cycles(table, required)
    sources = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in PINS}
    sources.update(producer_sources)
    if workspace:
        sources.update(workspace['sources'])
        sources[str(args.qwen_workspace.resolve())] = hashlib.sha256(args.qwen_workspace.read_bytes()).hexdigest()
    if args.qwen_providers:
        sources[str(args.qwen_providers.resolve())] = hashlib.sha256(args.qwen_providers.read_bytes()).hexdigest()
    for path in args.native_lowering:
        sources[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
    for path in args.native_lowering:
        for snapshot in sorted(path.parent.glob('*.source')):
            sources[str(snapshot.resolve())] = hashlib.sha256(snapshot.read_bytes()).hexdigest()
        for name in ('h3_exact_scalar_contract.py', 'compile_deepseek_snapshot.py', 'producer_pins.json'):
            snapshot = path.parent / name
            if snapshot.exists():
                sources[str(snapshot.resolve())] = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    if args.cycles:
        sources[str(args.cycles.resolve())] = hashlib.sha256(args.cycles.read_bytes()).hexdigest()
    if not args.verify:
        args.out.mkdir(parents=True, exist_ok=False)
    digests = {}; summaries = {}
    targets = args.target or list(graphs)
    if len(targets) != len(set(targets)):
        raise ValueError('duplicate target')
    for target in targets:
        result = compile_target(target, graphs[target], layouts[target], table, native.get(target), providers if target == 'Qwen' else None,
                                workspace if target == 'Qwen' else None)
        raw = encode(result); path = args.out / (target + '.json.gz')
        if args.verify:
            if gzip.decompress(path.read_bytes()) != raw:
                raise ValueError('calendar replay mismatch ' + target)
        else:
            path.write_bytes(gzip.compress(raw, mtime=0))
        digests[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        summaries[target] = {k: result[k] for k in ('status', 'PC_count', 'proof', 'cycles',
            'source_backed_extent_admission', 'constrained_extent_successors',
            'native_lowering_PC_count', 'native_operator_lowering_complete', 'native_primitive_count_gate',
            'workspace_provider_proof')}
    sources = {str(Path(k).relative_to(ROOT)) if Path(k).is_absolute() and Path(k).is_relative_to(ROOT) else k: v
               for k, v in sources.items()}
    manifest = {'schema': 'H3_COMPLETE_CALENDAR_REPLAY_V1', 'source_sha256': sources,
        'output_sha256': digests, 'endpoint_cycles': table, 'targets': summaries,
        'calibration_gate': 'Separate measured provider composition and numerical operator gates required; software ticks do not transfer to hardware clocks.',
        'replay': 'python tools/h3_complete_native_calendar.py --verify --out ' + str(args.out) +
            ''.join(' --native-lowering ' + str(p) for p in args.native_lowering) +
            (' --cycles ' + str(args.cycles) if args.cycles else '') +
            (' --qwen-providers ' + str(args.qwen_providers) if args.qwen_providers else '') +
            (' --qwen-workspace ' + str(args.qwen_workspace) if args.qwen_workspace else '') +
            ''.join(' --target ' + t for t in (args.target or []))}
    path = args.out / 'manifest.json'
    if args.verify:
        if read_json(path) != manifest:
            raise ValueError('source-pin manifest replay mismatch')
        print('PASS_SOURCE_PINNED_COMPLETE_CALENDAR_REPLAY')
    else:
        path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
        print(json.dumps(summaries, indent=2))


if __name__ == '__main__':
    main()
