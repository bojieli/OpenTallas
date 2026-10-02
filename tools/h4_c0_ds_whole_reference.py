"""Comparison-only whole-program field store and retained independent golden reuse.

No native Machine, provider execution, numerical rerun, or runtime payload API.
Unimplemented independent intermediate observers remain named refusals.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import io
import json
import math
import subprocess
from pathlib import Path
import numpy as np
from h4_c0_ds_fullgraph_inventory import NATIVE, sha, load

REFERENCE='ea7256eb1ac7a7895441f5a31dfb8ce5d05224d7c860e21c4b9c6ce1e6da8e56'
ARCHIVE='1c471976bbec0868161e80cef3c89c74c6861a3998693d9fe5d63a08a3e5836c'
RECORD='1d0a8fa599182f2cc1b1e24c7d57f82502e37e714301ebe2ab7c553c8d978824'
STATE='b59a99c8294625778d28306924067d5bbf706979068579280d6ee40cb24e6782'
MANIFEST='1e0c77e10c287d570d2062620514ca72ea44747e2051891bfc7d439c555e8424'
DTYPE={'F32':'<f4','U32':'<u4','I64':'<i8'}


def payload(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def template_fields(t):
    shapes={i['dst']:i['shape'] for i in t['code'] if 'dst' in i}
    types={}
    for i in t['code']:
        if 'dst' not in i:continue
        op=i['op']; explicit=i.get('attrs',{}).get('dtype')
        if explicit in DTYPE:dt=explicit
        elif op in ('BITCAST_U',):dt='U32'
        elif op in ('BITCAST_F',):dt='F32'
        elif op.startswith('FCMP'):dt='U32'
        elif op in ('F2I','IOTA'):dt='I64'
        elif op in ('FADD','FMUL','DIV','SQRT','FMAX','FMIN','I2F','LDEXP'):dt='F32'
        elif op=='SELECT':dt=types[i['src'][1]]
        elif op in ('SHR','SHL','AND','OR','XOR','IADD','ISUB','IMUL','IMOD'):
            dt='I64' if any(types[s]=='I64' for s in i['src']) else 'U32'
        elif op in ('RESHAPE','SLICE','TRANSPOSE','CONCAT','BROADCAST','TAKE','SCATTER','PACKET_COMMIT','ASSERT'):
            dt=types[i['src'][0]]
        else:raise ValueError('undeclared output dtype rule '+op)
        types[i['dst']]=dt
    return {name:dict(shape=shapes[v],dtype=DTYPE[types[v]]) for name,v in t['outputs'].items()}


def slots(native):
    """Source field identities and declared extents; no observed bytes inferred."""
    rows=[];field_cache={k:template_fields(t) for k,t in native['templates'].items()}
    for o in native['instructions']:
        for r in o['rank_bindings']:
            if r.get('empty_owned_extent'):continue
            fields=field_cache[r['template']]
            for w in o['writes']:
                result=w['native_result_binding']['result']
                for field in ['data']+o.get('compound_output_fields',{}).get(result,[]):
                    spec=fields[result if field=='data' else field]
                    shape=list(spec['shape'])
                    if field=='data':
                        elems=w['element_counts'][r['rank']]
                        if math.prod(shape)!=elems:shape=[elems]
                    rows.append(dict(PC=o['pc'],family=o['family'],layer=o['source_op'].get('layer'),
                        version=w['version'],rank=r['rank'],field=field,shape=shape,dtype=spec['dtype'],
                        bytes=math.prod(shape)*np.dtype(spec['dtype']).itemsize,
                        source_result=result,source_writer_binding=w['native_result_binding'],
                        source_template_sha256=r['template']))
    return rows


class ComparisonStore:
    """Content dedup across rank publications; never provides execution operands."""
    def __init__(self,out,required):
        self.out=Path(out);self.out.mkdir(parents=True,exist_ok=False)
        self.required={(s['PC'],s['version'],s['rank'],s['field']):s for s in required}
        self.observed={}
    def append(self,key,array,provenance):
        if key not in self.required or key in self.observed:raise ValueError('unknown/duplicate reference identity')
        s=self.required[key];a=np.ascontiguousarray(array)
        if list(a.shape)!=s['shape'] or a.dtype.str!=s['dtype']:raise ValueError('exact declared source shape/dtype')
        if not provenance.get('independent_golden') or provenance.get('runtime_operand_source'):raise ValueError('independent comparison-only provenance')
        digest=payload(a);p=self.out/(digest+'.npy')
        if not p.exists():np.save(p,a,allow_pickle=False)
        self.observed[key]=dict(PC=key[0],version=key[1],rank=key[2],field=key[3],generation=1,
            shape=s['shape'],dtype=s['dtype'],payload_sha256=digest,file_sha256=sha(p),path=p.name,provenance=provenance)
    def contract(self):
        return dict(native_program_sha256=NATIVE,expectations=list(self.observed.values()),
            status='SCOPED_INDEPENDENT_RETAINED_REFERENCE_NOT_EXECUTION',
            golden_stimuli_in_executor=False,hardware_qualified=False,full_token_qualified=False)


def verify_retained(reference,record,archive,manifest,source_root):
    if (sha(reference),sha(record),sha(archive))!=(REFERENCE,RECORD,ARCHIVE):raise ValueError('reviewable immutable retained golden inputs')
    if sha(manifest)!=MANIFEST:raise ValueError('exact admitted immutable source manifest')
    ref=load(reference);rec=load(record);m=load(manifest)
    recipe=m['checkpoint_initial_embedding']
    if sha(recipe['token_history_source'])!=REFERENCE or sha(recipe['initializer_source'])!=recipe['initializer_sha256']:
        raise ValueError('actual checkpoint entering state source closure')
    if m['generation']!=1:raise ValueError('exact retained version generation')
    if ref['checkpoint']['revision']!=m['checkpoint_revision'] or ref['checkpoint']['index_sha256']!=m['checkpoint_index_sha256']:
        raise ValueError('released checkpoint mismatch')
    if ref['state']['state_sha256']!=STATE or ref['seed']!=20260930 or ref['arith']!='chunk8' or ref['fuse']!=[]:
        raise ValueError('entering state/arithmetic mismatch')
    if ref['token_history']!=[19673,48197,13977,74560,112671,119148,47073,16754]:raise ValueError('actual entering history')
    for name,pin in rec['golden'].items():
        if sha(Path(source_root)/name)!=pin['sha256'] or ref['source_sha256'][name]!=pin['sha256']:
            raise ValueError('independent arithmetic source changed')
    if rec['input_sha256']!=ref['layers'][0]['input_sha256'] or rec['output_sha256']!=ref['layers'][0]['output_sha256']:
        raise ValueError('retained layer lineage')
    with np.load(archive,allow_pickle=False) as f:a={k:f[k].copy() for k in f.files}
    for name,digest in rec['trace_sha256'].items():
        if name not in a or payload(a[name])!=digest:raise ValueError('retained independent trace bytes')
    if payload(a['h_in'])!='05a98a7bbdd2902cca51139c839c039e49000f9ecc3970af06a7458cca55a931':raise ValueError('actual input RF seed image')
    if not np.array_equal(a['pre_in'],np.array([1,0,0,0],dtype='<f4')):raise ValueError('entering pre state')
    if payload(a['h_out'])!=rec['trace_sha256']['block0'] or payload(a['pre_out'])!=rec['trace_sha256']['pre0']:
        raise ValueError('complete retained layer state bytes')
    return a,ref,rec


def build(native_path,manifest,reference,record,archive,source_root,out):
    if sha(native_path)!=NATIVE:raise ValueError('canonical corrected source required')
    n=load(native_path);required=slots(n)
    if len(required)!=292912 or sum(s['PC']>=11 for s in required)!=291248:raise ValueError('complete canonical witness census')
    a,ref,rec=verify_retained(reference,record,archive,manifest,source_root)
    store=ComparisonStore(out,required)
    # Preserve the actual historical producer, never silently repin to a newer tool.
    historical='tools/rtl_v41_fullshape_layer_campaign.py'
    old=subprocess.check_output(['git','show',ref['source_commit']+':'+historical],cwd=source_root)
    if hashlib.sha256(old).hexdigest()!=ref['source_sha256'][historical]:raise ValueError('historical independent producer origin')
    origins=Path(out)/'retained_origins';origins.mkdir()
    (origins/'golden_campaign.py.snapshot').write_bytes(old)
    for path in (reference,record,archive):
        (origins/Path(path).name).write_bytes(Path(path).read_bytes())
    provenance=dict(independent_golden=True,runtime_operand_source=False,reference_sha256=REFERENCE,
        archive_sha256=ARCHIVE,record_sha256=RECORD,producer_source_commit=ref['source_commit'],
        released_checkpoint_revision=ref['checkpoint']['revision'],entering_state_sha256=STATE,
        arithmetic='chunk8',scope='retained released-checkpoint layer0 golden trace; no new numerical execution')
    for s in required:
        pc=s['PC']
        if pc not in (50,51,52):continue
        o=n['instructions'][pc]
        if o['source_op'].get('layer')!=0:raise ValueError('exact layer0 mapping')
        if pc==50:
            lo,hi=o['writes'][0]['producer_extent'][s['rank']];v=a['L0.ffn'][lo:hi]
        elif pc==51:v=a['L0.ffn']
        elif s['source_result']=='h':v=a['h_out']
        elif s['source_result']=='pre':v=a['pre_out']
        else:raise ValueError('unknown retained stage binding')
        store.append((pc,s['version'],s['rank'],s['field']),v,provenance)
    source_paths=[__file__,reference,record,archive,manifest,native_path,
        Path(source_root)/'tools/hdc_golden_v41.py',Path(source_root)/'tools/hdc_golden.py',
        origins/'golden_campaign.py.snapshot']
    contract=store.contract();contract.update(reference_source_sha256={str(Path(p).resolve()):sha(p) for p in source_paths},
        input_manifest_sha256=sha(manifest),PCs=[50,51,52],output_count=len(store.observed),
        comparison_rule='complete field source identity/shape/dtype/bytes; comparison payloads never provider inputs')
    out=Path(out);(out/'expected_outputs.json').write_text(json.dumps(contract,sort_keys=True,indent=2)+'\n')
    # Projection is uncompressed published payload with all rank copies. It is not a cap.
    census=Counter();family_bytes=Counter()
    for s in required:
        census[s['family']]+=1;family_bytes[s['family']]+=s['bytes']
    summary=dict(status='SINGLE_ORDERED_PRODUCER_PLAN_WITH_SCOPED_REUSE',required_fields=len(required),
        required_PC11_onward=291248,existing_PC11_19=1440,new_retained_fields=len(store.observed),
        remaining_PC11_onward=291248-1440-len(store.observed),families=dict(census),
        all_rank_uncompressed_payload_bytes=sum(s['bytes'] for s in required),family_payload_bytes=dict(family_bytes),
        projection_scope='declared output shape/dtype; metadata, checkpoint, entering state, temporaries and runtime journals additional',
        actual_reused_unique_files=len(list(out.glob('*.npy'))),actual_reused_file_bytes=sum(p.stat().st_size for p in out.glob('*.npy')),
        whole_program_reference_producer=dict(executions=1,sequence='source-ordered 40 golden layers then golden head; preserve original arithmetic/reduction order',
            backend='ComparisonStore content-addressed comparison-only field sink',
            already_available='released checkpoint lazy decoding and unchanged independent Model.layer/head',
            missing='independent intermediate observers for every linear/HC/expert/index/compressor/compound/group field and source-owned rank fragments',
            starting_state='load/validate actual immutable source images and contracts; seed recipe alone is not a substitute',
            final_reference_digest=ref['logits_sha256'],final_reference_payload_available=False),
        retained_full_layer_metadata=40,retained_complete_payload_layers=[0],
        missing_reference_reason='full seed20260930 archive retired except retained shards; full-model digests are not byte witnesses',
        resource_projection=dict(runtime_seconds=None,peak_memory_bytes=None,
            reason='requires source phase and lazy weight/state inventory with Dewey; no fake bound from layer0 elapsed time',
            arbitrary_resource_caps=False,production_journal_bytes=None),
        no_numeric_reexecution=True,whole_program_reference_ready=False,hardware_qualified=False,full_token_qualified=False)
    summary['zero_publication_refusals']=[dict(PC=o['pc'],family=o['family'],
        required='independent released-checkpoint selected expert descriptor identity; no zero-output automatic PASS')
        for o in n['instructions'] if not o['writes']]
    header_bytes=0
    for s in required:
        b=io.BytesIO()
        np.lib.format.write_array_header_1_0(b,dict(descr=s['dtype'],fortran_order=False,shape=tuple(s['shape'])))
        header_bytes+=b.tell()
    summary['storage_projection']=dict(
        field_payload_bytes=sum(s['bytes'] for s in required),all_field_NPY_header_bytes=header_bytes,
        all_field_NPY_bytes_without_dedup=sum(s['bytes'] for s in required)+header_bytes,
        source_identity_catalog_json_bytes=len(json.dumps(required,sort_keys=True,separators=(',',':')).encode()),
        dedup_credit_before_observation=0,interpretation='one file per field conservative projection; actual sink content-deduplicates byte-identical fields',
        exclusions=['checkpoint source files','entering history images','producer temporaries','additional reference provenance','actual provider lifecycle journal'],
        admission_capacity_is_not_runtime_cap=True)
    m=load(manifest)
    state_images=[dict(layer=i['layer'],path=i['path'],shape=i['shape'],
        file_sha256=i['file_sha256'],payload_sha256=i['payload_sha256'],
        logical_bytes=math.prod(i['shape'])*4) for i in m['history_images']]
    summary['resource_projection'].update(entering_history_images=state_images,
        entering_history_payload_bytes=sum(i['logical_bytes'] for i in state_images),
        actual_initial_state_scope=m['source_state_scope'],
        memory_lifetime_policy='one source-ordered layer, lazy released weights evicted after layer; entering history read-only mapped, expected fields flushed immediately',
        reference_runtime_not_291248_invocations=True)
    phases=[]
    for layer in range(40):
        pcs=[o for o in n['instructions'] if o['source_op'].get('layer')==layer]
        fs=[s for s in required if s['layer']==layer]
        phases.append(dict(layer=layer,PCs=[o['pc'] for o in pcs],families=sorted({o['family'] for o in pcs}),
            published_fields=len(fs),unduplicated_rank_payload_bytes=sum(s['bytes'] for s in fs),
            entering_history_image_bytes=sum(i['logical_bytes'] for i in state_images if i['layer']==layer),
            original_golden_expert_ids_for_reference_cost_only=ref['layers'][layer]['experts'],
            observation_rule='independent original Model.layer operations; each declared source fragment must have a specific intermediate observer; missing observer refuses completeness'))
    summary['producer_phases']=phases
    for name,data in [('whole_program_fields.json.gz',required)]:
        (out/name).write_bytes(gzip.compress(json.dumps(data,sort_keys=True,separators=(',',':')).encode(),mtime=0))
    (out/'summary.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n')
    (out/'artifact_manifest.json').write_text(json.dumps(dict(artifacts={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()},source_pins=contract['reference_source_sha256']),sort_keys=True,indent=2)+'\n')
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('native','manifest','reference','record','archive','source_root','out'):p.add_argument('--'+k.replace('_','-'),type=Path,required=True)
    x=p.parse_args();print(json.dumps(build(x.native,x.manifest,x.reference,x.record,x.archive,x.source_root,x.out),sort_keys=True))
