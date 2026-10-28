import json,os,subprocess,sys
from pathlib import Path
p=Path(sys.argv[1]); w=Path(sys.argv[2]); out=Path(sys.argv[3]); extra=sys.argv[4:]
os.environ['PYTHONPATH']=str(w/'tools/die_plan')+':/srv/opentallas-scratch2/claude/die-proto-2325/pylib'
os.environ['OPENBLAS_NUM_THREADS']='2';os.environ['PYTHONDONTWRITEBYTECODE']='1';os.environ['MPLCONFIGDIR']=str(out/'mpl')
out.mkdir(parents=True,exist_ok=True)
args=json.load(open(p/'args.json'))
sha=subprocess.check_output(['git','-C',str(w),'rev-parse','HEAD'],text=True).strip()
dirty=subprocess.check_output(['git','-C',str(w),'status','--short','tools'],text=True)
(out/'source.txt').write_text(sha+'\n'+dirty)
with open(out/'export.log','w') as f:
    code=subprocess.call(['python3',str(w/'tools/die_plan/qc_clk_mesh3_export.py'),*args,*extra,'--out',str(out/'export')],stdout=f,stderr=subprocess.STDOUT,cwd=p)
raise SystemExit(code)
