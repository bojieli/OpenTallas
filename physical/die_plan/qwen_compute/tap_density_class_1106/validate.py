"""Apply the event to the POR copy, reload with schema.Plan, recompute density taps per type; write new_taps.json."""
import json, sys, subprocess
from pathlib import Path
WT, EV, PLAN = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(WT / "tools/die_plan")); import taps as T, schema as S
out = EV.parent / "plan_qc52_tapclass_candidate.json"
print(subprocess.run([sys.executable, "-I", str(EV / "apply_event.py"), str(PLAN), str(out)], check=True, capture_output=True, text=True).stdout)
raw = json.loads(out.read_text()); P = S.Plan(raw, str(PLAN))
patch = json.loads((EV / "clock_patches.json").read_text()); res = {}
for tn in sorted(patch):
    tp = T.density_taps(P, tn, False); res[tn] = [list(x) for x in tp]
    assert len(tp) == patch[tn]["model"]["taps"], (tn, len(tp))
    import gen_phys as G   # the kit exports this clock block produces must be legal (affinity radius <= tap radius)
    ex = G.tap_chain_affinity_exports(raw["partition_types"][tn]) + G._density_cfg(raw["partition_types"][tn])
    assert any("OT_TAP_CHAIN_AFFINITY" in e for e in ex) and any("OT_TAP_REASSIGN_UM" in e for e in ex), (tn, ex)
(EV / "new_taps.json").write_text(json.dumps(res, separators=(",", ":")) + "\n")
print("VALIDATE PASS", len(res), "types; taps", sum(len(v) for v in res.values()))
