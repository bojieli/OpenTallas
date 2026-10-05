"""Additive canonical GPU event calendar; earlier3cycleINT records preserved.

RF2+ADD/MUL/INTadd/FCMP core7 ->9 serialcycles; RF2+SHFLcore5 ->7.
DIV scalarII1/core19: one active lane issued each cycle, lastRFvisible at
2+(active-1)+19. Other INT variants have explicit UNBOUND cost, never zero.
No bank/quad/service mapping or contextual SS/FF qualification is invented.
"""
from collections import Counter
from copy import deepcopy
from types import FunctionType,SimpleNamespace
import w19_gpu_norm_calendar as N
import w19_gpu_attention_finish as A
import deepseek_hbm_complete_isa as I
import w19_gpu_compare_lowering as L

KNOWN={'FADD':9,'FMUL':9,'IADD':9,'ISUB':9,'FCMP_GT':9,'FCMP_LT':9,'SHFL':7,'LOAD':2,'STORE32':3,'STORE16':3,'DIV':21}
# Ordinary logic/shift/conversion/CLZ/multiply remains missing until a concrete
# canonicalGPU datapath cost is bound.9 is ONLY an interpreter scheduling proxy.
UNBOUND={'AND','OR','XOR','SHR','SHL','IEQ','INE','F2I','CLZ','IMUL','MOV','WIDEN'}


def events(program,active_lanes=32):
    if not 1<=active_lanes<=32:raise ValueError('finite warp active lanes')
    p=deepcopy(program);missing=Counter()
    for i in p:
        if i['op'] not in KNOWN:
            if i['op'] not in UNBOUND:raise ValueError('no canonical opcode mapping '+i['op'])
            missing[i['op']]+=1
        i['latency']=KNOWN.get(i['op'],9)
    # Arity/dependency/liveness validation only; old numerical code stays pinned.
    validator=FunctionType(L.calendar.__code__,{**L.calendar.__globals__,'C':SimpleNamespace(ARITY={**A.ARITY,**N.ARITY},CONSTANTS=A.CONSTANTS|N.CONSTANTS)})
    cal=validator(p,active_lanes);ready={};issue=0;slots=set();dividerfree=0;rows=[]
    for pc,i in enumerate(p):
        start=max([issue]+[ready.get(s,0) for s in i['src']]);lat=i['latency']+(active_lanes-1 if i['op']=='DIV' else 0)
        if i['op']=='DIV':start=max(start,dividerfree)
        end=start+lat
        while i['dst'] and end in slots:start+=1;end+=1
        if i['dst']:ready[i['dst']]=end;slots.add(end)
        row={'pc':pc,'opcode':i['op'],'src':i['src'],'dst':i['dst'],'RF_read_candidate':start,
             'RF_operand_ready_candidate':start+2,'RF_writeback_candidate':end if i['dst'] else None,
             'RF_ports':'2R1W','active_lanes':active_lanes,'shared_word_addresses':None,
             'shared_bank_mapping':None,'quad_locality':None,'opcode_cost_bound':i['op'] in KNOWN,
             'qualified_clock':None}
        if i['op']=='DIV':
            row['scalar_issue_events']=[{'lane':lane,'issue_candidate':start+2+lane,'core_complete_candidate':start+2+lane+19,'active_lanes':1} for lane in range(active_lanes)]
            dividerfree=start+2+active_lanes;row['dependent_vector_ready_candidate']=end
        else:row['issue_candidate']=start+2
        rows.append(row);issue=start+1
    return {'events':rows,'RF_peak_live_regs':cal['peak_live_value_registers'],'address_loop_regs':8,
      'candidate_cycles_assuming_UNBOUND_opcodes_9':cal['cycles'],'issue_cycles':None if missing else cal['cycles'],
      'unbound_opcode_counts':dict(missing),'timing_admission':'FAIL_CLOSED' if missing else 'CANDIDATE_NO_PHYSICAL_QUALIFICATION',
      'physical_bank_service_and_SSFF_bound':False,'DIVs_per_SM_cycle':1,'DIV_core_latency':19,'RF_read_latency':2}


class CanonicalWarpBackend(I.WarpBackend):
    def __init__(self):super().__init__();self.unpriced=Counter()
    def account(self,kind,p,m,warps,lanes,n,size):
        c=events(p,lanes);self.launches[kind]+=1;self.max_live=max(self.max_live,c['RF_peak_live_regs'])
        self.metrics['warp_invocations']+=warps;self.metrics['active_values']+=n;self.metrics['inactive_tail_values']+=size-n
        if c['issue_cycles'] is not None:self.metrics['known_serial_issue_candidate_cycles']+=warps*c['issue_cycles']
        else:self.metrics['warp_invocations_with_UNBOUND_opcode_cost']+=warps
        self.metrics['shared_issue_candidate_cycles']+=warps*m.admission['shared_issue_cycles']
        for k,v in c['unbound_opcode_counts'].items():self.unpriced[k]+=v*warps
        for i in p:
            self.opcodes[i['op']]+=warps;self.metrics['RF_operand_bits_including_immediates']+=warps*lanes*32*len(i['src'])
            if i['dst']:self.metrics['RF_write_bits']+=warps*lanes*32
            if i['shared']:self.metrics['shared_requested_bytes']+=warps*lanes*4
    def summary(self):
        r=super().summary();r.update(canonical_timing_basis='RF2+INTadd/FCMP/ADD/MUL7=9;SHFL5+RF2=7;scalarDIV19+RF2',
              unbound_opcode_counts=dict(self.unpriced),legacy3cycleINT_timing_adopted=False,
              full_graph_cycles=None,physical_calendar_admission='FAIL_CLOSED')
        return r
