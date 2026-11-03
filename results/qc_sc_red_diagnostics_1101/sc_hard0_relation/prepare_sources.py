from pathlib import Path
import subprocess
p=Path(__file__).resolve().parent
for label,sha in [('old','051340895d9'),('new','98bbbbd8184')]:
 for name in ['qfd_dv_s5_sc2_k79.sv','qfd_dv_s5_sc2_leaf.sv']:
  (p/(label+'_'+name)).write_bytes(subprocess.check_output(['git','show',sha+':rtl/qwen_dv/s5/'+name]))
