#!/usr/bin/env python3
"""Small actual-source control projection. Run under ot-run admission, never locally."""
import ast,json,subprocess,sys,hashlib
from pathlib import Path
out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
subprocess.run([sys.executable,'tools/s81_hc_fault_retire/prepare_projection.py','--out',str(out)],check=True)
# Read immutable source inventory without importing heavyweight numerical golden modules.
tree=ast.parse(Path('tools/s81_suhc/hc_gate.py').read_text())
rtl=next(ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='RTL'for t in n.targets))
fp=next(ast.literal_eval(n.value.keywords[0].value)for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='FP'for t in n.targets))
sources=[x for x in rtl+fp if Path(x).exists()]
sources += ['rtl/dsrom_sys/s81_static_control/'+x+'.sv'for x in ['ot_s81_fixed_issue','ot_s81_fixed_mailbox','dsfd_stage_seq_static_c','dsfd_stage_seq_static_c8']]
sources += [str(out/'hc_control_projection.sv'),'rtl/dsrom_sys/s81_suhc/test/tb_s81_hc_fault_retire.sv']
(out/'source_manifest.json').write_text(json.dumps({x:hashlib.sha256(Path(x).read_bytes()).hexdigest()for x in sources},indent=2)+'\n')
cmd=['iverilog','-g2012','-DDSFD_SUHC_STATIC_ISSUE','-s','tb_s81_hc_fault_retire','-o',str(out/'probe')]+sources
(out/'compile_command.json').write_text(json.dumps(cmd,indent=2)+'\n')
with (out/'compile.log').open('w')as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
print('HC_FAULT_BUILD rc=',r.returncode,flush=True);sys.exit(r.returncode)
