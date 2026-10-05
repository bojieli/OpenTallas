import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w19_qwen_hbm_vector_fixture as V


def test_tp_projection_order_and_full_shape_guard():
    parts={d:np.arange(d*3072,(d+1)*3072,dtype=np.uint32) for d in (0,1)}
    q,k,v=V.split_projections(parts)
    assert q[2047]==2047 and q[2048]==3072 and q[-1]==5119
    assert k[0]==2048 and k[512]==5120 and k[-1]==5631
    assert v[0]==2560 and v[512]==5632 and v[-1]==6143
    with pytest.raises(ValueError):V.split_projections({0:parts[0]})


def test_full_heads_nonzero_rope_and_fp8_clip_bytes():
    raw=np.random.default_rng(19).normal(size=3072).astype(np.float32)
    raw[2560:2563]=[449,-449,0]
    qn=np.linspace(.5,1.5,128,dtype=np.float32)
    kn=qn[::-1].copy()
    data,checks=V.compose(V.G.bits(raw),0x3f800000,qn,kn,1e-6,17,1e6)
    assert data['q_norm_bits'].shape==(16,128) and data['k_norm_bits'].shape==(4,128)
    assert data['q_bf16_bits'].dtype==np.uint16
    assert data['v_fp8_bits'].ravel()[:3].tolist()==[0x7e,0xfe,0]
    assert checks==dict(nonfinite=0,fp8_saturation_inputs=2,deployed_boundary_mismatches=0)
