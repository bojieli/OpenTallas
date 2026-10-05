"""Independent released-checkpoint header gates for every native tensor binding.

No weights are decoded and no numerical operator runs. These gates expose exact
codec/row/K/descriptor prerequisites; they are not numerical witness or runtime
admission. All routed alternatives are catalogued, never oracle-selected.
"""
import argparse
import fcntl
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import struct
from h4_c0_ds_fullgraph_inventory import NATIVE,sha,load

class Headers:
    def __init__(self,root,revision,index_sha256):
        self.root=Path(root).resolve();self.files={};self.receipts={}
        if self.root.name!=revision or sha(self.root/'model.safetensors.index.json')!=index_sha256:
            raise ValueError('released immutable checkpoint revision/index required')
        self.index=load(self.root/'model.safetensors.index.json')['weight_map']
    def get(self,name):
        filename=self.index[name]
        if filename not in self.files:
            p=(self.root/filename).resolve()
            if Path(filename).name!=filename:raise ValueError('checkpoint index shard basename required')
            fd=os.open(p,os.O_RDONLY);fcntl.flock(fd,fcntl.LOCK_SH|fcntl.LOCK_NB)
            stamp=os.fstat(fd);length=struct.unpack('<Q',os.pread(fd,8,0))[0]
            if not 0<length<=stamp.st_size-8:raise ValueError('actual safetensors header extent')
            raw=os.pread(fd,length,8)
            if len(raw)!=length:raise ValueError('complete checkpoint header read')
            self.files[filename]=(fd,json.loads(raw),stamp,length)
            self.receipts[filename]=dict(path=str(p),header_sha256=hashlib.sha256(raw).hexdigest(),header_bytes=length,
                file_stat=dict(dev=stamp.st_dev,ino=stamp.st_ino,bytes=stamp.st_size,mtime_ns=stamp.st_mtime_ns,ctime_ns=stamp.st_ctime_ns))
        fd,header,stamp,length=self.files[filename];now=os.fstat(fd)
        if (stamp.st_dev,stamp.st_ino,stamp.st_size,stamp.st_mtime_ns,stamp.st_ctime_ns)!=(now.st_dev,now.st_ino,now.st_size,now.st_mtime_ns,now.st_ctime_ns):
            raise ValueError('checkpoint header source changed')
        m=header[name];a,b=m['data_offsets']
        if not 0<=a<b<=stamp.st_size-8-length:raise ValueError('actual tensor payload extent')
        return dict(logical_tensor=name,shard=filename,dtype=m['dtype'],shape=m['shape'],
            tensor_data_offsets=[a,b],absolute_file_offsets=[8+length+a,8+length+b],raw_payload_bytes=b-a)
    def close(self):
        for fd,*_ in self.files.values():os.close(fd)


def gate(header,binding,spec,name):
    """Header-only check against the real provider's declared format semantics."""
    if binding['kind']=='immutable_parameter_provider':
        errors=[]
        if header['dtype'] not in ('BF16','F32'):errors.append('parameter_codec_not_supported')
        if header['shape']!=spec['shape']:errors.append('parameter_source_view_needed')
        return errors
    fmt=binding['format'];want={'fp4':'I8','fp8':'F8_E4M3','bf16':'BF16'}[fmt]
    errors=[]
    if header['dtype']!=want:errors.append('weight_source_codec_mismatch')
    if len(header['shape'])!=2:errors.append('weight_source_not_matrix')
    if header['shape'][-1]!=spec['shape'][-1]:
        # weight scales have their own source codec/shape checked by caller.
        if name!='weight_scale_codes' and not binding['logical_tensor'].__class__ is list and not str(binding['logical_tensor']).endswith('attn.wo_a.weight'):
            errors.append('weight_K_source_view_needed')
    return errors


def build(native_path,manifest_path,out):
    if sha(native_path)!=NATIVE:raise ValueError('exact canonical full source required')
    out=Path(out)
    if out.exists():raise ValueError('fresh metadata gate evidence')
    n=load(native_path);m=load(manifest_path)
    ck=Headers(m['checkpoint_path'],m['checkpoint_revision'],m['checkpoint_index_sha256'])
    records=[];cache={};missing=[]
    try:
        for op in n['instructions']:
            for tid,bs in op['provider_bindings'].items():
                for field,b in bs.items():
                    if b['kind'] not in ('immutable_weight_provider','immutable_parameter_provider'):continue
                    logical=b['logical_tensor'];names=[]
                    if isinstance(logical,list):
                        slot,matrix=logical;layer=op['source_op']['layer']
                        names=logical if all(isinstance(x,str) for x in logical) else ([f'layers.{layer}.ffn.experts.{i}.{matrix}.weight' for i in range(384)] if slot<6 else [f'layers.{layer}.ffn.shared_experts.{matrix}.weight'])
                    else:names=[logical]
                    checks=[]
                    for tensor in names:
                        if tensor not in cache:
                            if tensor not in ck.index:
                                missing.append(tensor);cache[tensor]=dict(missing=True,logical_tensor=tensor)
                            else:
                                h=ck.get(tensor);scale=tensor.removesuffix('.weight')+'.scale'
                                if b['kind']=='immutable_weight_provider' and b['format'] in ('fp8','fp4'):
                                    h['scale_header']=ck.get(scale) if scale in ck.index else dict(missing=True,logical_tensor=scale)
                                cache[tensor]=h
                        h=cache[tensor];errors=['released_tensor_absent'] if h.get('missing') else gate(h,b,n['templates'][tid]['providers'][field],field)
                        if 'scale_header' in h and (h['scale_header'].get('missing') or h['scale_header']['dtype']!='F8_E8M0'):
                            errors.append('weight_scale_source_codec_missing')
                        checks.append(dict(tensor=tensor,gaps=errors))
                    records.append(dict(PC=op['pc'],family=op['family'],template=tid,field=field,
                        logical_binding=logical,source_tensor_choices=checks,dynamic_route_required=isinstance(logical,list) and isinstance(logical[0],int),
                        ordered_matrix_concat_required=isinstance(logical,list) and all(isinstance(x,str) for x in logical),
                        actual_route_producer_retirement_required=isinstance(logical,list) and isinstance(logical[0],int) and logical[0]<6,
                        scope='locked header metadata only; raw selected bytes and independent arithmetic gate remain required'))
        for name in cache:
            if not cache[name].get('missing'):ck.get(name)  # Final inode/stamp revalidation.
        out.mkdir(parents=True)
        def emit(name,value):
            (out/(name+'.json.gz')).write_bytes(gzip.compress(json.dumps(value,sort_keys=True,separators=(',',':')).encode(),mtime=0))
        emit('operator_checkpoint_bindings',records);emit('released_tensor_headers',cache)
        summary=dict(status='RELEASED_CHECKPOINT_HEADER_GATES_NOT_NUMERICAL_QUALIFICATION',native_sha256=NATIVE,
            checkpoint_revision=m['checkpoint_revision'],checkpoint_index_sha256=m['checkpoint_index_sha256'],
            manifest_sha256=sha(manifest_path),binding_count=len(records),unique_tensor_count=len(cache),
            header_files=ck.receipts,missing_tensors=sorted(set(missing)),
            source_view_or_codec_gaps=[dict(PC=r['PC'],field=r['field'],choices=[x for x in r['source_tensor_choices'] if x['gaps']]) for r in records if any(x['gaps'] for x in r['source_tensor_choices'])],
            tensor_payloads_read=0,oracle_route_selection=False,operator_numerical_gates_passed=0,
            hardware_qualified=False,full_token_qualified=False,source_pins={str(Path(__file__).resolve()):sha(__file__)})
        (out/'summary.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n')
        (out/'artifact_manifest.json').write_text(json.dumps({str(p):sha(p) for p in sorted(out.iterdir())},sort_keys=True,indent=2)+'\n')
        return summary
    finally:ck.close()

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('native','manifest','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();r=build(a.native,a.manifest,a.out)
    print(json.dumps({k:r[k] for k in ('status','binding_count','unique_tensor_count','missing_tensors')},sort_keys=True))
