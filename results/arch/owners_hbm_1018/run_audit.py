"""OWNERS-HBM / NATIVE-HBM routed native pin audit (method = lanes/OWNERS-S81.md header + lanes/NATIVE-BATCH.md).
usage: python3 run_audit.py <repo-with-tools/hier_contract @ origin/main> <dir with views.tsv and v/<commit>/<view>>
views.tsv: short commit, cell, view dir, record (or main AUTO-MERGE) commit, die, die-table element.
Views are `git archive <commit> <view dir>` of the closure job's record commit (main AUTO-MERGE commit of the view when
the record carries no exported view).  launch = O - R <= 220, capture = S + R <= 190 (TT; R = insertion.json boundary
mean = pin-flop arrival RELATIVE to the boundary the parent compensates); clock = boundary spread <= 80 at TT AND FF.
Absolute insertion (R) and sink counts are guidance only (never a FAIL).  No --relative-to used."""
import sys,json,subprocess,re
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1])/"tools/hier_contract"))
import native_pin_audit as N, pinreg_audit as PA
D=Path(sys.argv[2]); out=[]
def corner_spreads(ins):
    res={}
    if not ins: return res
    blocks=[ins]+list(ins.get("clocks",{}).values()) if isinstance(ins.get("clocks"),dict) else [ins]
    for b in blocks:
        for cn in ("tt","ff"):
            bd=(b.get(cn) or {}).get("boundary") if isinstance(b.get(cn),dict) else None
            if bd and bd.get("n"):
                res[(b.get("clock") or "ck")+"/"+cn]=dict(mean=bd["mean"],spread=round(bd["max"]-bd["min"],1),n=bd["n"])
    return res
def jobname(root,vd):
    for n in ("abstract.json","export.json"):
        f=root/vd/n
        if f.exists():
            m=N.JOB_RE.search(f.read_text(errors="replace")[:20000])
            if m: return m.group(1)
    return None
for line in open(D/"views.tsv"):
    c,blk,vd,full,die,el=line.rstrip("\n").split("\t")
    root=D/"v"/c
    r=N.audit_one((str(root),blk,vd)); r.update(element=el,record_commit=full,view=vd,die=die,job=jobname(root,vd))
    if r.get("error"): r["verdict"]="NOT_AUDITABLE"; out.append(r); continue
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
    sp_ff=max([v["spread"] for k,v in cs.items() if k.endswith("/ff")],default=r.get("ff_spread_ps"))
    r["spread_tt_ps"]=sp_tt; r["spread_ff_ps"]=sp_ff
    clk_ok=(sp_tt is not None and sp_tt<=80) and (sp_ff is None or sp_ff<=80)
    if not ins: r["verdict"]="NOT_AUDITABLE"; r["fail_why"]=(r.get("fail_why","")+"; no insertion.json (ideal-clock ETM, no pin-flop reference)").lstrip("; ")
    else:
        r["verdict"]="BINDABLE" if (r.get("pass") and clk_ok) else "FAIL"
        if not clk_ok and "spread" not in r.get("fail_why",""): r["fail_why"]=(r.get("fail_why","")+f"; boundary spread tt {sp_tt} ff {sp_ff} > 80").lstrip("; ")
    out.append(r)
json.dump(dict(schema="owners_hbm_native_1018",tool="tools/hier_contract/native_pin_audit.py audit_one @ "+sys.argv[3] if len(sys.argv)>3 else "",launch_ps=N.LAUNCH_PS,capture_ps=N.CAPTURE_PS,spread_ps=80,rule="owner 0dq 10-17: relative pin-flop arrival + TT/FF boundary spread; insertion/sinks guidance",records=out),open(D/"owners_hbm_native_audit.json","w"),indent=1)
for r in out:
    print(r["die"],"|",r["element"],"|",r.get("job"),"|",r["cell"],"|",r["view"],"|L",r.get("launch_ps"),r.get("launch_pin"),"|C",r.get("capture_ps"),r.get("capture_pin"),"|R",r.get("R_ps"),"sp tt",r.get("spread_tt_ps"),"ff",r.get("spread_ff_ps"),"|comb",r.get("comb_pins"),"|",r["verdict"],r.get("fail_why","") or "",r.get("error","") or "","|",r.get("launch_fail_pins",[])[:6],r.get("capture_fail_pins",[])[:6],"| nL",len(r.get("launch_fail_pins",[])),"nC",len(r.get("capture_fail_pins",[])))
