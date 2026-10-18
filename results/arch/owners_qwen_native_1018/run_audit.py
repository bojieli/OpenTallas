import sys,json
from pathlib import Path
D=sys.argv[1]
sys.path.insert(0,D+"/tools/hier_contract")
import native_pin_audit as N, pinreg_audit as PA
out=[]
rows=[l.rstrip("\n").split("\t") for l in open(D+"/views.tsv")]
byjob={r[0]:r for r in rows}
# supplementary relative mode for the width-1 forwarded lane (assumed chain rlyh0_1_SW -> rlyh_1_SN -> landh_1_EW)
REL={"qfwd_rlyh_1_sn_65x30-f1-93960f2c9":"qfwd_rlyh0_1_sw_65x30-f2-9ddc1acf2",
     "qfwd_landh_1_ew_65x30-f2-9ddc1acf2":"qfwd_rlyh_1_sn_65x30-f1-93960f2c9"}
def fails(root,blk,vd,refs_fn):
    pass
for job,blk,vd,c in rows:
    root=f"{D}/v/{job}"
    r=N.audit_one((root,blk,vd)); r.update(job=job,record_commit=c,view=vd)
    lp=Path(root)/vd/f"{blk}_tt.lib"
    ij=Path(root)/vd/"insertion.json"; ins=json.loads(ij.read_text()) if ij.exists() else None
    lib=PA.parse_lib(lp); refs=PA.clock_refs(lib,ins,"tt")
    fl=[];fc=[]
    for n,m in PA.pin_metrics(lib,refs).items():
        if m["dir"]=="output" and m["out"] is not None and m["out"]>N.LAUNCH_PS: fl.append((n,round(m["out"],1)))
        if m["dir"]=="input" and m["inp"] is not None and m["inp"]>N.CAPTURE_PS: fc.append((n,round(m["inp"],1)))
    r["launch_fail_pins"]=sorted(fl,key=lambda x:-x[1]); r["capture_fail_pins"]=sorted(fc,key=lambda x:-x[1])
    if job in REL:
        nj=REL[job]; nb=byjob[nj]
        try:
            comp=PA.compensation(f"{D}/v/{nj}/{nb[2]}")
            rr=N.audit_one((root,blk,vd,comp))
            r["relative_supplementary"]=dict(neighbour_job=nj,pass_=rr.get("pass"),fail_why=rr.get("fail_why"),relative=rr.get("relative"),
                launch_ps=rr.get("launch_ps"),capture_ps=rr.get("capture_ps"))
        except Exception as e:
            r["relative_supplementary"]=dict(neighbour_job=nj,error=f"{type(e).__name__}: {e}")
    out.append(r)
json.dump(dict(schema="owners_qwen_native_1018",tool="tools/hier_contract/native_pin_audit.py audit_one",tool_commit=open(D+"/tool_commit.txt").read().strip(),
  launch_ps=N.LAUNCH_PS,capture_ps=N.CAPTURE_PS,spread_ps=80,records=out),open(D+"/native_audit.json","w"),indent=1)
for r in out:
    print(r["job"],"|L",r.get("launch_ps"),r.get("launch_pin"),"|C",r.get("capture_ps"),r.get("capture_pin"),"|R",r.get("R_ps"),"sp",r.get("spread_ps"),"ffsp",r.get("ff_spread_ps"),
      "|comb",r.get("comb_pins"),"|ff Lmin",r.get("ff_launch_min_ps"),"hold",r.get("ff_hold_need_ps"),"|","PASS" if r.get("pass") else "FAIL "+r.get("fail_why","")+r.get("error",""),
      "|",r["launch_fail_pins"][:6],r["capture_fail_pins"][:6],"|REL",r.get("relative_supplementary"))
