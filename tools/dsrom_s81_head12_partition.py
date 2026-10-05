#!/usr/bin/env python3
"""Owner-selected S81 12-head storage inventory; TP4 arithmetic unchanged.

Reuse accepted layer/table allocation and released checkpoint header catalogue.
Append raw DSpark storage once; distribute physical pairs, not arithmetic ranks.
No payload/image generation, allocator sweep, runtime or RTL changes.
"""
import argparse
from bisect import bisect_right
import copy
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'results/uarch/dsrom_s81_released_binding_20261004/canonical/inventory.json'
HEADERS=ROOT/'results/quality/w16_w17_checkpoint_header_catalogue_20261001'
PRICE=ROOT/'results/uarch/dsrom_l2_head_mac_20261004/model.json'
SYSTEM=ROOT/'results/uarch/dsrom_c_recheck_20261004/model.json'
OUT=ROOT/'results/uarch/dsrom_s81_head12_partition_20261004/canonical'
PAIR_BYTES=524288


def require(ok,why):
    if not ok:raise ValueError(why)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compile_inventory():
    old=json.loads(OLD.read_text());price=json.loads(PRICE.read_text())
    require((old['stages'],old['TP'],old['head_dies'])==(81,4,8),'not accepted old S81')
    inv=copy.deepcopy(old);layout=inv['dedicated_storage']
    require(sum(t['pairs'] for t in layout['global_tensors'])==5051,'global pair offsets changed')
    index=json.loads((HEADERS/'model.safetensors.index.json').read_text())['weight_map']
    names=sorted(n for n in index if n.startswith('mtp.'))
    require(len(names)==2401,'released DSpark tensor coverage changed')
    pins={str(p.relative_to(ROOT)):digest(p) for p in (OLD,PRICE,SYSTEM,HEADERS/'model.safetensors.index.json')}
    tensors=[];cursor=0;headers={}
    for name in names:
        shard=index[name]
        if shard not in headers:
            p=HEADERS/'headers'/(shard+'.header.json')
            headers[shard]=json.loads(p.read_text());pins[str(p.relative_to(ROOT))]=digest(p)
        h=headers[shard][name];start,end=h['data_offsets']
        width={'I8':1,'U8':1,'F8_E4M3':1,'F8_E8M0':1,'BF16':2,'F32':4}[h['dtype']]
        size=end-start
        require(size==math.prod(h['shape'])*width,'released tensor extent '+name)
        tensors.append(dict(tensor=name,shape=h['shape'],dtype=h['dtype'],source_shard=shard,
                            source_data_offsets=[start,end],bytes=size,
                            storage_byte_range=[cursor,cursor+size],
                            stored_encoding_unchanged=True))
        cursor+=size
    require(cursor==price['basis']['dspark_bytes']==7932874632,'DSpark bytes differ from approved model')
    draft_pairs=math.ceil(cursor/PAIR_BYTES)
    total=5051+draft_pairs;per=math.ceil(total/12)
    layout.update(head_dies=12,head_storage_pairs_per_die_ceiling=per,
                  head_storage_total_pairs=total,
                  head_storage_partition='global_pair_round_robin',
                  head_storage_pair_bytes=PAIR_BYTES,
                  head_storage_partition_formula='die=global_pair%12; pair=global_pair//12',
                  dspark_storage=dict(pair_start=5051,pairs=draft_pairs,bytes=cursor,
                                      words=math.ceil(cursor/32),tensor_count=len(tensors),
                                      tensor_order='source name ascending; packed byte concatenation',
                                      word_data_bits=256,secded_bits=0,tensors=tensors,
                                      tail_word_zero_padding_bytes=(-cursor)%32,
                                      transport_ABI_qualified=False))
    inv.update(head_dies=12,total_dies=372,
               head_storage_revision='owner_selected_head12_with_released_dspark',
               source_inventory_sha256=digest(OLD))
    # Actual head weight phases: one physical pair span; never TP12 or sums
    # between rows/ranks. Boundary K offsets are multiples of1024, hence8.
    head=next(t for t in layout['global_tensors'] if t['tensor']=='head.weight')
    phases=[]
    for r in range(4):
        lo=r*32320*5120;hi=(r+1)*32320*5120
        for p in range(head['pairs']):
            a=max(lo,p*262144);b=min(hi,(p+1)*262144)
            if a>=b:continue
            gp=head['pair_start']+p
            phases.append(dict(source_node='Lhead.I5',source_tensor='head.weight',arithmetic_rank=r,
                global_pair=gp,storage_die=gp%12,local_pair=gp//12,
                tensor_element_range=[a,b],global_row_begin=a//5120,
                first_K=a%5120,global_row_end_exclusive=math.ceil(b/5120),
                final_K_exclusive=(b-1)%5120+1,
                K_order_unchanged=True,partial_row_requires_ordered_native_tree_join=True))
    bydie=[]
    for d in range(12):
        owned=len(range(d,total,12));hp=len(range(head['pair_start']+(d-head['pair_start'])%12,
                                                 head['pair_start']+head['pairs'],12))
        bydie.append(dict(storage_die=d,owned_pairs=owned,physical_ROM4096_macros=owned*4,
                          head_weight_pairs=hp,physical_owner_is_not_arithmetic_rank=True))
    return inv,dict(schema='dsrom.s81.head12.physical-weight-partition.v1',
                    TP=4,vocab_rows_per_rank=32320,head_dies=12,
                    global_raw_offsets_unchanged=True,by_die=bydie,head_phases=phases,
                    phases_are_source_weight_ownership_spans_not_invented_ISA_CFG=True),pins


def model(inv,partition):
    price=json.loads(PRICE.read_text());dec=json.loads(SYSTEM.read_text())
    s=dec['priced']['S81_ragged_RD64_replicated'];area=s['area'];system=s['system']
    pair=area['variable']/area['pairs'];fixed=area['die_mm2']-area['variable']
    nv5=next(v for v in price['variants'] if v['NV']==5)
    delta_pair=nv5['pair_delta_placed_um2']/1e6
    costs=[dict(d,head_die_model_mm2=fixed+d['owned_pairs']*pair+
                d['head_weight_pairs']*delta_pair) for d in partition['by_die']]
    corrected8total=8*fixed+inv['dedicated_storage']['head_storage_total_pairs']*pair+2525*delta_pair
    selected12total=sum(d['head_die_model_mm2'] for d in costs)
    oldcount=system['total_dies'];factor=372/oldcount
    return dict(schema='dsrom.s81.head12.sizing.v1',TP=4,old_head_dies=8,head_dies=12,
        old_system_dies=oldcount,system_dies=372,die_delta=4,
        die_count_delta_fraction=4/oldcount,head_mac_NV=5,
        raw_global_pairs=5051,raw_dspark_pairs=15131,dspark_source_bytes=7932874632,
        global_raw_payload_offsets_preserved=True,
        old_8die_inventory_omitted_dspark=True,by_die=costs,
        source_pair_field_mm2=pair,source_fixed_service_mm2_per_die=fixed,
        added_fixed_service_mm2=4*fixed,
        total_head_silicon_mm2=selected12total,
        corrected8head_silicon_mm2_with_same_drafter_NV5=corrected8total,
        head_silicon_delta_mm2_vs_corrected8=selected12total-corrected8total,
        system_silicon_delta_mm2_vs_corrected8=selected12total-corrected8total,
        max_head_die_mm2=max(d['head_die_model_mm2'] for d in costs),
        margin_target_mm2=dec['margin_target_die_mm2'],
        area_screen_fits=all(d['head_die_model_mm2']<=dec['margin_target_die_mm2'] for d in costs),
        power=dict(basis='SOURCE MODEL equal-average-die proxy; not measured head leakage or activity',
            static_icg_old_kW=system['static_kW_icg'],static_icg_12die_proxy_kW=system['static_kW_icg']*factor,
            static_icg_delta_proxy_kW=system['static_kW_icg']*(factor-1),
            static_pg_old_kW=system['static_kW_b1_pg'],static_pg_12die_proxy_kW=system['static_kW_b1_pg']*factor,
            static_pg_delta_proxy_kW=system['static_kW_b1_pg']*(factor-1),
            actual_added_die_and_drafter_dynamic_W=None,power_qualified=False),
        runtime_ports_and_transport_qualified=False,physical_admission=False,
        latency='No arithmetic/TP/tree change; native transport calendar and NV5 route owned by Claude',
        existing_NV5_SS_prelayout_wns_ps=nv5['ss_prelayout_wns_ps'])


def drafter_address(inventory,tensor,byte_offset):
    l=inventory['dedicated_storage'];ds=l['dspark_storage']
    t=next(t for t in ds['tensors'] if t['tensor']==tensor)
    require(type(byte_offset) is int and 0<=byte_offset<t['bytes'],'drafter byte coordinate')
    offset=t['storage_byte_range'][0]+byte_offset
    w,lane=divmod(offset,32);gp=ds['pair_start']+w//16384
    pair,die=divmod(gp,inventory['head_dies']);mb,logical=divmod(w%16384,8192)
    return dict(storage_die=die,local_pair=pair,mb=mb,parity=logical%2,
                physical_row=logical//2,bit_range=[lane*8,lane*8+8],global_pair=gp)


def drafter_word(inventory,source,die,macro,row):
    """Exact raw-storage callback using existing Checkpoint.raw; no image."""
    l=inventory['dedicated_storage'];ds=l['dspark_storage'];dies=inventory['head_dies']
    require(all(type(v) is int for v in (die,macro,row)) and 0<=die<dies and
            0<=macro<l['head_storage_pairs_per_die_ceiling']*4 and 0<=row<4096,
            'drafter physical coordinate')
    pair,leaf=divmod(macro,4);gp=pair*dies+die
    w=(gp-ds['pair_start'])*16384+(leaf//2)*8192+2*row+leaf%2
    require(0<=w<ds['words'],'request outside actual drafter storage')
    lo=w*32;end=min(lo+32,ds['bytes']);out=bytearray()
    ts=ds['tensors'];starts=[t['storage_byte_range'][0] for t in ts]
    i=bisect_right(starts,lo)-1
    while lo<end:
        t=ts[i];begin,limit=t['storage_byte_range'];n=min(limit,end)-lo
        require(n>0,'drafter source ownership gap')
        out.extend(source.raw(t['tensor'],lo-begin,n));lo+=n;i+=1
    return bytes(out)+bytes(32-len(out)) # ONLY declared tail-word padding


def emit(out=OUT):
    inv,part,pins=compile_inventory();out=Path(out);out.mkdir(parents=True,exist_ok=False)
    for name,data in [('inventory.json',inv),('head_partition.json',part),('model.json',model(inv,part)),
                      ('source_inputs.json',pins)]:
        (out/name).write_text(json.dumps(data,sort_keys=True,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT)
    emit(p.parse_args().out)
