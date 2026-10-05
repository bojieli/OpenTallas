#!/usr/bin/env python3
"""Demand-paged native S82 ROM word compiler and source execution fragment API.

Software interface only: no RTL, physical admission, numerical matvec or inference.
Copies of scales in word formats are codec metadata, not extra weight owners.
"""
import json, math, os, struct
from pathlib import Path
import dsrom_s73_pair1 as M

SNAPSHOT='dba1be0a40aa45a94ad051997016db3960a90277'
DEFAULT_CHECKPOINT=Path.home()/'.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots'/SNAPSHOT

class Checkpoint:
    """Read exact source bits with pread, without constructing a second 510GB image."""
    def __init__(self, root=DEFAULT_CHECKPOINT):
        self.root=Path(root)
        self.index=json.loads((self.root/'model.safetensors.index.json').read_text())['weight_map']
        self.files={};self.read_bytes=0
    def descriptor(self,tensor):
        shard=self.index[tensor]
        if shard not in self.files:
            fd=os.open(self.root/shard,os.O_RDONLY)
            try:
                n=struct.unpack('<Q',os.pread(fd,8,0))[0]
                header=json.loads(os.pread(fd,n,8))
            except BaseException:
                os.close(fd);raise
            self.files[shard]=(fd,8+n,header)
        fd,base,header=self.files[shard]
        return fd,base,header[tensor]
    def raw(self,tensor,offset,length):
        fd,base,d=self.descriptor(tensor);a,b=d['data_offsets']
        if offset<0 or length<0 or offset+length>b-a:raise ValueError('source byte bounds')
        data=os.pread(fd,length,base+a+offset)
        if len(data)!=length:raise EOFError(tensor)
        self.read_bytes+=length
        return data
    def element(self,tensor,row,col=0):
        _,_,d=self.descriptor(tensor)
        shape=d['shape'];cols=shape[-1] if len(shape)>1 else 1
        count=math.prod(shape)
        i=row*cols+col
        if not 0<=col<cols or not 0<=i<count:raise ValueError('source element bounds')
        width={'F32':4,'BF16':2,'F8_E4M3':1,'F8_E8M0':1,'I8':1,'U8':1}[d['dtype']]
        return int.from_bytes(self.raw(tensor,i*width,width),'little')
    def close(self):
        for fd,_,_ in self.files.values():os.close(fd)
        self.files.clear()

def scale_value(m,source,row,col):
    return source.element(m['source_scale_tensor'],row if m['source_dtype']=='I8' else row//32,col//32)

def payload_value(m,source,rank,row,k):
    """Value as stored by the declared codec; preserve the golden BF16 RNE boundary."""
    a=M.physical_address(m,rank,row,k);sr,sk=a['source_row'],a['source_col']
    if m['format']=='fp4':
        code=source.element(m['tensor'],sr,sk//2)
        return (code>>(4*(sk%2)))&15
    v=source.element(m['tensor'],sr,sk)
    if m['conversion']=='FP8+UE8M0->BF16_RNE':
        import numpy as np
        from tools import hdc_golden as G
        from tools import hdc_golden_v41 as V
        if v in (127,255):raise ValueError('E4M3 NaN')
        exponent=scale_value(m,source,sr,sk)-127
        with np.errstate(over='ignore',invalid='ignore'):
            dense=np.array([V.E4M3[v]*np.exp2(exponent)],dtype=np.float32)
        return int(G.bits(G.to_bf16(dense))[0]>>16)
    if m['conversion']!='native':raise ValueError('unknown conversion')
    return v

def word_coordinates(m,rank,macro,physical_row):
    """Inverse physical word decoder. Reject unowned words, including retained replicas."""
    owners=m.get('physical_owner_ranks',[0,1,2,3])
    if rank not in owners:raise ValueError('rank is multicast consumer, not physical weight owner')
    if not 0<=physical_row<4096 or not 0<=macro<4*m['compiled_NP']:raise ValueError('macro bounds')
    pair,leaf=divmod(macro,4);mb,parity=divmod(leaf,2);word=2*physical_row+parity
    runs=[r for r in m['plans'] if r[1]==pair and r[5]<=word<r[5]+r[3]*r[6]]
    if len(runs)!=1:raise ValueError('word has no unique matrix owner')
    si,_,first,n,stride,start,w=runs[0]
    index,j=divmod(word-start,n);row=2*(first+j*stride)+mb
    e,length=m['segments'][si];order=M.C.S.segment_order(m['format'],e,length)
    if len(order)!=w:raise ValueError('word run/codec length mismatch')
    u,b,h=order[index]
    slots=M.C.S.word_slots(m['format'],e,length,u,b,h)
    result=[]
    for slot,k in enumerate(slots):
        if k<0 or row>=m['rows']:continue
        if m['format']=='bf16':result.append((row,k,16*slot,16))
        else:
            result.extend((row,k+j,(136*slot if m['format']=='fp4' else 0)+j*(4 if m['format']=='fp4' else 8),4 if m['format']=='fp4' else 8)
                          for j in range(min(32,e+length-k,m['K']-k)))
    return result

def matrix_word(m,source,rank,macro,physical_row):
    """Compile a single 274-bit word; unused bits zero, ROM ECC omitted."""
    coords=word_coordinates(m,rank,macro,physical_row);word=0
    for row,k,bit,width in coords:
        value=payload_value(m,source,rank,row,k)
        if not 0<=value<1<<width:raise ValueError('codec width')
        word|=value<<bit
    if m['format']!='bf16':
        scales={}
        for row,k,bit,width in coords:
            a=M.physical_address(m,rank,row,k)
            sb=128+136*(k%512//256) if m['format']=='fp4' else 256
            v=scale_value(m,source,a['source_row'],a['source_col'])
            if sb in scales and scales[sb]!=v:raise ValueError('inconsistent word scale')
            scales[sb]=v
        for bit,v in scales.items():word|=v<<bit
    if word>>274:raise ValueError('physical word width')
    return word

def auxiliary_address(tensor,offset):
    if not 0<=offset<tensor['source_storage_bytes']:raise ValueError('auxiliary source bounds')
    spans=[s for s in tensor['payload_spans'] if s['source_byte_range'][0]<=offset<s['source_byte_range'][1]]
    if len(spans)!=1:raise ValueError('auxiliary owner')
    s=spans[0];byte=s['pair_data_byte_range'][0]+offset-s['source_byte_range'][0]
    word,byte_lane=divmod(byte,32);slot,a=divmod(word,8192)
    return dict(stage=s['stage'],rank=s['rank'],macro=4*s['pair']+2*slot+a%2,row=a//2,bit=8*byte_lane)

def auxiliary_word(tensors,source,stage,rank,macro,row):
    if not 0<=row<4096 or not 0<=macro<9552 or rank not in range(4) or not 0<=stage<82:raise ValueError('auxiliary physical bounds')
    pair,leaf=divmod(macro,4);slot,parity=divmod(leaf,2)
    start=32*(slot*8192+2*row+parity);end=start+32
    data=bytearray(32);occupied=set()
    for t in tensors:
        for s in t['payload_spans']:
            if (s['stage'],s['rank'],s['pair'])!=(stage,rank,pair):continue
            lo=max(start,s['pair_data_byte_range'][0]);hi=min(end,s['pair_data_byte_range'][1])
            if lo>=hi:continue
            lanes=set(range(lo-start,hi-start))
            if occupied & lanes:raise ValueError('auxiliary byte overlap')
            occupied|=lanes
            offset=s['source_byte_range'][0]+lo-s['pair_data_byte_range'][0]
            data[lo-start:hi-start]=source.raw(t['tensor'],offset,hi-lo)
    if not occupied:raise ValueError('unowned auxiliary word')
    return int.from_bytes(data,'little')

def provider_word(provider,source,macro,row):
    """Compile the canonical rank-0 HE/CROM word using explicit native offsets."""
    pair,leaf=divmod(macro,4);mb,parity=divmod(leaf,2)
    if pair not in provider['pairs'] or not 0<=row<4096:raise ValueError('provider physical bounds')
    slots=math.ceil(provider['words_per_bank']/8192)
    linear_slot=2*provider['pairs'].index(pair)+mb
    bank,slot=divmod(linear_slot,slots)
    native_word=slot*8192+2*row+parity
    if bank>=provider['banks'] or native_word>=provider['words_per_bank']:raise ValueError('unowned provider padding')
    word=0
    for lane in range(8):
        if provider['kind']=='HE':
            ds=[d for d in provider['declarations'] if d['native_bank_word_base']<=native_word<d['native_bank_word_base']+d['rows']*math.ceil(d['K']/64)]
            if len(ds)!=1:raise ValueError('HE word identity')
            d=ds[0];sr,beat=divmod(native_word-d['native_bank_word_base'],math.ceil(d['K']/64))
            col=beat*64+lane*8+bank
            if col>=d['K']:continue
            v=source.element(d['tensor'],sr,col)
        elif provider['kind']=='CROM':
            index=8*native_word+lane
            ds=[d for d in provider['declarations'] if d['native_FP32_element_base']<=index<d['native_FP32_element_base']+d['elements']]
            if not ds:continue
            if len(ds)!=1:raise ValueError('CROM element identity')
            d=ds[0];flat=index-d['native_FP32_element_base']
            _,_,header=source.descriptor(d['tensor'])
            cols=header['shape'][-1] if len(header['shape'])>1 else 1
            v=source.element(d['tensor'],flat//cols,flat%cols)
            if d['dtype']=='BF16':v<<=16
            elif d['dtype']!='F32':raise ValueError('unsupported constant expansion')
        else:raise ValueError('provider kind')
        if v>>32:raise ValueError('FP32 width')
        word|=v<<(lane*32)
    return word

def execution_fragments(matrices,layer,alias,rank,expert_ids=None,selector_slot=None):
    """Bind runtime source operation to ordered row fragments and real source ranks.

    Dispatch each fragment only after its producer input is available; this API
    supplies addresses, not a zero-latency dispatch/multicast/gather assumption.
    """
    if rank not in range(4):raise ValueError('rank')
    if selector_slot is not None:
        if expert_ids is None or len(expert_ids)!=6 or any(type(e)!=int or not 0<=e<384 for e in expert_ids) or list(expert_ids)!=sorted(set(expert_ids)):
            raise ValueError('six distinct ascending runtime EIDs')
        if not 0<=selector_slot<6 or not alias.startswith('exp0.'):raise ValueError('selector identity')
        alias=alias.replace('exp0.',f'exp{expert_ids[selector_slot]}.',1)
    elif expert_ids is not None:raise ValueError('unexpected expert IDs')
    fragments=[m for m in matrices if m['layer']==layer and m.get('original_alias',m['alias'])==alias]
    if not fragments:raise KeyError((layer,alias))
    fragments.sort(key=lambda m:m.get('row_offset',0))
    expected=0
    result=[]
    for m in fragments:
        if m.get('row_offset',0)!=expected:raise ValueError('row gather gap/overlap')
        expected+=m['rows']
        a=M.physical_address(m,rank,0,0)
        result.append(dict(matrix=m,die_id=4*m['stage']+a['physical_owner_rank'],
            requested_rank=rank,source_slice=m['rank_slices'][rank],
            gather_local_rows=[m.get('row_offset',0),expected],ordered_K=m['segments'],
            result_multicast_required=a['owner_result_multicast_required'],
            dispatch_timing_qualified=False))
    return result

class SourceExecution:
    """Resolve pinned descriptor IDs into S82 fragments using live EID values.

    Retained node records provide source operation identity only. Old stage,
    phase, address patches and native admission verdicts never authorize S82.
    """
    def __init__(self,matrices,bindings,demand):
        import hashlib
        self.matrices={}
        for m in matrices:
            self.matrices.setdefault((m['layer'],m.get('original_alias',m['alias'])),[]).append(m)
        self.nodes={n['id']:n for n in demand['nodes']};self.bindings={}
        for b in bindings:
            if b['node'] in self.bindings:raise ValueError('duplicate source binding')
            if b.get('address_bound') or b.get('alias')=='head':
                n=self.nodes[b['node']]
                digest=hashlib.sha256(json.dumps(n,sort_keys=True,separators=(',',':')).encode()).hexdigest()
                if digest!=b['source_node_semantic_sha256']:raise ValueError('source node identity')
                if n['template_word_sha256']!=b['template_word_sha256']:raise ValueError('source template identity')
            self.bindings[b['node']]=b
        if set(self.bindings)!=set(self.nodes):raise ValueError('source node coverage')
    def resolve(self,node,rank,expert_ids=None):
        b=self.bindings[node]
        if not b.get('address_bound'):raise ValueError('non-field operation requires dedicated execution interface')
        slot=b['selector_slot'];alias=b['alias']
        if slot is not None:
            if expert_ids is None or len(expert_ids)!=6 or any(type(e)!=int or not 0<=e<384 for e in expert_ids) or list(expert_ids)!=sorted(set(expert_ids)):
                raise ValueError('six distinct ascending runtime EIDs')
            alias=alias.replace('exp0.',f'exp{expert_ids[slot]}.',1)
        elif expert_ids is not None:raise ValueError('unexpected expert IDs')
        ms=self.matrices[(b['layer'],alias)]
        f=execution_fragments(ms,b['layer'],alias,rank)
        instruction=self.nodes[node]['instruction']
        qe=b['kind']=='QE'
        rows=instruction['qe_nout'] if qe else instruction['me_nout']
        K=instruction['qe_nb']*32 if qe else instruction['me_k']*(1<<instruction.get('me_split',0))
        if sum(x['matrix']['rows'] for x in f)!=rows or any(x['matrix']['K']!=K for x in f):raise ValueError('source operation dimensions')
        return dict(node=node,fragments=f,input_VM_elements=b['consumer_X_FP32_VM_elements'],
            output_VM_base=b['consumer_output_base_elements'],predicate=b['instruction_predicate'],
            output_format=b['output_format'],source_identity_verified=True,
            native_dispatch_qualified=False,calendar_qualified=False)

class DieROM:
    """Bind one actual S82 rank die's physical macros to native payload owners.

    The index uses only this die's word intervals. Unowned/padding words are
    rejected, so a missing initializer cannot masquerade as a zero weight.
    """
    def __init__(self,stage,rank,matrices,providers,auxiliary):
        if stage not in range(82) or rank not in range(4):raise ValueError('S82 rank die')
        self.stage,self.rank=stage,rank;self.intervals={};self.providers={};self.aux={}
        for m in matrices:
            if m['stage']!=stage or rank not in m['physical_owner_ranks']:continue
            for si,p,first,n,stride,start,w in m['plans']:
                self.intervals.setdefault(p,[]).append((start,start+n*w,m))
        for p in providers:
            if p['stage']!=stage or rank!=p['physical_owner_rank']:continue
            for pair in p['pairs']:
                if pair in self.providers:raise ValueError('duplicate raw provider')
                self.providers[pair]=p
        for t in auxiliary:
            for s in t['payload_spans']:
                if (s['stage'],s['rank'])==(stage,rank):
                    entries=self.aux.setdefault(s['pair'],[])
                    if not any(existing is t for existing in entries):entries.append(t)
        if (set(self.intervals)&set(self.providers) or set(self.intervals)&set(self.aux)
                or set(self.providers)&set(self.aux)):raise ValueError('physical payload class overlap')
        for pair,runs in self.intervals.items():
            if pair not in range(2388):raise ValueError('element bounds')
            runs.sort(key=lambda r:r[0])
            if any(a[1]>b[0] for a,b in zip(runs,runs[1:])):raise ValueError('physical matrix overlap')
    def read(self,source,macro,row):
        if macro not in range(9552) or row not in range(4096):raise ValueError('physical macro bounds')
        pair,leaf=divmod(macro,4);word=2*row+leaf%2
        if pair in self.providers:return provider_word(self.providers[pair],source,macro,row)
        if pair in self.aux:return auxiliary_word(self.aux[pair],source,self.stage,self.rank,macro,row)
        matches=[m for a,b,m in self.intervals.get(pair,[]) if a<=word<b]
        if len(matches)!=1:raise ValueError('no unique physical payload owner')
        return matrix_word(matches[0],source,self.rank,macro,row)
    def inventory(self):
        return dict(stage=self.stage,rank=self.rank,die_id=4*self.stage+self.rank,
            physical_weight_macros=9552,actual_field_pairs=2388,BF_dual_pairs=512,q_only_pairs=1876,
            matrix_owner_pairs=len(self.intervals),raw_provider_owner_pairs=len(self.providers),
            auxiliary_owner_pairs=len(self.aux),ROM_ECC=False,field_padding_pairs=0,
            unowned_frames_still_charged=True,physical_admission=False)
