import sys,json
sys.path.insert(0,sys.argv[1]+"/tools/tools/hier_contract")
import native_pin_audit as N, pinreg_audit as PA
D=sys.argv[1]; out=[]
for line in open(D+"/views.tsv"):
    job,blk,vd,c=line.rstrip("\n").split("\t")
    root=f"{D}/v/{job}"
    r=N.audit_one((root,blk,vd)); r.update(job=job,record_commit=c,view=vd)
    # list failing pins
    from pathlib import Path
    lp=Path(root)/vd/f"{blk}_tt.lib"
    if not lp.exists(): lp=Path(str(lp)+".gz")
    ij=Path(root)/vd/"insertion.json"; ins=json.loads(ij.read_text()) if ij.exists() else None
    lib=PA.parse_lib(lp); refs=PA.clock_refs(lib,ins,"tt")
    fl=[];fc=[]
    for n,m in PA.pin_metrics(lib,refs).items():
        if m["dir"]=="output" and m["out"] is not None and m["out"]>N.LAUNCH_PS: fl.append((n,round(m["out"],1)))
        if m["dir"]=="input" and m["inp"] is not None and m["inp"]>N.CAPTURE_PS: fc.append((n,round(m["inp"],1)))
    r["launch_fail_pins"]=sorted(fl,key=lambda x:-x[1]); r["capture_fail_pins"]=sorted(fc,key=lambda x:-x[1])
    out.append(r)
json.dump(dict(schema="native_batch_1017",launch_ps=N.LAUNCH_PS,capture_ps=N.CAPTURE_PS,spread_ps=80,records=out),open(D+"/native_batch_audit.json","w"),indent=1)
for r in out:
    sp=r.get("spread_ps"); ok=r.get("pass") and (sp is not None and sp<=80)
    print(r["job"],"|",r.get("launch_ps"),r.get("launch_pin"),"|",r.get("capture_ps"),r.get("capture_pin"),"|R",r.get("R_ps"),"sp",sp,"|comb",r.get("comb_pins"),"|",r.get("ref_src"),"|","PASS" if ok else "FAIL "+r.get("fail_why","")+(r.get("error","")), "|", r["launch_fail_pins"][:6], r["capture_fail_pins"][:6])
