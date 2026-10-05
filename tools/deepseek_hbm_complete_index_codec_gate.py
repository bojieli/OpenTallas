"""Bounded source-produced tagged-row gate; synthetic fixtures, no checkpoint I/O."""
import argparse,hashlib,json,subprocess
from pathlib import Path
import numpy as np
import deepseek_hbm_complete_index_codec as C
import deepseek_hbm_complete_index_codec_model as Model
import deepseek_hbm_complete_packed_index_provider as P
import deepseek_hbm_complete_memory as Memory
import deepseek_hbm_complete_index_consumer as Consumer


def gate():
    root=Path(__file__).resolve().parents[1]
    rows=[]
    for name,bits in [('quiet_nan_payload',0x7fc12345),('signaling_nan_payload',0x7f812345),
                      ('negative_nan_payload',0xffc76543),('positive_inf',0x7f800000),('negative_inf',0xff800000)]:
        row=np.zeros(128,np.float32);row[0]=np.array(bits,np.uint32).view(np.float32)
        row[1:5]=np.array([0x80000000,0x3f800000,0xbf800000,1],np.uint32).view(np.float32)
        rows.append((name,row))
    for name,row in [('normal',np.linspace(-3,2,128,dtype=np.float32)),('negative_zero',np.full(128,-0.,np.float32)),
                     ('finite_scale253_overflow',np.full(128,np.finfo(np.float32).max,np.float32))]:rows.append((name,row))
    binding=C.ProducerBinding();memory=Memory.PersistentMemory()
    state=P.PackedIndexStateArray(np.zeros((len(rows),128),np.float32),memory,'ik',0)
    witnesses=[]
    for i,(name,row) in enumerate(rows):
        produced=binding.qdq_fp4_e8m0(row)
        with np.errstate(invalid='ignore',over='ignore',under='ignore'):reference=C.V.qdq_fp4_e8m0(row)
        if not np.array_equal(np.asarray(produced).view(np.uint32),reference.view(np.uint32)):
            raise AssertionError('source producer mismatch '+name)
        state[i]=produced;returned=state[i]
        if not np.array_equal(returned.view(np.uint32),reference.view(np.uint32)):
            raise AssertionError('tagged source row consumer mismatch '+name)
        epoch=state.current_generation[i]
        raw=memory.values[('KV','ik',0,i,'generation',epoch)]
        header=memory.values[('KV','ik',0,i,'descriptor')]
        witnesses.append({'name':name,'input_F32_bits':row.view(np.uint32).tolist(),
            'actual_produced_F32_bits':np.asarray(produced).view(np.uint32).tolist(),
            'retained_reference_F32_sha256':hashlib.sha256(reference.tobytes()).hexdigest(),
            'actual_returned_F32_sha256':hashlib.sha256(returned.tobytes()).hexdigest(),
            'format':produced.format_tag,'payload_bytes':len(produced.wire_payload),
            'descriptor_sector_hex':header.hex(),'initialized_payload_sector_hex':raw.hex(),
            'producer_receipt':binding.receipts[-1],'bit_exact':True})
    memory.fence()
    query=np.stack([binding.qdq_fp4_e8m0(np.linspace(-2,3,128,dtype=np.float32)) for _ in range(32)])
    weights=np.ones(32,np.float32);consumers=[]
    for name,indices in [('finite_normal',[5,6]),('actual_exceptional_returned_rows',list(range(8)))]:
        keys=state[indices]
        scores,receipt=Consumer.route_scores(query,keys,weights,ids=np.array(indices,np.int64))
        expected=Consumer.reference_scores(query,keys,weights,np.array(indices,np.int64))
        if not np.array_equal(scores.view(np.uint64),expected.view(np.uint64)):
            raise AssertionError('actual source score consumer mismatch '+name)
        consumers.append({'name':name,'current_query_F32_sha256':hashlib.sha256(query.tobytes()).hexdigest(),
                         'returned_key_F32_sha256':hashlib.sha256(keys.tobytes()).hexdigest(),
                         'actual_F64_ABI_score_bits':scores.view(np.uint64).tolist(),
                         'reference_F64_ABI_score_sha256':hashlib.sha256(expected.tobytes()).hexdigest(),
                         'receipt':receipt,'bit_exact':True})
    old=root/'results/rtl/deepseek_hbm_complete_20261001/index-producer-domain-r1.json'
    original=json.loads(old.read_text())
    for path,digest in original['source_pins'].items():
        if hashlib.sha256((root/path).read_bytes()).hexdigest()!=digest:raise AssertionError('source domain pin drift '+path)
    model=Model.build()
    paths=['tools/deepseek_hbm_complete_index_codec_gate.py','tools/deepseek_hbm_complete_memory.py',
           'tests/test_deepseek_hbm_complete_index_codec.py','tests/test_deepseek_hbm_complete_index_codec_model.py',
           'tests/test_deepseek_hbm_complete_packed_index_provider.py']
    return {'schema':'opentallas.deepseek.index-tagged-producer-gate.v1','verdict':'PASS',
        'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
        'source_pins':{**model['source_pins'],**{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}},
        'witnesses':witnesses,'actual_returned_row_score_consumer_witnesses':consumers,
        'actual_software_row_events':state.row_events,
        'actual_software_memory':memory.summary(),'outstanding_row_leases':len(state.leases),
        'outstanding_publications':len(state.publications),'checkpoint_data_reads':0,
        'fixture':'synthetic boundary values; no retained checkpoint or full token execution',
        'normal_numeric_tests':'all253 finite-input scale values x all16 nibble codes; midpoint neighbors/signs at each scale; original query/compressor callsite fixtures',
        'retained_domain_failure':str(old.relative_to(root)),
        'retained_domain_failure_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),
        'fallback':'actual unchanged reference producer decoded bits, tagged512B; not inversepacked and not lowered ordinaryGPU producer arithmetic',
        'transport_bit_exact':True,'whole_GPU_arithmetic_complete':False,'DUT_RTL_executed':False,
        'physical_provider_bound':False,'physical_cycles':None,'hardware_build_authorized':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);a=parser.parse_args()
    if a.out.exists():raise SystemExit('preserve existing evidence')
    root=Path(__file__).resolve().parents[1]
    if subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip():raise SystemExit('clean source required')
    a.out.parent.mkdir(parents=True,exist_ok=True)
    try:r=gate()
    except Exception as e:r={'verdict':'FAIL','failure':repr(e),'DUT_RTL_executed':False}
    a.out.write_text(json.dumps(r,separators=(',',':'))+'\n')
    raise SystemExit(r['verdict']!='PASS')
