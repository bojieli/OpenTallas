"""republish the plan dead-input declarations from the reproven proof (same ports; module_sha256 of the current source)."""
import json,sys
from pathlib import Path
sys.path.insert(0,"tools/die_plan")
import dead_inputs as D, added_tap_recentre as AT
OLD="results/token_pass/s81_dead_inputs_2148/proof_closing_s13obs_1029.json"; NEW="results/token_pass/s81_dead_inputs_2148/proof_closing_source39_1101.json"
f=sys.argv[1]; src=Path(f).read_text(); P=json.loads(src)
n0=0
for t in P["partition_types"].values():
    if "dead_inputs" in t:
        k=len(t["dead_inputs"]); t["dead_inputs"]=[d for d in t["dead_inputs"] if d.get("proof")!=OLD]; n0+=k-len(t["dead_inputs"])
n=D.apply_plan_declarations(P,NEW,".")
Path(f).write_text(AT.dumps_like(P,src)); print("dropped",n0,"applied",n)
