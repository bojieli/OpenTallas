import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import pytest
import torch
from safetensors.torch import save_file
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_hbm_complete_program import compile_program
from qwen_hbm_complete_executor import CheckpointWeights,SoftwareGPUProvider,execute
from qwen_hbm_complete_reference import PostExecutionReference
from test_qwen_hbm_complete_program import small

def fixture_checkpoint(path,config):
    generator=torch.Generator().manual_seed(930)
    def weight(rows,k):return (torch.randn(rows,k,generator=generator)*.1).to(torch.bfloat16)
    h=config['hidden_size'];hd=config['head_dim'];ff=config['intermediate_size'];v=config['vocab_size']
    tensors={'model.embed_tokens.weight':weight(v,h),'lm_head.weight':weight(v,h),'model.norm.weight':torch.ones(h,dtype=torch.bfloat16)}
    for layer in range(config['num_hidden_layers']):
        p=f'model.layers.{layer}'
        tensors[p+'.input_layernorm.weight']=torch.linspace(.8,1.2,h).to(torch.bfloat16)
        tensors[p+'.post_attention_layernorm.weight']=torch.linspace(.9,1.1,h).to(torch.bfloat16)
        for name in ('q','k'):tensors[p+f'.self_attn.{name}_norm.weight']=torch.ones(hd,dtype=torch.bfloat16)
        for name in ('q','k','v','o'):tensors[p+f'.self_attn.{name}_proj.weight']=weight(h,h)
        for name in ('gate','up'):tensors[p+f'.mlp.{name}_proj.weight']=weight(ff,h)
        tensors[p+'.mlp.down_proj.weight']=weight(h,ff)
    save_file(tensors,str(path/'weights.safetensors'))
    (path/'config.json').write_text(json.dumps(config))
    (path/'model.safetensors.index.json').write_text(json.dumps({'weight_map':{key:'weights.safetensors' for key in tensors}}))
    lock={'revision':'bounded-test-fixture','expected_files':[dict(path=name,sha256=hashlib.sha256((path/name).read_bytes()).hexdigest(),size_bytes=(path/name).stat().st_size) for name in ('config.json','model.safetensors.index.json','weights.safetensors')]}
    return lock,tensors

def test_lazy_actual_bf16_reader_and_fullrow_normfold_column_partition(tmp_path):
    torch.set_num_threads(1)
    c=small();program=compile_program(c,context=32,groups=16);lock,tensors=fixture_checkpoint(tmp_path,c)
    weights=CheckpointWeights(program,tmp_path,row_batch=4,lock=lock)
    from hdc_qwen_int8_image_w12 import quantize_full_rows_then_partition
    for key in ('L0.qkv.d1','L0.gu.d0','L0.o.d1','L0.down.d0','head.d1'):
        d=program['weight_descriptors'][key];codes,scales=weights.matrix(key);qc=[];sc=[]
        for source in d['checkpoint_sources']:
            q,s=quantize_full_rows_then_partition(tensors[source],die=d['die'],axis='columns' if d['name'] in ('o','down') else 'rows',norm=tensors[d['folded_norm']] if d['folded_norm'] else None)
            qc.append(q.numpy());sc.append(s.float().numpy().reshape(-1))
        assert np.array_equal(codes,np.concatenate(qc))
        assert np.array_equal(scales,np.concatenate(sc))
    assert weights.file_pins['weights.safetensors']==lock['expected_files'][-1]['sha256']
    assert all(r['row_start'] is None or r['row_stop']-r['row_start']<=4 for r in weights.reads)
    with pytest.raises(ValueError,match='bounded row aperture'):weights.read_tensor('lm_head.weight',0,8)
    with pytest.raises(ValueError,match='bounded row reads'):weights.tensor('lm_head.weight')

def test_postexecution_independent_two_token_checkpoint_exactness(tmp_path):
    torch.set_num_threads(1)
    c=small();p=compile_program(c,context=32,groups=16);lock,_=fixture_checkpoint(tmp_path,c)
    weights=CheckpointWeights(p,tmp_path,row_batch=4,lock=lock);provider=SoftwareGPUProvider(p,weights)
    reference=PostExecutionReference(p,weights);token=3
    for position in range(2):
        reference.start_token(token,position)
        def observer(op,values):
            for name,value in zip(op['outputs'],values):
                if name in ('L0.X','L1.X'):reference.layer(int(name[1]),value.copy())
                elif name=='head.norm':reference.final_norm(value)
                elif name in ('head.d0.scaled','head.d1.scaled'):reference.head(int(name[6]),value.copy())
        result=execute(p,provider,token,position,observer=observer)
        assert result['next_token']==reference.next_token
        assert not provider.memory.leases and not provider.memory.pending
        token=result['next_token']
    assert len(reference.comparisons)==10
    assert all(x['bit_mismatches']==0 for x in reference.comparisons)
    assert len(provider.memory.published)==8
    releases=[x for x in provider.memory.events if x['event']=='software_reader_lease_released']
    assert len(releases)==8

def test_source_mutation_rejected_and_comparison_never_injected(tmp_path):
    torch.set_num_threads(1)
    c=small();p=compile_program(c,context=32,groups=16);lock,_=fixture_checkpoint(tmp_path,c)
    weights=CheckpointWeights(p,tmp_path,row_batch=4,lock=lock)
    weights.embedding(3)
    source=tmp_path/'weights.safetensors'
    with source.open('ab') as stream:stream.write(b'x')
    with pytest.raises(ValueError,match='changed after admission'):weights.embedding(4)
    reference=PostExecutionReference(p,weights)
    with pytest.raises(ValueError,match='post-execution exactness failure'):
        reference.compare('mutant',np.array([1],np.float32),torch.tensor([2.]))
    assert reference.comparisons[-1]['bit_mismatches']==1

def test_leases_release_only_after_both_actual_software_consumers():
    p=compile_program(small(),context=32,groups=16);provider=SoftwareGPUProvider(p)
    values=np.ones((1,4),np.float32);ticket=provider.memory.submit_KV(0,0,0,values,values)
    provider.memory.read_KV(0,0,0,provider.memory.fence(ticket));lease=provider.memory.last_lease
    with pytest.raises(ValueError,match='before score'):provider.memory.consumer_done(lease,'PV')
    provider.memory.consumer_done(lease,'SCORES')
    assert lease in provider.memory.leases
    with pytest.raises(ValueError,match='duplicate'):provider.memory.consumer_done(lease,'SCORES')
    provider.memory.consumer_done(lease,'PV')
    assert lease not in provider.memory.leases
    with pytest.raises(ValueError,match='unknown'):provider.memory.consumer_done(lease,'PV')
