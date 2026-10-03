"""Read-only source-exact active spans and explicit old-sector origin checks.

No numerical execution, fabricated initialization, physical ACK or service cost.
"""
import ast
import gzip
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/h4_hbm_qwen_observed_kv_cache_20261002'


def require(ok,message):
    if not ok:raise ValueError(message)

def source_mapper(native,source):
    tree=ast.parse(source)
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef)and n.name=='TileWords')
    method=next(n for n in cls.body if isinstance(n,ast.FunctionDef)and n.name=='key')
    scope={};exec(compile(ast.Module(body=[method],type_ignores=[]),'<pinned TileWords.key>','exec'),scope)
    class Mapper:pass
    mapper=Mapper();mapper.homes={(v['version'],h['rank'],h['SM']):h for v in native['operands']for h in v['homes']if 'home'in h}
    return mapper,scope['key']

def spans(native,source,version,rank,position,*,mapping=None):
    require(type(position)is int and 0<=position<native['source_program']['context_capacity'],'active position bound')
    value=next(v for v in native['operands']if v['version']==version)
    require(value['homes'] and all('home'in h for h in value['homes']),'source word homes; opaque controls excluded')
    shape=[position+1 if n=='position+1'else n for n in value['shape']]
    count=math.prod(shape);mapper,key=mapping or source_mapper(native,source);result=[]
    for start in range(0,count,128):
        addresses=[key(mapper,version,w,rank)for w in range(start,min(count,start+128))]
        page,lane=addresses[0]
        require(all(p==page and l==lane+i for i,(p,l)in enumerate(addresses)),'source contiguous page/window')
        record=mapper.homes[version,rank,page[2]]
        row=dict(version=version,rank=rank,SM=page[2],provider_ref=record['provider_ref'],global_word_start=start,words=len(addresses),page=list(page),lane_start=lane,bytes=len(addresses)*4)
        if page[0]=='RF':row.update(RF_slot=page[3],physical_mirrors=2,accepted_mirror_ACK_required=True,active_lane_mask_hex=hex(((1<<len(addresses))-1)<<lane),old_tail_bytes=512-len(addresses)*4,physical_ACK_observed=False)
        else:row.update(byte_address=page[3]+4*lane,sector32_count=(lane*4%32+len(addresses)*4+31)//32,decoded_visibility_observed=False)
        result.append(row)
    require(sum(x['words']for x in result)==count,'exact active shape coverage')
    return dict(version=version,shape=shape,active_words=count,spans=result)

def verify_old_origin(origin,capture,payload):
    if origin is None or capture is None:return dict(status='UNKNOWN_MISSING_ACTUAL_OLD_SECTOR_ORIGIN',physical_credit=False)
    require(type(payload)is bytes and len(payload)==32,'actual complete32B old payload')
    require(origin['event']in ('allocation_init_visible','backend_refill_capture'),'positive initialization/refill origin')
    for e in (origin,capture):
        require(e['valid']is True and e['ready']is True,'accepted source backend event')
        require(type(e['sequence'])is int and e['sequence']>=0,'nonnegative ordered event')
        require(type(e['generation'])is int and 0<e['generation']<2**64,'exact generation')
        require(type(e['rank'])is int and e['rank']in (0,1),'exact rank')
        require(type(e['address'])is int and e['address']%32==0 and 0<=e['address']<2**34,'exact aligned32B address')
        require(e['full_sector_valid']is True,'all32 old bytes valid')
        require(e['payload_sha256']==hashlib.sha256(payload).hexdigest(),'actual old payload identity')
        require(len(e['backend_source_sha256'])==64 and all(c in '0123456789abcdef'for c in e['backend_source_sha256']),'backend source identity')
    require(capture['event']=='old_sector_capture','actual capture event')
    require(all(origin[k]==capture[k]for k in ('generation','rank','address','backend_source_sha256')),'same origin address/generation/backend')
    require(capture['origin_sequence']==origin['sequence']<=capture['sequence'],'causal retained origin; no stale replacement')
    require(origin['mask']==0xffffffff,'full-sector initialization/refill mask')
    return dict(status='PASS_EXPLICIT_OLD_ORIGIN_PAYLOAD_LINK',physical_credit=False,scope='input receipts only; backend event provenance and installed hardware require independent binding')

def prepare():
    import h4_hbm_qwen_observed_kv_cache as endpoint
    directory=endpoint.compile_directory();native=json.loads(gzip.decompress(endpoint.inputs()['Qwen_tiled.json.gz']))
    source=(ROOT/'tools/h3_qwen_bounded_native.py').read_text()
    require(hashlib.sha256(source.encode()).hexdigest()=='282e57ab97f2dcdd0205b6f4e11ec189b669e3cc48548fab5f6d3c373d63c32b','exact admitted native issuer source')
    groups=[];mapping=source_mapper(native,source)
    for g in directory['groups']:
        versions={s['producer_version']for s in g['sectors']}|{s['decoded_read_version']for s in g['sectors']}
        consumer_ops=[o for o in native['operations']if o['pc']in [e['pc']for e in g['source_events']if e['event']=='consumer_done']]
        for o in consumer_ops:versions.update(o['reads']+o['writes'])
        groups.append(dict(key=g['key'],active_operands=[spans(native,source,v,g['die'],0,mapping=mapping)for v in sorted(versions)],old_origin_status=verify_old_origin(None,None,b'')))
    return dict(schema='QWEN_SOURCE_EXACT_ACTIVE_ISSUER_R1',bounded_source_sha256=hashlib.sha256(source.encode()).hexdigest(),endpoint_source_sha256=hashlib.sha256(Path(endpoint.__file__).read_bytes()).hexdigest(),directory_sha256=hashlib.sha256((BASE/'directory.json.gz').read_bytes()).hexdigest(),groups=groups,model=dict(position=0,groups=72,additional_MACs=0,additional_ports=0,physical_cycles=None,per_port_bytes_cycle=None,boundary_bits_cycle=None,area=None,hardware_build_ready=False),scope='source-exact shape/window/home plan only; no accepted physical transactions',production_consumers_observed=False,old_sector_origins_observed=False,physical_credit=False)

if __name__=='__main__':print(json.dumps(prepare(),indent=2))
