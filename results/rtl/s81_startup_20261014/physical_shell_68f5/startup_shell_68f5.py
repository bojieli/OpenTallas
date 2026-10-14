from pathlib import Path
import json,hashlib,subprocess,re
base=Path(__file__).resolve().parent;src=base/'src';out=base/'proof';out.mkdir(exist_ok=True)
files=['rtl/dsrom_sys/s81_ctrl/ot_s81_stage_seq.sv', 'rtl/dsrom_sys/s81_ctrl/ot_s81_pkg_ctrl.sv', 'rtl/dsrom_sys/s81_ctrl/ot_s81_stage_guard.sv', 'rtl/dsrom_sys/s81_ctrl/ot_s81_hop_tx.sv', 'rtl/dsrom_sys/s81_ctrl/ot_s81_stop.sv', 'rtl/dsrom_sys/s81_ctrl/ot_s81_host_cq.sv', 'rtl/dsrom_sys/s81_ctrl/ot_s81_ctrl.sv', 'rtl/dsrom_sys/s81_ctrl/ot_s81_startup_barrier.sv', 'rtl/dsrom_sys/ot_dsrom_stall_export.sv', 'rtl/dsrom_sys/ot_dsrom_link_ct.sv', 'rtl/dsrom_sys/ot_dsrom_link_chan.sv', 'rtl/link/ot_link_crc32.sv', 'rtl/lib/ot_skid_buffer.sv', 'physical/s81_ctrl/rtl/dsfd_sp_ctrl_startup_core.sv', 'physical/s81_ctrl/rtl/dsfd_sp_ctrl_startup.sv', 'physical/s81_ctrl/rtl/dsfd_sp_ctrl_src_startup.sv', 'physical/s81_ctrl/rtl/dsfd_sp_ctrl_h_startup.sv', 'rtl/dsrom_sys/s81_ctrl/test/tb_s81_ctrl_startup_shell.sv']
receipt={'source_commit':'68f53c142','physical_admission':False,'source_sha256':{s:hashlib.sha256((src/s).read_bytes()).hexdigest() for s in files},'runs':[]}
vl='/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator'
for label,args,pattern,positive in [('positive',[],'STARTUP_SHELL PASS',True),('mutant',['-GMUT=1'],'STARTUP_SHELL_EARLY',False)]:
 cmd=[vl,'--binary','--timing','-Wno-fatal','-Wno-lint','-Wno-style','-I'+str(src/'rtl/dsrom_sys/s81_ctrl'),'--top-module','tb_s81_ctrl_startup_shell','--Mdir',str(out/label),'-o','sim','-j','8']+args+[str(src/s) for s in files]
 with (out/(label+'.build.log')).open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
 receipt.setdefault('builds',{})[label]={'command':cmd,'returncode':r.returncode};(out/'gate.json').write_text(json.dumps(receipt,indent=2));print(label,'BUILD',r.returncode,flush=True)
 if r.returncode:raise SystemExit(r.returncode)
 with (out/(label+'.log')).open('w') as log:r=subprocess.run([str(out/label/'sim')],stdout=log,stderr=subprocess.STDOUT)
 text=(out/(label+'.log')).read_text();ok=pattern in text and (r.returncode==0 if positive else r.returncode!=0)
 receipt['runs'].append(dict(label=label,returncode=r.returncode,expected_pattern=pattern,ok=ok,log_sha256=hashlib.sha256(text.encode()).hexdigest()));(out/'gate.json').write_text(json.dumps(receipt,indent=2));print(label,'RUN',r.returncode,ok,flush=True)
 if not ok:raise SystemExit(1)
receipt['verdict']='POSITIVE_PASS_ACTUAL_MUTANT_FAIL';(out/'gate.json').write_text(json.dumps(receipt,indent=2));print('STARTUP_SHELL_DONE',flush=True)
