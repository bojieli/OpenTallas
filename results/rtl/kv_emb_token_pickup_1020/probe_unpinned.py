import subprocess,runpy,sys,pathlib
# Use the existing diagnostic unchanged, removing host pinning from its ot-run call.
orig=subprocess.run
def run(cmd,*a,**kw):
 if isinstance(cmd,list) and cmd and cmd[0]=='ot-run' and '--hosts' in cmd:
  i=cmd.index('--hosts');cmd=cmd[:i]+cmd[i+2:]
 return orig(cmd,*a,**kw)
subprocess.run=run
sys.argv=[str(pathlib.Path(__file__).parents[3]/'tools/ref_tile/cts_native_probe.py')]+sys.argv[1:]
runpy.run_path(sys.argv[0],run_name='__main__')
