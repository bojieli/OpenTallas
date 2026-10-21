import json,subprocess,pathlib
p=pathlib.Path.cwd();m=json.load(open('manifest.json'));v=pathlib.Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
files=[str(p/f['path']) for f in m['files']];dirs=sorted(set(str(pathlib.Path(f).parent)for f in files))
r=subprocess.run([str(v),'--lint-only','--timing','-Wno-fatal','--top-module',m['top'],'-GENABLE_SERVICE=1','-GENABLE_NATIVE=1','-GENABLE_TOKEN=1','-GNL=2']+['+incdir+'+x for x in dirs]+files,stdout=open('lint.log','w'),stderr=subprocess.STDOUT)
print('HOST_WRAPPER_LINT',r.returncode,len(files),flush=True);raise SystemExit(r.returncode)
