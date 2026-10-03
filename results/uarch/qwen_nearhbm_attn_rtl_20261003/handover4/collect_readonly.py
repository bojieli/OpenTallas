import base64,hashlib,json,pathlib,subprocess,datetime
ROOT=pathlib.Path('/home/ubuntu/OpenTallas-qwen-nearhbm-handover4/results/uarch/qwen_nearhbm_attn_rtl_20261003/handover4')
ROOT.mkdir(parents=True,exist_ok=True)
REMOTE=r'''
import base64,hashlib,json,pathlib,subprocess,datetime,sys
host=sys.argv[1]; out={'host':host,'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':{},'jobs':{}}
def read(p,full=False):
 p=pathlib.Path(p)
 if not p.is_file(): return {'path':str(p),'exists':False}
 b=p.read_bytes(); d={'path':str(p),'exists':True,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
 if full: d['base64']=base64.b64encode(b).decode()
 else:d['tail']=b[-3000:].decode(errors='replace')
 return d
def cmd(args):return subprocess.run(args,text=True,capture_output=True).stdout.strip()
if host=='epyc':
 s=pathlib.Path('/srv/opentallas-scratch/claude/nearhbm'); wt=s/'wt'; names=['hub_r7','row_engine_r6']
 for n in ['partition_exactness_final.json','prod_exhaustive_final.json','prove400.exit','prod_exh.exit','chain.log','pnr_verdicts.json']:out['files'][n]=read(s/'q'/n,True)
 for n in ['gate_hd128_r8_dpi.json','gate_hd128_r6_dpi.json','real_vs_dpi_hd16.json']:out['files'][n]=read(wt/'results/uarch/qwen_nearhbm_attn_rtl_20261003'/n,True)
else:s=pathlib.Path('/home/ubuntu/nhbp');wt=s/'wt4';names=['row_engine_r4']
out['source_head']=cmd(['git','-C',str(wt),'rev-parse','HEAD']);out['source_status']=cmd(['git','-C',str(wt),'status','--short'])
for name in names:
 work=s/'run'/f'{name}.work'; receipt=read(s/'run'/f'{name}.receipt.json',True)
 d={'receipt':receipt,'driver_log':read(s/'run'/f'{name}.log'),'metrics':{},'terminal':{'exists':False},'sources':{}}
 if receipt.get('exists'):
  rec=json.loads(base64.b64decode(receipt['base64'])); args=rec['driver_args']
  for i,a in enumerate(args):
   if a=='--source':d['sources'][args[i+1]]=read(wt/args[i+1])
  if '--output' in args:d['terminal']=read(wt/args[args.index('--output')+1],True)
 for p in sorted((work/'orfs/logs').glob('**/*.json')):d['metrics'][str(p.relative_to(work))]=read(p,True)
 logs=list((work/'orfs/logs').glob('**/*.log'));d['latest_log']=read(max(logs,key=lambda p:p.stat().st_mtime)) if logs else None
 needle='persistent-workdir '+str(work)
 ps=cmd(['ps','-eo','pid,ppid,etime,rss,args']);d['processes']=[x for x in ps.splitlines() if needle in x or (str(work) in x and 'docker run' in x)]
 out['jobs'][name]=d
if host=='epyc':
 s=pathlib.Path('/home/ubuntu/hbm-rf-fullsize-ssff-20261003-r3');w=s/'work/orfs'; logs=w/'logs/asap7/opentallas_ot_gpu_rf_w6_physical_context_asap7/base'
 rf={'unit':cmd(['systemctl','--user','show','hbm-rf-fullsize-ssff-20261003-r3.service','-p','ActiveState','-p','SubState','-p','MainPID','-p','ExecMainStatus']),'metrics':{},'artifacts':{}}
 for n in ['admission.json','process.json','macro_gate.json','supervisor-terminal.json','physical.json']:rf['artifacts'][n]=read(s/n,True)
 for p in sorted(logs.glob('*.json')):rf['metrics'][p.name]=read(p,True)
 rf['macro_placement_log']=read(logs/'2_2_floorplan_macro.log',True)
 ls=list(logs.glob('*.log'));rf['latest_log']=read(max(ls,key=lambda p:p.stat().st_mtime)) if ls else None
 net=w/'results/asap7/opentallas_ot_gpu_rf_w6_physical_context_asap7/base/1_2_yosys.v'
 import re
 b=net.read_bytes();names=re.findall(r'(?m)^\s*ot_sram_1r1w_128x256_m1_r2c2\s+([^\n(]+)\s*\(',b.decode());rf['netlist']={'path':str(net),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'macro_instances':[n.strip() for n in names]}
 infos=cmd(['docker','ps','-q']).splitlines();rf['containers']=[]
 for cid in infos:
  info=json.loads(cmd(['docker','inspect',cid]))[0]
  if not any(str(s) in m.get('Source','') for m in info['Mounts']):continue
  pid=info['State']['Pid']; cg=pathlib.Path('/proc')/str(pid)/'cgroup'; cgpath=cg.read_text().strip().split(':')[-1];c=pathlib.Path('/sys/fs/cgroup'+cgpath)
  x={'id':cid,'init_pid':pid,'cgroup':cgpath,'image':info['Image'],'state':info['State']}
  for n in ['memory.current','memory.peak','memory.events']:x[n]=(c/n).read_text().strip()
  rf['containers'].append(x)
 out['rf']=rf
print(json.dumps(out))
'''
for host,alias in [('epyc','ot-epyc1tb'),('agidock','ot-agidock128')]:
 r=subprocess.run(['ssh',alias,'python3 - '+host],input=REMOTE,text=True,capture_output=True,check=True)
 d=json.loads(r.stdout);(ROOT/(host+'-snapshot.json')).write_text(json.dumps(d,indent=2)+'\n')
 print(host,d['source_head'],{k: {'processes':v['processes'],'terminal':v['terminal']['exists'],'latest_log':v['latest_log']['path'] if v['latest_log'] else None} for k,v in d['jobs'].items()})
