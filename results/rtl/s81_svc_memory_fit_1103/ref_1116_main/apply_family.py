import sys,json
from pathlib import Path
W=Path("/srv/opentallas-scratch2/claude/fable-fix-s81-svc")
sys.path.insert(0,str(W/"candidate_main/tools/die_plan"))
import s81_svc_memory_closure as C
C.CUR_REF=W/"regen/pt/results/rtl/s81_svc_memory_fit_1103/ref_1116_main"
generated=json.loads((W/"f2sv_main/results.json").read_text())
assert len(generated)==16 and not any(generated.values()),generated
packet=W/"family_main2"; rpt=json.loads((packet/"closure.json").read_text())
res={}
for t in sorted(generated):
 d=W/"f2sv_main"/t
 kr=json.loads((d/"kit_rtl.json").read_text())
 b=d/(kr["bound_module"]+".sv")
 r=rpt["types"][t]
 assert C.sha(C.canon_h8(b.read_text()))==r["before_sha256"],(t,"canonical source mismatch")
 closed=(packet/b.name).read_text()
 assert C.sha(closed)==r["after_sha256"],(t,"closed sha mismatch")
 receipt=C.apply_kit(d,closed=closed,form="v2")
 assert receipt["status"]=="APPLIED",(t,receipt)
 res[t]={k:receipt[k] for k in ["status","before_sha256","after_sha256","macros_added"]}
 print(t,"APPLIED",receipt["after_sha256"][:12],flush=True)
(W/"apply_family.json").write_text(json.dumps(res,indent=1)+"\n")
print("FAMILY_APPLIED_MAIN_PASS 16/16",flush=True)
