import pathlib,sys,subprocess,json,hashlib,time,shutil
S=pathlib.Path("/srv/opentallas/repos/hubble-wg-service-09944fc4a");O=pathlib.Path("/srv/opentallas/jobs-overflow/hubble-wg-service-r2")
sys.path.insert(0,str(S/"tools"))
from dshbm_expert_workgroup import exported_weight_reader
from dshbm_expert_workgroup_interleave import paired_rows,compact_stream,expand_stream
src=["ot_hbm_accel_cdc_fifo.sv","ot_hbm_accel_expert_stream_pc_la.sv","ot_hbm_accel_expert_fetch_stream_la.sv","ot_hbm_accel_expert_stream_pc_wg.sv","ot_hbm_accel_wg_dispatch.sv","ot_hbm_accel_expert_fetch_stream_wg.sv","ot_hbm_accel_wg_gearbox.sv"]
paths=[S/"rtl/hbm_accel/service"/n for n in src]+[S/"rtl/test/hbm_accel/tb_hbm_accel_wg_service.sv"]
rec=dict(source_commit="09944fc4a",status="BUILDING_SERVICE_ONLY",scope="actual die2/stack0 released GU+W2 source bytes, 32PC service; no SM/numerical/wholetoken/physical transfer",source_sha256={str(p.relative_to(S)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},cases=[],adopted=False,rate_credit=False,start_delay_credit_us=0)
def save():(O/"record.json").write_text(json.dumps(rec,indent=2)+"\n")
save()
try:
 cmd=["verilator","--binary","--timing","-O2","-Wno-fatal","-j","16","--top-module","tb_hbm_accel_wg_service","--Mdir",str(O/"obj")]+[str(p) for p in paths]
 rec["compile_command"]=cmd;save()
 with (O/"compile.log").open("w") as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
 exe=O/"obj/Vtb_hbm_accel_wg_service";rec["binary_sha256"]=hashlib.sha256(exe.read_bytes()).hexdigest();save()
 for L in (20,3):
  weights=pathlib.Path(f"/srv/opentallas-scratch/jobs/hubble-expert-workgroup-source-inputs-20261005/L{L}")
  ids=json.loads((weights/"source.json").read_text())["expert_ids"];reader=exported_weight_reader(weights,L,ids)
  out=O/f"L{L}";out.mkdir();gu=[];words=[]
  for e in ids:
   p,s=paired_rows(reader,e,2,0);raw=compact_stream(p,s)
   gu.extend(int.from_bytes(raw[i:i+128],"little") for i in range(0,len(raw),128));words.extend(expand_stream(raw))
  (out/"gu.hex").write_text("".join(f"{w:0256x}\n" for w in gu));(out/"sm_expected.hex").write_text("".join(f"{w:0272x}\n" for w in words))
  source=pathlib.Path(f"/srv/opentallas/jobs-overflow/hubble-expert-w2-source-20261005/L{L}/stack0_complete")
  for name in ("w2.hex","cfg_lut.hex","cfg_lines.hex"):shutil.copy2(source/name,out/name)
  args=[str(exe),f"+DIR={out}","+notice_lead_ps=300000"]+[f"+id{i}={e}" for i,e in enumerate(ids)]
  begin=time.monotonic()
  with (out/"runtime.log").open("w") as f:r=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT)
  text=(out/"runtime.log").read_text();ok=r.returncode==0 and "FIRST verdict=PASS" in text
  rec["cases"].append(dict(layer=L,die=2,stack=0,ids=ids,exit=r.returncode,exact_bytes=ok,wall_seconds=time.monotonic()-begin,argv=args,input_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob("*.hex")},calendar=[l for l in text.splitlines() if l.startswith(("SLOT ","BW ","FIRST "))]));save()
  if not ok:raise RuntimeError(f"service-only {L} FAIL; preserve firstfailure; no caplift/retry")
  with (out/"corrupted_FAIL.log").open("w") as f:bad=subprocess.run(args+["+mut=1"],stdout=f,stderr=subprocess.STDOUT)
  if not (bad.returncode!=0 and "GU sector mismatch" in (out/"corrupted_FAIL.log").read_text()):raise RuntimeError("negative not rejected")
 rec["status"]="PASS_SERVICE_BYTES_ONLY";save()
except Exception as e:
 rec["status"]="FAIL_RETAINED";rec["error"]=repr(e);save();raise
