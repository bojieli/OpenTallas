import pathlib,hashlib,json,re,subprocess,datetime,os
B=pathlib.Path("/srv/opentallas-scratch/claude/refill-1225")
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def rec(p):
 b=p.read_bytes();s=b.decode(errors="replace")
 lines=s.splitlines(); witnesses=[x for x in lines if re.search(r"PASS|FAIL|Error:|# exit|overall rc|OK   |case .*kind=|cases=|Verilator 5",x)]
 return {"path":str(p),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest(),"witnesses":witnesses,"tail":lines[-4:]}
r={"collected_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"source_commit":(B/"QWREG/src/SOURCE_COMMIT").read_text().strip()}
r["top_legs"]=[rec(p) for p in sorted((B/"QWREG/out").glob("*.out"))]
r["nested"]=[]
for d in [B/"QWREG/src/results/rtl/mu_qwen_1018"/x/"runs" for x in ["amix","adopt_slice","head"]]:
 for p in sorted(d.iterdir()):
  if p.is_file() and p.suffix in [".out",".log",".txt"]:r["nested"].append(rec(p))
r["source_hashes"]={}
for d in ["rtl/qwen_split","rtl/test/qwen_dv","rtl/test/mu_qwen_1018","rtl/test/mu_qwen_seq","rtl/test/mu_qwen_tok","tools/xdie_qtp8"]:
 for p in sorted((B/"QWREG/src"/d).rglob("*")):
  if p.is_file() and p.suffix in [".sv",".py",".sh",".svh"]:r["source_hashes"][str(p.relative_to(B/"QWREG/src"))]=sha(p)
r["layer"]={"bench_outputs":[rec(p) for p in (B/"QWLAYER").glob("nu*/runs/*/bench.out")],"run_script":rec(B/"QWLAYER/run.sh"),"logs":[rec(p) for p in sorted((B/"QWLAYER").glob("nu*.log"))]}
ps=subprocess.check_output(["ps","-eo","pid,ppid,etimes,pcpu,rss,args"],text=True)
rows=[]
for l in ps.splitlines()[1:]:
 f=l.split(None,5)
 if len(f)==6: rows.append((int(f[0]),int(f[1]),f))
roots=[pid for pid,ppid,f in rows if "make -C " in f[5] and ("/QWREG/" in f[5] or "/QWLAYER/" in f[5]) and not f[5].startswith("sh -c")]
r["builds"]=[]
for root in roots:
 ids={root};change=True
 while change:
  new={pid for pid,ppid,f in rows if ppid in ids};change=bool(new-ids);ids|=new
 leaves=[f for pid,ppid,f in rows if pid in ids and "/cc1plus " in f[5]]
 rf=next(f for pid,ppid,f in rows if pid==root)
 r["builds"].append({"make_pid":root,"elapsed_s":int(rf[2]),"command":rf[5],"cc1plus":len(leaves),"cpu_sum":sum(float(f[3]) for f in leaves),"rss_kib":sum(int(f[4]) for f in leaves)})
print(json.dumps(r,indent=2))
