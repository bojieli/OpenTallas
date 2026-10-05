"""Source-bound finite-F32 index quantizer/68B packer and full-scale decoder.

Ordinary FP32/INT32 instructions reproduce qdq_fp4_e8m0's rounding boundaries.
No native quantizer, FP64 consumer, table lookup or FP32 scaling of signedzero.
Finite F32 input reaches UE8M0 codes1..253. Nonfinite input is explicitly outside
this admitted domain; no claim that the unchanged source rejects such input.
Hardware costs/reconvergence/provider/phase admission are still unresolved.
"""
import numpy as np
import deepseek_hbm_complete_index as X
import hdc_golden as G
import hdc_golden_v41 as V

ins=X.K.ins
branch=X.K.branch
BASE_BITS=(0,0x3f000000,0x3f800000,0x3fc00000,0x40000000,0x40400000,0x40800000,0x40c00000)
MID_BITS=(0x3e800000,0x3f400000,0x3fa00000,0x3fe00000,0x40200000,0x40600000,0x40a00000)
PACKED=1
DECODED_F32=2


def classify_program():
    p=[ins('LOAD','bits','input'),ins('AND','exponent','bits',0x7f800000),
       ins('IEQ','exception','exponent',0x7f800000)]
    for offset in [16,8,4,2,1]:
        p += [{'op':'SHFL','dst':'other','src':['exception'],'offset':offset},
              ins('OR','exception','exception','other')]
    return p+[{**ins('STORE','flags','exception'),'predicate_stride':32}]


def route_program():
    p=[ins('MOV','flag',0)]
    for block in range(4):
        p += [{**ins('LOAD','partial',f'block{block}'),'broadcast':True},ins('OR','flag','flag','partial')]
    return p+[{**ins('STORE','route','flag'),'predicate_stride':32}]


def classify(values):
    a=np.asarray(values,np.float32)
    if a.shape!=(128,):raise ValueError('source index row128')
    m=X.SIMT((4,32),{'input':a.reshape(4,32).view(np.uint32)}).run(classify_program())
    flags=m.stores['flags'][:,0]
    r=X.SIMT((1,32),{f'block{j}':flags[j] for j in range(4)}).run(route_program())
    return bool(r.stores['route'][0,0]),[m,r]


def scale_bits(dst,value,exponent,prefix):
    """Exact dyadic scaling to F32 bits, incl subnormal and infinity, no FMUL.

    All source values are small dyadics; at scale exponent>=-126 subnormal
    shifts are<=2 and exact, so no discarded nonzero bit/RNE approximation.
    """
    a=lambda n:prefix+n
    p=[ins('AND',a('sign'),value,0x80000000),ins('AND',a('abs'),value,0x7fffffff)]
    body=[ins('SHR',a('bias'),a('abs'),23),ins('IADD',a('bias'),a('bias'),exponent),
          ins('AND',a('mant'),a('abs'),0x7fffff)]
    sub=[ins('OR',a('sig'),a('mant'),0x800000),ins('ISUB',a('shift'),1,a('bias')),
         ins('SHR',a('out'),a('sig'),a('shift'))]
    normal=[ins('SHL',a('hi'),a('bias'),23),ins('OR',a('out'),a('hi'),a('mant'))]
    body += [branch('BGT',a('bias'),254,[ins('MOV',a('out'),0x7f800000)],
                    [branch('BLT',a('bias'),1,sub,normal)]),ins('OR',dst,a('out'),a('sign'))]
    return p+[branch('BEQ',a('abs'),0,[ins('MOV',dst,a('sign'))],body)]


def bf16_bits(dst,value,prefix):
    a=lambda n:prefix+n
    return [ins('SHR',a('hi'),value,16),ins('AND',a('odd'),a('hi'),1),
            ins('IADD',a('bias'),a('odd'),0x7fff),ins('IADD',a('rounded'),value,a('bias')),
            ins('AND',dst,a('rounded'),0xffff0000)]


def quant_program():
    # One warp holds32 contiguous terms of one source quantizer block.
    p=[ins('LOAD','x','input'),ins('AND','abs','x',0x7fffffff),ins('MOV','amax','abs')]
    for offset in [16,8,4,2,1]:
        p += [{'op':'SHFL','dst':'other','src':['amax'],'offset':offset}]
        p += X.L.compare('amax','amax','other',True,'max_')
    floor=int(G.bits(V.FP4_AMAX_FLOOR_E8M0));inverse=int(G.bits(V.FP4_MAX_INV))
    p += X.L.compare('amax','amax',floor,True,'floor_')
    p += [ins('FMUL','s','amax',inverse),ins('SHR','e','s',23),ins('AND','e','e',255),
          ins('ISUB','e','e',127),ins('AND','fraction','s',0x7fffff),ins('INE','ceil','fraction',0),
          ins('IADD','e','e','ceil'),ins('MOV','code',0)]
    for lower,midpoint in enumerate(MID_BITS):
        p += scale_bits('threshold',midpoint,'e','threshold_')
        p += [ins('FCMP_GT','above','abs','threshold'),ins('IEQ','tie','abs','threshold'),
              ins('AND','tie_up','tie',lower&1),ins('OR','choose','above','tie_up'),
              # Ordered thresholds make the latest crossing the next code.
              branch('BEQ','choose',1,[ins('MOV','code',lower+1)],[])]
    # Source np.sign turns input-0 into+0, but negative nonzero rounding to0
    # retains negativezero. Do not use the canonical-zero FP32 multiply pipe.
    p += [ins('FCMP_LT','negative','x',0),ins('SHL','signcode','negative',3),
          ins('OR','code','code','signcode'),ins('IADD','scale','e',127),
          ins('STORE','codes','code'),{**ins('STORE','scales','scale'),'predicate_stride':32}]
    return p


def pack_program():
    # A warp hasone row/lane and assembles its seventeen U32 wire words.
    p=[]
    for word in range(16):
        p += [ins('MOV','packed',0)]
        for nibble in range(8):
            p += [ins('LOAD','code',f'code{word*8+nibble}'),ins('SHL','part','code',nibble*4),
                  ins('OR','packed','packed','part')]
        p += [ins('STORE',f'word{word}','packed')]
    p += [ins('MOV','packed',0)]
    for block in range(4):
        p += [ins('LOAD','scale',f'scale{block}'),ins('SHL','part','scale',block*8),ins('OR','packed','packed','part')]
    return p+[ins('STORE','word16','packed')]


def decode_program():
    p=[]
    for j in range(128):
        p += [ins('LOAD','packed',f'word{j//8}'),ins('SHR','code','packed',4*(j%8)),
              ins('AND','code','code',15),ins('AND','magnitude','code',7),ins('MOV','base',0)]
        for code,bits in enumerate(BASE_BITS):
            p += [ins('IEQ','choose','magnitude',code),ins('ISUB','mask',0,'choose'),
                  ins('AND','part','mask',bits),ins('OR','base','base','part')]
        p += [ins('AND','sign','code',8),ins('SHL','sign','sign',28),ins('OR','base','base','sign'),
              ins('LOAD','scales','word16'),ins('SHR','scale','scales',(j//32)*8),ins('AND','scale','scale',255),
              ins('ISUB','e','scale',127)]
        p += scale_bits('bits','base','e','decode_')+bf16_bits('out','bits','round_')
        p += [ins('STORE',f'value{j}','out')]
    return p


def quantize_pack(values):
    """Actual prequant-input producer entry, no inverse packing of decoded rows."""
    values=np.asarray(values,np.float32)
    if values.ndim!=2 or values.shape[1]!=128 or not 1<=len(values)<=64:
        raise ValueError('finite 1..64 rows of128 source terms')
    if not np.all(np.isfinite(values)):raise ValueError('nonfinite producer input domain not admitted')
    q=X.SIMT((len(values)*4,32),{'input':values.reshape(-1,32).view(np.uint32)}).run(quant_program())
    codes=q.stores['codes'].reshape(len(values),128)
    scales=q.stores['scales'][:,0].reshape(len(values),4)
    if np.any(scales<1) or np.any(scales>253):raise AssertionError('finite source scale proof violated')
    pad=(-len(values))%32;c=np.pad(codes,((0,pad),(0,0)));s=np.pad(scales,((0,pad),(0,0)))
    m=X.SIMT((len(c)//32,32),{**{f'code{j}':c[:,j].reshape(-1,32) for j in range(128)},
                             **{f'scale{j}':s[:,j].reshape(-1,32) for j in range(4)}}).run(pack_program())
    words=np.stack([m.stores[f'word{j}'].reshape(-1)[:len(values)] for j in range(17)],axis=-1)
    payload=np.ascontiguousarray(words.astype('<u4')).view(np.uint8).reshape(len(values),68)
    decoded,d=unpack(payload)
    return payload,decoded,{'quantizer':q,'packer':m,'decoder':d}


def unpack(rows):
    rows=np.asarray(rows)
    if rows.dtype!=np.uint8 or rows.ndim!=2 or rows.shape[1]!=68 or not 1<=len(rows)<=64:
        raise ValueError('bounded uint8 wire rows')
    if np.any(rows[:,64:]<1) or np.any(rows[:,64:]>253):
        raise ValueError('scales0/254/255 unreachable for finite input; malformed/nonfinite domain not admitted')
    n=len(rows);words=np.ascontiguousarray(rows).view('<u4').reshape(n,17)
    words=np.pad(words,((0,(-n)%32),(0,0)))
    m=X.SIMT((len(words)//32,32),{f'word{j}':words[:,j].reshape(-1,32) for j in range(17)}).run(decode_program())
    values=np.stack([m.stores[f'value{j}'].reshape(-1)[:n] for j in range(128)],axis=-1).view(np.float32)
    return values,m


class ProducedRow(np.ndarray):
    """Produced decoded row and the payload from the same quantizer invocation."""
    def __new__(cls,value,payload,format_tag=PACKED):
        row=np.asarray(value,np.float32).copy().view(cls);row.wire_payload=bytes(payload);row.format_tag=format_tag;return row


def decode_payload(format_tag,payload):
    if format_tag==PACKED:
        if len(payload)!=68:raise ValueError('packed payload68')
        decoded,_=unpack(np.frombuffer(payload,np.uint8)[None,:]);return decoded[0]
    if format_tag==DECODED_F32:
        if len(payload)!=512:raise ValueError('decoded F32 payload512')
        # Exact bit transport: do not apply another rounding/canonicalzero op.
        return np.frombuffer(payload,dtype='<u4').copy().view(np.float32)
    raise ValueError('unknown row format')


class ProducerBinding:
    """Opt-in replacement bound to existing source qdq_fp4_e8m0 call sites.

    Returned decoded values AND their produced payload are retained together.
    No StateArray/controller residency integration is claimed by this class.
    """
    def __init__(self):self.receipts=[];self.last_payload=None
    def qdq_fp4_e8m0(self,x,block=32):
        if block!=32:raise ValueError('source block32')
        a=np.asarray(x,np.float32)
        if a.shape!=(128,):raise ValueError('source index row128')
        exceptional,classifier=classify(a)
        if exceptional:
            # Actual unchanged source produces these decoded bits. Retain them;
            # never inverse-pack a NaN/Inf row or invent an exponent escape.
            # This macro has NOT been lowered/credited as ordinary GPU math.
            with np.errstate(over='ignore',invalid='ignore',under='ignore'):decoded=V.qdq_fp4_e8m0(a,block)
            self.last_payload=np.asarray(decoded,dtype='<f4').tobytes()
            self.receipts.append({'format':DECODED_F32,'payload_bytes':512,
                'producer':'retained source qdq_fp4_e8m0 reference macro',
                'ordinary_GPU_producer_lowered':False,'GPU_cycles':None,
                'ordinary_classification_programs':[m.summary() for m in classifier]})
            return ProducedRow(decoded,self.last_payload,DECODED_F32)
        payload,decoded,programs=quantize_pack(a[None,:]);self.last_payload=payload[0].tobytes()
        self.receipts.append({'format':PACKED,'payload_bytes':68,
                             'ordinary_programs':{k:v.summary() for k,v in programs.items()},
                             'ordinary_classification_programs':[m.summary() for m in classifier]})
        return ProducedRow(decoded[0],self.last_payload,PACKED)
