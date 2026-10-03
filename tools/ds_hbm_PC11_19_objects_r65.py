"""Source-only retained output objects and publication workspaces through PC19.
Complements Peirce's committed sector/graph components. No provider constructor,
checkpoint payload, arithmetic callback, numerical execution or release credit.
"""
import json,math,sys,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/ds_hbm_PC11_19_objects_r65_20261003'
DT={'F32':np.dtype('<f4'),'U32':np.dtype('<u4'),'I64':np.dtype('<i8')}


def template_outputs(template):
    types={};shapes={}
    for node in template['code']:
        op=node['op'];a=[types[k] for k in node['src']];attrs=node['attrs']
        if op in ('LOAD','CONST'):dtype=DT[attrs['dtype']]
        elif op in ('IOTA','F2I'):dtype=DT['I64']
        elif op in ('BITCAST_F','I2F','FADD','FMUL','DIV','SQRT','LDEXP'):dtype=DT['F32']
        elif op=='BITCAST_U' or op.startswith('FCMP'):dtype=DT['U32']
        elif op in ('SHR','SHL','AND','OR','XOR','IADD','ISUB','IMUL','IMOD'):
            dtype=DT['I64'] if DT['I64'] in a else DT['U32']
        elif op in ('FMAX','FMIN','CONCAT'):dtype=np.result_type(*a)
        elif op=='SELECT':dtype=np.result_type(*a[1:])
        elif op in ('RESHAPE','SLICE','TRANSPOSE','BROADCAST','TAKE','SCATTER','ASSERT','PACKET_COMMIT'):dtype=a[0]
        else:raise ValueError('unpriced native dtype operation: '+op)
        types[node['dst']]=dtype;shapes[node['dst']]=node['shape']
    return {name:dict(dtype=str(types[key]),shape=shapes[key],
        bytes=math.prod(shapes[key])*types[key].itemsize) for name,key in template['outputs'].items()}


def output_rows(native,homes,stop=19):
    layouts={};rows=[];faults=[]
    for op in native['instructions'][:stop+1]:
        for owner in op['rank_bindings']:
            if owner.get('empty_owned_extent'):continue
            rank=owner['rank']
            for write in op['writes']:
                if owner.get('buffer_programs'):
                    matches=[b for b in owner['buffer_programs'] if b['write_version']==write['version']]
                    if not matches:continue
                    if len(matches)!=1:raise ValueError('ambiguous source buffer owner')
                    tid=matches[0]['template']
                else:tid=owner['template']
                if tid not in layouts:layouts[tid]=template_outputs(native['templates'][tid])
                result=write['native_result_binding']['result'];value=layouts[tid][result]
                indices=[i for i in write['home_indices'] if rank in homes[i]['rank_group']]
                physical=sum(homes[i]['word_count']*4 for i in indices)
                row=dict(PC=op['pc'],rank=rank,version=write['version'],result=result,template=tid,
                    **value,physical_home_bytes=physical,home_indices=indices,
                    cache_release_credit_bytes=0)
                if physical!=value['bytes']:
                    faults.append(dict(row,reason='typed native output bytes differ from declared U32 home words'))
                rows.append(row)
    return rows,faults


def object_model(rows):
    payload=sum(r['bytes'] for r in rows)
    headers=keys=locations=0
    for row in rows:
        rank=len(row['shape']);header=sys.getsizeof(np.empty((0,)*max(1,rank),dtype=np.uint8))
        # empty_like backing + dtype view + reshaped cache: no alias payload credit
        headers+=3*header
        key=(row['version'],row['rank'])
        keys+=sys.getsizeof({key:None})+sys.getsizeof(key)+sys.getsizeof(row['version'])+sys.getsizeof(row['rank'])
        n=len(row['home_indices'])
        locations+=sys.getsizeof(dict(indices=None,shape=None,dtype=None,pc=None))
        locations+=sys.getsizeof([])+n*(8+sys.getsizeof((1<<64)-1))
        locations+=sys.getsizeof(())+rank*(8+sys.getsizeof((1<<64)-1))+sys.getsizeof(np.dtype(row['dtype']))
    max_bytes=max(r['bytes'] for r in rows);max_words=(max_bytes+3)//4
    # Literal r30 publish: idx, block, chosen (int64), uint32 payload,
    # temporary predicates, covered Python integers/set, and restored raw words.
    scatter=max_words*(3*8+4+1+sys.getsizeof((1<<64)-1)+sys.getsizeof({0})+4)
    cache=payload+headers+keys+locations
    return dict(produced_output_count=len(rows),produced_payload_bytes_no_release_credit=payload,
        cached_ndarray_headers_bytes=headers,published_dictionary_and_key_bytes=keys,
        retained_location_metadata_bytes=locations,one_producer_cache_object_upper_bytes=cache,
        old_and_cold_cache_object_upper_bytes=2*cache,
        largest_single_publication_bytes=max_bytes,publication_scatter_and_readback_workspace_upper_bytes=scatter,
        original_Machine_output_and_publication_input_copy_upper_bytes=payload,
        all_cache_payloads_retained_through19=True,physical_RF_mirror_data_not_doublecounted_as_cache=True,
        numpy_unknown_allocator_arena_credit=0)


def generate():
    from ds_hbm_pc10_projection_r46 import source_inputs
    native,homes,manifest=source_inputs()
    rows,faults=output_rows(native,homes)
    component=json.loads((OUT/'Peirce_component_snapshot.json').read_bytes())
    objects=object_model(rows)
    inputs={str(Path(v['path']).resolve() if Path(v['path']).is_absolute() else (ROOT/v['path']).resolve())
        for v in manifest['initial_versions']}
    inputs.update(str(Path(v['path']).resolve() if Path(v['path']).is_absolute() else (ROOT/v['path']).resolve())
        for v in manifest['view_bindings'].values() if 'path' in v)
    mappings=sum(Path(p).stat().st_size for p in inputs)
    scope=[r for r in rows if 11<=r['PC']<=19]
    model=dict(schema='DS_PC11_19_RETAINED_OUTPUT_OBJECT_COMPONENT_R65',
        scope=[11,19],native_PC_count=len(native['instructions']),
        retained_output_objects=objects,new_scope_output_count=len(scope),
        new_scope_typed_payload_bytes=sum(r['bytes'] for r in scope),
        immutable_initial_and_auxiliary_mapped_file_bytes=mappings,
        immutable_checkpoint_LOAD_stream_component_bytes=component['PC11_19_component']['immutable_LOAD_bytes'],
        inherited_sector_graph_components=component['PC11_19_component'],
        output_rows=rows,typed_home_faults=faults,
        status='FAIL_TYPED_OUTPUT_HOME_JOIN' if faults else 'OBJECT_COMPONENT_SIZED_WHOLE_RAM_STILL_PENDING',
        no_arrays_or_sectors_instantiated=True,no_payload_read=True,
        whole_resource_admission=False,numerical_GO=False,
        remaining=['exact whole constructor/identity copies','V3 closure/serialization and restored sector dictionary lifecycle',
          'selected checkpoint header/codec temporaries','whole provider/checkpoint journal and witness record sizing',
          'explicit actual checkpoint source-class transition'],
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
          ['tools/ds_hbm_PC11_19_objects_r65.py','tools/h3_deepseek_complete_native.py',
           'tools/h3_ds_checkpoint_provider_r30.py','tools/h3_ds_checkpoint_provider_r33.py',
           'tools/ds_hbm_pc10_projection_r46.py','results/uarch/ds_hbm_PC11_19_objects_r65_20261003/Peirce_component_snapshot.json']})
    (OUT/'model.json').write_text(json.dumps(model,sort_keys=True,indent=2)+'\n')
    print(json.dumps({k:model[k] for k in ['status','new_scope_output_count','new_scope_typed_payload_bytes']},indent=2))
    print('typed_home_faults',len(faults));print('cache_objects_upper_bytes',objects['old_and_cold_cache_object_upper_bytes'])

if __name__=='__main__':generate()
