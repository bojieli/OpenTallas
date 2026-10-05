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



TILE_ROWS=128
TILE_CODE_K=32
TILE_FLOAT_K=16
TILED_OUT=ROOT/OUT/'tiled_r1'



def code_sector_count(rows,K):
    if K%32==0: return rows*(K//32)
    def tile(n):
        total=0
        for column in range(0,K,32):
            sectors=set(); width=min(32,K-column)
            for row in range(n):
                first=row*K+column
                sectors.update(range(first//32,(first+width-1)//32+1))
            total+=len(sectors)
        return total
    return (rows//128)*tile(128)+(tile(rows%128) if rows%128 else 0)


def interleaved_BF16_windows(K,S):
    previous=None; count=0
    for s in range(min(K,S)):
        for k in range(s,K,S):
            page=k//128
            if previous!=page: count+=1; previous=page
    return count

def tiled_counts(op,p,position):
    """Analytical counts before tiled execution; no tensor materialization."""
    c=p['config']; a=op['attributes']; name=op['opcode']; T=position+1
    hd=c['head_dim']; nh=c['num_attention_heads']//2; kv=c['num_key_value_heads']//2
    shape=p['register_shapes'][op['outputs'][0]]
    size=math.prod(T if n=='position+1' else n for n in shape) if shape else 1
    count=Counter(); extra={}
    def rms(n,heads=1,weighted=False):
        leaves=1<<(((n+7)//8)-1).bit_length()
        count['FMUL_words']+=heads*(n+11+(2*n if weighted else 0))
        count['FADD_words']+=heads*(n+leaves-1+4)
        count['FMUL_vector_commands']+=heads*((n+7)//8+11+(2*((n+127)//128) if weighted else 0))
        count['FADD_vector_commands']+=heads*(n+leaves-1+4)
    if name in ('MATRIX','SCORES','PV'):
        if name=='MATRIX':
            d=p['weight_descriptors'][a['weight']]; rows,K,S,heads=d['rows'],d['K'],d['split'],1
        else: rows,K,S,heads=(T,hd,a['split'],nh) if name=='SCORES' else (hd,T,a['split'],nh)
        if S<1 or S&(S-1) or (name=='MATRIX' and K%S): raise ValueError('unsupported source split geometry')
        rowtiles=(rows+127)//128
        count['FMUL_words']=heads*rows*K; count['FADD_words']=heads*rows*(K+S-1)
        count['FMUL_vector_commands']=heads*rowtiles*K
        count['FADD_vector_commands']=heads*rowtiles*(K+S-1)
        count['tree_merges']=heads*rowtiles*(S-1)
        if name=='MATRIX':
            count['ITOF_vector_commands']=rowtiles*K
            count['BF16_pack_windows']=rowtiles*((K+127)//128)
            count['code_tile_reads']=rowtiles*((K+31)//32)
            count['code_payload_bytes']=rows*K
            # Rowtile boundary is128 rows, hence32B aligned for integer K.
            count['code_sectors32']=code_sector_count(rows,K)
        elif name=='SCORES':
            count['BF16_pack_windows']=heads*rowtiles*interleaved_BF16_windows(K,S)
            count['FMUL_words']+=heads*rows; count['FMUL_vector_commands']+=heads*rowtiles
        extra=dict(rows=rows,K=K,split=S,heads=heads,rowtiles=rowtiles,
                   split_order='contiguous' if name=='MATRIX' else 'interleaved',
                   leaf_lengths='K/split' if name=='MATRIX' else 'max(0,ceil((K-s)/split))',
                   root_tree='streaming adjacent left/right carries, all split zero leaves retained',
                   accumulator_words_max=128,carry_stack_vectors=(S-1).bit_length()+1,
                   code_tile_shape_max=[128,32],float_tile_shape_max=[128,16])
    elif name=='RSTD': rms(p['register_shapes'][op['inputs'][0]][-1])
    elif name=='HEAD_NORM': rms(hd,p['register_shapes'][op['inputs'][0]][0],True)
    elif name=='FINAL_NORM': rms(c['hidden_size'],1,True)
    elif name in ('ROW_SCALE','SCALAR_MUL','NORMALIZE'):
        count['FMUL_words']=size; count['FMUL_vector_commands']=(size+127)//128
        if name=='NORMALIZE':
            count['FMUL_vector_commands']=nh*((hd+127)//128)
            count['FMUL_words']+=nh*6; count['FADD_words']=nh*3
            count['FMUL_vector_commands']+=nh*6; count['FADD_vector_commands']=nh*3
    elif name=='RESIDUAL': count.update(FADD_words=size,FADD_vector_commands=(size+127)//128)
    elif name=='ALL_REDUCE':
        count.update(FADD_words=size,FMUL_words=size,FADD_vector_commands=(size+127)//128,FMUL_vector_commands=(size+127)//128,
                     collective_payload_bytes=size*8)
    elif name=='SILU_GATE': count.update(FMUL_words=17*size,FADD_words=14*size,FMUL_vector_commands=17*((size+127)//128),FADD_vector_commands=14*((size+127)//128))
    elif name=='EXP_SUM':
        leaves=1<<(((T+7)//8)-1).bit_length(); batches=(T+127)//128
        count.update(FMUL_words=nh*T*9,FADD_words=nh*(12*T+leaves-1),
                     FMUL_vector_commands=nh*batches*9,FADD_vector_commands=nh*(batches*11+T+leaves-1),
                     max_compare_words=nh*(T-1),BF16_pack_windows=nh*batches)
    elif name=='ROPE':
        heads=p['register_shapes'][op['outputs'][0]][0]; batches=(hd//2+127)//128
        count.update(FMUL_words=2*size,FADD_words=size,FMUL_vector_commands=4*heads*batches,FADD_vector_commands=2*heads*batches)
    elif name=='EMBED': count.update(FMUL_words=size,FMUL_vector_commands=(size+127)//128,ITOF_vector_commands=(size+127)//128)
    elif name=='KV_WRITE': count.update(FP8_PACK_words=2*kv*hd,KV_store_bytes=2*kv*hd)
    elif name=='KV_READ': count.update(FP8_UNPACK_words=2*kv*T*hd,KV_read_payload_bytes=2*kv*T*hd)
    elif name=='ARGMAX': count.update(argmax_comparisons=3*(p['register_shapes'][op['inputs'][0]][0]-1))
    elif name=='ARGMAX_REDUCE': count.update(argmax_comparisons=3,collective_payload_bytes=16)
    return dict(position=position,logical_counts=dict(count),matrix=extra,
                ports={'RF_2R1W_read_bits':8192,'RF_mirrored_write_payload_bits':4096,'RF_mirrors':2,
                       'shared_beat_bytes':128,'HBM_sector_bytes':32},
                transfer_count_policy='runtime actual provider page/sector counters; fullshape conservative serialized service budgets, never measured timing',
                clock_and_latency='C_RF_READ+C_RF_ACK+C_SHARED_BEAT+C_HBM_SECTOR+C_NoC+C_CDC+C_REVERSE_GRANT plus native primitive costs, all unknown and nonzero provisional inputs required')


def tile_feasibility_model(p=None):
    p=compile_program() if p is None else p
    return dict(schema='opentallas.H3.qwen-tile-feasibility.v1',before_implementation=True,
        target='Qwen_HBM',RF_workspace_vectors=32,RF_vector_bytes=512,RF_logical_bytes=16384,RF_mirrors=2,
        RF_physical_bytes=32768,shared_physical_bytes=65536,
        shared_regions=[{'name':'double_tile','range':[0,16384]}, {'name':'landing','range':[16384,16896]}, {'name':'capture','range':[16896,17408]}],
        shared_reserved_bytes=17408,shared_fits=True,temporary_HBM_bytes=0,
        matrix_code_double_buffer_bytes=2*128*32,attention_FP32_double_buffer_bytes=2*128*16*4,
        RF_layout={'carry':[0,13],'accumulator_product_weight':[13,16],'scalar_or_x':[16,17],
                   'primitive_scratch':[17,30],'source_page_cache':[30,32]},
        RF_allocation_policy='phase reuse, never additive sum of historical symbols; at most32 live vectors including tree and page cache',
        source_storage='r17 original32SM version_homes and32MiB/rank activation_scratch at base4714740864;37504B/rank KV state, no successor native arena',
        matrix='128 output rows, aligned32-code columns; INT8 conversion one128-lane column at a time; BF16 source page128 words; one split accumulator and log2(split)+1 tree vectors',
        attention='128 output positions/dimensions,16 interleaved K/context elements; KV_READ decoded source words published in128-word windows to actual r17 homes',
        reduction='seq8 leaves, zero-padded adjacent pair tree implemented with left/right carry stack; preserve every round and empty split leaf',
        single_user_latency='ordered symbolic transaction sum; tile loads, captures, shared, RF, NoC, CDC and reverse retirement all charged; no throughput/clock gain credited',
        hardware_or_timing_credit=False,
        per_PC_counts=[dict(pc=o['id'],opcode=o['opcode'],**tiled_counts(o,p,p['context_capacity']-1)) for o in p['instructions']])


COMMON_NATIVE={'LOAD','CONST','RESHAPE','SLICE','TRANSPOSE','CONCAT','BROADCAST','TAKE','SCATTER',
 'FADD','FMUL','DIV','SQRT','FMAX','FMIN','FCMP_GT','FCMP_LT','FCMP_EQ','FCMP_NE','SELECT',
 'BITCAST_U','BITCAST_F','SHR','SHL','AND','OR','XOR','IADD','ISUB','IMUL','IMOD','I2F','F2I',
 'LDEXP','PACKET_COMMIT','ASSERT','IOTA','COPY','FP8_PACK','FP8_UNPACK'}
QWEN_ALIASES={'BITS':'BITCAST_U','FLOAT_BITS':'BITCAST_F','CMP_GT':'FCMP_GT','CMP_LT':'FCMP_LT',
 'CMP_EQ':'FCMP_EQ','CMP_NE':'FCMP_NE','ITOF':'I2F','FTOI':'F2I','IADD64':'IADD','SHL64':'SHL'}


class NativePrimitiveVM:
    """Generic typed tile VM; DS code ABI and Qwen leaf recipes are adapters.

    Arrays are restricted to128 words at the primitive boundary. Bigger tensors
    require explicit outer tile programs. DIV is an explicitly bound scalar
    instruction provider, never a high-level operator callback.
    """
    def __init__(self,div=None):
        self.div=div; self.fault=False; self.error_events=[]; self.current_pc=None; self.counts=Counter(); self.word_counts=Counter(); self.peak_vectors=0
    def primitive(self,op,args,attrs=None,shape=None):
        at={} if attrs is None else attrs
        if op not in COMMON_NATIVE: raise ValueError('unsupported native primitive '+op)
        if any(np.size(x)>128 for x in args): raise ValueError('native operand needs outer tile loop')
        a=[np.asarray(x) for x in args]
        dtype={'F32':F,'U32':np.uint32,'I64':np.int64}
        with np.errstate(all='ignore'):
            if op=='IOTA':
                if shape is None or len(shape)!=1 or not 0<=shape[0]<=128: raise ValueError('native IOTA tile shape')
                v=np.arange(shape[0],dtype=np.int64)
            elif op=='CONST':
                v=np.asarray(at['bits'],np.uint32).view(F) if at['dtype']=='F32' else np.asarray(at['value'],dtype[at['dtype']])
            elif op in ('FADD','FMUL','SQRT','DIV'):
                x=[z.astype(F,copy=False) for z in a]
                if op=='DIV':
                    if self.div is None: raise ValueError('exact scalar DIV provider required')
                    v,faults=self.div(*x); self.fault|=bool(np.any(faults))
                    if np.any(faults): self.error_events.append({'pc':self.current_pc,'op':'DIV','errors':np.asarray(faults,np.uint32).tolist()})
                else: v=x[0]+x[1] if op=='FADD' else x[0]*x[1] if op=='FMUL' else np.sqrt(x[0])
                v=np.asarray(v,F); self.fault|=bool(np.any(~np.isfinite(v)))
                if at.get('canonical_zero',True): v=poszero(v)
            elif op=='FMAX': v=np.maximum(*a).astype(F)
            elif op=='FMIN': v=np.minimum(*a).astype(F)
            elif op.startswith('FCMP_'):
                v={'FCMP_GT':np.greater,'FCMP_LT':np.less,'FCMP_EQ':np.equal,'FCMP_NE':np.not_equal}[op](*a).astype(np.uint32)
            elif op=='SELECT': v=np.where(a[0]!=0,a[1],a[2])
            elif op=='BITCAST_U': v=a[0].astype(F,copy=False).view(np.uint32)
            elif op=='BITCAST_F': v=a[0].astype(np.uint32,copy=False).view(F)
            elif op in ('SHR','SHL','AND','OR','XOR','IADD','ISUB','IMUL','IMOD'):
                wide=at.get('dtype')=='I64' or (at.get('dtype')!='U32' and any(x.dtype==np.int64 for x in a))
                integer=np.int64 if wide else np.uint32
                x,y=[z.astype(integer) for z in a]
                if op in ('SHR','SHL') and np.any((y<0)|(y>=(64 if wide else 32))): raise ValueError('native shift range')
                if op=='IMOD' and np.any(y==0): raise ValueError('native modulo zero')
                v={'SHR':np.right_shift,'SHL':np.left_shift,'AND':np.bitwise_and,'OR':np.bitwise_or,
                   'XOR':np.bitwise_xor,'IADD':np.add,'ISUB':np.subtract,'IMUL':np.multiply,'IMOD':np.remainder}[op](x,y).astype(integer)
            elif op=='I2F': v=a[0].astype(F)
            elif op=='F2I':
                if np.any(~np.isfinite(a[0])) or np.any(np.abs(a[0].astype(np.float64))>=2**63): raise ValueError('native F2I range')
                v=a[0].astype(np.int64)
            elif op=='LDEXP':
                exponent=a[1].astype(np.uint32).view(np.int32) if a[1].dtype==np.uint32 else a[1].astype(np.int32)
                v=np.ldexp(a[0].astype(F),exponent).astype(F)
                self.fault|=bool(np.any(~np.isfinite(v)))
            elif op=='COPY': v=a[0].copy()
            elif op=='RESHAPE': v=a[0].reshape(shape)
            elif op=='SLICE':
                sl=[slice(None)]*a[0].ndim; sl[at['axis']]=slice(at['start'],at['stop'],at.get('step',1)); v=a[0][tuple(sl)]
            elif op=='TRANSPOSE': v=a[0].transpose(at['axes'])
            elif op=='CONCAT': v=np.concatenate(a,axis=at.get('axis',0))
            elif op=='BROADCAST': v=np.broadcast_to(a[0],shape)
            elif op=='TAKE':
                if np.any(a[1]<0) or np.any(a[1]>=a[0].shape[at['axis']]): raise ValueError('native address range')
                v=np.take(a[0],a[1].astype(np.int64),axis=at['axis'])
            elif op=='SCATTER':
                v=a[0].copy(); index=int(a[1])
                if not 0<=index<v.shape[at['axis']]: raise ValueError('native scatter range')
                sl=[slice(None)]*v.ndim; sl[at['axis']]=index; v[tuple(sl)]=a[2]
            elif op=='ASSERT':
                if not np.all(a[0]): raise ValueError('native assertion '+at.get('reason',''))
                v=a[0].copy()
            elif op=='PACKET_COMMIT':
                if self.fault: raise ValueError('fault prevents successful publication')
                if 'lease' in at and at.get('lease_state')!='visible': raise ValueError('packet lease before visibility')
                v=a[0].copy()
            elif op=='FP8_PACK': v=pack8(a[0])
            elif op=='FP8_UNPACK':
                codes=a[0].astype(np.uint8)
                if np.any((codes&127)==127): raise ValueError('FP8 NaN backing')
                v=poszero(fp8_table()[codes&127]*np.where(codes&128,-1,1))
            else: raise ValueError('LOAD needs bound provider record')
        if np.size(v)>128: raise ValueError('native result needs outer tile loop')
        if shape is not None and list(np.shape(v))!=list(shape): raise ValueError('native result shape')
        self.counts[op]+=1; self.word_counts[op]+=np.size(v)
        return np.asarray(v).copy()
    def run_ds(self,program,providers):
        r={}; last={}
        for pc,node in enumerate(program['code']):
            for ref in node['src']: last[ref]=pc
        outputs=set(program['outputs'].values())
        for pc,node in enumerate(program['code']):
            self.current_pc=pc
            if node['op'] not in COMMON_NATIVE: raise ValueError('unsupported native primitive '+node['op'])
            if node['dst'] in r: raise ValueError('native SSA overwrite')
            if any(ref not in r for ref in node['src']): raise ValueError('unpublished native register')
            at=node['attrs']
            if node['op']=='LOAD':
                record=providers.get(at['name'])
                if not isinstance(record,dict) or not record.get('lease') or record.get('state')!='visible': raise ValueError('unbound native provider lease')
                v=np.asarray(record['value'],dtype={'F32':F,'U32':np.uint32,'I64':np.int64}[at['dtype']])
                if v.size>128 or list(v.shape)!=node['shape']: raise ValueError('provider tile shape')
                v=v.copy(); self.counts['LOAD']+=1; self.word_counts['LOAD']+=v.size
            else: v=self.primitive(node['op'],[r[x] for x in node['src']],at,node['shape'])
            r[node['dst']]=v
            self.peak_vectors=max(self.peak_vectors,sum((max(4,x.nbytes)+511)//512 for x in r.values()))
            if self.peak_vectors>32: raise ValueError('native RF32 capacity')
            for ref in list(r):
                if last.get(ref,-1)<=pc and ref not in outputs: del r[ref]
        return {name:r[ref].copy() for name,ref in program['outputs'].items()}
    def run_qwen(self,nodes,env,reserved=2):
        env=dict(env); last={}; output=nodes[-1]['dst']
        for pc,node in enumerate(nodes):
            for text in node.get('src',[]):
                for item in ast.walk(ast.parse(text,mode='eval')):
                    if isinstance(item,ast.Name): last[item.id]=pc
        for pc,node in enumerate(nodes):
            op=node['op']; args=[expression(text,env) for text in node['src']]
            if op=='MOV': v=self.primitive('COPY',args)
            elif op=='NEG': v=self.primitive('BITCAST_F',[self.primitive('XOR',[self.primitive('BITCAST_U',[np.asarray(args[0],F)]),np.uint32(0x80000000)],{'dtype':'U32'})])
            else:
                attrs={'dtype':'I64'} if op in ('IADD64','SHL64') else {'dtype':'U32'} if op in ('IADD','ISUB','SHR','AND','OR') else {}
                v=self.primitive(QWEN_ALIASES.get(op,op),args,attrs)
            assign(node['dst'],v,env)
            vectors=reserved+sum((max(4,np.asarray(value).nbytes)+511)//512 for value in env.values())
            self.peak_vectors=max(self.peak_vectors,vectors)
            if vectors>32: raise ValueError('tile RF32 capacity')
            for ref in list(env):
                if ref!=output and last.get(ref,-1)<=pc: del env[ref]
        return env[output]



@lru_cache(maxsize=1)
def _restoring_DIV31():
    # Import only the integer primitive transcription, never the rational oracle.
    source=subprocess.check_output(['git','show','e03c40e40:tools/h3_exact_scalar_contract.py'],cwd=ROOT).decode()
    node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='restoring_div31')
    namespace={}; exec(compile(ast.Module(body=[node],type_ignores=[]),'<pinned integer DIV31>','exec'),namespace)
    return namespace['restoring_div31']


def restoring_DIV_provider(a,b):
    a,b=np.broadcast_arrays(np.asarray(a,F),np.asarray(b,F))
    if a.size>128: raise ValueError('DIV provider outer tile required')
    result=np.empty(a.shape,np.uint32); faults=np.empty(a.shape,np.uint32)
    primitive=_restoring_DIV31()
    for index in np.ndindex(a.shape):
        r=primitive(int(a[index].view(np.uint32)),int(b[index].view(np.uint32)))
        result[index]=r['y']
        faults[index]=1 if r.get('stage')=='decode_argument' else 2 if r['fault'] else 0
    return result.view(F),faults


TILE_COSTS=('C_NATIVE','C_RF_READ','C_RF_ACK','C_SHARED_BEAT','C_HBM_SECTOR','C_NoC','C_CDC','C_REVERSE_GRANT')


def tile_service_budget(op,p):
    """Conservative serialized service reservation, not measured transaction counts.

    Bounds deliberately include inactive lanes and one RF/HBM page per source
    word. Serial reservation makes finite credits and port capacities feasible;
    an owner can substitute the exact runtime transaction trace to tighten it.
    """
    counts=tiled_counts(op,p,p['context_capacity']-1)['logical_counts']
    commands=sum(v for k,v in counts.items() if k.endswith('_vector_commands'))
    # Every leaf recipe has <=128 instructions. A movement-only op still pays.
    shapes=p['register_shapes']
    source_words=sum(math.prod(p['context_capacity'] if n=='position+1' else n for n in shapes[v]) for v in op['inputs'])
    result_words=sum(math.prod(p['context_capacity'] if n=='position+1' else n for n in shapes[v]) for v in op['outputs'])
    native=sum(physical_tile_export(op,p,p['context_capacity']-1)['native_primitive_commands'].values())+16*(source_words+result_words)+128
    # Three input pages and two output mirrors per native command. One source
    # page per word bounds scatter and reload even for interleaved KV trees.
    words=source_words+result_words+256*native
    hbm=16*words+counts.get('code_sectors32',0)+counts.get('KV_store_bytes',0)+counts.get('KV_read_payload_bytes',0)
    return dict(C_NATIVE=native,C_RF_READ=2*words,C_RF_ACK=2*words,
                C_SHARED_BEAT=8*words,C_HBM_SECTOR=hbm,C_NoC=words,
                C_CDC=2*words,C_REVERSE_GRANT=words)


def materialize_tile_calendar(native,costs):
    """One finite serialized software calendar, positive provisional costs only."""
    if set(costs)!=set(TILE_COSTS) or any(not math.isfinite(v) or v<=0 for v in costs.values()):
        raise ValueError('all provisional service costs must be finite and positive')
    end=0; operations=[]
    for op in native['operations']:
        budget=op['calendar_export']['conservative_serial_service_budget']
        duration=sum(budget[k]*costs[k] for k in TILE_COSTS)
        operations.append(dict(pc=op['pc'],start=end,end=end+duration,service_budget=budget,
            lease='one native tile command, release only after capture ACK/reverse grant',
            dependencies=op['dependencies'],providers=op['provider_binding']))
        end+=duration
    return dict(schema='opentallas.H3.finite-tile-calendar.v1',operations=operations,duration=end,
        costs=costs,cost_scope='explicit provisional parameters; conservative upper service reservation, no hardware qualification',
        resources={'RF_vectors':32,'RF_ports':'2R1W mirrored ACK','shared_bytes':17408,
                   'shared_port_bytes_per_service':128,'HBM_sector_bytes':32,'outstanding_tiles':1,
                   'source_sector_credits_used':1,'source_sector_credits_available':4},
        temporary_HBM_bytes=0,hardware_or_timing_credit=False)

def common_native_abi():
    return dict(schema='opentallas.HBM.native-primitive-ABI.v1',supported=sorted(COMMON_NATIVE),
        Qwen_aliases=QWEN_ALIASES,DS_adapter='run_ds(code/dst/src/shape/attrs/providers/outputs)',
        Qwen_adapter='run_qwen(op/dst/src expressions), bounded scalar/vector leaf only',
        max_tile_words=128,max_RF_vectors=32,bit_types=['F32','U32','I64','E4M3_byte'],
        integer='U32 modulo32, I64 modulo64; signed I64 SHR, logical U32 SHR; shifts range checked; modulo zero rejected',
        rounding='FADD/FMUL/SQRT/DIV binary32 RNE with +0 canonicalization unless explicit canonical_zero=False; BITCAST, integer and movement exact; BF16 is explicit integer RNE recipe',
        exceptions='nonfinite FP arithmetic records fault and retains source bits; F2I nonfinite/outsideI64 rejected; DIV requires exact primitive provider and fault sideband; NaN compares false exceptNE; E4M3 NaN backing rejected',
        provider='LOAD requires visible identity-bearing bounded tile lease; shape/versions/SSA/capacity checked; PACKET_COMMIT with lease requires visible state',
        DIV_provider={'callable':'restoring_DIV_provider','commit':'e03c40e40','function':'restoring_div31','algorithm':'decode/normalize,27 integer restoring steps, guard/sticky RNE, capture error1 argument/error2 overflow; no rational oracle'},
        unsupported='reject before execution; no macro opcode or high-level numerical callback fallback')


def tile_microcode():
    root=norm('unused','out',4096,1e-6); root=root[next(i for i,n in enumerate(root) if n.get('dst')=='vb'):]
    return dict(add=[ins('FADD','out','a','b')],mul=[ins('FMUL','out','a','b')],
        convert=[ins('ITOF','out','x')],bf16=bfpack('x','out'),exp=exponential('x','out'),
        reciprocal=reciprocal('x','out'),rsqrt=root,
        fp8pack=[ins('FP8_PACK','out','x')],fp8unpack=[ins('FP8_UNPACK','out','x')],
        maximum=[ins('FMAX','out','a','b')],neg=[ins('NEG','out','x')],
        argmax=[ins('CMP_GT','win','candidate','best'),ins('CMP_NE','nan','candidate','candidate'),
                ins('CMP_EQ','best_valid','best','best'),ins('AND','first_nan','nan','best_valid'),ins('OR','out','win','first_nan')],
        winner=[ins('CMP_GT','win','b','a'),ins('CMP_EQ','equal','b','a'),ins('CMP_LT','lower','bi','ai'),
                ins('AND','tie','equal','lower'),ins('OR','out','win','tie')])



def tiled_kernel_calls(op,p,position):
    counts=tiled_counts(op,p,position)['logical_counts']; name=op['opcode']; c=p['config']; T=position+1
    nh=c['num_attention_heads']//2; hd=c['head_dim']; kv=c['num_key_value_heads']//2
    calls=Counter()
    if name=='RSTD' or name=='FINAL_NORM': calls['rsqrt']=1
    elif name=='HEAD_NORM': calls['rsqrt']=p['register_shapes'][op['outputs'][0]][0]
    if name=='EXP_SUM': calls.update(exp=nh*((T+127)//128),maximum=nh*(T-1),neg=nh)
    elif name=='SILU_GATE': calls.update(exp=(c['intermediate_size']//2+127)//128,neg=(c['intermediate_size']//2+127)//128)
    if name=='SILU_GATE': calls['reciprocal']=(c['intermediate_size']//2+127)//128
    elif name=='NORMALIZE': calls['reciprocal']=nh
    if name=='ROPE': calls['neg']=p['register_shapes'][op['outputs'][0]][0]*((hd//2+127)//128)
    if name=='ARGMAX': calls['argmax']=p['register_shapes'][op['inputs'][0]][0]-1
    if name=='ARGMAX_REDUCE': calls['winner']=1
    if name=='KV_WRITE': calls['fp8pack']=2*kv*((hd+127)//128)
    if name=='KV_READ': calls['fp8unpack']=2*((kv*T*hd+127)//128)
    calls['bf16']=counts.get('BF16_pack_windows',0)
    calls['convert']=counts.get('ITOF_vector_commands',0)
    calls['add']=counts.get('FADD_vector_commands',0)-3*calls['rsqrt']-10*calls['exp']-3*calls['reciprocal']
    calls['mul']=counts.get('FMUL_vector_commands',0)-10*calls['rsqrt']-9*calls['exp']-6*calls['reciprocal']
    if any(v<0 for v in calls.values()): raise ValueError('kernel invocation accounting')
    return {k:v for k,v in calls.items() if v}


@lru_cache(maxsize=1)
def tile_kernel_ABI():
    inputs={'add':['a','b'],'mul':['a','b'],'convert':['x'],'bf16':['x'],'exp':['x'],
            'reciprocal':['x'],'rsqrt':['variance'],'fp8pack':['x'],'fp8unpack':['x'],
            'maximum':['a','b'],'neg':['x'],'argmax':['candidate','best'],'winner':['a','b','ai','bi']}
    profiles={}
    for name,nodes in tile_microcode().items():
        scalar=name in ('rsqrt','maximum','argmax','winner')
        env={x:Shape(()) if scalar else Shape((128,)) for x in inputs[name]}; steps=[]; counts=Counter()
        for node in nodes:
            args=[shape_eval(x,env) for x in node['src']]
            result=inferred_result(node,args,{})
            shape=shapeof(result); op=node['op']
            primitive=['BITCAST_U','XOR','BITCAST_F'] if op=='NEG' else ['COPY'] if op=='MOV' else [QWEN_ALIASES.get(op,op)]
            counts.update(primitive)
            bits=64 if op in ('FTOI','IADD64','SHL64') else 8 if op=='FP8_PACK' else 32
            steps.append(dict(op=op,native_steps=primitive,reads=[dict(expression=text,shape_max=list(shapeof(arg))) for text,arg in zip(node['src'],args)],
                write={'symbol':node['dst'],'shape_max':list(shape),'bits_per_element':bits,'RF_vectors_max':max(1,(math.prod(shape)*bits+4095)//4096)},
                round_point='binary32 RNE + canonical zero' if op in ('FMUL','FADD') else 'bit-exact movement/integer or declared converter'))
            env[node['dst']]=result
        profiles[name]=dict(steps=steps,native_counts_per_invocation=dict(counts),tile_shape_scope='max128; scalar broadcasts do not allocate full tensor')
    return profiles


def physical_tile_export(op,p,position):
    calls=tiled_kernel_calls(op,p,position); profiles=tile_kernel_ABI(); counts=Counter()
    for name,times in calls.items():
        for primitive,n in profiles[name]['native_counts_per_invocation'].items(): counts[primitive]+=times*n
    return dict(kernel_invocations=calls,native_primitive_commands=dict(counts),
        kernel_ABI_reference='tile_kernel_ABI',working_shapes_max='all native FP/int/movement results <=128 elements; I64 charges two32-bit RF words',
        provider_reads='separate explicit source homes and immutable extent byte ranges, under publication/ACK/reverse leases',
        source_order='procedural tile controller TiledMachine.execute/dot/rms frozen by source SHA; serialized leaf kernels execute these native steps')

def fixture_tile_provider(p,versioned):
    """Use the identical distributed allocator for reduced software fixtures."""
    from h3_distributed_norm_endpoint import distribute
    distributed=distribute('Qwen',versioned); homes=[]; controls=[]; allocations=[]
    values={v['id']:v for v in versioned['operands']}; byversion=defaultdict(list)
    for rank in range(2):
        ext=copy.deepcopy(p['memory_allocation'][rank]['extents']); scratch=next(e for e in ext if e['name']=='activation_scratch')
        scratch['bytes']=32*1048576; end=scratch['base']+scratch['bytes']
        ext.append(dict(name='KV_provider_state',base=end,bytes=37504,role='software_provider_state'))
        for e in ext: e.update(rank=rank,provider_ref=f"Qwen.rank{rank}.extent.{e['name']}")
        allocations.append(dict(rank=rank,extents=ext,global_allocated_end_bytes=end+37504))
    for item in distributed['homes']:
        v=values[item['version']]
        for rank in item['rank_group']:
            home=copy.deepcopy(item['home'])
            if home['class']=='spill':
                scratch=next(e for e in allocations[rank]['extents'] if e['name']=='activation_scratch')
                home.update(global_byte_base=scratch['base']+item['SM']*1048576+home['byte_offset'])
            record=dict(version=item['version'],provider_ref=f"Qwen.{item['version']}.rank{rank}.SM{item['SM']}",
                        rank=rank,SM=item['SM'],home=home,word_count=item['word_count'],birth_pc=v['birth_pc'],
                        retire_pc=v['retire_pc'],consumers=v['consumers'],release_event=f"RELEASE:{item['version']}:r{rank}:s{item['SM']}")
            homes.append(record); byversion[v['id']].append(record['provider_ref'])
    for v in values.values():
        if v['bits_per_element']==0:
            for rank,n in enumerate(v['elements_per_rank']):
                if n:
                    record=dict(version=v['id'],rank=rank,provider_ref=f"Qwen.control.{v['id']}.rank{rank}",
                                birth_pc=v['birth_pc'],consumers=v['consumers'],state_extent=f'Qwen.rank{rank}.extent.KV_provider_state')
                    controls.append(record); byversion[v['id']].append(record['provider_ref'])
    operations=[]
    for o,source in zip(versioned['operations'],p['instructions']):
        attrs=source['attributes']; name=source['opcode']; external=[]
        def add(rank,extent,**meta):
            if not any(e['name']==extent for e in allocations[rank]['extents']): raise ValueError('fixture external extent')
            external.append(dict(provider_ref=f'Qwen.rank{rank}.extent.{extent}',**meta))
        if name in ('MATRIX','ROW_SCALE','ALL_REDUCE'):
            d=p['weight_descriptors'][attrs.get('weight',attrs.get('post_scale_weight'))]
            prefix='head' if d['layer'] is None else f'L{d["layer"]}.{d["name"]}'
            add(d['die'],prefix+('.codes' if name=='MATRIX' else '.scales'),weight_descriptor=d)
        if name in ('EMBED','FINAL_NORM','ROPE','HEAD_NORM'):
            extent_name='embedding' if name=='EMBED' else 'final_norm' if name=='FINAL_NORM' else 'rope_table' if name=='ROPE' else f'L{attrs["layer"]}.qk_norm'
            ranks=o['participants']
            for rank in ranks: add(rank,extent_name,selector=attrs)
        if name in ('KV_WRITE','KV_READ','KV_FENCE'):
            for kind in ('K','V'): add(attrs['die'],f'L{attrs["layer"]}.{kind}')
            add(attrs['die'],'KV_provider_state')
        operations.append(dict(pc=o['pc'],opcode=o['opcode'],inputs={v:byversion[v] for v in o['reads']},
                     outputs={v:byversion[v] for v in o['writes']},external_providers=external))
    return dict(version_homes=homes,control_homes=controls,allocation=allocations,reuse_dependencies=[],operations=operations,
                resource_contract={'RF_workspace_slots':[0,32],'source_stage_sector_credits_per_rank':4,'logical_KV_reader_leases_per_rank':36},
                scope='reduced fixture distributed allocator; no default fullshape pin replacement')


def compile_tiled(program=None):
    p=compile_program() if program is None else copy.deepcopy(program)
    if program is None:
        with gzip.open(ROOT/INPUT,'rt') as stream: versioned=json.load(stream)
        provider,pin=load_provider_binding()
    else: versioned=make_versioned(p); provider=fixture_tile_provider(p,versioned); pin=None
    values={v['id']:binding(v) for v in versioned['operands']}
    for v in values.values(): v['shape']=p['register_shapes'][v['name']]
    join_provider_homes(values,provider)
    for allocation in provider['allocation']:
        rank=allocation['rank']; p['memory_allocation'][rank]['extents']=allocation['extents']
        p['memory_allocation'][rank]['allocated_bytes']=allocation['global_allocated_end_bytes']
    operations=[]
    for source,old,bound in zip(p['instructions'],versioned['operations'],provider['operations']):
        count=tiled_counts(source,p,p['context_capacity']-1)
        operations.append(dict(pc=source['id'],opcode=source['opcode'],reads=old['reads'],writes=old['writes'],
            dependencies=old['dependencies'],attributes=source['attributes'],provider_binding=bound,
            kernels=list(tile_microcode()),
            loop_program={'row_step':128,'code_K_window':32,'float_K_step':16,'KV_and_vector_window':128,
                          'norm_leaf':8,'norm_tree':'streaming adjacent carry stack, pad with source +0 leaves',
                          'matrix_split':'contiguous' if source['opcode']=='MATRIX' else 'interleaved',
                          'carry_rule':'combine left earlier leaf with right later leaf; all split leaves retained; one vector per level',
                          'source_address':'(version,rank,SM) via exact r17 homes; global_word block256 distribution',
                          'retirement':'tile consumer+capture ACK+reverse grant before buffer reuse; PC consumers before home release'},
            calendar_export={'schema':'opentallas.H3.native-bounded-tiles.v1','counts_full_context':count,
                'source_provider_operation':bound,'physical_primitives':physical_tile_export(source,p,p['context_capacity']-1),'RF_workspace_vectors':32,'shared_reserved_bytes':17408,
                'temporary_HBM_bytes':0,'provider_resource_contract':provider['resource_contract'],
                'duration':'ordered native+RF+shared+provider_sector+NoC+CDC+ACK+reverse grant costs, no zero-cost unknowns',
                'all_costs_provisional':True,
                'conservative_serial_service_budget':tile_service_budget(source,p),
                'transaction_scope':'upper service reservation; exact page/sector counts exported by executor',
                'placement':'serialized worker rank0 SM0, remote home transfers charged through NoC; no assumed extra local RF ports',
                'finite_calendar_entrypoint':'materialize_tile_calendar(native,positive_costs)'}))
    return dict(schema='opentallas.H3.qwen-bounded-tiled-native.v1',opt_in=True,default_enabled=False,
                source_program=p,operands=list(values.values()),operations=operations,provider_binding=provider,
                provider_binding_pin=pin,microcode=tile_microcode(),tile_kernel_ABI=tile_kernel_ABI(),primitive_ABI=common_native_abi(),
                feasibility=tile_feasibility_model(p),coverage={'PCs':len(operations),'families':dict(Counter(o['opcode'] for o in operations)),
                'all_PC_executable':True,'unsupported':[]},hardware_or_timing_credit=False)



class BoundKVStorage(Storage):
    """Packed r17 bitmap/reader records in the actually charged HBM extent.

    Host maps are simulator indexes and event logs. Publication, current producer
    identity, reader occupancy and completion are checked against physical bytes.
    The serialized executor has one staged writer (<=1024B source token payload),
    reusing idle shared tile space, rather than historical full-cache buffers.
    """
    def __init__(self,p):
        super().__init__(p); self.pc=0
        self.state={rank:extent(p,rank,'KV_provider_state') for rank in range(2)}
        self.counters=Counter()
    def state_write(self,rank,offset,data):
        e=self.state[rank]
        if offset<0 or offset+len(data)>e['bytes']: raise ValueError('KV state byte aperture')
        for i,byte in enumerate(data): self.bytes[rank,e['base']+offset+i]=byte
        self.counters['state_write_sectors32']+=len(set((e['base']+offset+i)//32 for i in range(len(data))))
    def state_read(self,rank,offset,count):
        e=self.state[rank]
        if offset<0 or offset+count>e['bytes']: raise ValueError('KV state byte aperture')
        self.counters['state_read_sectors32']+=len(set((e['base']+offset+i)//32 for i in range(count)))
        return bytes(self.bytes.get((rank,e['base']+offset+i),0) for i in range(count))
    def record(self,layer,rank): return int.from_bytes(self.state_read(rank,36864+16*layer,16),'little')
    def put_record(self,layer,rank,position,identity,producer_pc,done,status):
        if not 0<=layer<36 or not 0<=position<8192 or not 0<=identity<2**64 or not 0<=producer_pc<2048: raise ValueError('KV state identity aperture')
        value=position|(identity<<13)|(producer_pc<<77)|(done<<88)|(status<<90)
        self.state_write(rank,36864+16*layer,value.to_bytes(16,'little'))
    def bit(self,layer,rank,position):
        index=layer*8192+position
        return bool(self.state_read(rank,index//8,1)[0]&(1<<(index%8)))
    def begin(self,layer,die,position):
        if self.pending: raise ValueError('serialized writer lease busy')
        if self.bit(layer,die,position): raise ValueError('physical KV publication overwrite')
        tag=super().begin(layer,die,position)
        self.pending[tag]['producer_pc']=self.pc
        self.state_write(die,37440,self.tags.to_bytes(8,'little'))
        return tag
    def commit(self,tag):
        state=self.pending[int(tag)]; layer,rank,position=state['key']
        if len(state['payload'])>1024: raise ValueError('KV writer shared1024B staging bound')
        result=super().commit(tag)
        index=layer*8192+position; byte=self.state_read(rank,index//8,1)[0]|(1<<(index%8))
        self.state_write(rank,index//8,bytes([byte]))
        self.put_record(layer,rank,position,int(tag),state['producer_pc'],0,1)
        return result
    def acquire(self,fence,layer,die,position):
        if any(not self.bit(layer,die,pos) for pos in range(position+1)): raise ValueError('physical KV prefix unpublished')
        record=self.record(layer,die)
        if record&8191!=position or (record>>13)&((1<<64)-1)!=fence['tag']: raise ValueError('physical KV producer identity')
        if (record>>90)&3!=1: raise ValueError('physical KV reader record occupied')
        lease=super().acquire(fence,layer,die,position)
        self.put_record(layer,die,position,lease,(record>>77)&2047,0,2)
        return lease
    def read(self,lease,addresses):
        layer,rank,position=self.leases[int(lease)]['key']; record=self.record(layer,rank)
        if (record>>90)&3!=2 or (record>>13)&((1<<64)-1)!=lease: raise ValueError('physical KV reader lease identity')
        for address in np.asarray(addresses).flat:
            if not self.bit(layer,rank,self.decode_address(layer,rank,int(address))[1]): raise ValueError('physical KV read unpublished')
        return super().read(lease,addresses)
    def done(self,lease,stage):
        layer,rank,position=self.leases[lease]['key']; record=self.record(layer,rank)
        if (record>>13)&((1<<64)-1)!=lease or (record>>90)&3!=2: raise ValueError('physical KV completion lease')
        super().done(lease,stage)
        done=((record>>88)&3)|(1 if stage=='SCORES' else 2)
        self.put_record(layer,rank,position,lease,(record>>77)&2047,done,3 if done==3 else 2)

class TileWords:
    """Actual RF mirror/spill pages, not whole activation arrays in an SM."""
    def __init__(self,native):
        self.p=native['source_program']; self.values={v['version']:v for v in native['operands']}
        self.homes={}; self.control={}; self.pages={}; self.owners={}; self.live=set(); self.published=set(); self.shapes={}
        self.cache=None; self.counters=Counter(); self.events=[]; self.worker_SM=0; self.worker_rank=0
        for v in self.values.values():
            for h in v['homes']:
                if 'home' in h: self.homes[v['version'],h['rank'],h['SM']]=h
    def rank(self,version): return min(h['rank'] for h in self.values[version]['homes'])
    def key(self,version,word,rank):
        sm=(word//256)%32; local=(word//8192)*256+word%256
        record=self.homes.get((version,rank,sm))
        if record is None or local>=record['word_count']: raise ValueError('source home coordinate')
        h=record['home']
        if h['class']=='RF': return ('RF',rank,sm,h['slot_first']+local//128),local%128
        byte=h['global_byte_base']+4*local
        return ('HBM',rank,sm,h['global_byte_base']+(local//128)*512),local%128
    def reserve(self,version,position,kind='F32'):
        if version in self.live: raise ValueError('source SSA overwrite')
        v=self.values[version]; shape=tuple(position+1 if n=='position+1' else n for n in v['shape'])
        self.shapes[version]=(shape,kind); self.live.add(version)
        for h in v['homes']:
            if 'home' not in h: continue
            p=h['home']; start=p['slot_first'] if p['class']=='RF' else p['global_byte_base']
            count=p['vectors'] if p['class']=='RF' else p['bytes']//512; step=1 if p['class']=='RF' else 512
            for index in range(count):
                key=('RF' if p['class']=='RF' else 'HBM',h['rank'],h['SM'],start+index*step)
                if key in self.owners: raise ValueError('live provider alias')
                self.owners[key]=version
    def write(self,version,start,values):
        if version not in self.live: raise ValueError('unreserved destination')
        a=np.asarray(values)
        if a.size>128: raise ValueError('write needs outer128-word tile')
        kind=self.shapes[version][1]
        bits=a.astype(np.uint32).reshape(-1) if kind in ('U32','winner') else a.astype(F).view(np.uint32).reshape(-1)
        total=2 if kind=='winner' else math.prod(self.shapes[version][0])
        if start<0 or start+len(bits)>total: raise ValueError('source destination aperture')
        touched=set()
        for rank in sorted({h['rank'] for h in self.values[version]['homes']}):
            for i,word in enumerate(bits):
                key,lane=self.key(version,start+i,rank); touched.add(key)
                if self.owners.get(key)!=version: raise ValueError('destination provider lease identity')
                if key not in self.pages: self.pages[key]=[np.zeros(128,np.uint32) for _ in range(2 if key[0]=='RF' else 1)]
                for mirror in self.pages[key]: mirror[lane]=word
        for key in touched:
            self.counters['RF_write_ACK' if key[0]=='RF' else 'HBM_write_sectors32']+=1 if key[0]=='RF' else 16
            self.counters['source_write_payload_bits']+=4096
            if key[0]=='RF': self.counters['RF_mirror_write_bits']+=8192
            if (key[1],key[2])!=(self.worker_rank,self.worker_SM): self.counters['NoC_source_write_bits']+=4096
        self.cache=None
    def publish(self,version,value=None):
        if version not in self.live: raise ValueError('unreserved publication')
        if self.values[version]['homes'][0].get('home') is None: self.control[version]=copy.deepcopy(value)
        self.published.add(version); self.events.append(dict(event='publish',version=version))
    def read_indices(self,version,indices):
        if version not in self.published: raise ValueError('unpublished source')
        indexes=np.asarray(indices,dtype=np.int64).reshape(-1)
        if len(indexes)>128: raise ValueError('read needs outer128-word tile')
        shape,kind=self.shapes[version]; total=2 if kind=='winner' else math.prod(shape)
        if np.any(indexes<0) or np.any(indexes>=total): raise ValueError('source read aperture')
        result=np.empty(len(indexes),np.uint32); rank=self.rank(version)
        for i,word in enumerate(indexes):
            key,lane=self.key(version,int(word),rank)
            if self.owners.get(key)!=version: raise ValueError('source provider lease identity')
            if key not in self.pages: raise ValueError('unwritten provider page')
            if self.cache is None or self.cache[0]!=key:
                mirrors=self.pages[key]
                if len(mirrors)==2 and not np.array_equal(*mirrors): raise ValueError('RF mirror disagreement')
                self.cache=(key,mirrors[0].copy())
                self.counters['RF_read' if key[0]=='RF' else 'HBM_read_sectors32']+=1 if key[0]=='RF' else 16
                self.counters['source_read_payload_bits']+=4096
                if (key[1],key[2])!=(self.worker_rank,self.worker_SM): self.counters['NoC_source_read_bits']+=4096
            result[i]=self.cache[1][lane]
        self.counters['source_word_reads']+=len(indexes)
        return result if kind in ('U32','winner') else result.view(F)
    def read(self,version,start,count): return self.read_indices(version,np.arange(start,start+count,dtype=np.int64))
    def retire(self,pc):
        for version in list(self.live):
            if self.values[version]['retire_pc']!=pc: continue
            self.live.remove(version); self.published.remove(version); self.control.pop(version,None)
            for key in [k for k,v in self.owners.items() if v==version]:
                self.owners.pop(key); self.pages.pop(key,None)
            self.events.append(dict(event='release',version=version))
        self.cache=None
    def debug_snapshot(self,version,max_words=8192):
        """Post-commit TEST observer only; never used by the micro-op executor."""
        if version in self.control: return copy.deepcopy(self.control[version])
        shape,kind=self.shapes[version]; n=2 if kind=='winner' else math.prod(shape)
        if n>max_words: raise ValueError('debug snapshot bound')
        parts=[self.read(version,i,min(128,n-i)) for i in range(0,n,128)]
        a=np.concatenate(parts) if parts else np.empty(0,F)
        return (a[:1].view(F)[0],int(a[1])) if kind=='winner' else a.reshape(shape)


class TileFixtureWeights:
    """Random-access raw immutable fixture tiles, no complete matrix allocation."""
    def __init__(self,p): self.p=p; self.calls=[]; self.provider_reads=[]
    def read_tile(self,record,method,*args):
        if not record.get('provider_ref') or record.get('lease_state')!='visible': raise ValueError('immutable provider lease')
        self.provider_reads.append((record['provider_ref'],method))
        return getattr(self,method)(*args)
    def matrix_tile(self,key,row_start,row_count,column_start,column_count):
        d=self.p['weight_descriptors'][key]
        if not 0<row_count<=128 or not 0<column_count<=32 or row_start+row_count>d['rows'] or column_start+column_count>d['K']: raise ValueError('weight tile aperture')
        seed=int(hashlib.sha256(key.encode()).hexdigest()[:8],16)
        rows=np.arange(row_start,row_start+row_count,dtype=np.uint64)[:,None]
        cols=np.arange(column_start,column_start+column_count,dtype=np.uint64)[None,:]
        self.calls.append((key,row_start,row_count,column_start,column_count))
        return (((rows*131+cols*17+seed)%9).astype(np.int8)-4)
    def scale_tile(self,key,start,count): return np.full(count,F(.03125))
    def gamma_tile(self,layer,kind,start,count): return np.ones(count,F)
    def embedding_tile(self,token,start,count): return ((int(token)+np.arange(start,start+count))%9-4).astype(np.int8),F(.125)
    def rope_tile(self,position,theta,start,count):
        hd=self.p['config']['head_dim']; inv=(1/(theta**(np.arange(2*start,2*(start+count),2,dtype=np.float64)/hd))).astype(F)
        angle=(F(position)*inv).astype(F)
        return np.cos(angle.astype(np.float64)).astype(F),np.sin(angle.astype(np.float64)).astype(F)



class HBMByteTileProvider:
    """Concrete raw-byte transport adapter; no checkpoint arithmetic callback.

    The backend exposes read_tile_bytes(request) with actual provider identity,
    bounded byte ranges, visible backing, matched lease and reverse grant ACK.
    W8 full-row quantization is an upstream immutable producer, never silently
    performed by this consumer. BF16 and RoPE transport decoding is bit exact.
    """
    def __init__(self,backend): self.backend=backend
    def read_tile(self,record,method,*args):
        response=self.backend.read_tile_bytes(record)
        if not isinstance(response,dict) or response.get('provider_ref')!=record['provider_ref'] or response.get('lease')!=record['lease']:
            raise ValueError('immutable provider response identity')
        if response.get('state')!='visible' or not response.get('reverse_grant_ACK'):
            raise ValueError('immutable provider backing/reverse grant')
        payloads=response.get('payloads',[])
        if len(payloads)!=len(record['byte_ranges']) or any(len(data)!=r['bytes'] for data,r in zip(payloads,record['byte_ranges'])):
            raise ValueError('immutable provider response bytes')
        def bf(data):
            return (np.frombuffer(data,dtype='<u2').astype(np.uint32)<<16).view(F)
        if method=='matrix_tile': return np.stack([np.frombuffer(data,np.int8) for data in payloads])
        if method in ('scale_tile','gamma_tile'): return bf(payloads[0]).copy()
        if method=='embedding_tile': return np.frombuffer(payloads[0],np.int8).copy(),bf(payloads[1])[0]
        if method=='rope_tile': return tuple(np.frombuffer(data,dtype='<f4').copy() for data in payloads)
        raise ValueError('unsupported immutable byte tile '+method)

class TiledMachine:
    """Procedural tile/control interpreter over shared primitive microcode.

    Control methods only move bounded words, traverse exact source loops and
    call compiled primitive kernels. They never call a golden/operator oracle.
    Source tensor pages are RF/HBM backing; working arrays never exceed the
    declared RF32/shared17,408B limits.
    """
    def __init__(self,native,weights=None):
        if native.get('schema')!='opentallas.H3.qwen-bounded-tiled-native.v1': raise ValueError('tiled opt-in schema required')
        self.native=native; self.p=native['source_program']; self.store=TileWords(native)
        self.weights=weights or TileFixtureWeights(self.p); self.memory=BoundKVStorage(self.p); self.vm=NativePrimitiveVM()
        self.kv_leases={}; self.counters=Counter(); self.stack=[]; self.peak_shared=0; self.done=set()
        self.extents={e['provider_ref']:e for allocation in native['provider_binding']['allocation'] for e in allocation['extents']}
        self.current_external=[]
    def provider(self,method,*args):
        suffix={'matrix_tile':'.codes','scale_tile':'.scales','embedding_tile':'.embedding',
                'gamma_tile':'.final_norm' if method=='gamma_tile' and args[1]=='final' else '.qk_norm',
                'rope_tile':'.rope_table'}
        refs=[r for r in self.current_external if r['provider_ref'].endswith(suffix[method])]
        if not refs: raise ValueError('unbound external tile provider '+method)
        record=refs[0]; extent=self.extents.get(record['provider_ref'])
        if extent is None: raise ValueError('external extent missing')
        c=self.p['config']; h=c['hidden_size']; hd=c['head_dim']; ranges=[]
        if method=='matrix_tile':
            key,row,n,column,k=args; d=self.p['weight_descriptors'][key]
            if record['weight_descriptor']['key']!=key or not 0<n<=128 or not 0<k<=32: raise ValueError('code provider selector')
            if row<0 or column<0 or row+n>d['rows'] or column+k>d['K']: raise ValueError('code provider aperture')
            ranges=[(r*d['K']+column,k) for r in range(row,row+n)]
        elif method=='scale_tile':
            key,start,n=args
            if record['weight_descriptor']['key']!=key: raise ValueError('scale provider selector')
            ranges=[(2*start,2*n)]
        elif method=='gamma_tile':
            layer,kind,start,n=args; offset=hd if kind=='k' else 0
            ranges=[(2*(offset+start),2*n)]
        elif method=='embedding_tile':
            token,start,n=args
            if not 0<=token<c['vocab_size'] or start<0 or start+n>h: raise ValueError('embedding selector')
            ranges=[(token*h+start,n),(c['vocab_size']*h+2*token,2)]
        elif method=='rope_tile':
            position,theta,start,n=args
            if theta!=self.p['config']['rope_theta']: raise ValueError('RoPE provider source theta')
            ranges=[(4*(position*hd+start),4*n),(4*(position*hd+hd//2+start),4*n)]
        if method!='matrix_tile' and not 0<n<=128: raise ValueError('external provider tile aperture')
        if any(start<0 or size<0 or start+size>extent['bytes'] for start,size in ranges): raise ValueError('external byte aperture')
        bound=dict(record,base=extent['base'],bytes=extent['bytes'],lease_state='visible',
                   lease=f'PC{self.current_pc}.{record["provider_ref"]}',
                   byte_ranges=[{'address':extent['base']+start,'bytes':size} for start,size in ranges],
                   producer_dependency=record['provider_ref']+'.codec_backing_visible')
        if not hasattr(self.weights,'read_tile'): raise ValueError('raw provider read_tile ABI required')
        value=self.weights.read_tile(bound,method,*args)
        arrays=value if isinstance(value,tuple) else (value,)
        expected=(n,k) if method=='matrix_tile' else (n,)
        if np.shape(arrays[0])!=expected: raise ValueError('external tile result shape')
        if method in ('matrix_tile','embedding_tile'):
            if np.asarray(arrays[0]).dtype!=np.int8: raise ValueError('external INT8 code type')
        elif any(np.asarray(a).dtype!=F for a in arrays): raise ValueError('external FP32 decoded type')
        if method=='embedding_tile' and (np.asarray(arrays[1]).dtype!=F or int(np.asarray(arrays[1]).view(np.uint32))&65535): raise ValueError('embedding BF16 scale codec')
        if method in ('gamma_tile','scale_tile') and np.any(np.asarray(value).view(np.uint32)&65535): raise ValueError('external BF16 codec')
        sectors=set()
        for r in bound['byte_ranges']:
            sectors.update(range(r['address']//32,(r['address']+r['bytes']-1)//32+1))
        self.counters['immutable_HBM_sectors32']+=len(sectors)
        self.counters['immutable_provider_tile_ACK_reverse_release']+=1
        return value
    def kernel(self,name,**env):
        reserved=9+len(self.stack) # cache, accumulator, product, weight, x and control captures
        return self.vm.run_qwen(self.native['microcode'][name],env,reserved)
    def add(self,a,b): return self.kernel('add',a=a,b=b)
    def mul(self,a,b): return self.kernel('mul',a=a,b=b)
    def push(self,value):
        level=0
        while level<len(self.stack) and self.stack[level] is not None:
            value=self.add(self.stack[level],value); self.stack[level]=None; level+=1
        if level==len(self.stack): self.stack.append(value)
        else: self.stack[level]=value
    def root(self):
        present=[v for v in self.stack if v is not None]
        if len(present)!=1: raise ValueError('non-padded tree')
        value=present[0]; self.stack=[]; return value
    def scalar(self,version):
        if version in self.store.control: return self.store.control[version]
        return self.store.read(version,0,1)[0]
    def rms(self,version,start,n,eps):
        self.stack=[]; groups=(n+7)//8; leaves=1<<(groups-1).bit_length()
        # Only a128-word input page and one8-word square vector are live.
        for g in range(groups):
            x=self.store.read(version,start+8*g,min(8,n-8*g)); square=self.mul(x,x); value=F(0)
            for term in square: value=self.add(value,term)
            self.push(value)
        for _ in range(groups,leaves): self.push(F(0))
        total=self.root(); variance=self.add(self.mul(total,F(1/n)),F(eps))
        return self.kernel('rsqrt',variance=variance)
    def dot(self,rows,K,S,xreader,wreader,output,output_start,bf16=False,codes=False):
        for r0 in range(0,rows,128):
            rn=min(128,rows-r0); self.stack=[]; xcache=None; codecache=None
            for s in range(S):
                acc=np.zeros(rn,F)
                indexes=range(s*(K//S),(s+1)*(K//S)) if codes else range(s,K,S)
                # K traverses in exact golden split order. Empty leaves stay +0.
                for begin in range(0,len(indexes),32 if codes else 16):
                    kk=list(indexes[begin:begin+(32 if codes else 16)])
                    if codes:
                        for k in kk:
                            block=(k//32)*32
                            if codecache is None or codecache[0]!=block:
                                data=wreader(r0,rn,block,min(32,K-block))
                                if data.shape!=(rn,min(32,K-block)) or data.dtype!=np.int8: raise ValueError('raw code tile shape/type')
                                codecache=(block,data); self.peak_shared=max(self.peak_shared,2*data.nbytes)
                                self.counters['code_tile_reads']+=1; self.counters['code_payload_bytes']+=data.nbytes
                                sectors=set()
                                for row in range(r0,r0+rn):
                                    first=row*K+block; last=first+data.shape[1]-1
                                    sectors.update(range(first//32,last//32+1))
                                self.counters['code_sectors32']+=len(sectors)
                                self.counters['shared_write_beats128']+=(data.nbytes+127)//128
                                self.counters['tile_reserve_ACK_reverse_release']+=1
                            page=(k//128)*128
                            if xcache is None or xcache[0]!=page:
                                x=self.kernel('bf16',x=xreader(list(range(page,min(K,page+128)))))
                                xcache=(page,x); self.counters['BF16_pack_windows']+=1
                            self.counters['shared_read_beats128']+=(rn+127)//128
                            weight=self.kernel('convert',x=codecache[1][:,k-block])
                            acc=self.add(acc,self.mul(weight,xcache[1][k-page]))
                    else:
                        w=wreader(r0,rn,kk); x=xreader(kk)
                        if w.shape!=(rn,len(kk)) or w.dtype!=F: raise ValueError('FP32 attention tile shape/type')
                        self.peak_shared=max(self.peak_shared,2*w.nbytes)
                        self.counters['shared_write_beats128']+=(w.nbytes+127)//128
                        self.counters['shared_read_beats128']+=len(kk)*((4*rn+127)//128)
                        self.counters['tile_reserve_ACK_reverse_release']+=1
                        for j,k in enumerate(kk):
                            if bf16:
                                page=(k//128)*128
                                if xcache is None or xcache[0]!=page:
                                    xcache=(page,self.kernel('bf16',x=xreader(list(range(page,min(K,page+128)))))); self.counters['BF16_pack_windows']+=1
                                value=xcache[1][k-page]
                            else: value=x[j]
                            acc=self.add(acc,self.mul(w[:,j],value))
                self.push(acc)
            result=self.root()
            self.store.write(output,output_start+r0,result)
        if self.peak_shared>16384: raise ValueError('shared tile reservation')
    def execute(self,op):
        # Branches select tile/control programs; all arithmetic calls serialized
        # kernels above, independent of source golden and high-level providers.
        name=op['opcode']; a=op['attributes']; c=self.p['config']; hd=c['head_dim']; nh=c['num_attention_heads']//2
        self.current_external=op['provider_binding']['external_providers']; self.current_pc=op['pc']; self.memory.pc=op['pc']
        for record in self.current_external:
            if record['provider_ref'] not in self.extents: raise ValueError('unbound external provider')
        kv=c['num_key_value_heads']//2; T=self.position+1; reads=op['reads']; out=op['writes']
        for i,v in enumerate(out):
            kind='winner' if name=='ARGMAX' else 'U32' if name=='ARGMAX_REDUCE' else 'F32'
            self.store.reserve(v,self.position,kind)
        if name=='EMBED':
            for i in range(0,c['hidden_size'],128):
                codes,scale=self.provider('embedding_tile',int(self.scalar(reads[0])),i,min(128,c['hidden_size']-i))
                self.store.write(out[0],i,self.mul(self.kernel('convert',x=codes),scale))
        elif name=='RSTD': self.store.write(out[0],0,self.rms(reads[0],0,c['hidden_size'],a['epsilon']))
        elif name=='MATRIX':
            d=self.p['weight_descriptors'][a['weight']]
            self.dot(d['rows'],d['K'],d['split'],lambda indexes:self.store.read_indices(reads[0],indexes),
                lambda r,n,k,m:self.provider('matrix_tile',a['weight'],r,n,k,m),out[0],0,True,True)
        elif name in ('ROW_SCALE','SCALAR_MUL','RESIDUAL','ALL_REDUCE'):
            size=math.prod(self.store.shapes[out[0]][0])
            for start in range(0,size,128):
                n=min(128,size-start); x=self.store.read(reads[0],start,n)
                if name=='ROW_SCALE': value=self.mul(x,self.provider('scale_tile',a['weight'],start,n))
                elif name=='SCALAR_MUL': value=self.mul(x,self.scalar(reads[1]))
                else:
                    value=self.add(x,self.store.read(reads[1],start,n))
                    if name=='ALL_REDUCE': value=self.mul(value,self.provider('scale_tile',a['post_scale_weight'],start,n))
                self.store.write(out[0],start,value)
        elif name=='QKV_SPLIT':
            base=0
            for v in out:
                n=math.prod(self.store.shapes[v][0])
                for start in range(0,n,128): self.store.write(v,start,self.store.read(reads[0],base+start,min(128,n-start)))
                base+=n
        elif name in ('HEAD_NORM','FINAL_NORM'):
            heads=self.store.shapes[out[0]][0][0] if name=='HEAD_NORM' else 1
            dim=hd if name=='HEAD_NORM' else c['hidden_size']
            for head in range(heads):
                scalar=self.rms(reads[0],head*dim,dim,a['epsilon'])
                for start in range(0,dim,128):
                    n=min(128,dim-start); x=self.store.read(reads[0],head*dim+start,n)
                    gamma=self.provider('gamma_tile',a.get('layer'),a.get('kind','final'),start,n)
                    self.store.write(out[0],head*dim+start,self.mul(self.mul(x,scalar),gamma))
        elif name=='ROPE':
            half=hd//2; heads=self.store.shapes[out[0]][0][0]; position=int(self.scalar(reads[1]))
            for head in range(heads):
                for start in range(0,half,128):
                    n=min(128,half-start); lo=self.store.read(reads[0],head*hd+start,n); hi=self.store.read(reads[0],head*hd+half+start,n)
                    co,si=self.provider('rope_tile',position,a['theta'],start,n)
                    self.store.write(out[0],head*hd+start,self.add(self.mul(lo,co),self.mul(hi,self.kernel('neg',x=si))))
                    self.store.write(out[0],head*hd+half+start,self.add(self.mul(hi,co),self.mul(lo,si)))
        elif name=='KV_WRITE':
            tag=self.memory.begin(a['layer'],a['die'],int(self.scalar(reads[2])))
            for kind,v in [('K',reads[0]),('V',reads[1])]:
                base=extent(self.p,a['die'],f"L{a['layer']}.{kind}")['base']
                for head in range(kv):
                    for dim in range(0,hd,128):
                        n=min(128,hd-dim); codes=self.kernel('fp8pack',x=self.store.read(v,head*hd+dim,n))
                        dims=np.arange(dim,dim+n)
                        addr=base+((head*(self.p['context_capacity']//16)+self.position//16)*hd+dims)*16+self.position%16 if kind=='K' else base+(head*self.p['context_capacity']+self.position)*hd+dims
                        self.memory.write(tag,addr,codes)
            self.store.publish(out[0],tag)
        elif name=='KV_FENCE': self.store.publish(out[0],self.memory.commit(self.scalar(reads[0])))
        elif name=='KV_READ':
            lease=self.memory.acquire(self.scalar(reads[0]),a['layer'],a['die'],int(self.scalar(reads[1])))
            for kind,v in zip(('K','V'),out):
                base=extent(self.p,a['die'],f"L{a['layer']}.{kind}")['base']; size=kv*T*hd
                for start in range(0,size,128):
                    words=np.arange(start,min(size,start+128)); heads=words//(T*hd); positions=(words//hd)%T; dims=words%hd
                    addresses=base+((heads*(self.p['context_capacity']//16)+positions//16)*hd+dims)*16+positions%16 if kind=='K' else base+(heads*self.p['context_capacity']+positions)*hd+dims
                    values=self.kernel('fp8unpack',x=self.memory.read(lease,addresses)); self.store.write(v,start,values)
                self.kv_leases[v]=lease
        elif name=='SCORES':
            for head in range(nh):
                group=head//a['head_groups']
                def weights(r,n,kk):
                    data=np.empty((n,len(kk)),F)
                    for j,k in enumerate(kk): data[:,j]=self.store.read_indices(reads[1],group*T*hd+(np.arange(r,r+n)*hd)+k)
                    return data
                # Tree commits source-unscaled dot; postscale has its own round.
                self.dot(T,hd,a['split'],lambda indexes:self.store.read_indices(reads[0],head*hd+np.asarray(indexes)),weights,out[0],head*T,True)
                for start in range(0,T,128):
                    n=min(128,T-start)
                    self.store.write(out[0],head*T+start,self.mul(self.store.read_unpublished(out[0],head*T+start,n),F(1/np.sqrt(hd))))
            self.memory.done(self.kv_leases.pop(reads[1]),'SCORES')
        elif name=='EXP_SUM':
            for head in range(nh):
                maximum=self.store.read(reads[0],head*T,1)[0]
                for start in range(1,T,128):
                    for value in self.store.read(reads[0],head*T+start,min(128,T-start)): maximum=self.kernel('maximum',a=maximum,b=value)
                negative=self.kernel('neg',x=maximum); self.stack=[]; chunks=0; leaves=1<<(((T+7)//8)-1).bit_length()
                for start in range(0,T,128):
                    x=self.store.read(reads[0],head*T+start,min(128,T-start)); exps=self.kernel('exp',x=self.add(x,negative))
                    self.store.write(out[0],head*T+start,self.kernel('bf16',x=exps)); self.counters['BF16_pack_windows']+=1
                    for g in range(0,len(exps),8):
                        total=F(0)
                        for value in exps[g:g+8]: total=self.add(total,value)
                        self.push(total); chunks+=1
                for _ in range(chunks,leaves): self.push(F(0))
                self.store.write(out[1],head,self.root())
        elif name=='PV':
            for head in range(nh):
                group=head//a['head_groups']
                def weights(r,n,kk):
                    data=np.empty((n,len(kk)),F)
                    for j,k in enumerate(kk): data[:,j]=self.store.read(reads[1],(group*T+k)*hd+r,n)
                    return data
                self.dot(hd,T,a['split'],lambda indexes:self.store.read_indices(reads[0],head*T+np.asarray(indexes)),weights,out[0],head*hd)
            self.memory.done(self.kv_leases.pop(reads[1]),'PV')
        elif name=='NORMALIZE':
            for head in range(nh):
                inv=self.kernel('reciprocal',x=self.store.read(reads[1],head,1)[0])
                for start in range(0,hd,128):
                    n=min(128,hd-start); self.store.write(out[0],head*hd+start,self.mul(self.store.read(reads[0],head*hd+start,n),inv))
        elif name=='SILU_GATE':
            size=c['intermediate_size']//2
            for start in range(0,size,128):
                n=min(128,size-start); gate=self.store.read(reads[0],start,n); up=self.store.read(reads[0],size+start,n)
                ex=self.kernel('exp',x=self.kernel('neg',x=gate)); inverse=self.kernel('reciprocal',x=self.add(ex,F(1)))
                self.store.write(out[0],start,self.mul(self.mul(gate,inverse),up))
        elif name=='ARGMAX':
            size=math.prod(self.store.shapes[reads[0]][0]); best=self.store.read(reads[0],0,1)[0]; index=a['global_row_offset']
            for start in range(1,size,128):
                for j,value in enumerate(self.store.read(reads[0],start,min(128,size-start))):
                    if bool(self.kernel('argmax',candidate=value,best=best)): best=value; index=start+j+a['global_row_offset']
            bits=np.array([np.asarray(best,F).view(np.uint32),index],np.uint32); self.store.write(out[0],0,bits)
        elif name=='ARGMAX_REDUCE':
            left=self.store.read(reads[0],0,2); right=self.store.read(reads[1],0,2)
            win=bool(self.kernel('winner',a=left[:1].view(F)[0],b=right[:1].view(F)[0],ai=left[1],bi=right[1]))
            self.store.write(out[0],0,np.array([right[1] if win else left[1]],np.uint32))
        else: raise ValueError('unsupported tiled semantics '+name)
        for v in out:
            if v not in self.store.published: self.store.publish(v)
    def run(self,token,position,observer=None):
        if self.store.live: raise ValueError('unretired token')
        if not 0<=token<self.p['config']['vocab_size'] or not 0<=position<self.p['context_capacity']: raise ValueError('runtime aperture')
        self.position=position; self.done=set(); result=None
        for v in self.native['operands']:
            if v['birth_pc']==-1:
                self.store.reserve(v['version'],position,'U32'); self.store.write(v['version'],0,np.array([token if v['name']=='token' else position],np.uint32)); self.store.publish(v['version'])
        for op in self.native['operations']:
            if not set(op['dependencies'])<=self.done: raise ValueError('unretired dependency')
            if not set(op['reads'])<=self.store.published: raise ValueError('unpublished operand')
            self.execute(op)
            if op['opcode']=='ARGMAX_REDUCE': result=int(self.scalar(op['writes'][0]))
            if observer: observer(op,self.store)
            self.store.retire(op['pc']); self.done.add(op['pc'])
        if self.store.live or self.store.pages or self.kv_leases or self.memory.leases or self.memory.pending: raise ValueError('unretired tiled state')
        return dict(status='PASS_BOUNDED_TILED_SOFTWARE',next_token=result,PCs=len(self.done),RF_workspace_peak_vectors=self.vm.peak_vectors,
                    shared_tile_peak_bytes=self.peak_shared,primitive_counts=dict(self.vm.counts),primitive_word_counts=dict(self.vm.word_counts),
                    transfer_counts=dict(self.store.counters),tile_counts=dict(self.counters),KV_state_transfer_counts=dict(self.memory.counters),temporary_HBM_bytes=0,hardware_or_timing_credit=False)


def _read_unpublished(self,version,start,count):
    # Produced dot capture, not a forward source operand: same command lease.
    existed=version in self.published; self.published.add(version)
    try: return self.read(version,start,count)
    finally:
        if not existed: self.published.remove(version)
TileWords.read_unpublished=_read_unpublished


def tiled_cli(args):
    out=args.out/'tiled_r1'
    if args.exercise:
        config=dict(hidden_size=8,head_dim=4,num_attention_heads=2,num_key_value_heads=2,
                    intermediate_size=16,vocab_size=16,num_hidden_layers=36,rms_norm_eps=1e-6,rope_theta=1000000)
        native=compile_tiled(compile_program(config,context=32,groups=16)); machine=TiledMachine(native)
        runs=[]; token=3
        for position in range(2):
            result=machine.run(token,position); runs.append(result); token=result['next_token']
        print(canonical(dict(schema='opentallas.H3.qwen-bounded-software-replay.v1',config=config,
            executions=runs,source_homes_retired=not machine.store.owners,KV_leases_retired=not machine.memory.leases,
            oracle_callbacks=0,full_checkpoint_numerical_execution=False,
            fixture_scope='reduced shapes in identical distributed allocator; full compiler separately binds actual r17 homes',
            hardware_or_timing_credit=False)).decode(),end=''); return
    native=compile_tiled(); data=canonical(native); artifact=out/'Qwen_tiled.json.gz'
    if args.verify:
        manifest=json.loads((out/'manifest.json').read_text())
        for path,digest in manifest['source_sha256'].items():
            if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest: raise ValueError('tiled source pin mismatch '+path)
        if hashlib.sha256(artifact.read_bytes()).hexdigest()!=manifest['artifact_sha256']: raise ValueError('tiled artifact pin mismatch')
        with gzip.open(artifact,'rb') as f:
            if f.read()!=data: raise ValueError('tiled compiler replay mismatch')
        print(json.dumps(dict(status='PASS_EXACT_BOUNDED_COMPILER_REPLAY',**native['coverage']))); return
    out.mkdir(parents=True,exist_ok=True)
    with artifact.open('xb') as raw:
        with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as stream: stream.write(data)
    pins=['tools/h3_qwen_complete_native.py','tests/test_h3_qwen_complete_native.py',INPUT,
          'tools/qwen_hbm_complete_program.py','tools/h3_versioned_lowering.py',
          'tools/h3_distributed_norm_endpoint.py',
          OUT+'/tiled_r1/Peirce_native_76d564c9a.py.source']
    manifest=dict(schema=native['schema'],coverage=native['coverage'],provider_binding_pin=native['provider_binding_pin'],
        artifact_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
        source_sha256={path:hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in pins},
        replay='python tools/h3_qwen_complete_native.py --tiled --verify',
        exercise='python tools/h3_qwen_complete_native.py --tiled --exercise',
        tests='python -m pytest -q tests/test_h3_qwen_complete_native.py',hardware_or_timing_credit=False)
    (out/'manifest.json').write_bytes(canonical(manifest))
    (out/'common_native_ABI.json').write_bytes(canonical(native['primitive_ABI']))
    # Unit service values are explicit provisional software parameters, not cycles.
    calendar=materialize_tile_calendar(native,{name:1 for name in TILE_COSTS})
    with (out/'Qwen_serial_calendar.json.gz').open('xb') as raw:
        with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as stream: stream.write(canonical(calendar))
    print(json.dumps(native['coverage']))

def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--out',type=Path,default=ROOT/OUT)
    ap.add_argument('--tiled',action='store_true',help='Opt-in bounded RF32/shared tiled compiler and primitive VM')
    ap.add_argument('--verify',action='store_true')
    ap.add_argument('--exercise',action='store_true',help='Run all36 layers twice with reduced deterministic storage; output numerical trace hashes, no oracle')
    args=ap.parse_args()
    if args.tiled:
        return tiled_cli(args)
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
