"""Archive exact external immutable initializer files, never production outputs.

Uses frozen Peirce presence census plus original source manifest. No numerical
array is loaded, no live journal hashed, no provider/constructor/MRO changed.
Initial data, runtime producer dependency and comparison-only roles are distinct.
"""
import argparse,ast,gzip,hashlib,json,math,shutil,struct
from collections import Counter
from pathlib import Path


def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(65536),b''):h.update(b)
    return h.hexdigest()


def load(p):
    raw=Path(p).read_bytes();return json.loads(gzip.decompress(raw) if str(p).endswith('.gz') else raw)


def ownership(name,record):
    if record.get('golden_stimuli_in_executor') is True or record.get('runtime_operand_source') is False or 'independent' in record.get('scope','').lower():
        return 'COMPARISON_ONLY_FORBIDDEN_AS_DUT_INPUT','Never load an expected numerical intermediate as source data.'
    if name=='expert_descriptor_table':return 'INITIAL_IMMUTABLE_DESCRIPTOR','Checkpoint-file offsets+filename, not physical HBM addresses. Actual route IDs/version must select matrices and satisfy descriptor acquisition.'
    if name in ('selected_codes','selected_exp','selected_row_ids'):return 'INITIAL_IMMUTABLE_ROW_RESPONSE_CANDIDATE','Released Engram row prefetch for fixed original history; actual computed row IDs must match accepted descriptor IDs before use. Presence is not actual request/response qualification.'
    if name=='open_group':return 'INITIAL_IMMUTABLE_ENTERING_STATE','Only the pinned old logical position/state. Future append/current slot must come from actual producer, never reset from this image.'
    if name in ('multipliers','offsets','primes','raw_recent_tokens','token_map','E4M3_decode','attn_scale','engram_scale','index_rope_cos','index_rope_sin','index_w_scale'):return 'INITIAL_IMMUTABLE_CONSTANT_OR_HISTORY','Original config/tokenizer/codec/fixed entering history. Do not regenerate on remote; copy exact admitted bytes.'
    return 'UNCLASSIFIED_SOURCE_REFUSAL','No filename-based guess or source substitution.'


def npy_header(path):
    with open(path,'rb') as f:
        if f.read(6)!=b'\x93NUMPY':raise ValueError('immutable NPY magic')
        version=f.read(2)
        if version==b'\x01\x00':size=struct.unpack('<H',f.read(2))[0]
        elif version in (b'\x02\x00',b'\x03\x00'):size=struct.unpack('<I',f.read(4))[0]
        else:raise ValueError('declared NPY version')
        header=ast.literal_eval(f.read(size).decode('utf-8' if version==b'\x03\x00' else 'latin1'))
        return header,f.tell()


def archive(presence,presence_sha256,manifest,manifest_sha256,out):
    if sha(presence)!=presence_sha256 or sha(manifest)!=manifest_sha256:raise ValueError('frozen census and source manifest pins')
    c=load(presence);m=load(manifest);external={p:r for p,r in c['checked_payload_paths'].items() if not r['inside_checkout']}
    if len(external)!=67 or c['external_references']!=119:raise ValueError('full external67/119 census')
    bindings={}
    for key,row in m['view_bindings'].items():
        if row.get('path') in external:bindings.setdefault(row['path'],[]).append((key,row))
    if set(bindings)!=set(external) or sum(map(len,bindings.values()))!=119:raise ValueError('exact original binding coverage')
    out=Path(out);out.mkdir(parents=True,exist_ok=False);(out/'payloads').mkdir();records=[];counts=Counter();refs=0;total=0
    for old,audit in external.items():
        source=Path(old);stamp=source.stat();digest=sha(source);header,offset=npy_header(source);items=bindings[old]
        if header['fortran_order']:raise ValueError('explicit original C-order source only')
        roles=set();receipts=[]
        for key,row in items:
            PC,template,name=key.split('/');role,gate=ownership(name,row);roles.add(role)
            if role in ('COMPARISON_ONLY_FORBIDDEN_AS_DUT_INPUT','UNCLASSIFIED_SOURCE_REFUSAL'):raise ValueError('forbidden/unclassified initializer '+key)
            if row['sha256']!=digest or row['generation']!=m['generation'] or row['checkpoint_revision']!=m['checkpoint_revision']:
                raise ValueError('exact data/generation/checkpoint identity')
            if list(header['shape'])!=row['shape'] or header['descr']!={'F32':'<f4','I64':'<i8','U32':'<u4'}[row['dtype']]:raise ValueError('original source header/codec')
            if stamp.st_size!=offset+math.prod(header['shape'])*{'<f4':4,'<i8':8,'<u4':4}[header['descr']]:raise ValueError('complete source NPY payload extent')
            deps=row['source_binding'].get('identity_from_versions',[])
            actual=[v for v in deps if not v.startswith('DeepSeek.-1.')]
            receipts.append(dict(binding_key=key,PC=int(PC),template=template,operand=name,primary_data_ownership=role,
                exact_original_manifest_record=row,actual_producer_versions_required=actual,initial_versions_required=[v for v in deps if v.startswith('DeepSeek.-1.')],
                dynamic_source_selection_or_acquisition_gate=gate,handler_qualified=False,physical_visibility_or_reverse_qualified=False))
            counts[role]+=1;refs+=1
        if len(roles)!=1:raise ValueError('same file has incompatible source roles')
        name=digest[:16]+'_'+source.name;target=out/'payloads'/name
        shutil.copyfile(source,target)
        if sha(target)!=digest or source.stat()!=stamp:raise ValueError('source/archive drift')
        total+=stamp.st_size
        records.append(dict(original_path=old,archive_relative_path='payloads/'+name,file_sha256=digest,file_bytes=stamp.st_size,
            npy_shape=list(header['shape']),npy_dtype=header['descr'],primary_data_ownership=next(iter(roles)),bindings=receipts,
            source_stamp=dict(dev=stamp.st_dev,ino=stamp.st_ino,mtime_ns=stamp.st_mtime_ns,ctime_ns=stamp.st_ctime_ns),
            remote_same_identity_procedure='Copy verified archived bytes to the exact original absolute path, preserving original manifest strings. No automatic path rewrite or V3 identity exemption. Remote checkpoint index/shards, actual captured RF/shared state and class/code source closure remain separately required.'))
    if total!=3668108 or refs!=119:raise ValueError('exact complete source byte/ref census')
    shutil.copyfile(manifest,out/'original_source_manifest.json.gz');shutil.copyfile(presence,out/'frozen_external_presence_dependency.json')
    (out/'source_identity_map.json').write_text(json.dumps(records,sort_keys=True,indent=2)+'\n')
    summary=dict(status='PASS_EXACT_EXTERNAL_INITIALIZER_ARCHIVE_NOT_HANDLER_QUALIFICATION',paths=67,bindings=119,archived_payload_bytes=total,
        binding_ownership_counts=dict(counts),path_ownership_counts=dict(Counter(r['primary_data_ownership'] for r in records)),
        first_any_source_consumer_PC=min(b['PC'] for r in records for b in r['bindings']),
        first_post_PC10_source_consumer_PC=min(b['PC'] for r in records for b in r['bindings'] if b['PC']>10),
        source_checkpoint_revision=m['checkpoint_revision'],source_state_scope=m['source_state_scope'],generation=m['generation'],
        actual_producer_state_archived=False,actual_producer_dependency_fields=sum(bool(b['actual_producer_versions_required']) for r in records for b in r['bindings']),
        comparison_output_files_in_DUT_archive=0,large_live_journals_read_or_hashed=False,array_payloads_loaded=False,
        remote_constructor_or_payload_admitted=False,V3_class_guard_changed=False,handler_qualified=False,hardware_qualified=False,
        source_pins={str(Path(p).resolve()):sha(p) for p in [__file__,presence,manifest]})
    (out/'summary.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n')
    (out/'artifact_manifest.json').write_text(json.dumps(dict(artifacts={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()},source_pins=summary['source_pins']),sort_keys=True,indent=2)+'\n')
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('presence','manifest','out'):p.add_argument('--'+k,type=Path,required=True)
    for k in ('presence_sha256','manifest_sha256'):p.add_argument('--'+k.replace('_','-'),required=True)
    s=archive(**vars(p.parse_args()));print(json.dumps({k:s[k] for k in ['status','paths','bindings','archived_payload_bytes','binding_ownership_counts','first_post_PC10_source_consumer_PC']},sort_keys=True))
