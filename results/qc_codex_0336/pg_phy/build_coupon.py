"""Separate-supply feasibility coupon; legacy point-source diagnostic, not IR sign-off."""
import json
import sys
from pathlib import Path

repo = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repo / "tools/die_plan"))
import schema as S
import infra_pg_domains as G

inputs = Path(__file__).resolve().parent
plan = repo / "physical/die_plan/qwen_compute/plan_of_record/plan_qc46.json"
raw = S.load(plan)
raw["die"]["io"] = json.loads((plan.parent / "die_io.json").read_text())
# The current repository has no typed finite PHY power-pad dimensions. Preserve
# the existing diagnostic point-source model explicitly; never substitute the
# 70-um core C4 pad for the much finer published-assumption PHY power lattice.
# Core 150-um point sources also make the adjacent high-density core strip a
# conservative feasibility proxy rather than claiming the QC75 finite-pad gate.
raw["die"]["pg"]["bumps"] = {"pitch_um": 150, "pad_um": 0}
P = S.Plan(raw, plan)
pg = json.loads((inputs / "pg.json").read_text())
window = json.loads((inputs / "window.json").read_text())
result = G.make(P, plan.parent, pg, window, Path(sys.argv[1]), 8.64)
print(json.dumps({k: v for k, v in result.items() if k not in {"bumps", "die"}}, indent=1))
