"""All40 fixture writer, bit layout, capacity and immutable output gates."""
import sys,json
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w11_dsrom_full_tp_program_constants as W


def fixture_source(tmp_path):
    recipes,_=W.C.read(W.C.MAIN_BINDING_PIN,W.C.MAIN_BINDING)
    tensors={}
    for i,(name,r) in enumerate(recipes['recipes'].items()):
        if r.get('output_word_bits')!=64:continue
        n=int(np.prod(r['stored_shape']));dt=r['stored_dtype']
        bits=(np.arange(n,dtype=np.uint32)+i+(0x3f80 if dt=='BF16' else 0x3f800000))
        raw=bits.astype('<u2' if dt=='BF16' else '<u4').tobytes()
        path=tmp_path/f'{name}.bin';path.write_bytes(raw)
        tensors[name]={'path':str(path),'dtype':dt,'shape':r['stored_shape'],'sha256':W.sha(raw)}
    p=tmp_path/'source.json';p.write_text(json.dumps({'checkpoint':{'scope':'small deterministic synthetic fixture, not released checkpoint'},'tensors':tensors}))
    return p


def test_bit_golden_widen_preserves_signed_zero_nan_payload():
    src=np.array([0,0x8000,0x3f80,0x7fc1,0xff80],dtype='<u2')
    result=np.frombuffer(W.convert(src.tobytes(),'BF16','norm.weight',0),dtype='<u4').reshape(-1,2)
    assert np.array_equal(result[:,0],src.astype(np.uint32)<<16)
    assert not np.any(result[:,1])
    fp=np.array([0x80000000,0x7fc12345,0x3f800000],dtype='<u4')
    out=np.frombuffer(W.convert(fp.tobytes(),'F32','x',0),dtype='<u4').reshape(-1,2)
    assert np.array_equal(out[:,0],fp)


def test_all40_head_actual_images_and_finalnorm_binding(tmp_path):
    source=fixture_source(tmp_path);out=tmp_path/'output';m=W.write_images(source,out,508800)
    assert len(m['rank_images'])==4
    import w11_dsrom_full_tp_program as F
    original=F.head_descriptors()
    bound=W.bind_head_norm(original,m,0,out)
    assert next(op['c_base'] for op in bound if op.get('c_src')==F.I.SRC_CLO)==503680
    assert next(op.get('c_base',0) for op in original if op.get('c_src')==F.I.SRC_CLO)==0
    for rank in m['rank_images']:
        assert len(rank['constants'])==409 and rank['used_words']==508800
        assert rank['finalnorm_base_word']==503680
        image=(out/rank['image']).read_bytes();assert W.sha(image)==rank['image_sha256']
        words=np.frombuffer(image,dtype='<u4').reshape(-1,2);assert not words[:,1].any()
        previous=0
        for e in rank['constants'].values():
            assert e['base_word']==previous;previous=e['end_word_exclusive']
        e=rank['constants']['norm.weight'];raw=Path(e['source']['path']).read_bytes()
        assert image[e['base_word']*8:e['end_word_exclusive']*8]==W.convert(raw,'BF16','norm.weight',rank['rank'])
    with pytest.raises(ValueError,match='overwrite'):W.write_images(source,out,508800)


def test_capacity_and_bad_source_fail_before_output(tmp_path):
    source=fixture_source(tmp_path);out=tmp_path/'output'
    with pytest.raises(ValueError,match='capacity exceeded'):W.write_images(source,out,508799)
    assert not out.exists()
    m=json.loads(source.read_text());entry=m['tensors']['norm.weight'];Path(entry['path']).write_bytes(b'bad')
    with pytest.raises(ValueError,match='sourceSHA'):W.write_images(source,out,508800)
    assert not out.exists()

def test_existing_L0_checkpoint_positive():
    recipes,_=W.C.read(W.C.MAIN_BINDING_PIN,W.C.MAIN_BINDING)
    e=recipes['recipes']['layers.0.attn_norm.weight']['existing_L0_rank0_image_record']
    path=Path('/home/ubuntu/w17work/isa/scratch_s20260930/images/ctx1048576_L00_r0/w.attn_norm.bin')
    if not path.exists():pytest.skip('historical source unavailable on this host')
    raw=path.read_bytes()
    assert W.sha(raw)==e['source_tensor_sha256']
    packed=W.convert(raw,'BF16','layers.0.attn_norm.weight',0)
    assert W.sha(packed)==e['output_image_sha256']
