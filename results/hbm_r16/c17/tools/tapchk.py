import sys, json
from pathlib import Path
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/codex-hbm-plan-1351/tools/die_plan")
import check as C, schema as S
pd = Path(sys.argv[1]).resolve(); P = S.Plan(S.load(str(pd / "die_plan.json")), pd / "die_plan.json"); R = C.Report(True)
print("taps_cores", C.check_taps_cores(P, R, str(pd)))
try:
    print("clock_entry_macro", C.check_clock_entry_macro(P, R, str(pd), None))
except Exception as e:
    print("clock_entry_macro n/a", repr(e)[:200])
for i in R.items:
    if i["level"] == "ERROR": print(i["level"], i["check"], i["msg"][:300])
