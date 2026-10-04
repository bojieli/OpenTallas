#!/usr/bin/env python3
"""SIM_ONLY current S81 L20 functional issue using retained exact TP4 semantics."""
import argparse, ast, copy, gzip, hashlib, inspect, json, os, time, traceback
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();status={'scope':'SIM_ONLY S81 L20 position1048575',
      'native_timing_claim':False,'physical_qualified':False,'expected_outputs_as_inputs':False,
      'sim_only_dispatch_cycles':0,'native_cycles':None,'verdict':'RUNNING'}
    (a.out/'pid').write_text(str(os.getpid())+'\n')
    try:
        import v41_fullshape_isa as S
        import hdc_isa_v41 as I
        root=Path(__file__).resolve().parents[1]
        demand_path=root/'results/uarch/dsrom_native_weight_address_join_20261002/inputs/demand-r5.json.gz'
        demand_raw=demand_path.read_bytes();demand=json.loads(gzip.decompress(demand_raw))
        nodes=sorted((n for n in demand['nodes'] if n['scope']==20 and n['kind']=='instruction'),
                     key=lambda n:n['instruction_index'])
        if len(nodes)!=144 or [n['instruction_index'] for n in nodes]!=list(range(144)):
            raise ValueError('actual ordered L20 144-node program required')
        fields=[];words=[]
        for n in nodes:
            f={k:tuple(v) if isinstance(v,list) and not k.startswith('_') else v
               for k,v in n['instruction'].items()}
            w=I.encode(full_shape=True,**f)
            if hashlib.sha256(w.to_bytes(256,'little')).hexdigest()!=n['template_word_sha256']:
                raise ValueError('actual S81 source instruction changed: '+n['id'])
            fields.append(f);words.append(w)
        program=a.out/'current_s81_L20.hex'
        program.write_text(''.join(f'{w:0512x}\n' for w in words))
        bind,scratch=S.case(1048576,20260930,20)
        original_layout=S.BoundLayout
        old=json.loads(bind.read_text())['instruction_trace']
        if len(old)!=144:raise ValueError('retained image provider trace differs')
        # Source templates keep their actual ISA words. Only the SIM_ONLY weight
        # lookup translates to existing released rank-image physical addresses.
        # All operands/results/DYN/expert IDs continue through actual produced VM.
        translations=[]
        for pc,(n,f,row) in enumerate(zip(nodes,fields,old)):
            diffs={k:[f.get(k),v] for k,v in row['fields'].items() if f.get(k)!=v}
            if set(diffs)-{'qe_wbase','qe_istride','me_wbase','he_wbase'}:
                raise ValueError(f'PC{pc}: non-weight source translation is forbidden: {diffs}')
            translations.append({'node':n['id'],'source_sha256':n['template_word_sha256'],
                                 'weight_lookup_only':diffs})
        class CurrentSourceLayout(original_layout):
            def __init__(self,path):
                super().__init__(path);self.current_pc=None
                self.bind=copy.deepcopy(self.bind)
                for pc,row in enumerate(self.bind['instruction_trace']):
                    row['fields']={k:v for k,v in fields[pc].items() if not k.startswith('_')}
            def qe_matrix(self,base,eid,stride):
                pc=self.current_pc
                if pc is None:raise ValueError('weight lookup without actual source PC')
                return super().qe_matrix(base+old[pc]['fields'].get('qe_wbase',0)-fields[pc].get('qe_wbase',0),
                                         eid,old[pc]['fields'].get('qe_istride',stride))
            def engine_matrix(self,engine,base):
                pc=self.current_pc
                if pc is None:raise ValueError('weight lookup without actual source PC')
                key='me_wbase' if engine=='ME' else 'he_wbase'
                return super().engine_matrix(engine,base+old[pc]['fields'].get(key,0)-fields[pc].get(key,0))
        S.BoundLayout=CurrentSourceLayout
        for name in ('qe','me','he'):
            original=getattr(S.Rank,name)
            def wrapped(self,f,pc,log,_original=original):
                self.lay.current_pc=pc
                return _original(self,f,pc,log)
            setattr(S.Rank,name,wrapped)
        # Do not use expected expert IDs to authorize/select a source operation.
        # Actual XU writes RAW IDs; the retained image lookup refuses any absent
        # resulting expert instead of substituting the expected selection.
        tree=ast.parse(inspect.getsource(S.run_context))
        for n in ast.walk(tree):
            if isinstance(n,ast.If) and 'lay.selected' in ast.unparse(n.test):
                n.test=ast.Constant(False)
        ast.fix_missing_locations(tree)
        ns={};exec(compile(tree,inspect.getsourcefile(S.run_context),'exec'),S.__dict__,ns)
        run=ns['run_context']
        (a.out/'source_mapping.json').write_text(json.dumps({'demand_sha256':hashlib.sha256(demand_raw).hexdigest(),
          'canonical_inventory_sha256':hashlib.sha256((root/'results/uarch/dsrom_s81_released_binding_20261004/canonical/inventory.json').read_bytes()).hexdigest(),
          'program_sha256':hashlib.sha256(program.read_bytes()).hexdigest(),
          'provider_bind':str(bind),'provider_bind_sha256':S.sha(bind),'translations':translations},indent=2)+'\n')
        def on_pc(pc,ranks):
            status['sim_only_dispatch_cycles']=pc+1
            print(f'SIM_ONLY current-S81 L20 PC{pc} unit{fields[pc]["unit"]} completed',flush=True)
            (a.out/'live.json').write_text(json.dumps(status,indent=2)+'\n')
        result=run(1048576,scratch,bind,program,seed=20260930,layer=20,on_pc=on_pc)
        (a.out/'functional.json').write_text(json.dumps(result,indent=2)+'\n')
        status['verdict']='PASS' if result['verdict']=='pass' else 'FAIL'
        status['completed_instructions']=result['instructions_executed']
        status['cycle_basis']='one SIM_ONLY exact operator-dispatch step; excludes native latency/physical headline'
        status['failure']=result.get('defects',[])
    except BaseException as exc:
        status.update(verdict='FAIL',failure=str(exc),traceback=traceback.format_exc())
        traceback.print_exc()
    status['wall_seconds']=time.monotonic()-started
    (a.out/'terminal.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(status),flush=True)
    return 0 if status['verdict']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
