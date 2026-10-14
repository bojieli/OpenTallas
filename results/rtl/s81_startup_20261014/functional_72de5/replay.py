from pathlib import Path
import subprocess,json,hashlib,re
base=Path('/srv/opentallas-scratch/codex/s81-startup-72de5');src=base/'src';out=base/'proof';out.mkdir(exist_ok=True)
files=['rtl/dsrom_sys/s81_ctrl/ot_s81_stage_seq.sv', 'rtl/dsrom_sys/s81_ctrl/ot_s81_pkg_ctrl.sv', 'rtl/dsrom_sys/s81_ctrl/ot_s81_stage_guard.sv', 'rtl/dsrom_sys/s81_ctrl/ot_s81_hop_tx.sv', 'rtl/dsrom_sys/s81_ctrl/ot_s81_stop.sv', 'rtl/dsrom_sys/s81_ctrl/ot_s81_host_cq.sv', 'rtl/dsrom_sys/s81_ctrl/ot_s81_ctrl.sv', 'rtl/dsrom_sys/s81_ctrl/ot_s81_startup_barrier.sv', 'rtl/dsrom_sys/ot_dsrom_stall_export.sv', 'rtl/dsrom_sys/ot_dsrom_link_ct.sv', 'rtl/dsrom_sys/ot_dsrom_link_chan.sv', 'rtl/link/ot_link_crc32.sv', 'rtl/dsrom_sys/s81_ctrl/test/tb_s81_ctrl_chain.sv', 'rtl/dsrom_sys/s81_ctrl/test/tb_s81_startup_barrier.sv']
receipt={'source_commit':'72de5eb2f','schema':'opentallas.s81.startup.functional_gate.v1','physical_admission':False,'scope':'Real controller operation-admission path plus acknowledgment barrier; producer-ready exports/full native assembly and physical recovery remain open','source_sha256':{s:hashlib.sha256((src/s).read_bytes()).hexdigest() for s in files},'runs':[]}
vl='/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator'
configs=[('chain_default','tb_s81_ctrl_chain',[],['','+forge'],'pass','TB_S81_CTRL_CHAIN.*PASS'),('chain_startup','tb_s81_ctrl_chain',['-GSTARTUP_TEST=1'],['','+forge'],'pass','TB_S81_CTRL_CHAIN.*PASS'),('chain_early','tb_s81_ctrl_chain',['-GSTARTUP_TEST=1','-GSTARTUP_MUT=1'],[''],'fail','STARTUP_EARLY'),('chain_stop','tb_s81_ctrl_chain',['-GMUT=1'],[''],'fail','TB_S81_CTRL_CHAIN.*FAIL'),('chain_nosrc','tb_s81_ctrl_chain',['-DS81_GUARD_MUTANT_NOSRC'],['+forge'],'fail','TB_S81_CTRL_CHAIN.*FAIL'),('barrier','tb_s81_startup_barrier',[],[''],'pass','STARTUP_BARRIER PASS'),('barrier_early','tb_s81_startup_barrier',['-GMUT=1'],[''],'fail','STARTUP_EARLY')]
for label,top,args,runs,expected,pattern in configs:
 use=files[:-2]+[files[-2 if top=='tb_s81_ctrl_chain' else -1]]
 cmd=[vl,'--binary','--timing','-Wno-fatal','-Wno-lint','-Wno-style','-Wno-MULTIDRIVEN','-I'+str(src/'rtl/dsrom_sys/s81_ctrl'),'--top-module',top,'--Mdir',str(out/label),'-o','sim','-j','8']+args+[str(src/s) for s in use]
 with (out/(label+'.build.log')).open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 print(label,'BUILD',r.returncode,flush=True)
 receipt.setdefault('builds',{})[label]={'command':cmd,'returncode':r.returncode};(out/'gate.json').write_text(json.dumps(receipt,indent=2))
 if r.returncode:raise SystemExit(r.returncode)
 for arg in runs:
  name=label+('_forge' if arg else '');cmd=[str(out/label/'sim')]+([arg] if arg else [])
  with (out/(name+'.log')).open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=600)
  text=(out/(name+'.log')).read_text();match=bool(re.search(pattern,text));ok=match and (r.returncode==0 if expected=='pass' else (r.returncode!=0 or 'FAIL' in text))
  receipt['runs'].append({'name':name,'expected':expected,'returncode':r.returncode,'matched_expected_behavior':match,'verdict':'PASS' if ok else 'FAIL','log_sha256':hashlib.sha256(text.encode()).hexdigest()});(out/'gate.json').write_text(json.dumps(receipt,indent=2));print(name,r.returncode,ok,flush=True)
  if not ok:raise SystemExit(1)
receipt['verdict']='POSITIVE_PASS_MUTANT_FAIL';(out/'gate.json').write_text(json.dumps(receipt,indent=2));print('STARTUP_FUNCTIONAL_DONE',flush=True)
