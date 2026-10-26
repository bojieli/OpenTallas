"""Production-shape arithmetic miter: python3 prepare_run.py NEW_SCRATCH_DIR."""
from pathlib import Path
import subprocess,re,shutil,sys
here=Path(__file__).resolve().parent
repo=Path(subprocess.check_output(['git','-C',str(here),'rev-parse','--show-toplevel'],text=True).strip())
out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=False)
p='rtl/v41rom/ot_v41_fadd.sv'
old=subprocess.check_output(['git','-C',str(repo),'show','c51d6d9303:'+p],text=True)
old=re.sub(r'\bot_v41_fadd\b','ot_v41_fadd_ref',old);old=re.sub(r'\bot_v41_cut\b','ot_v41_cut_ref',old)
(out/'ref.sv').write_text(old);shutil.copy2(repo/p,out/'new.sv');shutil.copy2(repo/'rtl/common/ot_prefix.sv',out/'prefix.sv')
for f in ['run.py','tb.sv']:shutil.copy2(here/f,out/f)
subprocess.run([sys.executable,str(out/'run.py')],check=True)
