"""Comparison fragments for six BF16 compressor bindings, no arithmetic rerun.

Streams the reviewed PC/rank/writer metadata and reads only the three captured
1024-element original mv results. PC115 reuses its historical references;
PC443/776 get additive contracts. Never a provider input or constructor.
"""
import argparse,gzip,hashlib,json
from pathlib import Path
import numpy as np
from h4_c0_ds_selected_bf16_payload_witness import sha,canonical,ENROLLMENT_SHA,REVISION


def records(path):
    decoder=json.JSONDecoder()
    with gzip.open(path,'rt') as f:
        if f.read(1)!='[':raise ValueError('reviewed record array')
        buf=''
        while True:
            buf=buf.lstrip()
            if buf.startswith(','):buf=buf[1:].lstrip()
            if buf.startswith(']'):return
            try:value,end=decoder.raw_decode(buf)
            except json.JSONDecodeError:
                chunk=f.read(32768)
                if not chunk:raise ValueError('incomplete reviewed metadata record')
                buf+=chunk;continue
            yield value;buf=buf[end:]


def emit(bindings,bindings_sha256,enrollment,manifest,capture_root,existing_PC115,out):
    if sha(bindings)!=bindings_sha256 or sha(enrollment)!=ENROLLMENT_SHA:raise ValueError('reviewed binding/enrollment pins')
    source=json.loads(Path(manifest).read_bytes() if Path(manifest).suffix!='.gz' else gzip.decompress(Path(manifest).read_bytes()))
    if source['checkpoint_revision']!=REVISION:raise ValueError('same actual released checkpoint')
    chosen={r['PC']:r for r in records(bindings) if r['PC'] in (115,443,776)}
    if set(chosen)!={115,443,776}:raise ValueError('all six compressor bindings required')
    existing=json.loads(Path(existing_PC115).read_text());old={(e['version'],e['rank']):e for e in existing['expectations'] if e['PC']==115}
    if len(old)!=96:raise ValueError('complete independently sealed existing PC115 fields')
    out=Path(out);out.mkdir(parents=True,exist_ok=False);expectations=[];pins={str(Path(p).resolve()):sha(p) for p in [__file__,bindings,enrollment,manifest,existing_PC115]};enrolled=[]
    for pc,layer in [(115,2),(443,8),(776,14)]:
        rec=chosen[pc]
        if rec['family']!='mv' or rec['source_op']['w']!=[f'layers.{layer}.attn.compressor.{s}.weight' for s in ('wkv','wgate')]:raise ValueError('exact ordered composite source')
        root=Path(capture_root)/f'layer_{layer:02d}';seal=json.loads((root/'sealed.json').read_text())
        if sha(root/'observations.jsonl')!=seal['observations_sha256']:raise ValueError('original immutable observation seal')
        rows=[json.loads(l) for l in (root/'observations.jsonl').read_text().splitlines()];calls={r['call_id']:r for r in rows if 'call_id' in r}
        mv=[r for r in calls.values() if r['function']=='mv' and calls.get(r['parent_call_id'],{}).get('function')=='Model.compressor']
        if len(mv)!=1:raise ValueError('single original ordered full composite mv')
        desc=mv[0]['result'];blob=root/desc['path']
        if desc['shape']!=[1024] or desc['dtype']!='<f4' or seal['blob_files'].get(blob.name)!=desc['file_sha256'] or sha(blob)!=desc['file_sha256']:raise ValueError('small original composite output pin')
        full=np.load(blob,allow_pickle=False)
        if full.shape!=(1024,) or full.dtype.str!='<f4' or hashlib.sha256(full.tobytes()).hexdigest()!=desc['payload_sha256']:raise ValueError('original captured result bytes')
        for path in [root/'sealed.json',root/'observations.jsonl',blob]:pins[str(path.resolve())]=sha(path)
        for rb in rec['ranks']:
            lo,hi=rb['row_interval'];value=np.ascontiguousarray(full[lo:hi]);digest=hashlib.sha256(value.tobytes()).hexdigest()
            if [lo,hi]!=[1024*rb['rank']//96,1024*(rb['rank']+1)//96] or len(rb['writers'])!=1:raise ValueError('exact caller/writer ownership')
            writer=rb['writers'][0]
            if writer['fields']['data']['shape']!=[hi-lo]:raise ValueError('exact output template shape')
            if pc==115:
                prior=old[(writer['version'],rb['rank'])]
                if prior['payload_sha256']!=digest or prior['shape']!=[hi-lo] or prior['dtype']!='<f4':raise ValueError('existing PC115 comparison bytes changed')
            else:
                name=digest+'.npy';path=out/name
                if not path.exists():np.save(path,value,allow_pickle=False)
                expectations.append(dict(PC=pc,version=writer['version'],rank=rb['rank'],generation=source['generation'],field='data',shape=[hi-lo],dtype='<f4',path=name,file_sha256=sha(path),payload_sha256=digest,provenance=dict(independent_golden=True,runtime_operand_source=False,original_function='mv',original_parent='Model.compressor',layer_capture_seal_sha256=sha(root/'sealed.json'))))
            enrolled.append(dict(PC=pc,rank=rb['rank'],template=rb['template_sha256'],version=writer['version'],output_payload_sha256=digest,existing_reference_reused=pc==115))
    if len(expectations)!=192 or len(enrolled)!=288:raise ValueError('complete composite output enrollment')
    contract=dict(status='INDEPENDENT_COMPOSITE_PC443_776_CAPTURED_REFERENCE_NOT_YET_COMPARED',native_program_sha256=source['native_program_sha256'],input_manifest_sha256=sha(manifest),checkpoint_revision=REVISION,reference_source_sha256=pins,expectations=expectations,PCs=[443,776],golden_stimuli_in_executor=False,arithmetic_reexecuted=False,full_token_qualified=False,hardware_qualified=False)
    (out/'expected_outputs.json').write_text(json.dumps(contract,sort_keys=True,indent=2)+'\n')
    (out/'all288_output_enrollment.json').write_text(json.dumps(enrolled,sort_keys=True,indent=2)+'\n')
    (out/'record.json').write_text(json.dumps(dict(status='PASS_CAPTURED_REFERENCE_COMPOSITE_OUTPUT_ENROLLMENT_NOT_DUT_COMPARISON',new_fields=192,reused_PC115_fields=96,array_source_payload_bytes=12288,native_arithmetic_reexecuted=False,provider_constructed=False,actual_outputs_compared=0,large_local_array_loads=False),sort_keys=True,indent=2)+'\n')
    (out/'artifact_manifest.json').write_text(json.dumps(dict(artifacts={p.name:sha(p) for p in out.iterdir()},source_pins=pins),sort_keys=True,indent=2)+'\n')
    return dict(new_fields=192,reused_PC115_fields=96,expected_outputs_sha256=sha(out/'expected_outputs.json'))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('bindings','enrollment','manifest','capture_root','existing_PC115','out'):p.add_argument('--'+name.replace('_','-'),type=Path,required=True)
    p.add_argument('--bindings-sha256',required=True)
    print(json.dumps(emit(**vars(p.parse_args())),sort_keys=True))
