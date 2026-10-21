import os, pathlib, subprocess, shlex, sys
case=sys.argv[1]
r=pathlib.Path(__file__).resolve().parent
os.chdir(r/'src')
e=os.environ.copy();v=str(pathlib.Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator');e['OT_VERILATOR']=e['VERILATOR']=v;e['PATH']=str(pathlib.Path(v).parent)+':'+e['PATH']
a=shlex.split(subprocess.check_output(['python3','tools/xdie_qtp8/cases.py','args',case],text=True))
raise SystemExit(subprocess.call(['python3','tools/qwen_coll_tp8_static_links_bench.py','--out',str(r/('out_'+case))]+a,env=e))
