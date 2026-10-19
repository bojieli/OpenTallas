#!/usr/bin/env python3
"""Fleet-only exact same-edge AQ comparison and three mechanism mutants."""
import hashlib,json,os,re,subprocess
from pathlib import Path
w=Path(__file__).resolve().parents[2]
files=['rtl/model_ready_hbm_r14/ot_hbm_r14_aq_pc_safe.sv','rtl/test/hbm_accel/svg_rel/ref_ot_hbm_r14_aq_pc_safe_18bd.sv','rtl/test/hbm_accel/svg_rel/tb_hbm_aq_fanout_equiv.sv','physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v']
v=str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator')
version=subprocess.check_output([v,'--version'],text=True).strip()
assert 'Verilator 5.050' in version
queue_depth=int(os.environ.get('BW_AQ_WQ','32'))
out=Path(os.environ.get('BW_AQ_OUT','../proof')).resolve();out.mkdir(exist_ok=True)
manifest={f:hashlib.sha256((w/f).read_bytes()).hexdigest() for f in files}
results=[]
for case in ['positive','HEAD','ACT','REFRESH']:
 obj=out/('obj_'+case)
 cmd=[v,'--binary','--timing','-Wno-fatal','--top-module','tb','-j','8','--Mdir',str(obj)]
 cmd+=['-GWQ='+str(queue_depth)]
 if case!='positive':cmd+=['+define+BW_AQ_MUT_'+case]
 with (out/(case+'_build.log')).open('w') as f:
  subprocess.run(cmd+[str(w/x) for x in files],stdout=f,stderr=subprocess.STDOUT,check=True)
 r=subprocess.run([str(obj/'Vtb')],text=True,capture_output=True)
 log=r.stdout+r.stderr;(out/(case+'.log')).write_text(log)
 passed=(r.returncode==0 and 'AQ_EQ_PASS' in log) if case=='positive' else (r.returncode!=0 and 'AQ_EQ_MISMATCH' in log)
 results.append(dict(case=case,pass_gate=passed,returncode=r.returncode,summary=re.findall(r'^.*AQ_EQ_(?:PASS|MISMATCH).*$',log,re.M)))
 print(json.dumps(results[-1]),flush=True)
(out/'receipt.json').write_text(json.dumps(dict(source_base='18bd3c0ef',queue_depth=queue_depth,verilator=version,source_sha256=manifest,results=results),indent=2)+'\n')
assert all(x['pass_gate'] for x in results)
