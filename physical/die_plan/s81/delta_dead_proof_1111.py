"""republish the plan dead-input declarations from the proof re-proven on main e5cc5a2 sources (DIE-S81-86 11-11, option (a)).

main 8d9b741c58 changed dsdv_svc_sx / dsdv_svc_sx_hrow, so the 11-01 proof no longer admitted. The re-proof is written to the SAME
path (proof_closing_source39_1101.json), which asbuilt_f.dead_input_proofs already selects, so no manifest change is needed. Same 36
declarations and dead ports; only dsdv_svc_sx module_sha256 (16 rows) and the dsdv_svc_sx_hrow dependency hash change. This drops the
plan rows of that proof and re-applies them from the re-proof (same form as delta_dead_proof_1103.py). Usage: python3 -I delta_dead_proof_1111.py PLAN.json (repo root cwd)."""
import json,sys
from pathlib import Path
sys.path.insert(0,"tools/die_plan")
import dead_inputs as D, added_tap_recentre as AT
OLD="results/token_pass/s81_dead_inputs_2148/proof_closing_source39_1101.json"; NEW=OLD
f=sys.argv[1]; src=Path(f).read_text(); P=json.loads(src)
n0=0
for t in P["partition_types"].values():
    if "dead_inputs" in t:
        k=len(t["dead_inputs"]); t["dead_inputs"]=[d for d in t["dead_inputs"] if d.get("proof")!=OLD]; n0+=k-len(t["dead_inputs"])
n=D.apply_plan_declarations(P,NEW,".")
Path(f).write_text(AT.dumps_like(P,src)); print("dropped",n0,"applied",n)
