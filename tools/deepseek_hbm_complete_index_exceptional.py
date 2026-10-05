"""Ordinary INT32 exceptional qdq producer derived from the actual source.

NaN block maximum gives source exponent129; Inf-only maximum gives128.
Neither exponent is forced into UE8M0. Produce decoded F32 bits, including the
source's BF16 payload-carry-to-negativezero corner, for tagged512B transport.
Finite blocks execute the existing ordinary finite quantizer. No FP64 compute.
All emitted instruction events are interpreted software, not DUT clock events.
"""
from collections import Counter
import hashlib
import numpy as np
import deepseek_hbm_complete_index_codec as C
import deepseek_hbm_complete_index as X
import deepseek_hbm_complete_canonical as Canon

ins=X.K.ins
branch=X.K.branch


def exceptional_program():
    p=[ins('LOAD','x','input'),ins('AND','abs','x',0x7fffffff),
       ins('AND','exp','x',0x7f800000),ins('IEQ','special','exp',0x7f800000),
       ins('AND','mant','x',0x7fffff),ins('INE','mant_nonzero','mant',0),
       ins('AND','isnan','special','mant_nonzero'),ins('MOV','anynan','isnan')]
    for offset in [16,8,4,2,1]:
        p += [{'op':'SHFL','dst':'other','src':['anynan'],'offset':offset},ins('OR','anynan','anynan','other')]
    p += [ins('AND','sign','x',0x80000000)]
    # Finite terms under source e129: q0 below/tied2^127, q.5 above,
    # with .5*2^129 overflowing F32. Source sign(-0) is+0.
    nan_block_finite=[branch('BGT','abs',0x7f000000,[ins('MOV','magnitude',0x7f800000)],
                            [ins('MOV','magnitude',0)])]
    # Source e128: midpoint.25 at2^126 ties to q0; midpoint.75 at
    # 3*2^126 ties to q1, which overflows. Interior q.5 yields2^127.
    inf_block_finite=[branch('BGT','abs',0x7e800000,
        [branch('BLT','abs',0x7f400000,[ins('MOV','magnitude',0x7f000000)],
                                      [ins('MOV','magnitude',0x7f800000)])],
        [ins('MOV','magnitude',0)])]
    finite=[branch('BEQ','abs',0,[ins('MOV','sign',0)],[]),
            branch('BEQ','anynan',1,nan_block_finite,inf_block_finite),ins('OR','out','magnitude','sign')]
    nan=[ins('OR','quiet','abs',0x00400000)]+C.bf16_bits('out','quiet','nanround_')
    p += [branch('BEQ','isnan',1,nan,
                 [branch('BEQ','special',1,[ins('OR','out',0x7f800000,'sign')],finite)]),
          ins('STORE','values','out')]
    return p


def normal_decoded_program():
    p=C.quant_program()+[ins('AND','magnitude','code',7),ins('MOV','base',0)]
    for code,bits in enumerate(C.BASE_BITS):
        p += [ins('IEQ','choose','magnitude',code),ins('ISUB','mask',0,'choose'),
              ins('AND','part','mask',bits),ins('OR','base','base','part')]
    p += [ins('AND','sign','code',8),ins('SHL','sign','sign',28),ins('OR','base','base','sign')]
    return p+C.scale_bits('bits','base','e','normaldecode_')+C.bf16_bits('out','bits','normalround_')+[ins('STORE','values','out')]


class TracedSIMT(X.SIMT):
    def __init__(self,*args,kernel,source_context=None,**kwargs):
        super().__init__(*args,**kwargs);self.kernel=kernel;self.source_context=source_context
        self.trace=[];self.writers={}
    def _values(self,array,mask):
        return [{'warp':w,'lanes':np.flatnonzero(mask[w]).tolist(),
                 'bits':np.asarray(array[w])[mask[w]].astype(np.uint32).tolist()}
                for w in range(len(mask)) if np.any(mask[w])]
    def run(self,program,active=None,path=()):
        active=np.ones(self.shape,bool) if active is None else active
        for pc,i in enumerate(program):
            mask=active.copy()
            if i.get('predicate_stride'):mask &= np.arange(32)[None,:]%i['predicate_stride']==0
            if not np.any(mask):continue
            operands=[];dependencies=set();bindings=[]
            for operand_index,symbol in enumerate(i['src']):
                shared=i['op']=='LOAD'
                array=self.array(self.memory[symbol]) if shared else self.read(symbol)
                immediate=isinstance(symbol,int) or symbol in X.CONST
                values={'kind':'shared' if shared else 'immediate' if immediate else 'register',
                        'symbol':symbol,'values':self._values(array,mask)}
                if shared:
                    values['logical_source_word_offsets']=[{'warp':w,'words':[w*32+lane for lane in np.flatnonzero(mask[w]).tolist()]}
                                                          for w in range(len(mask)) if np.any(mask[w])]
                elif not immediate:
                    prior=self.writers.get(symbol,np.full(self.shape,-1,np.int64))
                    for w,lane in zip(*np.nonzero(mask)):
                        source_lane=(int(lane)+i['offset'])%32 if i['op']=='SHFL' else int(lane)
                        producer=int(prior[w,source_lane])
                        if producer<0:raise AssertionError('uninitialized operand version')
                        producer_id=f'{self.kernel}:{producer}'
                        dependencies.add(producer_id)
                        bindings.append({'operand_index':operand_index,'register':symbol,
                            'warp':int(w),'lane':int(lane),'source_lane':source_lane,
                            'producer_event':producer_id,
                            'result_id':f'{producer_id}:{symbol}:{w}:{source_lane}'})
                operands.append(values)
            event_id=len(self.trace);event={'id':f'{self.kernel}:{event_id}','event_id':event_id,'kernel':self.kernel,'recipe_pc_path':list(path)+( [pc]),
                'source_context':self.source_context,'opcode':i['op'],'src':i['src'],'dst':i.get('dst'),
                'active_lanes':self._values(np.ones(self.shape,np.uint32),mask),
                'operand_reads':operands,'dependencies':sorted(dependencies),
                'operand_register_bindings':bindings,'result_register_bindings':[],
                'register_binding_domain':'executed virtual lane registers; physical allocation unbound',
                'RF_read_ports':2,'RF_write_ports':1,'RF_physical_register_allocation':None,
                'execution_kind':'software ordinary-op interpreter','hardware_cycle':None,
                'canonical_latency_candidate':Canon.KNOWN.get(i['op']),'actual_RF_ready_cycle':None,
                'actual_shared_visible_cycle':None,'actual_RF_writeback_cycle':None}
            self.trace.append(event)
            if i['op'].startswith('B'):
                a,b=[self.read(s).view(np.int32) for s in i['src']]
                take=(a==b) if i['op']=='BEQ' else (a<b) if i['op']=='BLT' else (a>b)
                yes=mask&take;no=mask&~take
                self.counts[i['op']]+=int(np.count_nonzero(np.any(mask,axis=1)))
                event['branch_taken_yes']=self._values(take.astype(np.uint32),yes)
                event['branch_taken_no']=self._values((~take).astype(np.uint32),no)
                self.run(i['yes'],yes,path+(pc,'yes'));self.run(i['no'],no,path+(pc,'no'))
            else:
                super().run([i],active)
                if i['op']=='STORE':
                    event['shared_write_values']=self._values(self.stores[i['dst']],mask)
                    event['logical_destination_word_offsets']=[{'warp':w,'words':[w*32+lane for lane in np.flatnonzero(mask[w]).tolist()]}
                                                              for w in range(len(mask)) if np.any(mask[w])]
                else:
                    event['register_write_values']=self._values(self.regs[i['dst']],mask)
                    event['result_register_bindings']=[{'register':i['dst'],'warp':int(w),'lane':int(lane),
                        'result_id':f'{self.kernel}:{event_id}:{i["dst"]}:{w}:{lane}'} for w,lane in zip(*np.nonzero(mask))]
                    prior=self.writers.setdefault(i['dst'],np.full(self.shape,-1,np.int64));prior[mask]=event_id
        return self


def produce(values,trace=False,source_context=None):
    a=np.asarray(values,np.float32)
    if a.shape!=(128,):raise ValueError('actual row128')
    memory={'input':a.reshape(4,32).view(np.uint32)}
    make=lambda kernel:TracedSIMT((4,32),memory,kernel=kernel,source_context=source_context) if trace else X.SIMT((4,32),memory)
    classifier=make('index_block_classify').run(C.classify_program())
    exceptional=classifier.stores['flags'][:,0]!=0
    normal=make('index_finite_producer').run(normal_decoded_program(),np.broadcast_to((~exceptional)[:,None],(4,32)))
    special=make('index_exceptional_producer').run(exceptional_program(),np.broadcast_to(exceptional[:,None],(4,32)))
    # Disjoint warp ownership writes the corresponding rows; this is byte
    # assembly of produced registers, not a host arithmetic/select primitive.
    out=np.zeros((4,32),np.uint32)
    for warp in range(4):out[warp]=(special if exceptional[warp] else normal).stores['values'][warp]
    programs={'classify':classifier,'finite_blocks':normal,'exceptional_blocks':special}
    return out.reshape(128).view(np.float32),programs


def witness(values,source_context=None):
    a=np.asarray(values,np.float32);out,programs=produce(a,True,source_context)
    with np.errstate(invalid='ignore',over='ignore',under='ignore'):reference=C.V.qdq_fp4_e8m0(a)
    if not np.array_equal(out.view(np.uint32),reference.view(np.uint32)):raise AssertionError('source exceptional producer mismatch')
    return {'source_input_F32_bits':a.view(np.uint32).tolist(),'source_input_bits_sha256':hashlib.sha256(a.tobytes()).hexdigest(),
            'actual_produced_F32_bits':out.view(np.uint32).tolist(),'retained_reference_F32_sha256':hashlib.sha256(reference.tobytes()).hexdigest(),
            'ordinary_program_receipts':{k:v.summary() for k,v in programs.items()},
            'executed_ordinary_events':{k:v.trace for k,v in programs.items()},
            'bit_exact':True,'FP64_operations':0,'DUT_RTL_executed':False,'hardware_cycles':None}
