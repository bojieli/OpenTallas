#!/usr/bin/env python3
"""Source-owned physical row templates for remaining canonical S81 SU tensors.

No ISA snapshot addresses or tensor values are consumed. This fixes spatial
allocation and exact scalar identity, including all384 possible expert source
producers. Native transfer/boot/commit/consumer edges remain separate contracts.
Missing calendars and the canonical SW576 versus hardware1024 adaptation reject
executable qualification; this module never substitutes reference results.
"""
import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/s81_compile_schedule'))
import operand_layout as FIRST
import su_stage_coverage as STAGE_COVERAGE
MATRIX=FIRST.MATRIX
STAGES=MATRIX.parent/'stage_map.json'
DEMAND=ROOT/'results/uarch/dsrom_native_weight_address_join_20261002/inputs/demand-r5.json.gz'
MOE_BASES=(6000,6321,6642,6963,7312,7633,7954)
NEW={
 'moe_y':dict(base_row=8320,nrows=80,scalars=1280,format='FP32 widened BF16',producer='actual six sequential MOE adds',consumer='TP4 all-gather then HCPOST'),
 'softmax_scores':dict(base_row=8448,nrows=640,scalars=10240,format='FP32 head-major16x640 maximum',producer='native QK',consumer='SE'),
 'softmax_exp':dict(base_row=9088,nrows=640,scalars=10240,format='FP32 head-major16x640 maximum',producer='SE',consumer='native PV'),
 'softmax_pv':dict(base_row=9728,nrows=512,scalars=8192,format='FP32 16x512',producer='native PV',consumer='SO'),
 'softmax_out':dict(base_row=10240,nrows=256,scalars=8192,format='packed BF16,32values/row',producer='SO',consumer='actual WO_A groups'),
 'attention_o_raw':dict(base_row=10496,nrows=128,scalars=2048,format='FP32 rank-local WO_A',producer='actual WO_A groups',consumer='QB'),
 'attention_o_quant':dict(base_row=10624,nrows=98,scalars=2048,format='two49row QB vectors including actual QDQ outputs',producer='QB',consumer='actual WO_B rank-column slice'),
 'parameter_storage':dict(base_row=12544,nrows=256,scalars=4096,format='actual descriptors/gains/RoPE/weights; native boot/producer contract REQUIRED',producer='actual constant boot and RW',consumer='SU kernels'),
}

def bank(row):return (row&31)^(((row>>5)&7)<<2)

def layout():
    items={k:dict(v) for k,v in FIRST.LAYOUT.items()}
    items.update({k:dict(v) for k,v in NEW.items()})
    for slot,base in enumerate(MOE_BASES):
        items[f'moe_e{slot}']=dict(base_row=base,nrows=320,scalars=1280,row_stride=4,used_rows=80,
            sparse_commit_profile=dict(slot=slot,base_row=base,row_stride=4,nrows=80,expected_words=1280,word_mask=65535,
                                       ARM_complete_before_first_commit=None,CHECK_after_last_commit=None,
                                       native_profile_bound=False),
            format='FP32 field output widened from exact BF16',producer='shared.w2' if slot==6 else f'actual selected expert slot{slot} W2',consumer='sequential MOE_SUM',slot=slot,compiler_tensor_geometry=dict(base_row=base,nrows=80,row_stride=4,reserved_span_rows=320))
    for slot in range(7):
        items[f'sw_gu{slot}']=dict(base_row=10752+128*slot,nrows=128,scalars=1152,
            format='72actual rows:36G followedby36U;56reserved rows are NEVER operands',
            producer='actual W1/W3',consumer='required native SW576',used_rows=72,
            actual_lanes=576,required_hardware_lanes=576,native_kernel_bound=False)
        items[f'sw_q{slot}']=dict(base_row=11648+28*slot,nrows=28,scalars=576,
            format='required SW576 output:9code+1exponent+18QDQ rows',used_rows=28,
            producer='required native SW576',consumer='actual TP4 activation gather',native_kernel_bound=False)
        items[f'sw_gather{slot}']=dict(base_row=12096+64*slot,nrows=40,scalars=2304,
            format='four rank records:9code rows+1 exponent row each',producer='actual TP4 activation gather',consumer='actual W2 all72column blocks')
    return items

def verify_layout(items):
    used={}
    for name,a in items.items():
        # Reserve complete spans, including stride holes, until source-bound
        # lifetimes allow explicit reuse. No overlap is hidden in unused words.
        for row in range(a['base_row'],a['base_row']+a['nrows']):
            if row in used:raise ValueError(f'physical overlap {name}/{used[row]} at{row}')
            if not 0<=row<16384:raise ValueError('native VM capacity')
            used[row]=name
    bases=[items[f'moe_e{s}']['base_row'] for s in range(7)]
    if any(items[f'moe_e{s}'].get('row_stride')!=4 for s in range(7)):raise ValueError('MOE requires stride4')
    for edge in range(80):
        rows=[b+4*edge for b in bases]
        if any(r%4!=p%4 for p,r in enumerate(rows)):raise ValueError('SU read colour')
        if len({bank(r) for r in rows})!=7:raise ValueError('SU read bank conflict')
    return dict(reserved_rows=len(used),highest_reserved_row=max(used),vm_capacity_rows=16384,
                moe_edges=80,moe_requests=560,moe_bank_conflicts=0,
                source_timing_and_lifetimes_qualified=False)

def expert_slot(alias,selected):
    if alias.startswith('shared.'):return 6
    m=re.match(r'exp(\d+)\.',alias)
    if not m:raise ValueError('actual expert or shared source required')
    if (selected is None or len(selected)!=6 or any(type(e)!=int or not 0<=e<384 for e in selected)
            or list(selected)!=sorted(set(selected))):raise ValueError('six actual distinct ascending native EIDs required')
    expert=int(m[1])
    if expert not in selected:raise ValueError('unselected expert producer')
    return selected.index(expert)

def field_destination(matrix,rank,global_row,*,selected=None):
    if type(rank)!=int or not 0<=rank<4:raise ValueError('rank')
    lo,hi=matrix['rank_slices'][rank]['rows']
    if type(global_row)!=int or not lo<=global_row<hi:raise ValueError('source rank row')
    alias=matrix.get('original_alias') or matrix['alias']
    if re.match(r'(shared|exp\d+)\.w[123](\.|$)',alias):
        slot=expert_slot(alias,selected)
        w=re.search(r'\.w([123])',alias)[1]
        width=1280 if w=='2' else 576
        scalar=global_row-width*rank
        if not 0<=scalar<width:raise ValueError('actual canonical expert shape')
        if w=='2':tensor=f'moe_e{slot}';row=MOE_BASES[slot]+4*(scalar//16)
        else:tensor=f'sw_gu{slot}';row=10752+128*slot+(36 if w=='3' else 0)+scalar//16
    elif alias.startswith('wo_a.group'):
        scalar=global_row-2048*rank
        if not 0<=scalar<2048:raise ValueError('actual WO_A rank shape')
        tensor='attention_o_raw';row=10496+scalar//16
    else:
        # Existing source-owned first allocation, not old ISA addresses.
        return FIRST.scalar_destination(matrix,rank,global_row)
    return dict(tensor=tensor,row=row,word=scalar%16,scalar_index=scalar,source_rank=rank,
                source_stage=matrix['stage'],native_endpoint_bound=False)

def sw_block(slot,source_rank,block,*,gathered):
    if slot not in range(7) or source_rank not in range(4) or block not in range(18):raise ValueError('canonical SW block')
    if gathered:base=12096+64*slot+10*source_rank;exp=base+9
    else:base=11648+28*slot;exp=base+9
    return dict(code_row=base+block//2,code_lsb=256*(block%2),exponent_row=exp,exponent_lsb=16*block,
                scalar_count=32,global_w2_scalar_begin=576*source_rank+32*block,
                native_gather_bound=False)

def qb_block(block):
    if type(block)!=int or not 0<=block<64:raise ValueError('canonical WO_B64 blocks')
    vector,within=divmod(block,32);base=10624+49*vector
    return dict(code_row=base+within//2,code_lsb=256*(within%2),exponent_row=base+16,
                exponent_lsb=16*within,scalar_count=32,scalar_begin=32*block)

def source_catalog():
    """Streaming metadata extraction avoids retaining all native plan payloads."""
    records=[];count=0
    with gzip.open(MATRIX,'rt') as f:
        for line in f:
            m=json.loads(line);count+=1
            alias=m.get('original_alias') or m['alias']
            if not (re.match(r'(shared|exp\d+)\.w[123](\.|$)',alias) or alias.startswith('wo_a.group')):continue
            records.append({k:m[k] for k in ('layer','alias','stage','rank_slices','K','rows')})
    if count!=46671:raise ValueError('actual canonical matrix coverage changed')
    # Every possible routed expert remains represented. Verify literal source
    # row intervals; a reduced expert catalogue cannot pass this allocation.
    groups=collections.defaultdict(list)
    for m in records:
        alias=m['alias']
        match=re.match(r'(shared|exp\d+)\.w([123])',alias)
        if not match:continue
        owner,w=match.groups();width=1280 if w=='2' else 576
        if m['K']!=(2304 if w=='2' else 5120):raise ValueError('canonical expert input dimension')
        for rank in range(4):groups[(m['layer'],owner,w,rank)].append(tuple(m['rank_slices'][rank]['rows']))
    for layer in range(40):
        for owner in ['shared']+[f'exp{e}' for e in range(384)]:
            for w in ('1','2','3'):
                width=1280 if w=='2' else 576
                for rank in range(4):
                    cursor=width*rank
                    for a,b in sorted(groups[(layer,owner,w,rank)]):
                        if a!=cursor or b<=a:raise ValueError('source expert row overlap/gap')
                        cursor=b
                    if cursor!=width*(rank+1):raise ValueError('source expert row coverage')
    return records

def build():
    if hashlib.sha256(MATRIX.read_bytes()).hexdigest()!=FIRST.MATRIX_SHA:raise ValueError('canonical source SHA')
    stages=json.loads(STAGES.read_text());demand=json.loads(gzip.decompress(DEMAND.read_bytes()))
    if len(stages['PHW_required_by_stage'])!=81 or any(v>10 for v in stages['PHW_required_by_stage']):raise ValueError('canonical81/PHW10')
    items=layout();check=verify_layout(items);catalog=source_catalog()
    # Source order and rounding are retained literally; no old a_base/o_base is
    # copied into this physical allocation. HC and control nodes remain visible.
    nodes=[]
    for n in demand['nodes']:
        i=n.get('instruction',{})
        if i.get('unit')!=2:continue
        nodes.append(dict(node=n['id'],scope=n['scope'],template_sha256=n['template_word_sha256'],
            semantic_tag=i.get('_tag'),reads=i.get('_reads',[]),writes=i.get('_writes',[]),
            shape={k:i[k] for k in ('su_nin','su_nout','su_d_nin','su_d_nout','rnd') if k in i},
            kernel_bound=False))
    return dict(schema='opentallas.s81.full-su-spatial-allocation.v1',qualified=False,
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (MATRIX,STAGES,DEMAND)},
        physical_layout=items,spatial_check=check,source_field_fragments=catalog,
        source_SU_nodes=nodes,he_crom_provider_homes_only=stages['provider_homes'],
        stage_execution_coverage=STAGE_COVERAGE.export(stages,catalog,nodes),
        parameter_bindings=dict(
            GQ=dict(descriptor=12544,actual_gain_rows=list(range(12545,12625))),
            GK=dict(descriptor=12625,actual_gain_rows=list(range(12626,12658))),
            QN=dict(rows=[12658]),KV=dict(rows=list(range(12659,12664))),QB=dict(rows=[12664]),
            SW=[dict(slot=s,descriptor=12665+s,actual_weight_row=12672,weight_word=5+s,
                     parameter_reads=[12665+s,12672],native_576_tap_ABI_bound=False,
                     source_weight='native RW' if s<6 else 'literal shared1.0 from actual init image') for s in range(7)],
            SE=dict(rows=[12673,12674]),SO=dict(rows=list(range(12675,12680))),
            QR=dict(rows=list(range(12680,12685))),RA=dict(rows=[12685]),RB=dict(rows=[12686]),
            RW=dict(descriptor=12687,result_row=12672,result_word_mask=0x7e0,shared_word11_preserved=True),
            CN=dict(rows=list(range(12688,12693))),IK=dict(rows=list(range(12693,12698))),
            actual_ROM_gain_RoPE_payload_bindings=False,actual_parameter_commit_edges=None),
        required_shapes=dict(SW_W=576,SW_active_read_slots=12,SW_quant_engines=6,SW_passes=3,
                             SW_lane_engines=144,SW_lanes_per_engine=4,existing_SW1024_compatible=False),
        native_sw_read_rows=[dict(slot=s,burst=b,rows=[10752+128*s+12*b+p for p in range(12)]) for s in range(7) for b in range(6)],
        native_reads=[dict(edge=r,slots=[dict(slot=p,row=b+4*r,bank=bank(b+4*r)) for p,b in enumerate(MOE_BASES)]) for r in range(80)],
        sw_gather_records=[dict(slot=s,source_rank=r,source_row=11648+28*s+j,
                               destination_row=12096+64*s+10*r+j,mask=65535)
                           for s in range(7) for r in range(4) for j in range(10)],
        unresolved=['actual81stage/rank SU/VM homes (HE/CROM provider_homes2L are NOT SU homes) and source-bound transfer/pack/write calendars',
                    'actual native SW576 kernel/28row output and measured exact fullshape gate (legacy1024 is incompatible, never padded implicitly)',
                    'actual T0 count/denominator lifetime and native PV/softmax full calendar',
                    'native SW activation TP4 gather for all7slots and all72W2blocks',
                    'actual descriptors/gains/RoPE/route weights constant/producer/commit bindings',
                    'all2654 raw SU instructions→exact native fused providers with rounding/order proof',
                    'persistent state, MTP continuation, global lifetimes and all other VM clients',
                    'actual physical paths, clock phases, commit visibility and end-to-end throughput'])

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    result=build();a.out.parent.mkdir(parents=True,exist_ok=True);raw=(json.dumps(result,separators=(',',':'))+'\n').encode()
    a.out.write_bytes(gzip.compress(raw,mtime=0) if a.out.suffix=='.gz' else raw)
    print(json.dumps(dict(schema=result['schema'],qualified=False,spatial_check=result['spatial_check'],
                         field_fragments=len(result['source_field_fragments']),raw_SU_nodes=len(result['source_SU_nodes']))))
if __name__=='__main__':main()
