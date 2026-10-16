#!/usr/bin/env python3
"""Lint the complete current 20-root native arithmetic graph; no black boxes."""
import ast,json,pathlib,subprocess,sys
root=pathlib.Path(__file__).resolve().parents[2]
ns={}
for node in ast.parse((root/'tools/s81_suhc/hc_gate.py').read_text()).body:
 if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('RTL','FP') for t in node.targets):
  ns[node.targets[0].id]=({k.arg:ast.literal_eval(k.value) for k in node.value.keywords} if isinstance(node.value,ast.Call) else ast.literal_eval(node.value))
files=ns['RTL']+ns['FP']['rtl']+[
 'rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_ccf_bankpipe.sv',
 'rtl/dsrom_sys/s81_suhc/static/ot_s81_hc_pad_roots20.sv',
 'rtl/dsrom_sys/s81_suhc/static/ot_s81_hc_cseq_static.sv',
 'rtl/dsrom_sys/s81_suhc/static/dsfd_sp_hc_comb_roots20.sv',
 'rtl/dsrom_sys/s81_suhc/static/dsfd_sp_hc_comb_calendar20.sv']
if len(sys.argv)>1 and sys.argv[1]=='--files':
 print('\n'.join(files));sys.exit()
out=pathlib.Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
vl=pathlib.Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
if not vl.exists():vl=pathlib.Path('/usr/bin/verilator')
for top in ('dsfd_sp_hc_comb_roots20','dsfd_sp_hc_comb_calendar20'):
 cmd=[str(vl),'--lint-only','--timing','-Wno-fatal','-DSYNTHESIS','--top-module',top,*files]
 with (out/(top+'.log')).open('w') as f:r=subprocess.run(cmd,cwd=root,stdout=f,stderr=subprocess.STDOUT)
 if r.returncode:sys.exit(r.returncode)
 print(top+' NATIVE_LINT_PASS',flush=True)
