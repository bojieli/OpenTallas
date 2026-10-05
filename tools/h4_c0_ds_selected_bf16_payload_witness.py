"""Independent locked selected-BF16 bits; comparison only, never DUT operands.

No provider constructor/MRO/manifest mutation, no prefix/matrix arithmetic.
Reads the explicitly reviewed 288 component spans in small chunks. Exact BF16
bits widen by a 16-bit shift, preserving signed zero/NaN payloads. Future actual
weight_view output can be compared only after its own scope/source admission.
"""
import argparse,fcntl,hashlib,json,os,resource,struct,time
from pathlib import Path

ENROLLMENT_SHA='dd73aebaf4c34f0c673540d2000cbcb00591e45136b144f218c96882b7ad73b2'
INDEX_SHA='74b0686a3d2891980d5e303251b075a3bccae2c2ff650747db2620a649b98fa8'
REVISION='dba1be0a40aa45a94ad051997016db3960a90277'


def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()


def widen_bits(raw):
    if len(raw)%2:raise ValueError('complete little-endian BF16 words required')
    return b''.join(struct.pack('<I',word[0]<<16) for word in struct.iter_unpack('<H',raw))


def compare_selected_weight(proof,plan,array):
    if canonical(plan)!=canonical(proof['plan']):raise ValueError('exact selected caller plan required')
    if list(array.shape)!=plan['shape'] or array.dtype.str!='<f4' or not array.flags.c_contiguous:
        raise ValueError('actual selected F32 codec/shape/layout')
    if hashlib.sha256(array.tobytes(order='C')).hexdigest()!=proof['expected_F32_bits_sha256']:
        raise ValueError('actual selected BF16 expansion bytes differ')
    return dict(status='PASS_ACTUAL_SELECTED_BF16_EXPANSION_BITS',PC=plan['PC'],rank=plan['rank'],
                template=plan['template'],matrix_arithmetic_qualified=False,hardware_qualified=False)


def audit(enrollment_path,census_path,census_sha256,checkpoint_root,out):
    if sha(enrollment_path)!=ENROLLMENT_SHA or sha(census_path)!=census_sha256:
        raise ValueError('reviewed enrollment/call census SHA required')
    enrollment=json.loads(Path(enrollment_path).read_text());census=json.loads(Path(census_path).read_text())
    root=Path(checkpoint_root);indexpath=root/'model.safetensors.index.json'
    if root.name!=REVISION or enrollment['checkpoint_revision']!=REVISION or sha(indexpath)!=INDEX_SHA:
        raise ValueError('exact released checkpoint revision/index')
    if census['actual_caller_count']!=288 or census['binding_count']!=6 or len(census['plans'])!=288:
        raise ValueError('exact 288-call six-binding source census')
    index=json.loads(indexpath.read_text())['weight_map'];files={};proofs=[];coverage={};total=0
    started=time.time_ns()
    try:
        for tensor,component in enrollment['components'].items():
            filename=component['shard']
            if Path(filename).name!=filename or index[tensor]!=filename:raise ValueError('selected shard index mapping')
            if filename not in files:
                fd=os.open(root/filename,os.O_RDONLY)
                try:
                    fcntl.flock(fd,fcntl.LOCK_SH|fcntl.LOCK_NB);stamp=os.fstat(fd)
                    count=struct.unpack('<Q',os.pread(fd,8,0))[0]
                    if count!=component['data_base']-8:raise ValueError('selected header length')
                    raw=os.pread(fd,count,8)
                    if len(raw)!=count or hashlib.sha256(raw).hexdigest()!=component['raw_header_sha256']:
                        raise ValueError('selected locked header SHA')
                    files[filename]=(fd,stamp,json.loads(raw))
                except BaseException:os.close(fd);raise
            fd,stamp,header=files[filename];actual=header[tensor]
            if actual['dtype']!='BF16' or actual['shape']!=[512,5120] or actual['data_offsets']!=component['data_offsets']:
                raise ValueError('selected component dtype/shape/extent')
            if component['scale_tensor'] is not None or component['layout']!='safetensors_C_row_major':
                raise ValueError('no invented scale or source layout')
            coverage[tensor]=[]
        for plan in census['plans']:
            pc=plan['PC'];rank=plan['rank'];layer={115:2,443:8,776:14}.get(pc)
            if layer is None or not 0<=rank<96 or plan['rows']!=[1024*rank//96,1024*(rank+1)//96]:
                raise ValueError('actual source PC/rank rows')
            if plan['logical_tensor']!=[f'layers.{layer}.attn.compressor.{part}.weight' for part in ('wkv','wgate')]:
                raise ValueError('wkv before wgate source order')
            if plan['shape']!=[plan['rows'][1]-plan['rows'][0],5120] or plan['K']!=[0,5120]:
                raise ValueError('actual fullK/LOAD shape')
            full=hashlib.sha256();segments=[];destination=0;selected=0
            for seg in plan['segments']:
                tensor=seg['tensor'];comp=enrollment['components'][tensor];first,last=seg['rows'];ordinal=seg['component_ordinal']
                expected_lo=max(plan['rows'][0],ordinal*512);expected_hi=min(plan['rows'][1],(ordinal+1)*512)
                if tensor!=plan['logical_tensor'][ordinal] or [first,last]!=[expected_lo-ordinal*512,expected_hi-ordinal*512]:
                    raise ValueError('component row projection/order')
                if seg['destination_rows']!=[destination,destination+last-first]:raise ValueError('contiguous source destination')
                lo=comp['data_base']+comp['data_offsets'][0]+first*5120*2;hi=lo+(last-first)*5120*2
                if [lo,hi]!=seg['source_file_byte_interval'] or hi>comp['data_base']+comp['data_offsets'][1]:
                    raise ValueError('actual selected byte interval')
                fd,stamp,header=files[seg['shard']];bits=hashlib.sha256();expanded=hashlib.sha256()
                for pos in range(lo,hi,16384):
                    raw=os.pread(fd,min(16384,hi-pos),pos)
                    if len(raw)!=min(16384,hi-pos):raise ValueError('complete selected source read')
                    f32=widen_bits(raw);bits.update(raw);expanded.update(f32);full.update(f32)
                if os.fstat(fd)!=stamp:raise ValueError('source shard changed during selected read')
                segments.append(dict(tensor=tensor,rows=[first,last],source_file_byte_interval=[lo,hi],BF16_bits_sha256=bits.hexdigest(),F32_bits_sha256=expanded.hexdigest()))
                coverage[tensor].append([first,last]);destination+=last-first;selected+=hi-lo
            if destination!=plan['shape'][0] or selected!=plan['selected_checkpoint_bytes']:raise ValueError('complete selected caller coverage')
            total+=selected;proofs.append(dict(plan=plan,segments=segments,expected_F32_bits_sha256=full.hexdigest(),comparison_only=True))
        for tensor,rows in coverage.items():
            ordered=sorted(rows);last=0
            for lo,hi in ordered:
                if lo!=last or hi<=lo:raise ValueError('no duplicate/hole in complete component rows')
                last=hi
            if last!=512:raise ValueError('all512 component rows required')
        if total!=31457280:raise ValueError('exact 30MiB selected source census')
        out=Path(out);out.mkdir(parents=True,exist_ok=False)
        (out/'selected_call_bit_proofs.json').write_text(json.dumps(proofs,sort_keys=True,indent=2)+'\n')
        stamps={name:dict(dev=st.st_dev,ino=st.st_ino,bytes=st.st_size,mtime_ns=st.st_mtime_ns,ctime_ns=st.st_ctime_ns) for name,(fd,st,_) in files.items()}
        for fd,st,_ in files.values():
            if os.fstat(fd)!=st:raise ValueError('selected source changed before sealing')
        summary=dict(status='PASS_INDEPENDENT_SELECTED_BF16_BITS_NOT_DUT_OUTPUT',calls=288,bindings=6,PCs=[115,443,776],
            released_checkpoint_revision=REVISION,selected_source_bytes=total,component_count=len(coverage),
            whole_component_row_coverage='all512 rows exactly once, fullK5120, ordered wkv then wgate',
            max_selected_call_bytes=census['max_selected_checkpoint_bytes'],read_chunk_bytes=16384,
            metadata_plus_stream_RAM_estimate_not_cap_bytes=128*(1<<20),measured_peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            started_ns=started,finished_ns=time.time_ns(),source_shard_stamps=stamps,
            actual_handler_outputs_compared=0,provider_payload_reads_admitted=False,provider_constructed=False,
            V3_guard_changed=False,native_program_executed=False,numerical_prefix_duplicated=False,
            matrix_arithmetic_qualified=False,hardware_qualified=False,
            source_pins={str(Path(p).resolve()):sha(p) for p in [__file__,enrollment_path,census_path,indexpath]})
        (out/'summary.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n')
        (out/'artifact_manifest.json').write_text(json.dumps(dict(artifacts={p.name:sha(p) for p in out.iterdir()},source_pins=summary['source_pins']),sort_keys=True,indent=2)+'\n')
        return summary
    finally:
        for fd,*_ in files.values():os.close(fd)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('enrollment_path','census_path','checkpoint_root','out'):p.add_argument('--'+name.replace('_','-'),type=Path,required=True)
    p.add_argument('--census-sha256',required=True)
    r=audit(**vars(p.parse_args()));print(json.dumps({k:r[k] for k in ('status','calls','selected_source_bytes','measured_peak_RSS_bytes','actual_handler_outputs_compared')},sort_keys=True))
