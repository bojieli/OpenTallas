"""Journal a bounded source integer subsequence at actual r20 PC14 addresses.

Explicit fixture values; not whole EXP_SUM, full token, PHY or hardware evidence.
"""
import argparse,gzip,hashlib,json
from pathlib import Path
import numpy as np
from hbm_provider_microvm_r21 import SectorProvider,Storage,MicroVM,Tensor,tensor_from_native_binding

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/'results/uarch/hbm_provider_microvm_r21_20261002/actual_r20_codec_fixture_metadata.json'

def diagnostic():
    f=json.loads(FIXTURE.read_bytes());a=f['rank_allocation'];homes={h['symbol']:h for h in f['PC14_homes']}
    p=SectorProvider({('Qwen',0):a['extents']});s=Storage(p,'Qwen',0,a['native_workspace_end']-4096,4096);v=MicroVM(s)
    n=np.tile(np.array([-126.,-1.,0.,127.],np.float32),32);pb=np.full(128,0x3f800000,np.uint32)
    providers={}
    for name,value,dtype in [('n',n,'F32'),('pb',pb,'U32')]:
        p.seed('Qwen',0,homes[name]['base'],value.tobytes())
        providers[name]=Tensor('Qwen',0,homes[name]['base'],(128,),dtype)
    def ins(op,dst,src=(),shape=(),**attrs):return dict(op=op,dst=dst,src=list(src),shape=list(shape),attrs=attrs)
    bindings={name:tensor_from_native_binding(homes[name],(128,)) for name in ('ni','exponent','resultbits')}
    code=[ins('LOAD','n',shape=(128,),name='n',dtype='F32'),ins('LOAD','pb',shape=(128,),name='pb',dtype='U32'),ins('FTOI','ni',['n'],(128,)),ins('CONST','shift',value=23,dtype='I64'),ins('SHL64','exponent',['ni','shift'],(128,)),ins('IADD64','resultbits',['pb','exponent'],(128,))]
    out=v.run({'source_pc':14,'code':code,'destination_bindings':bindings,'outputs':{'out':'resultbits'}},providers)['out']
    actual=s.read(out,np.arange(128));expected=pb.astype(np.int64)+(n.astype(np.int64)<<23)
    if not np.array_equal(actual,expected) or p.live or p.calendar or p.queue or p.resident or s.codec_locks or s.codec_leases:raise RuntimeError('diagnostic mismatch or undrained ownership')
    for pub in [e for e in s.codec_events if e['event']=='split64_both_streams_visible_granted_publication']:
        prior=[e for e in p.events if e['event']=='validated_reverse_grant' and e['tick']<=pub['tick']]
        if not prior:raise RuntimeError('publication without reverse completion')
    return {'scope':'SOFTWARE_SOURCE_INTEGER_SUBSEQUENCE_EXPLICIT_FIXTURE_128_LANES','source_metadata_SHA256':hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
        'source_homes':homes,'source_pc':14,'instructions':code,'expected_output_SHA256':hashlib.sha256(expected.tobytes()).hexdigest(),'actual_output_SHA256':hashlib.sha256(actual.tobytes()).hexdigest(),
        'values_match':True,'all_ownership_drained':True,'parameters':p.costs,'parameter_unit':'PROVISIONAL_ABSTRACT_SOFTWARE_TICKS','finite_staging_bytes':1536,
        'events':p.events,'codec_events':s.codec_events,'microop_events':v.journal,'hardware':False,'PHY':False,'whole_operator_or_fulltoken':False}

def emit(path):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(gzip.compress(json.dumps(diagnostic(),sort_keys=True,separators=(',',':')).encode(),mtime=0))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);emit(ap.parse_args().output)
