import json,sys,copy,subprocess,importlib.util
from pathlib import Path
R=Path('/srv/opentallas-scratch/claude/wt/codex-hbm-1030');FLO=Path('/srv/opentallas-scratch/claude/wt/codex-flow-1030/tools/die_plan');P=R/'results/hbm_die_codex_1030/su_structural_bridges';RUN=Path(__file__).resolve().parent/'binder_hook';RUN.mkdir(exist_ok=True)
sys.path[:0]=[str(FLO),str(R/'tools/die_plan')]
spec=importlib.util.spec_from_file_location('bind',FLO/'bind.py');B=importlib.util.module_from_spec(spec);sys.modules['bind']=B;spec.loader.exec_module(B)
manifest=json.load(open(P/'manifest_PREP.json'))['structural_bridges'];results=[]
for idx,group in enumerate(manifest):
 g=copy.deepcopy(group);inst=g['instances'][0];g['instances']=[inst];path=inst['path'];abi=inst['expected_abi'];out=RUN/str(idx);out.mkdir(exist_ok=True)
 decl=',\n'.join(f"{x['dir']} wire "+(f"[{x['width']-1}:0] "if x['width']>1 else'')+p for p,x in abi.items())
 source='(* blackbox *) module actual_ABI_member(\n'+decl+'\n);endmodule\n'
 source+='(* blackbox *) module consumer(input wire [3:0] D);endmodule\n'
 source+='module coupon(\n'+decl+'\n);actual_ABI_member before_compose('+','.join('.'+p+'('+p+')'for p in abi)+');consumer loaded(.D(lane_coll));endmodule\n'
 (out/'top.sv').write_text(source);ys=f'read_verilog -sv {out}/top.sv\nhierarchy -check -top coupon\nwrite_json {out}/top.json\n';(out/'top.ys').write_text(ys)
 q=subprocess.run(['yosys','-Q','-T','-s',str(out/'top.ys')],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True);(out/'top.log').write_text(q.stdout);assert q.returncode==0
 compose=dict(cores=[dict(inst=path,module=inst['expected_module'],members=['before_compose'],ports={p:dict(dir=x['dir'],bits=[[dict(member='before_compose',port=p,bit=i)]for i in range(x['width'])])for p,x in abi.items()})])
 (out/'compose.json').write_text(json.dumps(compose)+'\n')
 plan=dict(asbuilt=dict(top='coupon',map=dict(parts={'before_compose':['P','native'],path:['P','native'],path+'.u_phys':['P','native'],'loaded':['P','loaded']}),compose=str(out/'compose.json'),structural_bridges=[g]),partitions=[dict(name='P',type='p')],partition_types=dict(p=dict(module='P_module')))
 yjs=json.load(open(out/'top.json'));binder=B.Binder(plan,yjs,out,base=str(R));assert not binder.errors,binder.errors
 sink=next(c for c in binder.F.cells if c.path=='loaded');values=[binder.G.source(b)for b in sink.ports['D']];assert all(x[:2]==('const','0')for x in values)
 assert next(c for c in binder.F.cells if c.path==path+'.u_phys').module==inst['physical']['module'];assert len(binder.structural_bridge_receipts)==1
 default=copy.deepcopy(plan);default['asbuilt'].pop('structural_bridges');old=B.Binder(default,yjs,out,base=str(R));sink=next(c for c in old.F.cells if c.path=='loaded');assert all(old.G.source(b)[0]=='pin'for b in sink.ports['D'])
 results.append(dict(fragment=group['top'],postcompose_native_path=path,actual_Binder_constructor=True,loaded_constant_bits=4,default_keeps_original_pin=True,extra_cycles=0))
(P/'binder_hook_receipt.json').write_text(json.dumps(dict(scope='Real published FLOW Binder constructor with actual3bridge fragments and exact native ABIs in a minimal composition-order vehicle; not fullnativeBIND',flow_commit='5b3fbcc7c',cases=results),indent=2)+'\n')
print('PASS realBindercompose→actual3bridge→Graph; defaultpin controls;0cycles')
