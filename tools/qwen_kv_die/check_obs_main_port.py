#!/usr/bin/env python3
"""Check the actual main port's disabled path, generator outputs, and composed role pin."""
import ast,hashlib,json,os,subprocess,sys
from pathlib import Path
r=Path(sys.argv[1]).resolve();base=sys.argv[2];out=Path(sys.argv[3])
def old(p):return subprocess.check_output(['git','-C',str(r),'show',base+':'+p],text=True)
def binding(text,env):
 t=ast.parse(text);names={'HOST_RT_FILE','HOST_RT_MODULE','HOST_RT_OBS','HOST_RT_OBSX','HOST_RT_RENAMED','HOST_GROUPS','OBSX_HOST_GROUPS','OBSX_DCAL_DOB'};body=[]
 for n in t.body:
  if isinstance(n,ast.Assign)and any(isinstance(z,ast.Name)and z.id in names for z in n.targets):body.append(n)
  elif isinstance(n,ast.If)and any(isinstance(z,ast.Assign)and any(isinstance(q,ast.Name)and q.id=='HOST_RT_FILE'for q in z.targets)for z in ast.walk(n)):body.append(n)
  elif isinstance(n,ast.FunctionDef)and n.name=='host_rt_binding':body.append(n)
 oldenv=dict(os.environ);os.environ.update(env)
 try:
  g={'ROOT':r,'os':os};exec(compile(ast.Module(body=body,type_ignores=[]),'actual-host-binding','exec'),g);return g['host_rt_binding']()
 finally:os.environ.clear();os.environ.update(oldenv)
p='tools/qwen_kv_die/kv_die.py';a=old(p);b=(r/p).read_text();checks={}
for mu in ['0','1']:
 e={'OT_KV_MU':mu,'OT_KV_HOST_OBS':'0','OT_KV_HOST_OBSX':'0'}
 x=json.dumps(binding(a,e));y=json.dumps(binding(b,e));assert x==y;checks['disabled_binding_MU'+mu]=hashlib.sha256(y.encode()).hexdigest()
x=binding(b,{'OT_KV_MU':'1','OT_KV_HOST_MU':'0','OT_KV_HOST_OBS':'1','OT_KV_HOST_OBSX':'0'});assert x['module']=='qkd_host_root_admission';checks['host_mu_disabled_preserved']=True
checks['obs_master']=binding(b,{'OT_KV_MU':'1','OT_KV_HOST_OBS':'1','OT_KV_HOST_OBSX':'0'})['module'];assert checks['obs_master']=='qkd_host_root_admission_obs'
e={'OT_KV_MU':'1','OT_KV_HOST_OBS':'1','OT_KV_HOST_OBSX':'1','OT_KV_STATIC_DIE':'1','OT_KV_DCAL_BC':'1','OT_KV_DCAL_BC4':'1'}
x=binding(b,e);assert x['module']=='qkd_host_root_admission_obsx';assert all(p in x['ports']for p in ['obs_dcal_adm_done','obs_dcal_cal_ready','obs_dcal_running','obs_dcal_layer','obs_d2d_recovery_cycles']);checks['obsx_inputs']='all five present'
e['OT_KV_DCAL_BC4']='0'
try:binding(b,e)
except SystemExit:checks['missing_bc4_refused']=True
else:raise AssertionError('OBSX admitted without bc4')
p='tools/qwen_kv_die/kv_static_die.py';a=ast.parse(old(p));b=ast.parse((r/p).read_text());f=next(n for n in b.body if isinstance(n,ast.FunctionDef)and n.name=='_die_joins');removed=[n for n in f.body if (isinstance(n,ast.Assign)and any(isinstance(z,ast.Name)and z.id=='_kd'for z in n.targets))or(isinstance(n,ast.If)and 'HOST_RT_OBSX'in ast.dump(n.test))];assert len(removed)==2;f.body=[n for n in f.body if n not in removed];assert ast.dump(a)==ast.dump(b);checks['static_generator_disabled_AST']='IDENTICAL to base after removing guarded OBSX block'
p='rtl/qwen_sys/split_20261014/qkd_host_root_admission.sv';assert old(p)==(r/p).read_text();checks['main_original_host_bytes']='IDENTICAL'
for args in [('gen_host_root_mu.py',[]),('gen_host_root_obs.py',[]),('gen_host_root_obs.py',['--ext'])]:
 subprocess.run([sys.executable,str(r/'tools/qwen_kv_die/mu_peer'/args[0]),str(r),*args[1],'--check'],check=True)
checks['generated_MU_OBS_OBSX']='all byte-current from main sources'
p='tools/qwen_kv_die/kv_open_tail_roles.py';t=ast.parse((r/p).read_text());v=next(n.value for n in t.body if isinstance(n,ast.Assign)and any(isinstance(z,ast.Name)and z.id=='GENERATOR'for z in n.targets));rel,h=ast.literal_eval(v);assert hashlib.sha256((r/rel).read_bytes()).hexdigest()==h;checks['composed_generator_pin']=h
out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps({'base':base,'checks':checks,'verdict':'PASS','physical_coherence':'HOLD; common-edge RTL only'},indent=2)+'\n');print(json.dumps(checks,indent=2))
