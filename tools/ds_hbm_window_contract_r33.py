"""Explicit pretrimmed/full-ring window representation reconciliation.
Original lowering and numerical kernels remain immutable. New lowered input
shape and slice metadata are emitted and hashed; no invented leading row.
"""
import copy
import hashlib
import json

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':')).encode()

def row_contract(position, representation):
    if type(position) is not int or position < 0:
        raise ValueError('nonnegative source position')
    if representation not in ('pretrimmed127','full_ring128'):
        raise ValueError('explicit source representation required')
    old = min(position,127 if representation=='pretrimmed127' else 128)
    drop = max(0,old-127)
    return dict(position=position,representation=representation,input_rows=old,
                input_positions=list(range(position-old,position)),drop_rows=drop,
                output_positions=list(range(max(0,position-127),position+1)),
                output_rows=min(position+1,128),width=512,row_bytes=2048,
                consumed_old_rows=old-drop,new_row_position=position)

def lower_template(template, position, representation):
    c=row_contract(position,representation);t=copy.deepcopy(template)
    load=next(n for n in t['code'] if n['op']=='LOAD' and n['attrs'].get('name')=='window')
    slices=[n for n in t['code'] if n['op']=='SLICE' and n['src']==[load['dst']]]
    if len(slices)!=1 or slices[0]['attrs']!=dict(axis=0,start=1,step=1,stop=None):
        raise ValueError('source window LOAD/drop graph changed')
    sl=slices[0];concat=next(n for n in t['code'] if n['op']=='CONCAT' and sl['dst'] in n['src'])
    commit=next(n for n in t['code'] if n['op']=='PACKET_COMMIT' and n['src']==[concat['dst']])
    load['shape']=[c['input_rows'],512];t['providers']['window']['shape']=load['shape'][:]
    sl['attrs']['start']=c['drop_rows'];sl['shape']=[c['consumed_old_rows'],512]
    concat['shape']=[c['output_rows'],512];commit['shape']=concat['shape'][:]
    t['shape_parameters']['window']=c['input_rows']
    return t,c

def lower_full_native(native, position, representation='pretrimmed127'):
    if position < 127:
        raise ValueError('full emitted long-position attention has128rows; early positions need separately sized downstream templates')
    out=dict(native);out['templates']=dict(native['templates']);out['instructions']=[];remap={};witness=[]
    for op in native['instructions']:
        if op['family']!='q_norm_kv_row':out['instructions'].append(op);continue
        n=copy.deepcopy(op)
        for key in op['provider_bindings']:
            if key not in remap:
                template,contract=lower_template(native['templates'][key],position,representation)
                new=hashlib.sha256(canonical(template)).hexdigest();remap[key]=new;out['templates'][new]=template
            new=remap[key]
            n['provider_bindings'][new]=n['provider_bindings'].pop(key)
            b=n['provider_bindings'][new]['window']
            b['view']='explicit '+representation+' old window, '+str(out['templates'][new]['providers']['window']['shape'])
            b['window_representation']=representation;b['window_position']=position
            for r in n['rank_bindings']:
                if r.get('template')==key:r['template']=new
            witness.append(dict(PC=op['pc'],old_template=key,new_template=new,input_version=b['version'],output_version=next(w['version'] for w in op['writes'] if w['native_result_binding']['result']=='window')))
        out['instructions'].append(n)
    return out,witness

def initial_home_directory(original_native,produced_directory,position,representation):
    c=row_contract(position,representation);length=c['input_rows']*2048;reservation=(length+511)//512*512
    cursors={int(r):v for r,v in produced_directory['per_rank_reserved_bytes'].items()};rows=[]
    for op in original_native['instructions']:
        if op['family']!='q_norm_kv_row':continue
        binding=next(iter(op['provider_bindings'].values()))['window']
        for owned in op['rank_bindings']:
            rank=owned['rank'];off=cursors[rank]
            if off+reservation>33554432:raise BufferError('initial plus produced state exceeds charged32MiB/rank')
            rows.append(dict(version=binding['version'],rank=rank,generation=1,PC_first_consumer=op['pc'],
                base=33554432+off,bytes=length,reservation_bytes=reservation,AW=27,
                shape=[c['input_rows'],512],dtype='F32',representation=representation,
                logical_positions=c['input_positions'],row_stride_bytes=2048,
                source_payload_required=True,hardware_translation_bound=False))
            cursors[rank]+=reservation
    return dict(rows=rows,per_rank_total_reserved_bytes=cursors,capacity_per_rank=33554432,
                capacity_all96_ranks=3221225472,source_payloads_supplied=False)
