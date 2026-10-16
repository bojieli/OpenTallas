#!/usr/bin/env python3
"""Compiler-owned first native field/SU operand allocation, without tensor data.

The source matrix metadata proves scalar identity and TP slicing only. It does
not prove the current die's packet/capture wiring or completion cycles. No old
ISA address or fixture allocation is reused. The actual field/capture owners
must consume this allocation and emit the corresponding native write edges.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MATRIX=ROOT/'results/uarch/dsrom_s81_released_binding_20261004/canonical/matrix_map.jsonl.gz'
MATRIX_SHA='985a9ee7ea26d2a7bb1aebadc5151252836eacf8181e8794b1ef6d7819db0326'
LAYOUT={
 'q_norm_input':dict(base_row=4096,nrows=80,scalars=1280,format='fp32',producer='attn.a_allgather',consumer='attn.q_quant'),
 'q_norm_output':dict(base_row=4176,nrows=25,format='five groups each four FP8-code rows then one UE8M0 exponent row',producer='attn.q_quant',consumer='attn.wq_b'),
 'kv_norm_input':dict(base_row=4224,nrows=32,scalars=512,format='fp32',producer='attn.a_allgather',consumer='attn.kv_rope_qdq'),
 'kv_norm_output':dict(base_row=4256,nrows=25,format='8 FP8-code rows, one UE8M0 exponent row, 16 packed-BF16 QDQ rows',producer='attn.kv_rope_qdq',consumer='attn.own_row_write'),
 'router_input':dict(base_row=5008,nrows=6,scalars=96,format='fp32 rank-local96 logits',producer='ffn.router',consumer='ffn.softplus_sqrt'),
 'router_local_scores':dict(base_row=5024,nrows=6,scalars=96,format='fp32 rank-local96 sqrtsoftplus scores',producer='ffn.softplus_sqrt',consumer='ffn.router_allgather'),
 'route_ids':dict(base_row=5168,nrows=1,format='six selected uint32 IDs; actual selector producer',producer='ffn.top6_order',consumer='ffn.weights'),
 'router_all_scores':dict(base_row=5169,nrows=24,scalars=384,format='fp32 rank-major384 scores; immediately after IDs',producer='ffn.router_allgather',consumer='ffn.bias and ffn.weights'),
 'router_bias':dict(base_row=5193,nrows=24,scalars=384,format='residentFP32 bias; immediately after scores',producer='native constant boot',consumer='ffn.bias'),
 'router_biased_scores':dict(base_row=5232,nrows=24,scalars=384,format='fp32 biased scores',producer='ffn.bias',consumer='ffn.top6'),
 'compressor_kv':dict(base_row=4816,nrows=32,scalars=512,format='fp32',producer='attn.a_allgather',consumer='attn.cmp.pool or ratio1 CN'),
 'compressor_score':dict(base_row=4848,nrows=32,scalars=512,format='fp32',producer='attn.a_allgather',consumer='attn.cmp.pool'),
 'compressor_pool':dict(base_row=4880,nrows=32,scalars=512,format='BF16 values widened to FP32',producer='attn.cmp.pool',consumer='attn.cmp.row_qdq'),
 'q_projection':dict(base_row=4304,nrows=512,scalars=8192,format='fp32, 16 heads x512; QR updates only last64 elements/head',producer='attn.wq_b',consumer='attn.q_rope'),
}


def cp_binding(layer, context, slot, *, pool):
    """Literal CP14 row/pin ABI for real current all-gather producers.

    Store and pool reuse the same current rows on separate command epochs.
    No previous-token tensor is fabricated: physical CP history must already
    belong to this context, or first be filled by a real store/restore command.
    """
    if type(layer) is not int or layer not in (2,8,14):
        raise ValueError('CP512 ratio-two source layer must be2,8,14')
    if type(context) is not int or not 0<=context<2**32 or type(slot) is not int or slot not in (0,1) or type(pool) is not bool:
        raise ValueError('CP requires uint32 context, physical slot0/1 and bool pool')
    kv,score,out=(LAYOUT[n]['base_row']for n in ('compressor_kv','compressor_score','compressor_pool'))
    words=[out,kv,512,score,context,slot+2*pool]+[0]*10
    bank=lambda row:(row&31)^(((row>>5)&7)<<2)
    reads=[dict(relative_issue_cycle=4*j,slots=[0,1],rows=[kv+j,score+j],banks=[bank(kv+j),bank(score+j)])for j in range(32)]
    if any(r['banks'][0]==r['banks'][1]for r in reads):raise ValueError('CP paired reads collide on native XOR banks')
    return dict(kind='CP',opcode=14,descriptor_row=12336,descriptor_words=words,
                command_arg24=(14<<20)|12336,read_requests=reads,
                source_producers=[f'L{layer}.attn.a_allgather']*2,
                input_formats=['512 FP32 compressor.wkv values','512 FP32 compressor.wgate values'],
                output_rows=list(range(out,out+32))if pool else [],
                output_format='512 BF16 values widened to FP32',
                persistent_context=context,physical_slot=slot,pool=pool,
                actual_producer_write_edges_bound=False,history_lifetime_bound=False,
                dispatch_eligible=False,required='native allgather commit fence; real first-slot store/restore and one-context lifetime; measured command-pin and VM service edges')


def scalar_destination(matrix,rank,global_row):
    """Map one *actual source tensor row* to physical 16x32-bit VM storage.

    QN/KV operands are replicated across the TP4 consumer dies after gathering;
    each source rank contributes only its literal matrix row slice. WQ_B stays
    on its source rank and its two existing row fragments share one allocation.
    Packet phase tags must be explicitly joined by the field/capture owner.
    """
    if type(rank) is not int or not 0<=rank<4 or type(global_row) is not int:
        raise ValueError('actual TP4 rank and integer tensor row required')
    row0,row1=matrix['rank_slices'][rank]['rows']
    if not row0<=global_row<row1:
        raise ValueError('field row outside actual rank source slice')
    alias=matrix['alias']
    if alias=='wq_a':
        allocation='q_norm_input';scalar=global_row
    elif alias=='wkv':
        allocation='kv_norm_input';scalar=global_row
    elif alias=='gate':
        allocation='router_input';scalar=global_row-96*rank
    elif alias in ('compressor.wkv','compressor.wgate'):
        allocation='compressor_kv' if alias.endswith('wkv') else 'compressor_score';scalar=global_row
    elif alias.startswith('wq_b.rows'):
        allocation='q_projection';scalar=global_row-rank*8192
    else:
        raise ValueError('unbound source tensor; no heuristic allocation')
    item=LAYOUT[allocation]
    if not 0<=scalar<item['scalars']:
        raise ValueError('source shape does not fit actual consumer shape')
    return dict(tensor=allocation,row=item['base_row']+scalar//16,word=scalar%16,
                source_rank=rank,consumer_rank='all-four-after-real-allgather' if alias in ('wq_a','wkv','compressor.wkv','compressor.wgate') else rank,
                scalar_index=scalar)


def quantized_block_view(kind, block):
    """Actual SU output ABI for a field operand block of32 FP8 values.

    This supplies addresses/bit slices only. The native VM reader must fetch
    both records on its assigned cycles and drive the actual field input pins.
    There is no FP32 recomputation or unpacked C++ activation array here.
    """
    limit={'QN':40,'KV':16}.get(kind)
    if limit is None or type(block) is not int or not 0<=block<limit:
        raise ValueError('actual QN/KV block within compiled shape required')
    if kind=='QN':
        group,within=divmod(block,8)
        code_row=4176+5*group+within//2
        exponent_row=4176+5*group+4
        exponent_lsb=16*within
    else:
        code_row=4256+block//2
        exponent_row=4264
        exponent_lsb=16*block
    return dict(code_row=code_row,code_lsb=256*(block%2),code_bits=256,
                exponent_row=exponent_row,exponent_lsb=exponent_lsb,exponent_bits=16,
                scalar_begin=32*block,scalar_count=32,
                required_native_reads=sorted({code_row,exponent_row}),
                native_transport_bound=False)


def a_projection_gather_landing():
    """Actual per-rank20 WQ_A +8 WKV FP32 records, not fixture12."""
    rows=[]
    for rank in range(4):
        for record in range(28):
            tensor='q_norm_input' if record<20 else 'kv_norm_input'
            row=4096+20*rank+record if record<20 else 4224+8*rank+record-20
            rows.append(dict(source_rank=rank,source_record=record,destination_tensor=tensor,
                             destination_vm_row=row,word_mask=65535))
    return dict(mode=1,records_per_rank=28,total_output_rows=112,
                scope='WQ_A plus WKV only; compressor branch transport requires separate native binding',
                arg24=(1<<16)|28,records=rows,fixed_transport_cycles=None,
                historical_fixture_records_per_rank=12,historical_fixture_timing_usable=False,
                native_endpoint_bound=False)


def full_a_projection_gather_landing(layer):
    """Released source layers add real compressor records, never zero rows."""
    if type(layer) is not int or not 0<=layer<40:
        raise ValueError('actual backbone layer0..39 required')
    result=a_projection_gather_landing()
    result['records']=[dict(row) for row in result['records']]
    if layer in (2,8,14,20):
        for rank in range(4):
            for record in range(8):
                result['records'].append(dict(source_rank=rank,source_record=28+record,
                    destination_tensor='compressor_kv',destination_vm_row=4816+8*rank+record,word_mask=65535))
        result['records_per_rank']=36
    if layer in (2,8,14):
        for rank in range(4):
            for record in range(8):
                result['records'].append(dict(source_rank=rank,source_record=36+record,
                    destination_tensor='compressor_score',destination_vm_row=4848+8*rank+record,word_mask=65535))
        result['records_per_rank']=44
    result.update(total_output_rows=4*result['records_per_rank'],arg24=(1<<16)|result['records_per_rank'],
                  scope='actual ordinary Q/KV plus released compressor branches',layer=layer)
    return result


def router_gather_landing():
    records=[dict(source_rank=r,source_record=j,source_vm_row=5024+j,
                  destination_vm_row=5169+6*r+j,word_mask=65535) for r in range(4) for j in range(6)]
    return dict(mode=1,records_per_rank=6,total_output_rows=24,arg24=(1<<16)|6,records=records,
                scope='main384-expert router only; MTP128-expert path requires actual plan proof',
                fixed_transport_cycles=None,native_endpoint_bound=False)


def source_matrices(path=MATRIX):
    if hashlib.sha256(path.read_bytes()).hexdigest()!=MATRIX_SHA:
        raise ValueError('released source matrix metadata changed')
    result=[]
    with gzip.open(path,'rt') as f:
        for line in f:
            row=json.loads(line)
            if row.get('layer') in range(40) and (row['alias'] in ('wq_a','wkv','compressor.wkv','compressor.wgate','gate') or row['alias'].startswith('wq_b.rows')):
                result.append({k:row[k] for k in ('layer','alias','rank_slices','tensor','format','K','rows')})
    return result


def generate(matrices):
    coverage={}
    joins=[]
    for matrix in matrices:
        L=matrix['layer']
        for rank in range(4):
            begin,end=matrix['rank_slices'][rank]['rows']
            first=scalar_destination(matrix,rank,begin);last=scalar_destination(matrix,rank,end-1)
            key=(L,first['tensor'],rank)
            scalar_range=(first['scalar_index'],last['scalar_index']+1)
            coverage.setdefault(key,[]).append(scalar_range)
            joins.append(dict(layer=L,source_tensor=matrix['tensor'],alias=matrix['alias'],source_rank=rank,
                              source_global_rows=[begin,end],destination_first=first,destination_last=last,
                              implemented_write_path=False,fixed_calendar=None))
    expected={(L,name,rank) for L in range(40) for name in ('q_norm_input','kv_norm_input','q_projection','router_input') for rank in range(4)}
    expected |= {(L,'compressor_kv',rank) for L in (2,8,14,20) for rank in range(4)}
    expected |= {(L,'compressor_score',rank) for L in (2,8,14) for rank in range(4)}
    if set(coverage)!=expected:
        raise ValueError('missing/extra released field producer scope')
    for (L,name,rank),intervals in coverage.items():
        ordered=sorted(intervals)
        begin=0 if name!='q_projection' else 0
        # For replicated operands each source supplies its exact quarter.
        if name not in ('q_projection','router_input'):
            begin=rank*LAYOUT[name]['scalars']//4
        cursor=begin
        for lo,hi in ordered:
            if lo!=cursor or hi<=lo:
                raise ValueError('duplicate/gapped field producer rows')
            cursor=hi
        count=LAYOUT[name]['scalars'] if name in ('q_projection','router_input') else LAYOUT[name]['scalars']//4
        if cursor!=begin+count:
            raise ValueError('incomplete actual consumer row coverage')
    return dict(schema='opentallas.s81.first-native-operand-layout.v1',layout=LAYOUT,
                source_evidence=dict(path=str(MATRIX.relative_to(ROOT)),sha256=MATRIX_SHA),
                abi_evidence=[dict(path=rel,sha256=hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()) for rel in ('rtl/dsrom_sys/s81_suhc/ot_s81_su_core.sv','tools/s81_suhc/su_gate.py')],
                status='PRODUCTION_ALLOCATION_REQUIRES_NATIVE_PRODUCER_INTEGRATION',
                source_matrices=len(matrices),rank_fragments=len(joins),joins=joins,
                a_projection_allgather=a_projection_gather_landing(),
                router_allgather=router_gather_landing(),
                full_a_projection_allgather={str(L):full_a_projection_gather_landing(L) for L in range(40)},
                field_quantized_operand_views={kind:[quantized_block_view(kind,b) for b in range(count)] for kind,count in [('QN',40),('KV',16)]},
                descriptors=dict(QN=dict(row=12288,opcode=0,gain_set=1,input_row=4096,output_row=4176),
                                 KV=dict(row=12304,opcode=1,gain_set=2,input_row=4224,output_row=4256),
                                 QR=dict(row=12320,opcode=10,input_row=4304,output_row=4304,heads=16)),
                required=['real field partial/root -> capture row/lane identity',
                          'actual TP4 all-gather 320 wq_a +128 wkv values per rank',
                          'native resident Q/K gains, epsilon and four RoPE parameter rows per descriptor',
                          'actual field FP8 operand code/exponent views; no ideal FP32 array substitution',
                          'phase-pinned physical VM service and immutable calendar replay'],
                dispatch_eligible=False,qualified=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    r=generate(source_matrices());a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n')
    print(f"Allocated {r['source_matrices']} released matrices / {r['rank_fragments']} rank fragments; native transport unqualified")


if __name__=='__main__':
    main()
