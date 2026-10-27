#!/usr/bin/env python3
"""quick G0C core_faces only: faces.py TOOLS_DIR PLANDIR"""
import sys, json
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import check as C, schema as S
pd = Path(sys.argv[2]); raw = json.loads((pd / "die_plan.json").read_text())
R = C.Report(True); P = S.Plan(raw, pd / "die_plan.json")
s = C.check_core_faces(P, R, str(pd), None)
print(json.dumps(s))
for e in R.errors():
    print(e["level"], e["msg"][:220])
