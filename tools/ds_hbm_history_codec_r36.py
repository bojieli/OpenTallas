"""Explicit FP4 data representation for source-declared QDQ entering rows.
Encoding runs only in provider data preparation, not an operator callback.
Every encoding must decode bit-exactly; unsupported float payloads fail closed.
"""
import numpy as np
from ds_hbm_source_inputs_r34 import codecs

def encode(rows,mode):
    _,G,V,_=codecs();x=np.asarray(rows)
    if x.dtype!=np.float32 or x.ndim!=2 or not np.all(np.isfinite(x)):raise ValueError('finite typed source rows')
    block=16 if mode=='FP4E4' else 32 if mode=='FP4E8' else None
    if block is None or x.shape[1]%block:raise ValueError('source FP4 block geometry')
    a=x.reshape(-1,block);amax=np.maximum(np.max(np.abs(a),axis=1),V.FP4_AMAX_FLOOR_E4M3 if mode=='FP4E4' else V.FP4_AMAX_FLOOR_E8M0).astype(np.float32)
    if mode=='FP4E4':
        scale=np.minimum(V._e4m3_round(amax.astype(np.float64)/6.0),448.0)
        code=np.zeros(a.shape,np.int64);absolute=np.abs(a.astype(np.float64))
        for i,mid in enumerate(V.E2M1_MIDPOINTS):
            threshold=mid*scale[:,None];code=np.where((absolute>threshold)|((absolute==threshold)&((i+1)%2==0)),i+1,code)
        positive=V.E4M3[:127]
        scale_codes=np.searchsorted(positive,scale)
        if np.any(scale_codes>=127) or not np.array_equal(positive[scale_codes],scale):raise ValueError('exact finite source E4M3 scale')
        scales=scale_codes.astype(np.uint32).reshape(x.shape[0],-1)
    else:
        exp=V._ceil_log2(G.mul(amax,V.FP4_MAX_INV));scale=np.exp2(exp)
        q=V._round_grid(np.clip(a.astype(np.float64)*np.exp2(-exp)[:,None],-6.,6.),0,1)
        code=np.searchsorted(V.E2M1_VALUES,np.abs(q));scales=exp.astype(np.int64).reshape(x.shape[0],-1)
    # Sign bit is retained for negative zero in the data representation.
    code=code.astype(np.uint8)|(np.signbit(a).astype(np.uint8)<<3)
    flat=code.reshape(x.shape);packed=(flat[:,0::2]|(flat[:,1::2]<<4)).astype(np.uint32)
    out=decode(packed,scales,mode)
    if not np.array_equal(out.view(np.uint32),x.view(np.uint32)):raise ValueError('source row is not bit-exactly representable in declared FP4 codec')
    return packed,scales

def decode(packed,scales,mode):
    _,G,V,_=codecs();p=np.asarray(packed)
    if p.dtype!=np.uint32 or p.ndim!=2 or np.any(p>255):raise ValueError('paired raw packed bytes in U32 containers')
    nib=np.stack([p&15,p>>4],axis=2).reshape(p.shape[0],-1);values=np.array([0.,.5,1.,1.5,2.,3.,4.,6.,-0.,-.5,-1.,-1.5,-2.,-3.,-4.,-6.],np.float32)[nib]
    block=16 if mode=='FP4E4' else 32 if mode=='FP4E8' else None
    if block is None:raise ValueError('declared source codec')
    if np.asarray(scales).shape!=(p.shape[0],values.shape[1]//block):raise ValueError('paired scale shape')
    if mode=='FP4E4':
        if scales.dtype!=np.uint32 or np.any(scales>=127):raise ValueError('finite positive E4M3 scale bytes')
        s=V.E4M3[scales]
    else:
        if scales.dtype!=np.int64:raise ValueError('signed UE8M0 source exponents')
        s=np.exp2(scales)
    return G.to_bf16((values.reshape(p.shape[0],-1,block)*s[:,:,None]).astype(np.float32)).reshape(values.shape)
