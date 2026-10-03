"""Additive source-derived scratch-client installer; pinned638 hierarchy unchanged."""
import json,hashlib,re,textwrap
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];D=Path(__file__).resolve().parent
BASE=D.parent/'ranked';MUX='rtl/model/qwen_scratch_client_mux_20261003/ot_gpu_qwen_scratch_client_mux.sv'
TOP='ot_gpu_qwen_hbm_integrated_scratch'
def one(s,a,b):
 if s.count(a)!=1:raise ValueError('source changed: '+a)
 return s.replace(a,b)
def main():
 model=json.loads((ROOT/'rtl/model/qwen_scratch_client_mux_20261003/model.json').read_text())
 for p,h in model['source_sha256'].items():
  if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise ValueError('priced original changed '+p)
 ns={'__file__':str(D.parent/'generate.py'),'__name__':'source_helpers'}
 exec(compile((D.parent/'generate.py').read_text(),str(D.parent/'generate.py'),'exec'),ns)
 ports=ns['leaf_ports'](ROOT/MUX,'ot_gpu_qwen_scratch_client_mux')
 b=json.loads((BASE/'ports.json').read_text());s=(BASE/'ot_gpu_qwen_hbm_integrated_ranked.sv').read_text()
 s=one(s,'parameter bit ENABLE=0','parameter bit ENABLE=0,parameter bit ENABLE_SCRATCH_CLIENT=0')
 s=s.replace('ot_gpu_qwen_hbm_integrated_ranked',TOP)
 declarations=[' output wire scratch_client_enabled']
 for p in ports:
  if p['name']=='clk':continue
  name='scratch_'+p['name'];direction=p['direction']
  if p['name'] in ('por_n','run_enable') or p['name'].startswith(('route_','service_')):direction='output'
  b['pins'][name]=dict(direction=direction,bits=p['bits']*64,count=64,leaf_bits=p['bits'],leaf=p['name'],block='scratch')
  declarations.append(' '+direction+' wire ['+str(p['bits']*64-1)+':0] '+name)
 b['pins']['scratch_client_enabled']=dict(direction='output',bits=1,count=1,leaf='ENABLE_SCRATCH_CLIENT')
 s=one(s,');\nassign assembly_enabled',',\n'+',\n'.join(declarations)+'\n);\nassign assembly_enabled')
 # Every original SM scratch leaf port connects to this mux service side.
 for field in ('valid','write','addr','wdata','done_ready','ready','done','rdata'):
  s=one(s,'.scratch_'+field+'(sm_scratch_'+field, '.scratch_'+field+'(scratch_service_'+field)
 s=one(s,'.shared_router_drained(kv_shared_drained)', '.shared_router_drained(kv_shared_drained && (&scratch_drained))')
 # Actual SRAM ready/done/data retain single drivers; router aliases are mux outputs.
 connection=[];aliases=[]
 for p in ports:
  n,w=p['name'],p['bits'];suffix='[i]' if w==1 else '[i*'+str(w)+' +: '+str(w)+']'
  if n=='clk':expr='stream_clk'
  elif n=='por_n':expr='sm_rst_n[i]';aliases.append('assign scratch_por_n=sm_rst_n;')
  elif n=='run_enable':expr='kv_run_enable';aliases.append('assign scratch_run_enable={64{kv_run_enable}};')
  elif n.startswith('route_'):
   field=n[6:];expr='sm_scratch_'+field+suffix
   aliases.append('assign scratch_'+n+'=sm_scratch_'+field+';')
  else:expr='scratch_'+n+suffix
  connection.append('.'+n+'('+expr+')')
  if n.startswith('route_'):b['pins']['scratch_'+n]['direction']='output'
 s=one(s,'endmodule','assign scratch_client_enabled=ENABLE && ENABLE_SCRATCH_CLIENT;\n'+'\n'.join(dict.fromkeys(aliases))+'\nfor(genvar i=0;i<64;i=i+1)begin:g_scratch_client\n ot_gpu_qwen_scratch_client_mux #(.ENABLE_CLIENT(ENABLE && ENABLE_SCRATCH_CLIENT),.INDEX(i)) u_mux(\n '+',\n '.join(connection)+'\n );\nend\nendmodule')
 # Route alias declarations reflect physically driven signals (observations only).
 for n,p in b['pins'].items():
  if n.startswith('scratch_route_'):s=s.replace(' input wire ['+str(p['bits']-1)+':0] '+n,' output wire ['+str(p['bits']-1)+':0] '+n)
 (D/(TOP+'.sv')).write_text(s)
 dep=list(dict.fromkeys((BASE/'sources.f').read_text().splitlines()))
 dep.remove('rtl/model/qwen_hbm_integrated_20261003/ranked/ot_gpu_qwen_hbm_integrated_ranked.sv')
 dep+=[MUX,str((D/(TOP+'.sv')).relative_to(ROOT))]
 (D/'sources.f').write_text('\n'.join(dep)+'\n')
 b['top']=TOP;b['source_sha256']={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in dep}
 b['scratch_model_sha256']=hashlib.sha256((ROOT/'rtl/model/qwen_scratch_client_mux_20261003/model.json').read_bytes()).hexdigest()
 b['inventory'].update(scratch_client_mux_count=64,existing_scratch_services=64,existing_scratch_macros=128,new_SRAM_macros=0)
 b['unresolved']+=['Nash realheldworkspace239/owner55/base10/length11/exclusive toscratch.workspace_* and sameofferidentity, no hostreservation','Native actualMatrixservices use scratch.client_*; SMoutputs remain readonly','WholeGO manifest alloutputs/typedzeroRF pendingNash; issuer_r2 singlemask must not impersonate this','Scratch macro raw payload remains existing unprotected source; no SRAM reliability or physical clock credit']
 b['factory_source_sha256']['tools/gpu_sys/canonical_qwen_scratch_simulator.py']=hashlib.sha256((ROOT/'tools/gpu_sys/canonical_qwen_scratch_simulator.py').read_bytes()).hexdigest()
 (D/'ports.json').write_text(json.dumps(b,indent=2)+'\n')
 source=(D.parent/'generate.py').read_text();start=source.index('    cpp = [');end=source.index("    (OUT/'pin_driver.cpp').write_text",start)
 end=source.index('\n',end)
 driver=textwrap.dedent(source[start:end]).replace('ot_gpu_qwen_hbm_integrated',TOP).replace(' SM=64 W2=128',' SM=64 W2=256 RANKS=2 PC_PER_RANK=128 SCRATCH_CLIENT="<<unsigned(dut.scratch_client_enabled)<<"')
 exec(compile(driver,'source-derived pin driver','exec'),{'pins':b['pins'],'OUT':D})
if __name__=='__main__':main()
