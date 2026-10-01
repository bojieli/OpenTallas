"""Bounded decode replay from persisted source-produced bytes, no checkpoint/RTL."""
import ast,copy,hashlib,json,subprocess,types
from collections import Counter
from pathlib import Path
import numpy as np
import w13_index_f32_ports as P
REV='e49a98d09'
PATH='tools/deepseek_hbm_complete_index.py'
WPATH='results/rtl/deepseek_hbm_complete_20261001/index-tagged-producer-consumer-gate-r2.json'

def trace_decode():
    raw=subprocess.check_output(['git','show',REV+':'+PATH]);tree=ast.parse(raw)
    k=P.functions('w19_index32_integer_kernel',['ins','branch'],{})
    for node in ast.parse(P.source('w19_index32_integer_kernel')).body:
        if isinstance(node,ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name) and target.id in ('UNITS','ARITY'):setattr(k,target.id,ast.literal_eval(node.value))
    l=P.functions('w19_gpu_compare_lowering',['op','compare'],{})
    for node in ast.parse(P.source('w19_gpu_compare_lowering')).body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CONST' for t in node.targets):l.CONST=ast.literal_eval(node.value)
    env={'np':np,'Counter':Counter,'K':k,'L':l}
    selected=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in ('SIMT','decode_program','decode')]
    assignments=[n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('ARITY','CONST') for t in n.targets)]
    original_env=dict(env)
    exec(compile(ast.Module(body=copy.deepcopy(assignments+selected),type_ignores=[]),'unmodified_source_decode','exec'),original_env)
    cls=next(n for n in selected if isinstance(n,ast.ClassDef))
    method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='run')
    class Inject(ast.NodeTransformer):
        def visit_AugAssign(self,node):
            # One observer at the actual opcode count, after active mask/args.
            if ast.unparse(node.target)=='self.counts[code]':
                return [ast.parse('self.observe(i,args,mask)').body[0],node]
            return node
        def visit_Assign(self,node):
            if ast.unparse(node.targets[0])=='self.regs[i[\'dst\']]':
                return [node,ast.parse('self.result(i,mask)').body[0]]
            return node
    Inject().visit(method);module=ast.fix_missing_locations(ast.Module(body=assignments+selected,type_ignores=[]));exec(compile(module,'source_index_decode','exec'),env)
    Base=env['SIMT']
    class Traced(Base):
        def __init__(self,*a,**kw):
            super().__init__(*a,**kw);self.trace=[];self.versions={}
        def observe(self,i,args,mask):
            eid=len(self.trace);ops=[]
            for index,(name,value) in enumerate(zip(i['src'],args)):
                versions=self.versions.get(name)
                producer_ids=sorted(set(versions[mask].tolist())) if versions is not None else []
                ops.append({'operand_index':index,'source_name':name,'producer_result_ids':producer_ids,'producer_result_ids_by_active_lane':versions[mask].tolist() if versions is not None else [],'value_sha256':hashlib.sha256(np.asarray(value).tobytes()).hexdigest()})
            self.trace.append({'id':eid,'source_instruction_path':i['_source_path'],'op':i['op'],'dst':i.get('dst'),
                'operands':ops,'active_lane_indices':np.flatnonzero(mask).tolist(),'source_predicate_stride':i.get('predicate_stride'),
                'RF_read_tick':None,'issue_tick':None,'writeback_tick':None,'branch_decision':None})
            if i['op'].startswith('B'):
                a,b=[v.view(np.int32) for v in args];take=a==b if i['op']=='BEQ' else a<b if i['op']=='BLT' else a>b
                self.trace[-1]['branch_decision']={'yes_lanes':np.flatnonzero(mask&take).tolist(),'no_lanes':np.flatnonzero(mask&~take).tolist()}
        def result(self,i,mask):
            eid=self.trace[-1]['id'];name=i['dst'];versions=self.versions.setdefault(name,np.full(self.shape,-1,np.int32));versions[mask]=eid
            self.trace[-1]['result_id']=eid;self.trace[-1]['result_value_sha256']=hashlib.sha256(self.regs[name].tobytes()).hexdigest()
    env['SIMT']=Traced
    orig=env['decode_program']
    def program():
        p=orig()
        def assign(rows,prefix):
            for j,i in enumerate(rows):
                i['_source_path']=prefix+'/'+str(j)
                if i['op'].startswith('B'):assign(i['yes'],i['_source_path']+'/yes');assign(i['no'],i['_source_path']+'/no')
        assign(p,'decode32');return p
    env['decode_program']=program
    wr=subprocess.check_output(['git','show','e5d9ad00a:'+WPATH]);w=json.loads(wr)
    finite=[r for r in w['witnesses'] if all((v&0x7f800000)!=0x7f800000 for v in r['actual_produced_F32_bits'])]
    values=np.array([r['actual_produced_F32_bits'] for r in finite],np.uint32).view(np.float32)
    blocks=[]
    for b in range(4):
        units,exponents,m=env['decode'](values[:,b*32:b*32+32]);counts=Counter(e['op'] for e in m.trace)
        baseline_units,baseline_exponents,_=original_env['decode'](values[:,b*32:b*32+32])
        assert np.array_equal(units,baseline_units) and np.array_equal(exponents,baseline_exponents)
        assert dict(counts)==dict(m.counts)
        blocks.append({'block':b,'input_bytes_sha256':hashlib.sha256(values[:,b*32:b*32+32].tobytes()).hexdigest(),
            'executed_instruction_events':m.trace,'opcode_counts':dict(counts),'output_units_sha256':hashlib.sha256(units.tobytes()).hexdigest(),'output_exponents_sha256':hashlib.sha256(exponents.tobytes()).hexdigest(),
            'unmodified_source_output_equal':True,'physical_register_allocation':None,'branch_reconvergence_clock':None})
    return {'schema':'w13.index-finite-source-decode-replay.v1','source_pin':{'git':REV,'path':PATH,'sha256':hashlib.sha256(raw).hexdigest()},
        'persisted_input_pin':{'git':'e5d9ad00a','path':WPATH,'sha256':hashlib.sha256(wr).hexdigest()},
        'helper_source_pins':P.PINS,'source_rows':[r['name'] for r in finite],
        'real_key_rows':len(finite),'interpreter_padded_lanes':32-len(finite),'padding_is_not_hardware_work_credit':True,
        'blocks':blocks,'scope':'new bounded software replay of persisted actual-produced two finite rows; not historical runtime capture/full64tile/fullprogram',
        'checkpoint_reads':0,'nonfinite_domain_admitted':False,'shared_service_ticks':None,'actual_phase_leases':None,
        'physical_admission':False,'hardware_launch':False,'rate_credit':0}

if __name__=='__main__':
 import sys
 Path(sys.argv[1]).write_text(json.dumps(trace_decode(),indent=2)+'\n')
