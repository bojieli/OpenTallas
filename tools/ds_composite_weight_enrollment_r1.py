"""Bounded metadata-only enrollment for the six r6 composite binding gaps."""
import gzip
import hashlib
import json
from pathlib import Path
import h3_ds_composite_weight_binding_r1 as C

ROOT=C.ROOT
NATIVE='results/uarch/ds_hbm_storage_home_binding_r41_20261002/inputs/actual_native_c65.json.gz'
CATALOG='results/quality/w16_w17_checkpoint_header_catalogue_20261001/catalogue.json'
INDEX='results/quality/w16_w17_checkpoint_header_catalogue_20261001/model.safetensors.index.json'

def build():
    native=json.loads(gzip.decompress((ROOT/NATIVE).read_bytes()))
    catalog=json.loads((ROOT/CATALOG).read_bytes())
    index=json.loads((ROOT/INDEX).read_bytes())['weight_map']
    components={};operations={};paths={NATIVE,CATALOG,INDEX,
        'tools/h3_ds_composite_weight_binding_r1.py','tools/ds_composite_weight_enrollment_r1.py',
        'tools/h3_deepseek_complete_native.py','tools/deepseek_v41_deployment_quality.py',
        'tools/ds_producer_checkpoint_resume_v3.py'}
    for pc,layer in zip(C.PCS,C.LAYERS):
        op=native['instructions'][pc]
        names=[f'layers.{layer}.attn.compressor.{s}.weight' for s in ('wkv','wgate')]
        for name in names:
            filename=index[name];shard=catalog['shards'][filename]
            headerpath=str(Path(CATALOG).parent/shard['raw_header_path']);paths.add(headerpath)
            raw=(ROOT/headerpath).read_bytes()
            assert hashlib.sha256(raw).hexdigest()==shard['raw_header_sha256']
            h=json.loads(raw)[name]
            assert h['dtype']=='BF16' and h['shape']==[512,5120]
            components[name]=dict(dtype=h['dtype'],shape=h['shape'],data_offsets=h['data_offsets'],
                shard=filename,data_base=shard['data_base'],layout='safetensors_C_row_major',scale_tensor=None,
                raw_header_sha256=shard['raw_header_sha256'])
        operations[str(pc)]=dict(operation_sha256=C.digest(op),
            templates={t:C.digest(native['templates'][t]) for t in op['provider_bindings']},
            component_order=names,caller_order_sha256=C.digest(op['rank_bindings']))
    cls=C.provider_class();mro=C.source_identity(cls)
    paths.update(r['path'] for r in mro)
    record=dict(schema='DS_NATIVE_COMPOSITE_BF16_ENROLLMENT_R1',
        native_canonical_sha256=C.digest(native),native_gzip_sha256=hashlib.sha256((ROOT/NATIVE).read_bytes()).hexdigest(),
        checkpoint_revision=catalog['checkpoint_revision'],checkpoint_index_sha256=catalog['index_sha256'],
        components=components,operations=operations,provider_MRO=mro,
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(paths)},
        metadata_admission_only=True,payload_measured=False,numerical_prefix_launched=False,
        constructor_or_restore_admitted=False,hardware_admitted=False)
    plans=[]
    for pc in C.PCS:
        op=native['instructions'][pc]
        for owned in op['rank_bindings']: # preserve emitted order, never sort
            tid=owned['template'];required=op['provider_bindings'][tid]['weight']
            plans.append(C.resolve_call(native,record,'weight',required,owned,native['templates'][tid]['providers']['weight']))
    assert len(plans)==288 and sum(len(op['provider_bindings']) for op in (native['instructions'][pc] for pc in C.PCS))==6
    return record,dict(schema='DS_COMPOSITE_SELECTED_CALL_CENSUS_R1',plans=plans,
        binding_count=6,PC_count=3,actual_caller_count=len(plans),
        total_selected_checkpoint_bytes=sum(p['selected_checkpoint_bytes'] for p in plans),
        max_selected_checkpoint_bytes=max(p['selected_checkpoint_bytes'] for p in plans),
        max_output_bytes=max(p['output_bytes'] for p in plans),
        max_temporary_and_output_bound_bytes=max(p['temporary_and_output_bound_bytes'] for p in plans),
        component_row_coverage='per PC: wkv[0:512] then wgate[0:512]; full K[0:5120], no duplicate/hole',
        trained_payload_reads=0,numerical_or_constructor_execution=False,
        original_r6_gap_verdict_preserved=True)

if __name__=='__main__':
    enrollment,census=build();out=ROOT/C.OUT;out.mkdir(parents=True,exist_ok=True)
    for name,record in [('enrollment-r1.json',enrollment),('call-census-r1.json',census)]:
        path=out/name
        if path.exists():raise ValueError('preserve frozen enrollment')
        path.write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
