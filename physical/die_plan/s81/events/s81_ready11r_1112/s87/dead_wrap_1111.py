"""DIE-S81-87: stage wrapper for delta_dead_proof_1111.py (in place) -> IN OUT REPORT. Runs with cwd = repo root."""
import shutil, subprocess, sys
inp, out, rep = sys.argv[1:4]
shutil.copyfile(inp, out)
r = subprocess.run([sys.executable, "-I", "physical/die_plan/s81/delta_dead_proof_1111.py", out], capture_output=True, text=True)
open(rep, "w").write(r.stdout + r.stderr)
sys.exit(r.returncode)
