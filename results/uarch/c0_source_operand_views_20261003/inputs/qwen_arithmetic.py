#!/usr/bin/env python3
"""Opt-in Qwen HBM software native recipes. No RTL or timing admission.

The VM executes the serialized recipes, not the source opcode dispatcher. Weight
providers return storage only (codes, scales, gamma, RoPE tables). Expressions
are movement/index expressions in compiler-produced IR; FP arithmetic is always
an instruction with an explicit F32 rounding boundary. The software workspace
is virtual RF with spill backing; physical providers must implement the listed
transactions before this can become a hardware schedule.
"""
import argparse
import ast
from collections import Counter
import copy
import gzip
from functools import lru_cache
from collections import defaultdict
import hashlib
import json
import math
import subprocess
from pathlib import Path
import numpy as np
from qwen_hbm_complete_program import compile_program, OPCODES

ROOT = Path(__file__).resolve().parents[1]
INPUT = 'results/uarch/h3_versioned_lowering_20261002/Qwen.json.gz'
OUT = 'results/uarch/h3_qwen_complete_native_20261002'
PROVIDER_COMMIT='570536f48'
PROVIDER_PATH='results/uarch/qwen_hbm_provider_bindings_r17_20261002/Qwen_provider_binding.json.gz'
F = np.float32


def ins(op, dst, *src, **kw):
    return dict(op=op, dst=dst, src=list(src), **kw)


def loop(var, stop, body, start='0', step='1'):
    return dict(op='FOR', var=var, start=str(start), stop=str(stop), step=str(step), body=body)


def bfpack(src, dst):
    return [ins('BITS', 'bits', src), ins('SHR', 'hi', 'bits', '16'),
            ins('AND', 'lsb', 'hi', '1'), ins('IADD', 'bias', 'bits', '32767'),
            ins('IADD', 'rounded', 'bias', 'lsb'),
            ins('AND', 'packed', 'rounded', '4294901760'), ins('FLOAT_BITS', dst, 'packed')]


def reciprocal(src, dst):
    body = [ins('BITS', 'rb', src), ins('AND', 'rsign', 'rb', '2147483648'),
            ins('AND', 'rexponent', 'rb', '2139095040'),
            ins('CMP_EQ', 'positive', 'rsign', '0'),
            ins('CMP_NE', 'finite', 'rexponent', '2139095040'),
            ins('CMP_GT', 'large', 'rb', '2129859015'),
            ins('AND', 'saturate', 'positive', 'finite'), ins('AND', 'saturate', 'saturate', 'large'),
            ins('ISUB', 'seed', '2129859015', 'rb'), ins('SELECT', 'seed', 'saturate', '0', 'seed'),
            ins('FLOAT_BITS', 'ry', 'seed')]
    for _ in range(3):
        body += [ins('FMUL', 'rp', src, 'ry'), ins('NEG', 'rn', 'rp'),
                 ins('FADD', 'rc', 'f32(2)', 'rn'), ins('FMUL', 'ry', 'ry', 'rc')]
    return body + [ins('MOV', dst, 'ry')]


def exponential(src, dst):
    body = [ins('FMAX', 'ex', src, 'f32(-87)'), ins('FMIN', 'ex', 'ex', 'f32(88)'),
            ins('FMUL', 't', 'ex', 'f32(1.4426950408889634)'),
            ins('FADD', 'n', 't', 'f32(12582912)'), ins('FADD', 'n', 'n', 'f32(-12582912)'),
            ins('FMUL', 'nr', 'n', 'f32(.693145751953125)'), ins('NEG', 'nr', 'nr'),
            ins('FADD', 'r', 'ex', 'nr'), ins('FMUL', 'nr', 'n', 'f32(1.428606765330187e-6)'),
            ins('NEG', 'nr', 'nr'), ins('FADD', 'r', 'r', 'nr'), ins('MOV', 'poly', 'f32(0.001388888888888889)')]
    for c in [1/120, 1/24, 1/6, .5, 1, 1]:
        body += [ins('FMUL', 'poly', 'poly', 'r'), ins('FADD', 'poly', 'poly', f'f32({c!r})')]
    return body + [ins('BITS', 'pb', 'poly'), ins('FTOI', 'ni', 'n'), ins('SHL64', 'exponent', 'ni', '23'),
                   ins('IADD64', 'resultbits', 'pb', 'exponent'), ins('FLOAT_BITS', dst, 'resultbits')]


def sum_last(src, dst, n):
    """Seq8, skip inactive tail, then padded adjacent pair tree; no reassociation."""
    groups = f'(({n})+7)//8'
    leaves = f'pow2ceil({groups})'
    return [ins('MOV', 'sum_rows', f'reshape({src}, (-1, {n}))'),
            ins('MOV', 'chunks', f'zeros((sum_rows.shape[0], {leaves}))'),
            loop('g', groups, [ins('MOV', 'acc', 'zeros((sum_rows.shape[0],))'),
                 loop('j', f'min(8, ({n})-8*g)', [ins('FADD', 'acc', 'acc', 'sum_rows[:,8*g+j]')]),
                 ins('MOV', 'chunks[:,g]', 'acc')]),
            loop('tree_level', f'bitlength({leaves})-1', [ins('FADD', 'chunks', 'chunks[:,0::2]', 'chunks[:,1::2]')]),
            ins('MOV', dst, f'reshape(chunks[:,0], {src}.shape[:-1])')]


def norm(src, dst, n, eps):
    body = [ins('FMUL', 'squares', src, src)] + sum_last('squares', 'total', n)
    body += [ins('FMUL', 'mean', 'total', f'f32({1/n!r})'),
             ins('FADD', 'variance', 'mean', f'f32({eps!r})'),
             ins('BITS', 'vb', 'variance'), ins('SHR', 'shift', 'vb', '1'),
             ins('ISUB', 'ybits', '1597463007', 'shift'), ins('FLOAT_BITS', 'y', 'ybits'),
             ins('FMUL', 'half', 'variance', 'f32(.5)')]
    for _ in range(3):
        body += [ins('FMUL', 'yy', 'y', 'y'), ins('FMUL', 'hyy', 'half', 'yy'),
                 ins('NEG', 'nyy', 'hyy'), ins('FADD', 'corr', 'f32(1.5)', 'nyy'),
                 ins('FMUL', 'y', 'y', 'corr')]
    return body + [ins('MOV', dst, 'y')]


def dot(x, w, dst, split, interleaved):
    """Rows vectorized; every K accumulation and split tree is an instruction."""
    k = f'{x}.shape[-1]'
    start = 's' if interleaved else f's*({k}//{split})'
    stop = k if interleaved else f'(s+1)*({k}//{split})'
    step = str(split) if interleaved else '1'
    body = [ins('MOV', 'parts', f'zeros(({w}.shape[0], {split}))'),
            loop('s', split, [ins('MOV', 'dotacc', f'zeros(({w}.shape[0],))'),
                 loop('k', stop, [ins('FMUL', 'product', f'{w}[:,k]', f'{x}[k]'),
                                   ins('FADD', 'dotacc', 'dotacc', 'product')], start, step),
                 ins('MOV', 'parts[:,s]', 'dotacc')])]
    body += [ins('FADD', 'parts', 'parts[:,0::2]', 'parts[:,1::2]') for _ in range((split-1).bit_length())]
    return body + [ins('MOV', dst, 'parts[:,0]')]


def recipe(op, p):
    name = op['opcode']; a = op['attributes']; c = p['config']; hd = c['head_dim']
    nh = c['num_attention_heads']//2; kv = c['num_key_value_heads']//2
    h = c['hidden_size']; ff = c['intermediate_size']//2
    n = p['register_shapes'][op['inputs'][0]][-1] if p['register_shapes'][op['inputs'][0]] else 1
    if name == 'EMBED':
        return [ins('LOAD_EMBED_CODES', 'codes', 'input0'), ins('LOAD_EMBED_SCALE', 'scale', 'input0'),
                ins('ITOF', 'decoded', 'codes'), ins('FMUL', 'out0', 'decoded', 'scale')]
    if name == 'RSTD': return norm('input0', 'out0', n, a['epsilon'])
    if name == 'MATRIX':
        d = p['weight_descriptors'][a['weight']]
        return [ins('LOAD_WEIGHT', 'w_codes', key=a['weight']), ins('ITOF', 'w', 'w_codes')] + bfpack('input0', 'x') + dot('x', 'w', 'out0', d['split'], False)
    if name == 'ROW_SCALE':
        return [ins('LOAD_SCALE', 'scale', key=a['weight']), ins('FMUL', 'out0', 'input0', 'scale')]
    if name == 'SCALAR_MUL': return [ins('FMUL', 'out0', 'input0', 'input1')]
    if name == 'RESIDUAL': return [ins('FADD', 'out0', 'input0', 'input1')]
    if name == 'QKV_SPLIT':
        return [ins('MOV', 'out0', f'reshape(input0[:{nh*hd}], ({nh},{hd}))'),
                ins('MOV', 'out1', f'reshape(input0[{nh*hd}:{(nh+kv)*hd}], ({kv},{hd}))'),
                ins('MOV', 'out2', f'reshape(input0[{(nh+kv)*hd}:], ({kv},{hd}))')]
    if name in ('HEAD_NORM', 'FINAL_NORM'):
        return norm('input0', 'rstd', n, a['epsilon']) + [
            ins('LOAD_GAMMA', 'gamma', layer=a.get('layer'), kind=a.get('kind', 'final')),
            ins('FMUL', 'normalized', 'input0', 'rstd[...,None]'), ins('FMUL', 'out0', 'normalized', 'gamma')]
    if name == 'ROPE':
        half = hd//2
        return [ins('LOAD_ROPE_COS', 'co', 'input1', theta=a['theta']), ins('LOAD_ROPE_SIN', 'si', 'input1', theta=a['theta']),
                ins('NEG', 'ns', 'si'), ins('FMUL', 'a', f'input0[:,:{half}]', 'co'),
                ins('FMUL', 'b', f'input0[:,{half}:]', 'ns'), ins('FADD', 'lo', 'a', 'b'),
                ins('FMUL', 'a', f'input0[:,{half}:]', 'co'), ins('FMUL', 'b', f'input0[:,:{half}]', 'si'),
                ins('FADD', 'hi', 'a', 'b'), ins('MOV', 'out0', 'concat((lo,hi), -1)')]
    if name == 'KV_WRITE':
        context = p['context_capacity']
        kbase = extent(p, a['die'], f"L{a['layer']}.K")['base']
        vbase = extent(p, a['die'], f"L{a['layer']}.V")['base']
        # Byte addresses exactly match token16 K and contiguous V backing.
        return [ins('BEGIN_WRITE', 'out0', 'input2', layer=a['layer'], die=a['die']),
                ins('MOV', 'heads', f'reshape(arange({kv}), ({kv},1))'),
                ins('MOV', 'dims', f'reshape(arange({hd}), (1,{hd}))'),
                ins('MOV', 'ka', f'{kbase}+((heads*{context//16}+input2//16)*{hd}+dims)*16+input2%16'),
                ins('MOV', 'va', f'{vbase}+(heads*{context}+input2)*{hd}+dims'),
                ins('FP8_PACK', 'kc', 'input0'), ins('FP8_PACK', 'vc', 'input1'),
                ins('WRITE_BYTES', None, 'out0', 'ka', 'kc'), ins('WRITE_BYTES', None, 'out0', 'va', 'vc')]
    if name == 'KV_FENCE': return [ins('COMMIT_PUBLISH', 'out0', 'input0')]
    if name == 'KV_READ':
        context = p['context_capacity']
        kb = extent(p, a['die'], f"L{a['layer']}.K")['base']; vb = extent(p, a['die'], f"L{a['layer']}.V")['base']
        return [ins('ACQUIRE', 'lease', 'input0', 'input1', layer=a['layer'], die=a['die']),
                ins('MOV', 'heads', f'reshape(arange({kv}), ({kv},1,1))'),
                ins('MOV', 'positions', 'reshape(arange(input1+1), (1,-1,1))'),
                ins('MOV', 'dims', f'reshape(arange({hd}), (1,1,{hd}))'),
                ins('MOV', 'ka', f'{kb}+((heads*{context//16}+positions//16)*{hd}+dims)*16+positions%16'),
                ins('MOV', 'va', f'{vb}+(heads*{context}+positions)*{hd}+dims'),
                ins('READ_BYTES', 'kc', 'lease', 'ka'), ins('READ_BYTES', 'vc', 'lease', 'va'),
                ins('FP8_UNPACK', 'out0', 'kc'), ins('FP8_UNPACK', 'out1', 'vc'),
                ins('BIND_LEASE', None, 'lease')]
    if name == 'SCORES':
        return bfpack('input0', 'query') + [ins('MOV', 'out0', f'zeros(({nh}, input1.shape[1]))'),
                loop('head', nh, [ins('MOV', 'x', 'query[head]'), ins('MOV', 'w', f'input1[head//{a["head_groups"]}]'),
                     *dot('x', 'w', 'score', a['split'], True),
                     ins('FMUL', 'out0[head]', 'score', f'f32({float(1/np.sqrt(hd))!r})')]),
                ins('CONSUMER_DONE', None, stage='SCORES', input_index=1)]
    if name == 'EXP_SUM':
        # Source np.max: scan in position order, pair ties carry latter value.
        return [ins('MOV', 'maximum', 'input0[:,0]'),
                loop('t', 'input0.shape[1]', [ins('FMAX', 'maximum', 'maximum', 'input0[:,t]')], '1'),
                ins('NEG', 'negative_max', 'maximum'), ins('FADD', 'centered', 'input0', 'negative_max[:,None]'),
                *exponential('centered', 'exps'), *bfpack('exps', 'out0'),
                *sum_last('exps', 'out1', 'position+1')]
    if name == 'PV':
        return [ins('MOV', 'out0', f'zeros(({nh},{hd}))'), loop('head', nh, [
            ins('MOV', 'x', 'input0[head]'), ins('MOV', 'w', f'transpose(input1[head//{a["head_groups"]}])'),
            *dot('x', 'w', 'out0[head]', a['split'], True)]),
            ins('CONSUMER_DONE', None, stage='PV', input_index=1)]
    if name == 'NORMALIZE':
        return reciprocal('input1', 'inverse') + [ins('FMUL', 'scaled', 'input0', 'inverse[:,None]'), ins('MOV', 'out0', 'reshape(scaled, (-1,))')]
    if name == 'ALL_REDUCE':
        return [ins('ROUTE', 'rank0', 'input0', source_rank=0, destination_rank=0),
                ins('ROUTE', 'rank1', 'input1', source_rank=1, destination_rank=0),
                ins('FADD', 'total', 'rank0', 'rank1'), ins('LOAD_SCALE', 'scale', key=a['post_scale_weight']),
                ins('FMUL', 'out0', 'total', 'scale'), ins('BROADCAST', 'out0', 'out0', ranks=[0,1])]
    if name == 'SILU_GATE':
        return [ins('MOV', 'gate', f'input0[:{ff}]'), ins('MOV', 'up', f'input0[{ff}:]'),
                ins('NEG', 'negative_gate', 'gate'), *exponential('negative_gate', 'eg'),
                ins('FADD', 'denominator', 'eg', 'f32(1)'), *reciprocal('denominator', 'inverse'),
                ins('FMUL', 'silu', 'gate', 'inverse'), ins('FMUL', 'out0', 'silu', 'up')]
    if name == 'ARGMAX':
        return [ins('MOV', 'best', 'input0[0]'), ins('MOV', 'index', str(a['global_row_offset'])),
                loop('row', 'input0.shape[0]', [ins('CMP_GT', 'win', 'input0[row]', 'best'),
                     ins('CMP_NE', 'candidate_nan', 'input0[row]', 'input0[row]'),
                     ins('CMP_EQ', 'best_finite_or_inf', 'best', 'best'),
                     ins('AND', 'first_nan', 'candidate_nan', 'best_finite_or_inf'),
                     ins('OR', 'win', 'win', 'first_nan'),
                     ins('SELECT', 'best', 'win', 'input0[row]', 'best'),
                     ins('SELECT', 'index', 'win', f'row+{a["global_row_offset"]}', 'index')], '1'),
                ins('MOV', 'out0', '(best, int(index))')]
    if name == 'ARGMAX_REDUCE':
        return [ins('ROUTE', 'winner0', 'input0', source_rank=0, destination_rank=0),
                ins('ROUTE', 'winner1', 'input1', source_rank=1, destination_rank=0),
                ins('CMP_GT', 'greater', 'winner1[0]', 'winner0[0]'),
                ins('CMP_EQ', 'equal', 'winner1[0]', 'winner0[0]'), ins('CMP_LT', 'lower', 'winner1[1]', 'winner0[1]'),
                ins('AND', 'tie', 'equal', 'lower'), ins('OR', 'win', 'greater', 'tie'),
                ins('SELECT', 'out0', 'win', 'winner1[1]', 'winner0[1]')]
    raise ValueError('unimplemented opcode '+name)


def extent(p, die, name):
    return next(e for e in p['memory_allocation'][die]['extents'] if e['name'] == name)


def walk(nodes):
    for node in nodes:
        yield node
        if 'body' in node: yield from walk(node['body'])


def make_versioned(p):
    # Same first-fit allocator as the archived H3 input, including spill leases.
    from h3_versioned_lowering import Builder, allocate, compact
    b = Builder('Qwen')
    for name in ('token','position'): b.value(name, [1,1], pc=-1, external=True)
    for op in p['instructions']:
        writes = []
        for name in op['outputs']:
            shape = p['register_shapes'][name]
            size = int(np.prod([p['context_capacity'] if v == 'position+1' else v for v in shape])) if shape else 1
            bits = 0 if op['opcode'] in ('KV_WRITE','KV_FENCE') else 64 if op['opcode']=='ARGMAX' else 32
            writes.append((name, [size if r in op['participants'] else 0 for r in range(2)], bits, None))
        b.op(op['opcode'], op['inputs'], writes, op['id'], {'attributes':op['attributes']}, op['participants'])
    peaks = allocate(b); compact(b)
    return dict(operations=b.operations, operands=b.values, storage_demand=peaks)


def binding(v):
    homes = copy.deepcopy(v['homes'])
    for home in homes:
        if home['class'] == 'RF':
            home['word_address'] = 'vector_slots[element//128]*128+element%128'
            home['page'] = 'slot>>7'; home['bank'] = '(element%128)//8'; home['row'] = 'slot&127'
            home['read_copies'] = [0,1]; home['write_copies'] = [0,1]
        elif home['class'] == 'spill_arena':
            home['address_space'] = 'activation_spill'; home['word_address'] = 'byte_offset+4*element'
            # A software arena has a real relative address even without a hardware resident base.
            home.pop('resident_base', None)
        else:
            home.pop('address', None); home.pop('bytes', None)
            home['address_space'] = 'publication_table'; home['word_address'] = v['id']
            home['payload'] = 'tag:uint64,layer:uint32,die:uint32,position:uint32,generation:uint64'
    return dict(version=v['id'], name=v['name'], birth_pc=v['birth_pc'], retire_pc=v['retire_pc'],
                consumers=v['consumers'], elements_per_rank=v['elements_per_rank'], homes=homes,
                shape=None, lease=f"value:{v['id']}", release_after=f"PC{v['retire_pc']}.consumer_done")



@lru_cache(maxsize=1)
def load_provider_binding():
    raw=subprocess.check_output(['git','show',PROVIDER_COMMIT+':'+PROVIDER_PATH],cwd=ROOT)
    binding=json.loads(gzip.decompress(raw))
    return binding,dict(commit=PROVIDER_COMMIT,path=PROVIDER_PATH,sha256=hashlib.sha256(raw).hexdigest())


def join_provider_homes(values,provider):
    byversion=defaultdict(list)
    for item in provider['version_homes']+provider['control_homes']: byversion[item['version']].append(item)
    if set(byversion)!=set(values): raise ValueError('provider version coverage mismatch')
    for version,refs in byversion.items():
        for home in refs:
            if home['birth_pc']!=values[version]['birth_pc'] or home['consumers']!=values[version]['consumers']:
                raise ValueError('provider lifetime/consumer mismatch')
        values[version]['homes']=refs
        values[version]['provider_refs']=[h['provider_ref'] for h in refs]
        values[version]['home_partition']='block=global_word//256;SM=block%32;local=(block//32)*256+global_word%256'
    return byversion


def join_operation_provider(operation,provider_op,provider,extents,reuse):
    if operation['pc']!=provider_op['pc'] or operation['opcode']!=provider_op['opcode']:
        raise ValueError('provider opcode/PC mismatch')
    if set(operation['reads'])!=set(provider_op['inputs']) or set(operation['writes'])!=set(provider_op['outputs']):
        raise ValueError('provider read/write version mismatch')
    operation['provider_binding']=provider_op
    operation['calendar_export']['concrete_provider_operation']=provider_op
    operation['calendar_export']['provider_resource_contract']=provider['resource_contract']
    contract=provider['resource_contract']
    operation['calendar_export']['capacities'].update(writer_credits_per_rank=contract['source_stage_sector_credits_per_rank'],
        reader_records_per_rank=contract['source_stage_reader_records_per_rank'],ACK_capture_per_rank=contract['source_stage_ACK_capture_records_per_rank'],
        logical_KV_reader_leases_per_rank=contract['logical_KV_reader_leases_per_rank'],
        request_QD=contract['request_QD'],return_RQD=contract['return_RQD'],physical_tags_per_stack=contract['physical_tags_per_stack'],
        RF_transaction_lease=contract['RF_transaction_lease'])
    operation['calendar_export']['capacities'].pop('writer_credits',None)
    operation['calendar_export']['capacities'].pop('reader_credits',None)
    operation['calendar_export']['reuse_dependencies']=[edge for v in operation['writes'] for ref in provider_op['outputs'][v] for edge in reuse.get(ref,[])]
    for node in walk(operation['recipe']):
        if node['op']=='FOR': continue
        node['version_home_refs']={'reads':provider_op['inputs'],'writes':provider_op['outputs']}
        node['external_provider_refs']=provider_op['external_providers']
        node['external_dependencies']+=provider_op['external_providers']
        if node['op'].startswith('LOAD_'):
            current=node['provider_ref']; name=current['ref'].split('.HBM.',1)[1]
            selected=[e for ref,e in extents.items() if ref.endswith('.extent.'+name) and e['rank'] in operation['participants']]
            if not selected: raise ValueError('unbound immutable provider '+name)
            current.update(ref=selected[0]['provider_ref'],base=selected[0]['base'],extent_bytes=selected[0]['bytes'],
                           concrete_provider_refs=[e['provider_ref'] for e in selected],codec=selected[0]['codec'])
        elif node['op'] in ('BEGIN_WRITE','WRITE_BYTES','COMMIT_PUBLISH','ACQUIRE','READ_BYTES','BIND_LEASE','CONSUMER_DONE'):
            node['provider_ref'].update(ref=f"Qwen.rank{operation['participants'][0]}.extent.KV_provider_state",
                concrete_provider_refs=[e['provider_ref'] for e in provider_op['external_providers']],
                writer_credits=provider['resource_contract']['source_stage_sector_credits_per_rank'],
                reader_credits=provider['resource_contract']['source_stage_reader_records_per_rank'],
                writer_credits_per_rank=provider['resource_contract']['source_stage_sector_credits_per_rank'],
                reader_records_per_rank=provider['resource_contract']['source_stage_reader_records_per_rank'],
                logical_reader_leases_per_rank=36,reverse_order=provider['resource_contract']['ownership_event_order'])
        else:
            node['provider_ref']['concrete_operand_homes']=provider_op['inputs']
            node['provider_ref']['concrete_output_homes']=provider_op['outputs']
            node['provider_ref']['SM_partition']='chunk32_block256 over the exact version_homes; no SM0 copy'
            node['lane_expansion']['owner_SM']='(global_word//256)%32; lookup (version,rank,SM)'

def compile_native(program=None, versioned=None):
    provider,provider_pin=load_provider_binding() if program is None else (None,None)
    p = compile_program() if program is None else program
    if provider:
        p=copy.deepcopy(p)
        for allocation in provider['allocation']:
            rank=allocation['rank']
            p['memory_allocation'][rank]['extents']=allocation['extents']
            p['memory_allocation'][rank]['allocated_bytes']=allocation['global_allocated_end_bytes']
    if versioned is None:
        if program is None:
            with gzip.open(ROOT/INPUT, 'rt') as f: versioned=json.load(f)
        else: versioned = make_versioned(p)
    if len(p['instructions']) != len(versioned['operations']): raise ValueError('PC coverage mismatch')
    values = {v['id']:binding(v) for v in versioned['operands']}
    source_spill={d['rank']:d['peak_spill_arena_bytes'] for d in versioned['storage_demand']}
    workspace_base={r:((p['memory_allocation'][r]['allocated_bytes']+source_spill[r]+511)//512)*512 for r in range(2)}
    for v in values.values():
        v['shape']=p['register_shapes'][v['name']]
        for home in v['homes']:
            home['provider_ref']='qwen.rank{rank}.sm0.RF' if home['class']=='RF' else 'qwen.rank{rank}.HBM.activation_spill' if home['class']=='spill_arena' else 'qwen.rank{rank}.publication_table'
            if home['class']=='spill_arena':
                home['base_by_rank']={str(rank):((p['memory_allocation'][rank]['allocated_bytes']+511)//512)*512 for lo,hi in home['rank_ranges'] for rank in range(lo,hi)}
                home['word_address']='base_by_rank[rank]+byte_offset+4*element'

    if provider:
        join_provider_homes(values,provider)
        source_spill={a['rank']:next(e['bytes'] for e in a['extents'] if e['name']=='activation_scratch') for a in provider['allocation']}
        workspace_base={a['rank']:((a['global_allocated_end_bytes']+511)//512)*512 for a in provider['allocation']}
    ops = []
    for source, old in zip(p['instructions'], versioned['operations']):
        pc=source['id']
        if old['pc']!=pc or old['opcode']!=source['opcode'] or old['source']['attributes']!=source['attributes']:
            raise ValueError('source opcode/attribute mismatch')
        for key, names in [('reads',source['inputs']),('writes',source['outputs'])]:
            if [values[v]['name'] for v in old[key]]!=names: raise ValueError('source version mismatch')
        nodes = recipe(source,p)
        for node in walk(nodes):
            node['round_point'] = 'FP32_RNE_then_positive_zero' if node['op'] in ('FADD','FMUL') else 'FP32_RNE' if node['op'].startswith('F') else 'exact_integer_or_movement'
        ops.append(dict(pc=pc, opcode=source['opcode'], participants=source['participants'],
            reads=old['reads'], writes=old['writes'], dependencies=old['dependencies'],
            recipe=nodes, native_lowering={'instructions':nodes, 'executable':True},
            input_leases=[values[v]['lease'] for v in old['reads']],
            retire_events=['result_commit','input_consumer_done','last_use_lease_release'],
            temporary_storage={'space':f'virtual_RF.PC{pc}', 'address':'symbol ordinal, array word offset',
                'RF_workspace_slots':[0,32], 'overflow':'versioned software spill arena; provider spill/refill required'},
            schedule={'begin_after':'TOKEN_START' if pc==0 else f'PC{pc-1}.retire',
                'duration_symbol':f'T_Qwen_native_{pc}', 'duration_expression':'SUM_steps(SUM_loop_instances(native_vector_transactions*C_primitive + RF_read_beats*C_RF_READ + RF_write_beats*C_RF_WRITE_ACK + spill_refill_beats*C_SPILL_REFILL + spill_write_beats*C_SPILL_WRITE + HBM_beats*C_HBM + route_beats*C_NoC + CDC_beats*C_CDC + publication_events*C_PUBLISH + credit_wait_edges*C_CREDIT_WAIT))',
                'result_after':'all writes committed and held responses consumed', 'domain':'streaming_1.2GHz_and_serial_0.9GHz',
                'hardware_qualified':False}))
    for operation, source in zip(ops, p['instructions']):
        export_transactions(operation, source, p, values, workspace_base)
    if provider:
        extents={e['provider_ref']:e for a in provider['allocation'] for e in a['extents']}
        reuse=defaultdict(list)
        for edge in provider['reuse_dependencies']: reuse[edge['new_home']].append(edge)
        for operation,provider_op in zip(ops,provider['operations']):
            join_operation_provider(operation,provider_op,provider,extents,reuse)
    provider_layout=[]
    for rank in range(2):
        size=max((o['temporary_storage']['spill_bytes'] for o in ops if rank in o['participants']),default=0)
        end=workspace_base[rank]+size
        provider_layout.append(dict(rank=rank,source_spill_base=extent(p,rank,'activation_scratch')['base'] if provider else ((p['memory_allocation'][rank]['allocated_bytes']+511)//512)*512,
            source_spill_bytes=source_spill[rank],workspace_base=workspace_base[rank],workspace_bytes=size,
            end_address=end,stack_count=4,stack_capacity_bytes=20250000000,capacity_fit=end<=4*20250000000,
            stripe='global128Bline stack=line%4; stackline=line//4',residence_qualified=False))
    counts=Counter(o['opcode'] for o in ops)
    primitives=sorted({i['op'] for o in ops for i in walk(o['recipe'])})
    if set(counts)!=set(OPCODES): raise ValueError('family coverage mismatch')
    return dict(schema='opentallas.H3.qwen-complete-native-software.v1', opt_in=True,
        source_program=p, operands=list(values.values()), operations=ops,
        concrete_provider_binding=provider,provider_binding_pin=provider_pin,
        coverage={'PCs':len(ops),'families':dict(sorted(counts.items())), 'all_PC_executable':True,
                  'null_native_lowerings':0,'primitives':primitives},
        schedule={'policy':'serial PC retirement, ordered primitive issue, no ideal overlap',
                  'duration_expression':'+'.join(o['schedule']['duration_symbol'] for o in ops),
                  'unknowns':{k:dict(cost_symbol=f'C_{k}', resource=resource(k), hardware_provider_required=True) for k in primitives},
                  'qualified':False,
                  'transport_cost_parameters':{k:dict(symbol='C_'+k,measured=False,hardware_qualified=False) for k in
                       ('RF_READ','RF_WRITE_ACK','SPILL_REFILL','SPILL_WRITE','HBM','NoC','CDC','PUBLISH','CREDIT_WAIT')}},
        storage={'source_storage_demand':{'archived_SM0_only':versioned['storage_demand'],'superseded_by':provider_pin,'active_source_provider_allocation':provider['allocation'] if provider else None}, 'RF_copies':2,
                 'lanes':128,'RF_vectors':512,'immutable_memory':p['memory_allocation'],
                 'software_provider_layout':provider_layout,
                 'temporary_policy':'lane-local register symbols; cross-lane chunk/tree scratch; software spills are explicit virtual addresses'},
        provider_requirements={k:dict(interface=k, resource=resource(k), semantics='VM primitive; no source opcode callback',
                         cost=f'C_{k}', exact_semantics=primitive_semantics(k), SS_FF_qualified=False) for k in primitives},
        coordination={'Peirce':'shares scalar/INT/movement primitive contract; Qwen TP2 distinct from DS TP96',
                      'Kepler':'Integrated r17 from570536f48: concrete32SM version_homes, external extent references, reverse-release reuse dependencies and charged32MiB source spill; native temporary spill is an additional explicitly charged finite software extent',
                      'Epicurus':'Qwen has no DIV: mean is rounded FMUL by 1/N; reciprocal uses bit seed and three Newton steps'},
        actual_RTL_executed=False, hardware_or_timing_credit=False)



class Shape:
    """Bounded shape interpreter, no tensor arithmetic or weight allocation."""
    def __init__(self, shape): self.shape=tuple(int(n) for n in shape)
    def __getitem__(self,index):
        proxy=np.lib.stride_tricks.as_strided(np.zeros(1,dtype=np.uint8),shape=self.shape,strides=(0,)*len(self.shape))
        return Shape(np.shape(proxy[index]))
    def binary(self,other): return Shape(np.broadcast_shapes(self.shape,shapeof(other)))
    __add__=__radd__=__sub__=__rsub__=__mul__=__rmul__=__floordiv__=__rfloordiv__=__mod__=__rmod__=binary


def shapeof(value):
    return value.shape if isinstance(value,Shape) else np.shape(value)


def shape_reshape(value,shape):
    shape=list(shape); elements=math.prod(shapeof(value))
    if -1 in shape: shape[shape.index(-1)]=elements//math.prod(n for n in shape if n!=-1)
    if elements!=math.prod(shape): raise ValueError('shape reshape extent')
    return Shape(shape)


def shape_concat(values,axis):
    result=list(shapeof(values[0])); result[axis]=sum(shapeof(v)[axis] for v in values)
    return Shape(result)


def shape_eval(text,env):
    helpers={**HELPERS, 'zeros':lambda shape:Shape(shape), 'arange':lambda n:Shape((n,)),
             'reshape':shape_reshape, 'concat':shape_concat,
             'transpose':lambda x:Shape(shapeof(x)[::-1]), 'int':lambda x:0 if isinstance(x,Shape) else int(x)}
    return eval(compile(ast.parse(text,mode='eval'),'<native shape>','eval'),{'__builtins__':{},**helpers},env)


def primitive_semantics(op):
    semantics={
        'FADD':'Separate binary32 RNE addition, then canonicalize any signed zero to +0. No FMA.',
        'FMUL':'Separate binary32 RNE multiply, then canonicalize any signed zero to +0. No FMA.',
        'NEG':'XOR bit31 of FP32; preserve NaN payload and signed zero.',
        'BITS':'FP32 bits reinterpret as unsigned32; no conversion.',
        'FLOAT_BITS':'Unsigned32 modulo reinterpret as FP32; no numerical conversion.',
        'IADD':'unsigned32 modulo addition', 'ISUB':'unsigned32 modulo subtraction',
        'IADD64':'signed64 addition; final FLOAT_BITS truncates modulo 2^32',
        'SHL64':'signed64 left shift for exponent reconstruction',
        'SHR':'logical unsigned32 right shift', 'AND':'unsigned32 bitwise AND', 'OR':'unsigned32 bitwise OR',
        'ITOF':'signed integer storage to FP32 RNE', 'FTOI':'finite FP32 integral range-reduction n to signed64, toward zero',
        'FMAX':'binary32 maximum; latter equal operand, propagate NaN (source np.maximum)',
        'FMIN':'binary32 minimum; latter equal operand, propagate NaN (source np.minimum)',
        'SELECT':'predicate chooses a or b without numerical rounding; index remains integer',
        'MOV':'addressed copy/view/reshape only; shape/address integer arithmetic, no FP arithmetic',
        'FP8_PACK':'E4M3FN: sign only when rounded magnitude nonzero; RNE ties even; subnormal quantum 2^-9; normals 3 mantissa bits; saturate abs at448; nonfinite inputs rejected',
        'FP8_UNPACK':'E4M3FN magnitude code0..7 = code/512; code8..126=(1+(code%8)/8)*2^((code//8)-7); sign bit; +/-zero -> +0; magnitude127 rejected',
        'BEGIN_WRITE':'bounded8 writer credits; unique (layer,die,position); no overwrite of live/published generation',
        'WRITE_BYTES':'addressed uint8 backing writes staged under matching producer tag; no publication on acceptance',
        'COMMIT_PUBLISH':'require every K/V byte for token; commit backing then publish matching producer tag/key generation; retire writer credit',
        'ACQUIRE':'match fence key/tag and require all previous positions published; bounded72 reader credits',
        'READ_BYTES':'read only byte addresses under published lease; token16 K and contiguous V layouts',
        'BIND_LEASE':'associate K/V result versions with single reader lease',
        'CONSUMER_DONE':'SCORES before PV; retire reader only after both produced results; duplicate completion rejected',
        'ROUTE':'identity payload transfer on finite rank2 collective, no arithmetic or arrival-order permutation',
        'BROADCAST':'identity result publication to both ranks after rank-order reduction and postscale',
        'FOR':'finite exact integer range(start,stop,step); dependent body order preserved',
        'LOAD_WEIGHT':'read immutable signed INT8 weight codes from specified descriptor/address; no numerical oracle',
        'LOAD_SCALE':'read checkpoint BF16 per-row scale, exactly represented as FP32 storage by software provider',
        'LOAD_GAMMA':'read checkpoint BF16 norm gamma, exactly represented as FP32 storage by software provider',
        'LOAD_EMBED_CODES':'read one checkpoint W8 embedding row using token index; no per-layer activation injection',
        'LOAD_EMBED_SCALE':'read checkpoint BF16 row scale using token index',
        'LOAD_ROPE_COS':'FP32 constant table generated from source inv=(1/theta**(arange(0,hd,2)/hd)).F32; angle=F32(position)*inv rounded F32; cos computed in F64 then F32',
        'LOAD_ROPE_SIN':'same source table producer as COS; sin computed in F64 then F32',
    }
    if op.startswith('CMP_'): return 'ordered numerical comparison '+op[4:]+'; NaN comparisons false except NE; integer indices remain exact'
    return semantics[op]


def immutable_provider(node,source,p):
    op=node['op']; attrs=source['attributes']; name=None; die=source['participants'][0]
    ref={'ref':f'qwen.rank{die}.HBM', 'depends_on':'checkpoint_weight_and_table_residence', 'requires_before':'TOKEN_START'}
    if op in ('LOAD_WEIGHT','LOAD_SCALE'):
        d=p['weight_descriptors'][node['key']]; die=d['die']
        name=('head' if d['layer'] is None else f"L{d['layer']}.{d['name']}")+('.codes' if op=='LOAD_WEIGHT' else '.scales')
        ref.update(ref=f'qwen.rank{die}.HBM.{name}',descriptor=node['key'],
                   address='base+row*K+k' if op=='LOAD_WEIGHT' else 'base+2*row',
                   stored_bits=8 if op=='LOAD_WEIGHT' else 16,
                   shape=[d['rows'],d['K']] if op=='LOAD_WEIGHT' else [d['rows']],
                   source_tensors=d['checkpoint_sources'], folded_norm=d['folded_norm'])
    elif op in ('LOAD_EMBED_CODES','LOAD_EMBED_SCALE'):
        name='embedding'; h=p['config']['hidden_size']; vocab=p['config']['vocab_size']
        ref.update(ref=f'qwen.rank{die}.HBM.embedding',source_tensor='model.embed_tokens.weight',stored_bits=8 if op=='LOAD_EMBED_CODES' else 16,
                   address=f'base+token*{h}+element' if op=='LOAD_EMBED_CODES' else f'base+{vocab*h}+2*token')
    elif op=='LOAD_GAMMA':
        name='final_norm' if node['kind']=='final' else f"L{node['layer']}.qk_norm"
        offset=p['config']['head_dim']*2 if node['kind']=='k' else 0
        ref.update(ref=f'qwen.rank{die}.HBM.{name}',stored_bits=16,address=f'base+{offset}+2*element',
                   source_tensor='model.norm.weight' if node['kind']=='final' else f"model.layers.{node['layer']}.self_attn.{node['kind']}_norm.weight")
    elif op.startswith('LOAD_ROPE_'):
        name='rope_table'; hd=p['config']['head_dim']; offset=hd//2 if op.endswith('SIN') else 0
        ref.update(ref=f'qwen.rank{die}.HBM.rope_table',stored_bits=32,address=f'base+4*(position*{hd}+{offset}+element)',
                   producer='checkpoint_theta_position_FP32_angle_F64_trig_FP32_table',theta=node['theta'])
    if name:
        ref['base']=extent(p,die,name)['base']; ref['extent_bytes']=extent(p,die,name)['bytes']
    return ref


def inferred_result(node,args,p):
    op=node['op']
    if op=='LOAD_WEIGHT':
        d=p['weight_descriptors'][node['key']]; result=Shape((d['rows'],d['K']))
    elif op=='LOAD_SCALE': result=Shape((p['weight_descriptors'][node['key']]['rows'],))
    elif op=='LOAD_GAMMA': result=Shape((p['config']['hidden_size'] if node['kind']=='final' else p['config']['head_dim'],))
    elif op=='LOAD_EMBED_CODES': result=Shape((p['config']['hidden_size'],))
    elif op=='LOAD_EMBED_SCALE': result=Shape(())
    elif op.startswith('LOAD_ROPE'): result=Shape((p['config']['head_dim']//2,))
    elif op in ('MOV','ROUTE','BROADCAST'): result=args[0]
    elif op in ('BITS','FLOAT_BITS','NEG','ITOF','FTOI','FP8_PACK','FP8_UNPACK'): result=Shape(shapeof(args[0]))
    elif op=='SELECT': result=Shape(np.broadcast_shapes(*(shapeof(a) for a in args)))
    elif op in ('BEGIN_WRITE','ACQUIRE','COMMIT_PUBLISH'): result=Shape(())
    elif op=='READ_BYTES': result=Shape(shapeof(args[1]))
    elif op in ('WRITE_BYTES','BIND_LEASE','CONSUMER_DONE'): result=None
    else: result=Shape(np.broadcast_shapes(*(shapeof(a) for a in args)))
    return result

def export_transactions(operation,source,p,values,workspace_base):
    """Calendar-facing finite allocations and ordered vector transaction terms.

    Shape bounds are obtained without numerical execution. Count expressions
    retain nested sums (including shrinking tree levels), rather than assigning
    a zero cost to unavailable hardware services.
    """
    env={'position':p['context_capacity']-1}; maxima={}; producers={}; step=0
    for i,v in enumerate(operation['reads']):
        shape=tuple(p['context_capacity'] if n=='position+1' else n for n in values[v]['shape'])
        env[f'input{i}']=p['context_capacity']-1 if values[v]['name']=='position' else 0 if values[v]['name']=='token' else Shape(shape)
        if source['opcode']=='ARGMAX_REDUCE': env[f'input{i}']=(Shape(()),i)
        producers[f'input{i}']={'source_version':v,'provider_homes':values[v]['homes'],'after':f"PC{values[v]['birth_pc']}.result_commit" if values[v]['birth_pc']>=0 else 'TOKEN_START'}
    def visit(nodes,context):
        nonlocal step
        for node in nodes:
            if 'step_id' not in node:
                node['step_id']=f"PC{operation['pc']}.I{step}"; step+=1
            node['resource_ref']=resource(node['op']); node['cost_parameter']='C_'+node['op']
            node['external_dependencies']=[]
            if node['op']=='FOR':
                node['count_expression']=dict(kind='finite_range',start=node['start'],stop=node['stop'],step=node['step'],outer_loops=context)
                bounds=[int(shape_eval(node[k],env)) for k in ('start','stop','step')]
                indices=range(*bounds)
                if len(indices):
                    # Only tree loops change shapes between iterations. Other
                    # loops are index-parametric; one invocation gives their bound.
                    for index in indices if node['var']=='tree_level' else [indices[0]]:
                        env[node['var']]=index
                        visit(node['body'],context+[dict(var=node['var'],start=node['start'],stop=node['stop'],step=node['step'])])
                continue
            args=[shape_eval(text,env) for text in node.get('src',[])]
            op=node['op']
            result=inferred_result(node,args,p)
            resultshape=shapeof(result) if result is not None else ()
            old_shape=node.get('shape_max',[])
            if math.prod(resultshape)>=math.prod(old_shape) or 'shape_max' not in node: node['shape_max']=list(resultshape)
            reads=[]
            for text,a in zip(node.get('src',[]),args):
                referenced=sorted({n.id for n in ast.walk(ast.parse(text,mode='eval')) if isinstance(n,ast.Name) and n.id in producers})
                reads.append(dict(operand=text,shape_max=list(shapeof(a)),word_bits=64 if text in ('ka','va') else 8 if op=='FP8_UNPACK' else 32,
                    element_count_expression=f'numel(shape({text}))', producer_refs=[producers[n] for n in referenced]))
            node['read_ports']=reads
            node['source_arithmetic']=primitive_semantics(op)
            node['value_versions']={'reads':[{'operand':r['operand'],'producer_refs':r['producer_refs']} for r in reads],
                                    'write':node.get('dst'),'instance_identity':'(PC,step_id,loop_indices)',
                                    'recurrence':'a read of the same step uses its previous loop instance; first instance uses preceding definition'}
            node['write_port']={'operand':node.get('dst'),'shape_max':node['shape_max'], 'word_bits':8 if op=='FP8_PACK' else 32,
                                'elements_expression':'numel(result_shape_at_instance)'} if result is not None else {'operand':'external_transaction','word_bits':8 if op=='WRITE_BYTES' else 64}
            node['lane_expansion']={'lanes':128,'row_or_element_batches':'FOR beat in range(ceil(elements_at_instance/128))',
                                     'lane_index':'128*beat+lane','mask':'lane_index<elements_at_instance',
                                     'no_golden_reassociation':True}
            node['count_expression']=dict(outer_loops=context, primitive_invocations='SUM_over_outer_ranges(1)',
                native_vector_transactions='SUM_over_outer_ranges(ceil(numel(result_shape_at_instance)/128))',
                result_shape_rule={'instruction':op,'operands':node.get('src',[])},
                RF_read_transactions='2R maximum per vector beat; excess operands serialize',RF_write_transactions='1W both copies plus mirrored ACK',
                inactive_tail='mask inactive lanes, do not add inactive seq8 elements')
            if op.startswith('LOAD_'):
                node['provider_ref']=immutable_provider(node,source,p)
                node['external_dependencies']=[node['provider_ref']]
            elif op in ('ROUTE','BROADCAST'):
                node['provider_ref']={'ref':'qwen.TP2.collective','ranks':[0,1],'credits':1,'landing_slots':2,'epoch':f"PC{operation['pc']}",
                                      'release_after':'result_commit_and_both_consumers_done','no_reorder':True}
            elif op in ('BEGIN_WRITE','WRITE_BYTES','COMMIT_PUBLISH','ACQUIRE','READ_BYTES','BIND_LEASE','CONSUMER_DONE'):
                node['provider_ref']={'ref':f"qwen.rank{source['participants'][0]}.KV",'generation':'(layer,die,position,producer_tag)',
                                      'writer_credits':8,'reader_credits':72,'dependencies':operation['reads'],'ordered_after':operation['dependencies']}
            else: node['provider_ref']={'ref':'qwen.rank{rank}.sm0.SIMT','participants':source['participants'],'RF_read_copies':[0,1],'RF_write_copies':[0,1]}
            if op in ('READ_BYTES','WRITE_BYTES'):
                node['count_expression']['addressed_bytes']='numel(shape('+node['src'][1]+'))'
                node['count_expression']['HBM_sector_transactions']='number_of_unique_32B_sectors(addresses_at_instance)'
            if op.startswith('LOAD_'):
                node['count_expression']['HBM_bytes']='product(provider_ref.shape_or_result_shape)*provider_ref.stored_bits/8'
                node['count_expression']['HBM_sector_transactions']='ceil((byte_offset_mod32+HBM_bytes)/32)'
            dst=node.get('dst')
            if dst and result is not None:
                if '[' not in dst:
                    env[dst]=result
                    size=max(1,math.prod(shapeof(result)))
                    maxima[dst]=max(maxima.get(dst,0),size)
                    producers[dst]={'step':node['step_id'],'temporary':dst,'after':node['step_id']+'.result_commit'}
    visit(operation['recipe'],[])
    # One SM workspace plus finite HBM arena, recycled only at PC retirement.
    cursor=0; rfslot=3; allocations={}
    for name,size in maxima.items():
        byte_size=size*4; slots=(byte_size+511)//512
        if rfslot+slots<=32:
            home=dict(provider_ref='qwen.rank{rank}.sm0.RF',class_='RF',vector_slots=list(range(rfslot,rfslot+slots)),
                      word_address='vector_slots[element//128]*128+element%128',read_copies=[0,1],write_copies=[0,1])
            rfslot+=slots
        else:
            home=dict(provider_ref='qwen.rank{rank}.HBM.native_workspace',class_='spill',byte_offset=cursor,
                      base_by_rank={str(r):workspace_base[r] for r in source['participants']},
                      byte_address='base_by_rank[rank]+byte_offset+4*element',requires='refill_to_reserved_RF_then_compute_then_spill_with_ACK')
            cursor+=slots*512
        allocations[name]=dict(version=f"PC{operation['pc']}.tmp.{name}[loop_indices,definition_step]", max_words=size,bytes=byte_size,home=home,
                               lease=f"PC{operation['pc']}.workspace",release_after=f"PC{operation['pc']}.retire")
    operation['temporary_storage']=dict(allocations=allocations,RF_vectors_used=rfslot,spill_bytes=cursor,
        spill_endpoint='qwen.rank{rank}.HBM.native_workspace',RF_refill_slots=[0,1,2],
        issue_policy='sole SM0 command lease; serialize refill/operate/spill; no extra RF ports',
        lifetime='PC issue through retire; arrays have finite maximum shape at full context')
    operation['calendar_counts_full_context']=count_transactions(operation,source,p,values,p['context_capacity']-1)
    operation['calendar_export']=dict(schema='opentallas.H3.native-finite-transactions.v1',steps=operation['recipe'],
        concrete_counts_full_context=operation['calendar_counts_full_context'],
        dependencies=operation['dependencies'],participants=source['participants'],source_shapes=[values[v]['shape'] for v in operation['reads']],
        output_shapes=[values[v]['shape'] for v in operation['writes']],operand_versions=operation['reads']+operation['writes'],
        operand_provider_homes={v:values[v]['homes'] for v in operation['reads']+operation['writes']},
        leases=operation['input_leases']+[f"PC{operation['pc']}.workspace"],
        capacities={'RF_vectors':512,'RF_read_ports':2,'RF_write_ports':1,'shared_bytes':65536,
                    'writer_credits':8,'reader_credits':72,'collective_credits':1,'response_capture_slots':1},
        costs='C_<primitive> plus RF refill/spill, HBM, NoC, CDC, publication and credit-stall parameters; every unmeasured term symbolic',
        hardware_qualified=False)


def count_transactions(operation,source,p,values,position):
    """Exact recipe issue counts and vector-beat demand for one context extent.

    Shape-invariant loops are counted algebraically. Seq8 tails and interleaved
    split tails are counted separately; tree levels retain shrinking shapes.
    This evaluates no weights or activations and assigns no service latency.
    """
    env={'position':position}; counts={}; cache={}
    def ev(text):
        if text not in cache: cache[text]=compile(ast.parse(text,mode='eval'),'<count>','eval')
        helpers={**HELPERS,'zeros':lambda shape:Shape(shape),'arange':lambda n:Shape((n,)),
                 'reshape':shape_reshape,'concat':shape_concat,'transpose':lambda x:Shape(shapeof(x)[::-1]),
                 'int':lambda x:0 if isinstance(x,Shape) else int(x)}
        return eval(cache[text],{'__builtins__':{},**helpers},env)
    for i,v in enumerate(operation['reads']):
        shape=tuple(position+1 if n=='position+1' else n for n in values[v]['shape'])
        env[f'input{i}']=position if values[v]['name']=='position' else 0 if values[v]['name']=='token' else Shape(shape)
        if source['opcode']=='ARGMAX_REDUCE': env[f'input{i}']=(Shape(()),i)
    def visit(nodes,multiplier):
        for node in nodes:
            op=node['op']
            if op=='FOR':
                start,stop,step=(int(ev(node[k])) for k in ('start','stop','step'))
                indexes=range(start,stop,step)
                if not len(indexes): continue
                var=node['var']
                if var=='tree_level': groups=[(i,1) for i in indexes]
                elif var=='g' and len(indexes)>1: groups=[(indexes[0],len(indexes)-1),(indexes[-1],1)]
                elif var=='s':
                    knode=next(n for n in node['body'] if n['op']=='FOR' and n['var']=='k')
                    grouped={}
                    for i in indexes:
                        env[var]=i
                        bound=[int(ev(knode[k])) for k in ('start','stop','step')]
                        trip=len(range(*bound))
                        if trip not in grouped: grouped[trip]=[i,0]
                        grouped[trip][1]+=1
                    groups=list(grouped.values())
                else: groups=[(indexes[0],len(indexes))]
                for index,repeat in groups:
                    env[var]=index; visit(node['body'],multiplier*repeat)
                continue
            args=[ev(x) for x in node.get('src',[])]; result=inferred_result(node,args,p)
            entry=counts.setdefault(op,dict(primitive_invocations=0,native_vector_beats=0,logical_read_bits=0,logical_write_bits=0,RF_read_beats=0,RF_write_beats=0))
            elements=max(1,math.prod(shapeof(result))) if result is not None else 1
            if op=='WRITE_BYTES': elements=math.prod(shapeof(args[2]))
            elif op=='BIND_LEASE' or op=='CONSUMER_DONE': elements=1
            elif op=='LOAD_WEIGHT': elements=math.prod(shapeof(result))
            entry['primitive_invocations']+=multiplier
            entry['native_vector_beats']+=multiplier*((elements+127)//128)
            for text,a in zip(node.get('src',[]),args):
                # Immediate constants and shape literals require no RF reads.
                refs=[n.id for n in ast.walk(ast.parse(text,mode='eval')) if isinstance(n,ast.Name) and n.id in env and n.id not in ('position','g','j','k','s','head','row','tree_level','t')]
                if refs:
                    size=max(1,math.prod(shapeof(a)))
                    entry['logical_read_bits']+=multiplier*size*(8 if op=='FP8_UNPACK' else 32)
                    entry['RF_read_beats']+=multiplier*((size+127)//128)
            if result is not None:
                entry['logical_write_bits']+=multiplier*elements*(8 if op=='FP8_PACK' else 32)
                entry['RF_write_beats']+=multiplier*((elements+127)//128)
            dst=node.get('dst')
            if dst and '[' not in dst and result is not None: env[dst]=result
    visit(operation['recipe'],1)
    return dict(position=position,context_extent=position+1,by_primitive=counts,
        total_primitive_invocations=sum(c['primitive_invocations'] for c in counts.values()),
        RF_physical_read_bits=sum(c['RF_read_beats'] for c in counts.values())*4096,
        RF_physical_mirrored_write_bits=sum(c['RF_write_beats'] for c in counts.values())*8192,
        scope='explicit conservative RF materialization of every primitive operand/result; spills, table reads, HBM sectors, NoC, CDC and credit waits charged separately; no fusion or timing credit')

def resource(op):
    if op in ('FADD','FMUL'): return 'serial_SIMD_RF_2R1W'
    if op.startswith('LOAD_') or op in ('WRITE_BYTES','READ_BYTES','COMMIT_PUBLISH'): return 'HBM_L2_shared_RF_publication'
    if op in ('ROUTE','BROADCAST'): return 'TP2_collective_ordered_transport'
    if op in ('FOR',): return 'software_control_loop'
    return 'SIMT_INT_compare_movement_RF'


HELPERS = dict(reshape=np.reshape, transpose=np.transpose, concat=np.concatenate,
               zeros=lambda shape:np.zeros(shape,dtype=F), arange=np.arange,
               f32=F, int=int, min=min, max=max,
               pow2ceil=lambda n:1 << (int(n)-1).bit_length(), bitlength=lambda n:int(n).bit_length())


def expression(text, env):
    # Only generated indexing, integer address/shape arithmetic and movement calls.
    tree=ast.parse(text,mode='eval')
    for node in ast.walk(tree):
        if isinstance(node,ast.Call) and (not isinstance(node.func,ast.Name) or node.func.id not in HELPERS):
            raise ValueError('non-movement expression call')
        if isinstance(node,ast.Attribute) and node.attr!='shape': raise ValueError('expression attribute')
        if isinstance(node,(ast.Lambda,ast.ListComp,ast.DictComp,ast.GeneratorExp,ast.NamedExpr)):
            raise ValueError('expression code')
    return eval(compile(tree,'<native index>','eval'),{'__builtins__':{},**HELPERS},env)


def assign(dst, value, env):
    if '[' in dst:
        name, sub = dst.split('[',1)
        # Parse a subscript as indexing a proxy: assignment does not execute code.
        node=ast.parse(dst,mode='eval').body
        if not isinstance(node,ast.Subscript) or not isinstance(node.value,ast.Name): raise ValueError('destination')
        key=eval(compile(ast.Expression(node.slice),'<index>','eval'),{'__builtins__':{}},env)
        env[name][key]=value
    else: env[dst]=copy.deepcopy(value)


def poszero(value):
    a=np.asarray(value,dtype=F)
    return np.where(a==0,F(0),a).astype(F)


def pack8(value):
    # E4M3FN saturating RNE, matching the source contract; conversion is a native primitive.
    a=np.asarray(value,dtype=F); magnitude=np.abs(a).astype(np.float64)
    if np.any(~np.isfinite(a)): raise ValueError('nonfinite FP8 source')
    _,ex=np.frexp(magnitude); quantum=np.ldexp(1.,np.maximum(ex-1,-6)-3)
    rounded=np.minimum(np.rint(magnitude/quantum)*quantum,448).astype(F)
    table=fp8_table(); code=np.searchsorted(table,rounded).astype(np.uint8)
    return code | np.where((a<0)&(rounded!=0),128,0).astype(np.uint8)


def fp8_table():
    return np.array([F(i/512) if i<8 else F((1+(i%8)/8)*2**((i//8)-7)) for i in range(127)])


class Storage:
    """Address checked software HBM, delayed publication and two-consumer leases."""
    def __init__(self,p):
        self.p=p; self.bytes={}; self.pending={}; self.published={}; self.leases={}; self.tags=0; self.events=[]

    def begin(self, layer, die, position):
        key=(layer,die,int(position))
        if not 0<=key[2]<self.p['context_capacity']: raise ValueError('position aperture')
        if key in self.published or any(v['key']==key for v in self.pending.values()): raise ValueError('KV overwrite')
        if len(self.pending)>=8 or sum(v['key'][1]==die for v in self.pending.values())>=4: raise ValueError('writer credit exhaustion')
        tag=self.tags; self.tags+=1; self.pending[tag]=dict(key=key,payload={})
        self.events.append(dict(event='write_accept',tag=tag,key=key)); return tag

    def decode_address(self,layer,die,address):
        c=self.p['config']; context=self.p['context_capacity']; hd=c['head_dim']
        for kind in ('K','V'):
            e=extent(self.p,die,f'L{layer}.{kind}')
            if e['base']<=address<e['base']+e['bytes']:
                index=address-e['base']
                pos=((index//16//hd)%(context//16))*16+index%16 if kind=='K' else (index//hd)%context
                return kind,pos
        raise ValueError('KV byte aperture')

    def write(self,tag,addresses,codes):
        state=self.pending[int(tag)]; layer,die,_=state['key']
        ranges=[extent(self.p,die,f'L{layer}.{kind}') for kind in ('K','V')]
        for address,code in zip(np.asarray(addresses).flat,np.asarray(codes).flat):
            address=int(address)
            if not any(e['base']<=address<e['base']+e['bytes'] for e in ranges): raise ValueError('KV write aperture')
            if self.decode_address(layer,die,address)[1]!=state['key'][2]: raise ValueError('write generation address')
            if address in state['payload']: raise ValueError('duplicate write address')
            state['payload'][address]=int(code)
        if np.size(addresses)!=np.size(codes): raise ValueError('write extent')

    def commit(self,tag):
        tag=int(tag); state=self.pending[tag]; layer,die,_=state['key']; c=self.p['config']
        expected=2*(c['num_key_value_heads']//2)*c['head_dim']
        if len(state['payload'])!=expected: raise ValueError('incomplete KV commit')
        for address,code in state['payload'].items(): self.bytes[die,address]=code
        self.pending.pop(tag); self.published[state['key']]=tag
        self.events.append(dict(event='commit_publish',tag=tag,key=state['key']))
        return dict(tag=tag,key=state['key'])

    def acquire(self,fence,layer,die,position):
        key=(layer,die,int(position))
        if fence['key']!=key or self.published.get(key)!=fence['tag']: raise ValueError('stale fence')
        if any((layer,die,pos) not in self.published for pos in range(key[2]+1)): raise ValueError('missing previous KV')
        if len(self.leases)>=72 or sum(v['key'][1]==die for v in self.leases.values())>=36: raise ValueError('reader credits')
        lease=self.tags; self.tags+=1; self.leases[lease]=dict(key=key,done=set())
        self.events.append(dict(event='acquire',lease=lease,key=key)); return lease

    def read(self,lease,addresses):
        layer,die,position=self.leases[int(lease)]['key']
        ranges=[extent(self.p,die,f'L{layer}.{kind}') for kind in ('K','V')]
        flat=[]
        for a in np.asarray(addresses).flat:
            a=int(a)
            if not any(e['base']<=a<e['base']+e['bytes'] for e in ranges): raise ValueError('KV read aperture')
            byteposition=self.decode_address(layer,die,a)[1]
            if byteposition>position or (layer,die,byteposition) not in self.published: raise ValueError('read outside lease generation')
            if (die,a) not in self.bytes: raise ValueError('unpublished byte')
            flat.append(self.bytes[die,a])
        return np.array(flat,dtype=np.uint8).reshape(np.shape(addresses))

    def done(self,lease,stage):
        state=self.leases[lease]
        if stage in state['done'] or stage not in ('SCORES','PV'): raise ValueError('consumer completion')
        if stage=='PV' and 'SCORES' not in state['done']: raise ValueError('PV before SCORES')
        state['done'].add(stage); self.events.append(dict(event='consumer_done',lease=lease,stage=stage))
        if len(state['done'])==2:
            self.leases.pop(lease); self.events.append(dict(event='release',lease=lease))


class FixtureStorage:
    """Deterministic raw parameters, never expected activations."""
    def __init__(self,p): self.p=p; self.cache={}
    def matrix(self,key):
        if key not in self.cache:
            d=self.p['weight_descriptors'][key]; seed=int(hashlib.sha256(key.encode()).hexdigest()[:8],16)
            rng=np.random.default_rng(seed)
            self.cache[key]=(rng.integers(-4,5,(d['rows'],d['K']),dtype=np.int8),np.full(d['rows'],F(.03125)))
        return self.cache[key]
    def gamma(self,layer,kind):
        return np.ones(self.p['config']['hidden_size'] if kind=='final' else self.p['config']['head_dim'],dtype=F)
    def embedding_codes(self,token):
        return ((int(token)+np.arange(self.p['config']['hidden_size']))%9-4).astype(np.int8)
    def embedding_scale(self,token): return F(.125)
    def rope(self,position,theta):
        hd=self.p['config']['head_dim']; inv=(1/(theta**(np.arange(0,hd,2,dtype=np.float64)/hd))).astype(F)
        angle=(F(position)*inv).astype(F)
        return np.cos(angle.astype(np.float64)).astype(F),np.sin(angle.astype(np.float64)).astype(F)


class Machine:
    def __init__(self,native,weights=None):
        self.native=native; self.p=native['source_program']; self.weights=weights or FixtureStorage(self.p)
        self.storage=Storage(self.p); self.registers={}; self.lease_by_version={}; self.events=[]; self.primitive_counts=Counter()
        self.bindings={v['version']:v for v in native['operands']}
        self.provider_payloads={}; self.release_events=set(); self.provider_reuse=defaultdict(list)
        provider=native.get('concrete_provider_binding')
        if provider:
            for edge in provider['reuse_dependencies']: self.provider_reuse[edge['new_home']].append(edge['wait_release'])
        self.address_words={}; self.live=set(); self.expression_cache={}

    def value(self,text,env):
        # Cache validated code: full graph replay executes many identical primitive expressions.
        if text not in self.expression_cache:
            expression(text,env)
            self.expression_cache[text]=compile(ast.parse(text,mode='eval'),'<native index>','eval')
        return eval(self.expression_cache[text],{'__builtins__':{},**HELPERS},env)

    def nodes(self,nodes,env,operation):
        for node in nodes:
            op=node['op']
            if op=='FOR':
                start,stop,step=(int(self.value(node[k],env)) for k in ('start','stop','step'))
                if step<=0 or start<0 or stop<0: raise ValueError('loop aperture')
                for index in range(start,stop,step):
                    env[node['var']]=index; self.nodes(node['body'],env,operation)
                continue
            args=[self.value(x,env) for x in node.get('src',[])]
            self.primitive_counts[op]+=1
            if op=='FADD': result=poszero(np.asarray(args[0],dtype=F)+np.asarray(args[1],dtype=F))
            elif op=='FMUL': result=poszero(np.asarray(args[0],dtype=F)*np.asarray(args[1],dtype=F))
            elif op=='NEG': result=(np.asarray(args[0],dtype=F).view(np.uint32)^np.uint32(0x80000000)).view(F)
            elif op=='BITS': result=np.asarray(args[0],dtype=F).view(np.uint32)
            elif op=='FLOAT_BITS': result=np.asarray(args[0]).astype(np.uint32).view(F)
            elif op=='ITOF': result=np.asarray(args[0],dtype=F)
            elif op=='FTOI': result=np.asarray(args[0],dtype=np.int64)
            elif op in ('IADD','ISUB','AND','OR','SHR'):
                left=np.asarray(args[0]).astype(np.uint32); right=np.asarray(args[1]).astype(np.uint32)
                result={'IADD':np.add,'ISUB':np.subtract,'AND':np.bitwise_and,'OR':np.bitwise_or,'SHR':np.right_shift}[op](left,right).astype(np.uint32)
            elif op=='IADD64': result=np.asarray(args[0],dtype=np.int64)+np.asarray(args[1],dtype=np.int64)
            elif op=='SHL64': result=np.asarray(args[0],dtype=np.int64)<<np.int64(args[1])
            elif op in ('CMP_EQ','CMP_NE','CMP_GT','CMP_LT'):
                result={'CMP_EQ':np.equal,'CMP_NE':np.not_equal,'CMP_GT':np.greater,'CMP_LT':np.less}[op](*args)
            elif op=='FMAX': result=np.maximum(*args).astype(F)
            elif op=='FMIN': result=np.minimum(*args).astype(F)
            elif op=='SELECT': result=np.where(*args)
            elif op in ('MOV','ROUTE','BROADCAST'): result=args[0]
            elif op=='LOAD_WEIGHT': result=self.weights.matrix(node['key'])[0]
            elif op=='LOAD_SCALE': result=self.weights.matrix(node['key'])[1]
            elif op=='LOAD_GAMMA': result=self.weights.gamma(node['layer'],node['kind'])
            elif op=='LOAD_EMBED_CODES': result=self.weights.embedding_codes(int(args[0]))
            elif op=='LOAD_EMBED_SCALE': result=self.weights.embedding_scale(int(args[0]))
            elif op=='LOAD_ROPE_COS': result=self.weights.rope(int(args[0]),node['theta'])[0]
            elif op=='LOAD_ROPE_SIN': result=self.weights.rope(int(args[0]),node['theta'])[1]
            elif op=='FP8_PACK': result=pack8(args[0])
            elif op=='FP8_UNPACK':
                codes=np.asarray(args[0],dtype=np.uint8)
                if np.any((codes&127)==127): raise ValueError('FP8 NaN backing')
                result=poszero(fp8_table()[codes&127]*np.where(codes&128,-1,1))
            elif op=='BEGIN_WRITE': result=self.storage.begin(node['layer'],node['die'],args[0])
            elif op=='WRITE_BYTES': self.storage.write(*args); continue
            elif op=='COMMIT_PUBLISH': result=self.storage.commit(args[0])
            elif op=='ACQUIRE': result=self.storage.acquire(args[0],node['layer'],node['die'],args[1])
            elif op=='READ_BYTES': result=self.storage.read(*args)
            elif op=='BIND_LEASE':
                for version in operation['writes']: self.lease_by_version[version]=args[0]
                continue
            elif op=='CONSUMER_DONE':
                version=operation['reads'][node['input_index']]
                self.storage.done(self.lease_by_version.pop(version),node['stage']); continue
            else: raise ValueError('unknown native primitive '+op)
            assign(node['dst'],result,env)

    def addresses(self,version):
        v=self.bindings[version]
        for home in v['homes']:
            if self.native.get('concrete_provider_binding'):
                if 'home' not in home:
                    yield ('provider_control',home['rank'],home['provider_ref']); continue
                physical=home['home']; rank=home['rank']; sm=home['SM']
                if physical['class']=='RF':
                    for slot in range(physical['slot_first'],physical['slot_first']+physical['vectors']): yield ('RF',rank,sm,slot)
                else:
                    for byte in range(physical['global_byte_base'],physical['byte_end_exclusive'],512): yield ('provider_spill',rank,sm,byte)
                continue
            ranks=[r for lo,hi in home['rank_ranges'] for r in range(lo,hi)]
            for rank in ranks:
                if home['class']=='RF':
                    for slot in home['vector_slots']: yield ('RF',rank,home['SM'],slot)
                elif home['class']=='spill_arena':
                    for offset in range(home['byte_offset'],home['byte_offset']+((home['bytes']+511)//512)*512,512):
                        yield ('spill',rank,offset)
                else: yield ('publication',rank,version)

    def write_version(self,version,value):
        if version in self.live: raise ValueError('SSA overwrite')
        for address in self.addresses(version):
            if address in self.address_words: raise ValueError('live address alias')
            self.address_words[address]=version
        if self.native.get('concrete_provider_binding'):
            v=self.bindings[version]
            if isinstance(value,dict): raw=None
            elif isinstance(value,tuple): raw=np.array([np.asarray(value[0],dtype=F).view(np.uint32),int(value[1])],dtype=np.uint32)
            elif np.asarray(value).dtype.kind in 'iu': raw=np.asarray(value,dtype=np.uint32).reshape(-1)
            else: raw=np.asarray(value,dtype=F).view(np.uint32).reshape(-1)
            for h in v['homes']:
                ref=h['provider_ref']
                if any(event not in self.release_events for event in self.provider_reuse[ref]): raise ValueError('provider reuse before validated release')
                if 'home' not in h:
                    self.provider_payloads[ref]=copy.deepcopy(value); continue
                words=h['word_count']; local=np.arange(words,dtype=np.int64)
                global_indices=((local//256)*32+h['SM'])*256+local%256
                payload=np.zeros(words,dtype=np.uint32)
                valid=global_indices<len(raw)
                payload[valid]=raw[global_indices[valid]]
                self.provider_payloads[ref]=payload
                self.events.append(dict(event=h['publication_event'],provider_ref=ref,words=words,software_visibility=True))
        self.registers[version]=copy.deepcopy(value); self.live.add(version)
        self.events.append(dict(event='version_commit',version=version,lease=self.bindings[version]['lease']))

    def read_version(self,version):
        if not self.native.get('concrete_provider_binding'): return self.registers[version]
        original=self.registers[version]; homes=self.bindings[version]['homes']
        if 'home' not in homes[0]: return copy.deepcopy(self.provider_payloads[homes[0]['provider_ref']])
        count=2 if isinstance(original,tuple) else np.size(original)
        words=np.zeros(count,dtype=np.uint32); covered=np.zeros(count,dtype=bool)
        rank=min(h['rank'] for h in homes)
        for h in homes:
            if h['rank']!=rank: continue
            local=np.arange(h['word_count'],dtype=np.int64)
            indices=((local//256)*32+h['SM'])*256+local%256
            valid=indices<count; refs=h['provider_ref']
            if refs not in self.provider_payloads: raise ValueError('unpublished provider home')
            words[indices[valid]]=self.provider_payloads[refs][valid]; covered[indices[valid]]=True
        if not np.all(covered): raise ValueError('incomplete provider home reconstruction')
        if isinstance(original,tuple): return (words[:1].view(F)[0],int(words[1]))
        dtype=np.asarray(original).dtype
        if dtype.kind in 'iu': return words.astype(dtype).reshape(np.shape(original))
        return words.view(F).reshape(np.shape(original))

    def run(self,token,position,observer=None):
        if self.live: raise ValueError('unretired prior token')
        self.release_events.clear()
        if not 0<=token<self.p['config']['vocab_size'] or not 0<=position<self.p['context_capacity']: raise ValueError('runtime aperture')
        for v in self.native['operands']:
            if v['birth_pc']==-1: self.write_version(v['version'],token if v['name']=='token' else position)
        done=set(); result=None
        for operation in self.native['operations']:
            pc=operation['pc']
            if not set(operation['dependencies'])<=done: raise ValueError('unretired dependency')
            if not set(operation['reads'])<=self.live: raise ValueError('missing source version')
            env={'position':position}
            for i,v in enumerate(operation['reads']): env[f'input{i}']=self.read_version(v)
            self.nodes(operation['recipe'],env,operation)
            out=[env[f'out{i}'] for i in range(len(operation['writes']))]
            for v,value in zip(operation['writes'],out): self.write_version(v,value)
            if operation['opcode']=='ARGMAX_REDUCE': result=int(self.registers[operation['writes'][0]])
            if observer: observer(self.p['instructions'][pc],out)
            self.events.append(dict(event='PC_retire',pc=pc))
            for v in list(self.live):
                if self.bindings[v]['retire_pc']==pc:
                    for address in self.addresses(v):
                        if self.address_words.pop(address)!=v: raise ValueError('stale owner')
                    if self.native.get('concrete_provider_binding'):
                        for home in self.bindings[v]['homes']:
                            self.provider_payloads.pop(home['provider_ref'])
                            if 'release_event' in home:
                                self.release_events.add(home['release_event'])
                                self.events.append(dict(event=home['release_event'],reverse_grants='software acknowledged',hardware_visibility=False))
                    self.live.remove(v); self.registers.pop(v)
                    self.events.append(dict(event='value_lease_release',version=v,pc=pc))
            done.add(pc)
        if self.live or self.storage.pending or self.storage.leases or self.lease_by_version: raise ValueError('unretired state')
        return dict(status='SOFTWARE_NATIVE_PROGRAM_COMPLETED',next_token=result,instructions_retired=len(done),
                    primitive_counts=dict(self.primitive_counts),actual_RTL_executed=False,hardware_or_timing_credit=False)


def canonical(value): return json.dumps(value,sort_keys=True,separators=(',',':')).encode()+b'\n'


def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--out',type=Path,default=ROOT/OUT)
    ap.add_argument('--verify',action='store_true')
    ap.add_argument('--exercise',action='store_true',help='Run all36 layers twice with reduced deterministic storage; output numerical trace hashes, no oracle')
    args=ap.parse_args()
    if args.exercise:
        config=dict(hidden_size=8,head_dim=4,num_attention_heads=2,num_key_value_heads=2,
                    intermediate_size=16,vocab_size=16,num_hidden_layers=36,rms_norm_eps=1e-6,rope_theta=1000000)
        reduced=compile_native(compile_program(config,context=32,groups=16))
        provider,pin=load_provider_binding()
        join_provider_homes({v['version']:v for v in reduced['operands']},provider)
        reduced['concrete_provider_binding']=provider; reduced['provider_binding_pin']=pin
        machine=Machine(reduced)
        records=[]; outputs=[]; token=3
        for position in range(2):
            def observe(op,values):
                hashes=[]
                for value in values:
                    raw=canonical(value) if isinstance(value,dict) else np.asarray(value).tobytes()
                    hashes.append(hashlib.sha256(raw).hexdigest())
                outputs.append(dict(position=position,pc=op['id'],opcode=op['opcode'],output_sha256=hashes))
            result=machine.run(token,position,observer=observe); records.append(result); token=result['next_token']
        print(canonical(dict(schema='opentallas.H3.qwen-native-software-replay.v1',config=config,
            context_capacity=32,group_budget=16,executions=records,outputs=outputs,
            versions_retired=not machine.live,addresses_retired=not machine.address_words,
            KV_published=len(machine.storage.published),KV_leases_retired=not machine.storage.leases,
            oracle_callbacks=0,concrete_provider_binding_pin=pin,
            numerical_scope='reduced fixture payloads scattered into actual r17 maxshape source version homes; no trained checkpoint numerical claim',
            provider_home_publications=sum('provider_ref' in event and 'words' in event for event in machine.events),
            provider_home_releases=len([event for event in machine.events if event['event'].startswith('RELEASE:')]),
            provider_payloads_retired=not machine.provider_payloads,
            full_checkpoint_numerical_execution=False,hardware_or_timing_credit=False)).decode(),end='')
        return
    native=compile_native(); data=canonical(native)
    if args.verify:
        manifest=json.loads((args.out/'manifest.json').read_text())
        for path,digest in manifest['source_sha256'].items():
            if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest: raise ValueError('source pin mismatch '+path)
        if hashlib.sha256((args.out/'Qwen_native.json.gz').read_bytes()).hexdigest()!=manifest['output_sha256']: raise ValueError('native artifact pin mismatch')
        with gzip.open(args.out/'Qwen_native.json.gz','rb') as f:
            if f.read()!=data: raise ValueError('native replay mismatch')
        print(json.dumps(dict(status='PASS_EXACT_NATIVE_COMPILER_REPLAY',**native['coverage']))); return
    args.out.mkdir(parents=True,exist_ok=True)
    with (args.out/'Qwen_native.json.gz').open('xb') as raw:
        with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as f: f.write(data)
    pins=[INPUT,'tools/qwen_hbm_complete_program.py','tools/qwen_hbm_complete_executor.py',
          'tools/h3_versioned_lowering.py','compiler/models/qwen3-8b/config.json',
          'compiler/models/qwen3-8b/checkpoint_source.json','tools/h3_qwen_complete_native.py',
          'tools/qwen_hbm_complete_reference.py','tools/qwen3_deployment_quality.py',
          'tests/test_h3_qwen_complete_native.py']
    scalar_path='results/uarch/h3_exact_scalar_contract_20261002/model.json'
    scalar_bytes=subprocess.check_output(['git','show','66bd7367c:'+scalar_path],cwd=ROOT)
    manifest=dict(schema=native['schema'],coverage=native['coverage'],
        exact_scalar_contract={'commit':'66bd7367c','path':scalar_path,'sha256':hashlib.sha256(scalar_bytes).hexdigest(),
                               'correction_commit':'e03c40e40','witness_test':'test_exact_scalar_committed_contract_witnesses'},
        source_sha256={path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in pins},
        output_sha256=hashlib.sha256((args.out/'Qwen_native.json.gz').read_bytes()).hexdigest(),
        coordination=native['coordination'], provider_binding_pin=native['provider_binding_pin'],
        concrete_provider_coverage=native['concrete_provider_binding']['coverage'],hardware_or_timing_credit=False,
        replay='python tools/h3_qwen_complete_native.py --verify',
        tests='python -m pytest -q tests/test_h3_qwen_complete_native.py')
    with (args.out/'manifest.json').open('xb') as f: f.write(canonical(manifest))
    print(json.dumps(native['coverage']))


if __name__=='__main__': main()
