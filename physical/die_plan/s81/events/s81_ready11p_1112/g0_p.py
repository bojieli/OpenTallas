import json, re, subprocess, sys, uuid
from pathlib import Path
R = Path("/srv/opentallas-scratch2/claude/die-s81-85/compose1111"); REPO = R / "repo"
HERE = REPO / "physical/die_plan/s81"
plan = R / "out/s87_ready11p/plan.json"; out = R / "out/s87_ready11p/g0_out"; out.mkdir(exist_ok=True)
tmp = HERE / f".psplit_g0_{uuid.uuid4().hex}.json"; tmp.write_bytes(plan.read_bytes())
try:
    r = subprocess.run([sys.executable, "-I", str(REPO / "tools/die_plan/check.py"), str(tmp), "--out", str(out), "--quiet"], capture_output=True, text=True, cwd=REPO)
finally:
    tmp.unlink()
(out / "g0.log").write_text(r.stdout + r.stderr)
NUM = re.compile(r"carries \d+ bits on \d+ tracks = [0-9.]+")
key = lambda i: (i.get("check"), NUM.sub("carries N", i.get("msg") or ""))
rb = json.loads((R / "out/s87_ready11r/g0_out/g0_report.json").read_text()); ro = json.loads((out / "g0_report.json").read_text())
E = lambda x: [i for i in x["findings"] if i.get("level") == "ERROR"]
eb = {key(i) for i in E(rb)}; new = [i for i in E(ro) if key(i) not in eb]
ob = {key(i) for i in E(ro)}; gone = [i for i in E(rb) if key(i) not in ob]
res = dict(base_errors=len(E(rb)), out_errors=len(E(ro)), new=[f"[{i.get('check')}] {i.get('msg')}"[:300] for i in new], gone=len(gone))
(R / "out/s87_ready11p/g0_diff.json").write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1)[:2000])
