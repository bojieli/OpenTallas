#!/usr/bin/env python3
"""Existing core-face and completeness checks with the source plan's real sidecars."""
import json,sys
from pathlib import Path
sys.path.insert(0,'tools/die_plan')
import schema as S,check as C
plan=Path(sys.argv[1]);out=Path(sys.argv[2]);P=S.Plan(json.load(open(plan)),str(plan));R=C.Report(completeness=True)
a=C.check_core_faces(P,R,str(plan.parent),str(plan.parent/'core_conns.json'))
b=C.check_completeness(P,R,side=C.load_core_conns(plan.parent),plan_dir=plan.parent)
r=dict(scope='EXISTING_CHECKS_WITH_EXPLICIT_CONTEXT',core_faces=a,complete=b,errors=R.errors(),warnings=[r for r in R.items if r['level']=='WARN'])
out.write_text(json.dumps(r,indent=1));print(json.dumps(dict(errors=len(R.errors()),warnings=len([r for r in R.items if r['level']=='WARN']),core_faces=a)),flush=True)
