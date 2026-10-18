"""NATIVE-3 routed native pin audit (method = lanes/NATIVE-2.md + owner 0dq 10-17 relative clock rule).
usage: python3 run_audit.py <repo-with-tools/hier_contract> <dir with views.tsv and v/>
launch = O - R <= 220, capture = S + R <= 190 (TT; R = insertion.json boundary mean, i.e. pin-flop arrival
RELATIVE to the boundary the parent compensates); clock = boundary spread <= 80 at TT AND FF. Absolute
insertion (R) and sink counts are reported as guidance only (never a FAIL)."""
import sys,json,subprocess
from pathlib import Path
sys.path.insert(0,sys.argv[1]+"/tools/hier_contract")
import native_pin_audit as N, pinreg_audit as PA
D=Path(sys.argv[2]); out=[]
def jobname(c):
    s=subprocess.run(["git","-C",sys.argv[1],"log","-1","--format=%s%n%D",c],capture_output=True,text=True).stdout
    import re
    m=re.search(r"record (\S+) \(",s) or re.search(r"closure-record-(\S+?)(,|$)",s,re.M)
    return m.group(1) if m else c
def corner_spreads(ins):
    res={}
    if not ins: return res
    blocks=[ins]+[v for v in ins.get("clocks",{}).values()] if isinstance(ins.get("clocks"),dict) else [ins]
    for b in blocks:
        for cn in ("tt","ff"):
            bd=(b.get(cn) or {}).get("boundary") if isinstance(b.get(cn),dict) else None
            if bd and bd.get("n"):
                k=(b.get("clock") or "ck")+"/"+cn
                res[k]=dict(mean=bd["mean"],spread=round(bd["max"]-bd["min"],1))
    return res
for line in open(D/"views.tsv"):
    c,blk,vd,full,die=line.rstrip("\n").split("\t")
    root=D/"v"/c
    r=N.audit_one((str(root),blk,vd)); r.update(job=jobname(c),record_commit=full,view=vd,die=die)
    lp=root/vd/f"{blk}_tt.lib"
    if not lp.exists(): lp=Path(str(lp)+".gz")
    ij=root/vd/"insertion.json"; ins=json.loads(ij.read_text()) if ij.exists() else None
    lib=PA.parse_lib(lp); refs=PA.clock_refs(lib,ins,"tt")
    fl=[];fc=[]
    for n,m in PA.pin_metrics(lib,refs).items():
        if m["dir"]=="output" and m["out"] is not None and m["out"]>N.LAUNCH_PS: fl.append((n,round(m["out"],1)))
        if m["dir"]=="input" and m["inp"] is not None and m["inp"]>N.CAPTURE_PS: fc.append((n,round(m["inp"],1)))
    r["launch_fail_pins"]=sorted(fl,key=lambda x:-x[1]); r["capture_fail_pins"]=sorted(fc,key=lambda x:-x[1])
    cs=corner_spreads(ins); r["corner_boundary"]=cs
    sp_tt=max([v["spread"] for k,v in cs.items() if k.endswith("/tt")],default=r.get("spread_ps"))
    sp_ff=max([v["spread"] for k,v in cs.items() if k.endswith("/ff")],default=None)
    r["spread_tt_ps"]=sp_tt; r["spread_ff_ps"]=sp_ff
    clk_ok=(sp_tt is not None and sp_tt<=80) and (sp_ff is None or sp_ff<=80)
    r["verdict"]="BINDABLE" if (r.get("pass") and clk_ok) else "FAIL"
    if not clk_ok: r["fail_why"]=(r.get("fail_why","")+f"; boundary spread tt {sp_tt} ff {sp_ff} > 80").lstrip("; ")
    out.append(r)
json.dump(dict(schema="native_3_1017",launch_ps=N.LAUNCH_PS,capture_ps=N.CAPTURE_PS,spread_ps=80,rule="owner 0dq 10-17: relative pin-flop arrival + TT/FF boundary spread; insertion/sinks guidance",records=out),open(D/"native_3_audit.json","w"),indent=1)
for r in out:
    print(r["die"],"|",r["job"],"|",r["cell"],"|",r.get("launch_ps"),r.get("launch_pin"),"|",r.get("capture_ps"),r.get("capture_pin"),"|R",r.get("R_ps"),"sp tt",r["spread_tt_ps"],"ff",r["spread_ff_ps"],"|comb",r.get("comb_pins"),"|",r["verdict"],r.get("fail_why","") or "",r.get("error","") or "","|",r["launch_fail_pins"][:5],r["capture_fail_pins"][:5],"| nL",len(r["launch_fail_pins"]),"nC",len(r["capture_fail_pins"]))
