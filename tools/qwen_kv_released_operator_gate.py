"""Prepared default-off released-checkpoint KV operator gate; never a decode.

SCORES/PV arithmetic is not executed. Harness completes real storage leases
at source PCs after inspecting reads; these events cannot qualify production
consumer completion or repair the old live run's missing journal.
"""
import hashlib
import inspect
import json
from pathlib import Path
import numpy as np
from qwen_kv_observation_adapter import observed_storage
from qwen_kv_observation_verify import payload_layout, verify


def run(native, module, reference, output, admission, journal_validator, *, enabled=False):
    if not enabled:return dict(status='DISABLED_DEFAULT',native_decode=False)
    pins=admission['source_file_sha256']
    files={str(Path(module.__file__).resolve()),str(Path(inspect.getfile(module.Storage)).resolve()),
        str(Path(inspect.getfile(module.pack8)).resolve()),str(Path(inspect.getfile(observed_storage)).resolve()),
        str(Path(inspect.getfile(verify)).resolve()),str(Path(__file__).resolve())}
    for file in files:
        if hashlib.sha256(Path(file).read_bytes()).hexdigest()!=pins[file]:raise ValueError('operator source pin')
    if hashlib.sha256((json.dumps(native,sort_keys=True,indent=2)+'\n').encode()).hexdigest()!=admission['native_sha256']:raise ValueError('native frame pin')
    reference=Path(reference);output=Path(output)
    for name,want in admission['reference_file_sha256'].items():
        path=reference/name
        if Path(name).is_absolute() or '..' in Path(name).parts or hashlib.sha256(path.read_bytes()).hexdigest()!=want:raise ValueError('independent reference input pin')
    inventory=json.loads((reference/'reference_inventory.json').read_text())
    expected={}
    for row in inventory:
        import struct
        key=tuple(row['key']);data=(reference/row['file']).read_bytes()
        if hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('reference U8 identity')
        if key in expected:raise ValueError('duplicate independent reference group')
        if len(data)!=row['records']*9:raise ValueError('reference record extent')
        expected[key]=dict(struct.iter_unpack('<QB',data))
        if len(expected[key])!=row['records']:raise ValueError('duplicate independent reference address')
    memory=observed_storage(module.BoundKVStorage,output,enabled=True,native=native)(native['source_program'])
    names={v['version']:v['name']for v in native['operands']};leases={};trace=[]
    for op in native['operations']:
        code=op['opcode'];memory.pc=op['pc']
        if code in ('KV_WRITE','KV_FENCE','KV_READ'):
            a=op['attributes'];key=(a['layer'],a['die'],0)
        if code=='KV_WRITE':
            tag=memory.begin(*key)
            layout=payload_layout(native,key)
            for kind in ('K','V'):
                value=np.load(reference/f'L{key[0]}.rank{key[1]}.{kind}.prepack.npy',allow_pickle=False)
                if value.dtype!=np.float32 or value.shape!=(4,128) or not np.isfinite(value).all():raise ValueError('released operator input')
                codes=module.pack8(value).reshape(-1)
                addresses=[address for address,meta in sorted(layout.items(),key=lambda item:(item[1]['head'],item[1]['dim']))if meta['kind']==kind]
                memory.write(tag,np.array(addresses),codes)
            leases[key]=tag
        elif code=='KV_FENCE':leases[key]=memory.commit(leases[key])
        elif code=='KV_READ':
            lease=memory.acquire(leases[key],*key);leases[key]=lease;layout=payload_layout(native,key);outputs=[]
            for index,kind in enumerate(('K','V')):
                addresses=[address for address,meta in sorted(layout.items(),key=lambda item:(item[1]['head'],item[1]['dim']))if meta['kind']==kind]
                codes=memory.read(lease,np.array(addresses))
                decoded=module.fp8_table()[codes&127]*np.where(codes&128,-1,1).astype(np.float32)
                decoded=np.where(decoded==0,np.float32(0),decoded).astype('<f4')
                outputs.append(dict(version=op['writes'][index],shape=[4,1,128],sha256=hashlib.sha256(decoded.tobytes()).hexdigest()))
            trace.append(dict(pc=op['pc'],opcode=code,outputs=outputs))
        elif code in ('SCORES','PV'):
            parts=names[op['reads'][1]].split('.');key=(int(parts[0][1:]),int(parts[1][1:]),0)
            memory.done(leases[key],code)
    memory.finish_observation()
    result=verify(native,output,journal_validator,expected,trace)
    result.update(scope='released-checkpoint FP8 pack/storage/publication/read/retirement operator gate only',
        production_SCORES_PV_executed=False,production_lifecycle_qualified=False,
        consumer_completion='harness-driven after read inspection',native_decode=False)
    (output/'operator_gate_result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
