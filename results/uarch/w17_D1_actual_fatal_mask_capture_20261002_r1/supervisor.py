import os,json,hashlib,subprocess,time,resource,datetime,re,fcntl
from pathlib import Path
OUT=Path(__file__).resolve().parent
ROOT=Path("/tmp/opentallas-D1-parent-bound-attribution-20261002")
PLAN=ROOT/"results/uarch/w17_D1_reset_fault_attribution_20261002/debugger_plan.json"
SCRIPT=ROOT/"results/uarch/w17_D1_reset_fault_attribution_20261002/capture_masks.gdb"
RECOVERY=Path("/tmp/DS-recovery-negative-successor-capacity-20261002-r1/reservation.json")
COORD=RECOVERY.parent/"Hubble_D1_GDB_shared_capacity_20261002_r1.json"
OLD=ROOT/"results/uarch/w17_D1_disjoint_native_actual_runtime_20261002_r1/runtime"
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(name,value): (OUT/name).write_text(json.dumps(value,indent=2)+"\n")
fd=os.open(OUT/"invocation_once",os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
os.close(fd)
assert not subprocess.check_output(["git","status","--porcelain"],cwd=ROOT)
head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
assert head=="784f6de2bf393664f0e87ad79891414ccfd9110d"
p=json.loads(PLAN.read_text())
inputs={"binary":p["binary"],"program":p["program"],"GDB":p["debugger"]["path"],"approved_script":str(SCRIPT),"plan":str(PLAN),"old_runtime_log":str(OLD/"runtime.log"),"old_failed_receipt":str(OLD/"receipt.json")}
before={k:sha(v) for k,v in inputs.items()}
assert before["binary"]==p["binary_SHA256"]
assert before["program"]==p["program_SHA256"]
assert before["GDB"]==p["debugger"]["SHA256"]
recovery=json.loads(RECOVERY.read_text())
assert recovery["reservation_active"] and recovery["reserved_cpus"]==[6,7]
assert recovery["memory_reservation_bytes"]==16*1024**3
assert Path("/proc/"+str(recovery["PID"])).exists()
assert 8 in recovery["D1_CPUs_preserved"]
mem={k:int(v.split()[0])*1024 for k,v in (line.split(":",1) for line in Path("/proc/meminfo").read_text().splitlines()) if k in ("MemTotal","MemAvailable")}
reservation=96*1024**3;host=32*1024**3;peer=16*1024**3
assert mem["MemAvailable"]>=reservation+host+peer
assert os.sched_getaffinity(0)=={8}
for limit in (resource.RLIMIT_CPU,resource.RLIMIT_AS,resource.RLIMIT_FSIZE):
 resource.setrlimit(limit,(resource.RLIM_INFINITY,resource.RLIM_INFINITY))
lease=open(OUT/"D1_shared_reservation.lock","w")
fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
record={"schema":"opentallas.D1.actual-fatal-mask-capture.v1","source_head":head,"owned_supervisor_PID":os.getpid(),"UTC":datetime.datetime.now(datetime.timezone.utc).isoformat(),"input_paths":inputs,"input_hashes_before":before,"supervisor_SHA256":sha(__file__),"fresh_memory":mem,"D1_capacity_reservation_bytes":reservation,"host_reserve_bytes":host,"recovery_reserve_bytes":peer,"memory_after_reservations_bytes":mem["MemAvailable"]-reservation-host-peer,"MemoryMax":None,"capacity_reservation_not_kernel_limit":True,"CPU_affinity":[8],"recovery_reservation":recovery,"recovery_reservation_SHA256":sha(RECOVERY),"coordination_receipt":str(COORD),"coordination_SHA256":sha(COORD),"wall_limit":None,"CPU_limit":None,"AS_limit":None,"FS_limit":None,"simulator_launches":1,"compiler_or_link_launches":0,"fulltoken":False,"original_PC24_cause":"UNOBSERVED","service_bound":"BOUND_MISSING"}
argv=[p["debugger"]["path"],"-q","-batch","-nx","-x",str(SCRIPT),"-ex","run","-ex",'printf "D1_INFERIOR_EXIT code=%d\\n", $_exitcode']
record["argv"]=argv
write("admission.json",record)
start=time.monotonic()
with open(OUT/"gdb_runtime.log","w") as log:
 proc=subprocess.Popen(argv,cwd=OUT,stdout=log,stderr=subprocess.STDOUT)
 record["owned_GDB_PID"]=proc.pid
 write("start.json",record)
 code=proc.wait()
record["GDB_exit_code"]=code
record["wall_s"]=time.monotonic()-start
record["input_hashes_after"]={k:sha(v) for k,v in inputs.items()}
record["input_postcheck"]=record["input_hashes_after"]==before
log=(OUT/"gdb_runtime.log").read_text()
found=re.findall(r"D1_ACTUAL_FATAL_MASK fault_r=0x([0-9a-f]+) dbg_fs=0x([0-9a-f]+) violations=0x([0-9a-f]+)",log)
exits=re.findall(r"D1_INFERIOR_EXIT code=(-?[0-9]+)",log)
record["actual_mask_capture_count"]=len(found)
record["actual_masks"]={k:int(v,16) for k,v in zip(("fault_r","dbg_fs","violations"),found[0])} if len(found)==1 else None
record["inferior_exit_code"]=int(exits[-1]) if exits else None
record["original_fatal_seen"]="D1_SOURCE_OR_LEDGER_FAULT" in log
record["verdict"]="PASS_ACTUAL_MASK_CAPTURE_ORIGINAL_RUNTIME_FAIL_PRESERVED" if code==0 and record["inferior_exit_code"]==1 and len(found)==1 and record["original_fatal_seen"] and record["input_postcheck"] else "FAIL_CAPTURE_GATE"
record["recovery_reservation_unchanged"]=sha(RECOVERY)==record["recovery_reservation_SHA256"]
record["runtime_qualification"]=False
write("receipt.json",record)
fcntl.flock(lease,fcntl.LOCK_UN);lease.close()
write("reservation_released.json",{"owned_PID":os.getpid(),"D1_reservation_released":True,"recovery_lock_untouched":True,"UTC":datetime.datetime.now(datetime.timezone.utc).isoformat()})
