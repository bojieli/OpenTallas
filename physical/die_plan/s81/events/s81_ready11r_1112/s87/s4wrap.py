"""DIE-S81-87: stage wrapper for S81-ARCH-RTL-2 slice-4 (29c9b8791920): apply_slice4.py then gen.py latency --inplace. IN OUT REPORT; cwd = repo root."""
import shutil, subprocess, sys
from pathlib import Path
inp, out, rep = sys.argv[1:4]
S = "/srv/opentallas-scratch2/claude/die-s81-85/compose1111/s87/src/s4/results/arch/s81_slice4_pincycles_1111"
tmp = Path(out).with_suffix(".s4tmp.json")
r1 = subprocess.run([sys.executable, "-I", S + "/apply_slice4.py", inp, S + "/event_s4.json", str(tmp)], capture_output=True, text=True)
log = r1.stdout + r1.stderr
if r1.returncode:
    open(rep, "w").write(log); sys.exit(r1.returncode)
lat = Path(out).parent / "s4_latency_out"; lat.mkdir(exist_ok=True)
r2 = subprocess.run([sys.executable, "-I", "tools/die_plan/gen.py", "latency", str(tmp), "--inplace", "--out", str(lat)], capture_output=True, text=True)
log += r2.stdout[-3000:] + r2.stderr[-3000:]
open(rep, "w").write(log)
if r2.returncode: sys.exit(r2.returncode)
shutil.move(str(tmp), out)
