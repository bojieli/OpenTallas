#!/usr/bin/env python3
"""Actual installed leaf compile/contract gate, not a production RF ACK CDC join."""
import argparse,hashlib,json,os,resource,shutil,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RECORD=ROOT/'results/uarch/Euclid_installed_RFACK_CDC_contract_20261003'
BENCH='rtl/test/Euclid_installed_RFACK_CDC_20261003/'
RF=['rtl/gpu/ot_gpu_rf_service.sv','rtl/gpu/ot_gpu_rf_visibility_fence.sv','physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v']
CDC=['rtl/model_ready_hbm_r14/'+n for n in ['ot_hbm_r14_fifo2.sv','ot_hbm_r14_route.sv','ot_hbm_r14_clock_bridge.sv']]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def contract():
 m=json.loads((RECORD/'pre-verification-model-r1.json').read_text())
 for p,h in m['source_pins'].items():
  if sha(ROOT/p)!=h:raise ValueError('installed source pin '+p)
 if sha(ROOT/'tools/uarch_model.py')!=m['unified_model_sha256']:raise ValueError('model root changed')
 def source(path,*anchors):
  s=(ROOT/path).read_text()
  if not all(a in s for a in anchors):raise ValueError('literal source conditions '+path)
 source(RF[0],'wire idle = rst_n && !read_pending && !rsp_valid && !ack_valid;','if(write_go) begin ack_valid<=1;prefer_write<=0;end','else if(ack_valid && ack_ready) ack_valid<=0;','ack_valid<=0;')
 source(RF[1],'assign vector_ACK_visible=rst_n && pending && host_ack_valid;','assign vector_ACK_epoch=epoch;','if(host_wr_valid && host_wr_ready) begin pending<=1;','if(host_ack_valid && host_ack_ready) begin pending<=0;','active<=0;pending<=0;')
 source(CDC[0],'wire arst=wrn&&rrn;','assign wr=wrsync[1]&&ronw2&&!full;','assign rv=rrsync[1]&&wonr2&&!empty;')
 source(CDC[1],'assign ir=!live;assign ov=live&&left==0;','if(ov&&ore)live<=0;')
 source(CDC[2],'.wrn(rst_n)', '.rrn(rst_n)', '.EDGES(38)', '.rst_n(rst_n)')
 return {'source_contract':'PASS_LITERAL_INSTALLED_LEAF_PINS','wire_ACK_identity':None,'production_RF_ACK_CDC_connection':False,'production_clock_pair':None,'stale_external_ACK_rejection_proved':False,'unknown_cycles':m['unknown'],'hardware_or_rate_admitted':False}
def run(out):
 if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():raise ValueError('clean pinned source required')
 out.mkdir(exist_ok=False);r={'status':'STARTED','source_contract':contract(),'source_freeze':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'jobs':[],'caps':None,'headroom':{'available_memory':next(l for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')),'disk_free_B':shutil.disk_usage(out).free}}
 for name in ('CPU','AS','FSIZE'):
  key=getattr(resource,'RLIMIT_'+name);soft,hard=resource.getrlimit(key)
  if hard!=resource.RLIM_INFINITY:raise ValueError('unlimited hard '+name+' required')
  resource.setrlimit(key,(resource.RLIM_INFINITY,resource.RLIM_INFINITY))
 def job(argv,name):
  started=time.time()
  with (out/(name+'.log')).open('x') as f:p=subprocess.run(argv,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
  r['jobs'].append({'name':name,'argv':argv,'returncode':p.returncode,'wall_s':time.time()-started,'log_sha256':sha(out/(name+'.log'))})
  if p.returncode:raise ValueError('actual tool failure '+name)
  return (out/(name+'.log')).read_text()
 try:
  v='/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator';r['tool_pins']={p:sha(p) for p in [v,str(Path(v).with_name('verilator_bin')),'/usr/bin/iverilog','/usr/bin/vvp']}
  for top,sources,params in [('ot_gpu_rf_service',RF,[]),('ot_gpu_rf_visibility_fence',RF,['-GENABLE=1']),('ot_hbm_r14_clock_bridge',CDC,['-GWIDTH=471'])]:
   job([v,'--lint-only','--timing','--Wall','-Wno-fatal','--top-module',top]+params+[str(ROOT/p) for p in sources],top+'-lint')
  for top,sources,expected in [('tb_RFACK_conditional',RF,'PASS_RFACK_CONDITIONAL_DIRECT_COMMON_RESET'),('tb_CDC_common_reset',CDC,'PASS_CDC_OPAQUE_COMMON_RESET')]:
   binary=out/top
   job(['/usr/bin/iverilog','-g2012','-s',top,'-o',str(binary)]+[str(ROOT/p) for p in sources+[BENCH+top+'.sv']],top+'-compile')
   log=job(['/usr/bin/vvp',str(binary)],top+'-run')
   if expected not in log or 'FAIL_' in log:raise ValueError('conditional leaf assertion failure '+top)
  contract();r['status']='PASS_ACTUAL_COMPILE_AND_CONDITIONAL_LEAVES_ONLY_PRODUCTION_JOIN_BLOCKED'
 except Exception as e:r['status']='FAIL_INSTALLED_LEAF_QUALIFICATION';r['error']=str(e)
 with (out/'terminal.json').open('x') as f:json.dump(r,f,sort_keys=True,indent=2);f.write('\n')
 return 0 if r['status'].startswith('PASS_') else 1
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path);p.add_argument('--source-only',action='store_true');a=p.parse_args()
 if a.source_only:print(json.dumps(contract(),indent=2,sort_keys=True))
 elif a.out:raise SystemExit(run(a.out.resolve()))
 else:p.error('--out or --source-only required')
