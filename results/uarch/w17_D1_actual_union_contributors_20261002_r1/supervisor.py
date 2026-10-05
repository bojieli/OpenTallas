import sys,os,json,hashlib,subprocess,time,resource,datetime,re,fcntl
from pathlib import Path
OUT=Path(__file__).resolve().parent
ROOT=Path("/tmp/opentallas-D1-union-contributor-plan-20261002")
GO=Path("/tmp/D1-union-contributor-parent-GO-20261002.json")
PLAN=ROOT/"results/uarch/w17_D1_union_contributor_capture_plan_20261002/plan.json"
SCRIPT=PLAN.parent/"capture_contributors.gdb"
sys.path.insert(0,str(ROOT))
from tools.w17_D1_root_header_layout import validate_plan

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(name,value):(OUT/name).write_text(json.dumps(value,indent=2)+"\n")
os.close(os.open(OUT/"invocation_once",os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600))
assert not subprocess.check_output(["git","status","--porcelain"],cwd=ROOT)
head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
g=json.loads(GO.read_text());p=json.loads(PLAN.read_text())
assert g["approved"] is True and g["source_commit"]==head=="012be9cf09863f8c6b2d7f7cc274254a317bd246"
assert sha(PLAN)==g["plan_SHA256"] and sha(SCRIPT)==g["script_SHA256"]
validation=validate_plan(PLAN)
assert validation["status"]=="PASS_OFFLINE_SOURCE_HASH_AND_LAYOUT_ONLY"
old=ROOT/"results/uarch/w17_D1_disjoint_native_actual_runtime_20261002_r1/runtime"
last=ROOT/"results/uarch/w17_D1_actual_fatal_mask_capture_20261002_r1/receipt.json"
inputs={"binary":p["binary"]["path"],"program":p["program"]["path"],"GDB":p["GDB"]["path"],"GO":str(GO),"plan":str(PLAN),"approved_script":str(SCRIPT),"old_runtime_log":str(old/"runtime.log"),"old_failed_receipt":str(old/"receipt.json"),"previous_mask_receipt":str(last),"archive":"/tmp/w17-D1-native-joined-20261002-r1/obj/Vtb_D1_scope_core__ALL.a","root_header":p["layout"]["header"]}
before={k:sha(v) for k,v in inputs.items()}
for key in ("binary","program","GDB"):assert before[key]==g[key+"_SHA256"]
assert before["archive"]=="d724823df4d6f142d097601f4d551f52f0fdbb332a0cd52671eb3a67b3cf12a3"
recovery=subprocess.check_output(["systemctl","--user","show","DS-recovery-negative-successor-20261002-r1.service","-pMainPID","-pActiveState","-pResult"],text=True)
assert "MainPID=0" in recovery and "ActiveState=inactive" in recovery and "Result=success" in recovery
mem={k:int(v.split()[0])*1024 for k,v in (line.split(":",1) for line in Path("/proc/meminfo").read_text().splitlines()) if k in ("MemTotal","MemAvailable")}
reserve=g["admission"]["D1_capacity_reservation_bytes"];host=g["admission"]["host_reserve_bytes"];peer=g["admission"]["recovery_reserve_bytes"]
assert mem["MemAvailable"]>=reserve+host+peer
assert os.sched_getaffinity(0)=={8}
for limit in (resource.RLIMIT_CPU,resource.RLIMIT_AS,resource.RLIMIT_FSIZE):resource.setrlimit(limit,(resource.RLIM_INFINITY,resource.RLIM_INFINITY))
lease=open(OUT/"D1_CPU8_capacity_reservation.lock","w");fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
argv=[v.replace("SOURCE_ROOT",str(ROOT)) for v in g["future_argv"]]
assert argv==[p["GDB"]["path"],"-q","-batch","-nx","-x",str(SCRIPT),"-ex","run","-ex",'printf "D1_INFERIOR_EXIT code=%d\\n", $_exitcode']
record={"schema":"opentallas.D1.actual-KV-contributor-capture.v1","source_head":head,"owned_supervisor_PID":os.getpid(),"UTC":datetime.datetime.now(datetime.timezone.utc).isoformat(),"GO":g,"input_paths":inputs,"input_hashes_before":before,"supervisor_SHA256":sha(__file__),"fresh_validation":validation,"fresh_memory":mem,"D1_capacity_reservation_bytes":reserve,"host_reserve_bytes":host,"recovery_reserve_bytes":peer,"memory_after_reservations_bytes":mem["MemAvailable"]-reserve-host-peer,"MemoryMax":None,"CPU_affinity":[8],"recovery_fresh_terminal_state":recovery,"recovery_or_peer_locks_untouched":True,"wall_limit":None,"CPU_limit":None,"AS_limit":None,"FS_limit":None,"simulator_launches":1,"compiler_or_link_launches":0,"fulltoken":False,"original_PC24_cause":"UNOBSERVED","service_bound":"BOUND_MISSING","prefetch_fault_code":None,"prefetch_fault_code_availability":"NO_STORED_GENERATED_FIELD","argv":argv}
write("admission.json",record);start=time.monotonic()
with open(OUT/"gdb_runtime.log","w") as log:
 proc=subprocess.Popen(argv,cwd=OUT,stdout=log,stderr=subprocess.STDOUT)
 record["owned_GDB_PID"]=proc.pid;write("start.json",record);code=proc.wait()
record["GDB_exit_code"]=code;record["wall_s"]=time.monotonic()-start
record["input_hashes_after"]={k:sha(v) for k,v in inputs.items()}
record["input_postcheck"]=record["input_hashes_after"]==before
log=(OUT/"gdb_runtime.log").read_text()
def capture(prefix):
 pairs=re.findall(r"^"+prefix+r" ([^=\n]+)=0x([0-9a-f]+)$",log,re.M)
 if len({key for key,value in pairs})!=len(pairs):return None
 return {key:int(value,16) for key,value in pairs}
record["first_prime_fields"]=capture("D1_FIRST_PRIME_READY_SAMPLE")
record["fatal_fields"]=capture("D1_FATAL_FIELD")
exits=re.findall(r"D1_INFERIOR_EXIT code=(-?[0-9]+)",log)
record["inferior_exit_code"]=int(exits[-1]) if exits else None
record["original_fatal_seen"]="D1_SOURCE_OR_LEDGER_FAULT" in log
record["verdict"]="PASS_ACTUAL_CONTRIBUTOR_CAPTURE_RUNTIME_FAIL_PRESERVED" if code==0 and record["inferior_exit_code"]==1 and record["first_prime_fields"] is not None and len(record["first_prime_fields"])==8 and record["fatal_fields"] is not None and len(record["fatal_fields"])==39 and record["original_fatal_seen"] and record["input_postcheck"] else "FAIL_CAPTURE_GATE"
record["runtime_qualification"]=False
write("receipt.json",record)
fcntl.flock(lease,fcntl.LOCK_UN);lease.close()
write("reservation_released.json",{"D1_reservation_released":True,"owned_PID":os.getpid(),"recovery_or_peer_locks_untouched":True,"UTC":datetime.datetime.now(datetime.timezone.utc).isoformat()})
