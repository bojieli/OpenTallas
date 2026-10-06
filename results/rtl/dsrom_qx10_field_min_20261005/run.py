import pathlib,subprocess,os,json,time,shutil,sys,hashlib
J=pathlib.Path(__file__).resolve().parent
os.environ["PYTHONDONTWRITEBYTECODE"]="1"
def capacity(label):
 def sample():
  v=list(map(int,pathlib.Path("/proc/stat").read_text().splitlines()[0].split()[1:9])); return sum(v),v[3]
 a=sample();time.sleep(5);b=sample()
 m={x.split(":")[0]:int(x.split()[1]) for x in pathlib.Path("/proc/meminfo").read_text().splitlines()}
 r=dict(stage=label,utc=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),load1=os.getloadavg()[0],idle_cores_5s=(b[1]-a[1])/os.sysconf("SC_CLK_TCK")/5,required_cores=5,mem_available_bytes=m["MemAvailable"]*1024,disk_free_bytes=shutil.disk_usage(J).free,admission_reservation_GiB=32)
 with (J/"capacity.jsonl").open("a") as f:f.write(json.dumps(r)+"\n")
 if r["idle_cores_5s"]<5:
  (J/"capacity.refused").write_text(json.dumps(r)+"\n");sys.exit(75)
capacity("before-unchanged-guard")
if "--admitted" not in sys.argv:
 os.execv("/srv/opentallas-scratch/admit.sh",["admit.sh","32","--",sys.executable,str(J/"run.py"),"--admitted"])
capacity("actual-exec")
assert not subprocess.check_output(["git","-C",str(J/"src"),"status","--porcelain"])
m=json.loads((J/"noether-qx10-field-source-manifest.json").read_text())
assert all(hashlib.sha256((J/"src"/p).read_bytes()).hexdigest()==h for p,h in m["files"].items())
(J/"started.json").write_text(json.dumps(dict(pid=os.getpid(),source_commit=m["source_commit"],QX=10,utc=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())))+"\n")
cmds=[[sys.executable,"tools/dsrom_1m_field.py","build","--work",str(J/"work"),"--qelem","10","--jobs","4"],[sys.executable,"tools/dsrom_1m_field.py","run","--work",str(J/"work"),"--qelem","10","--jobs","1","--only","L20.a_proj.fp8,L20.exp158.gu,L20.exp158.w2","--regions","0"]]
for name,cmd in zip(("build","functional"),cmds):
 (J/(name+".command.json")).write_text(json.dumps(cmd)+"\n")
 with (J/(name+".log")).open("w") as f:r=subprocess.run(["/usr/bin/time","-v",*cmd],cwd=J/"src",stdout=f,stderr=subprocess.STDOUT)
 (J/(name+".rc")).write_text(str(r.returncode)+"\n")
 if r.returncode:sys.exit(r.returncode)
(J/"done").write_text("0\n")
