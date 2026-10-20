import pathlib,hashlib,json,datetime,subprocess
B=pathlib.Path('/srv/opentallas-scratch/claude/refill-1225/QWREG');S=B/'src';O=B/'out'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files=list(O.glob('*.out'))+list((S/'results/rtl/mu_qwen_1018/amix/runs').glob('*h.out'))+[O/'ctlm_nsl12/w/ctlm.out']
files+=list((O/'amix_w/H1').rglob('h.log'))+list((O/'amix_w/H4').rglob('h.log'))
files += [S/x for x in ['results/rtl/mu_qwen_1018/amix/run_group.sh','rtl/test/qwen_dv/dv_bench2.py','rtl/test/qwen_dv/run_tt_ctlm_dv.sh','rtl/test/mu_qwen_seq/run_mu_ctlm.sh']]
r={'collected_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_commit':(S/'SOURCE_COMMIT').read_text().strip(),'files':[{'path':str(p),'sha256':sha(p),'text':p.read_text(errors='replace')} for p in files]}
r['source_hashes']={}
for d in ['rtl/qwen_split','rtl/test/qwen_dv','rtl/test/mu_qwen_1018','rtl/test/mu_qwen_seq','rtl/test/mu_qwen_tok','tools/xdie_qtp8']:
 for p in sorted((S/d).rglob('*')):
  if p.is_file() and p.suffix in ['.sv','.py','.sh','.svh']:r['source_hashes'][str(p.relative_to(S))]=sha(p)
r['executables']=[]
for p in O.rglob('*'):
 if p.is_file() and p.name in ['Vtb','sim','Vtb_qfd_tt_ctlm_dv_lpf_eq']:
  r['executables'].append({'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size})
ps=subprocess.check_output(['ps','-eo','pid,ppid,etimes,pcpu,rss,args'],text=True)
r['live_processes']=[l for l in ps.splitlines() if '/QWREG/' in l and any(x in l for x in ['verilator_bin ','make -C','/cc1plus ','tt_ctlm_cal_bench.py'])]
print(json.dumps(r,indent=2))
