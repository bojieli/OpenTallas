"""HEAD-FORM-R3 W13 launch guard (HEAD-INT-R3 approved 11-27).
argv: CANDIDATE_JSON HOLDS_JSON ALLOWED_IN_FLIGHT(comma)
Re-projects the candidate onto the live kit_wave.json (w13_permit.py, read-only, temp dir), runs a dry
`kit_wave.py plan --config <projection> --probe` on rt b71c, and refuses (rc 3) unless every only_item of
s81_head is either eligible or a W12f row in flight whose type block is unchanged (ALLOWED_IN_FLIGHT),
no only_item is skipped for any other reason, and no WAIT-PLAN-VISUAL shows for s81_head."""
import json, re, subprocess, sys, tempfile
from pathlib import Path

cand, holds, allowed = sys.argv[1], sys.argv[2], set(x for x in sys.argv[3].split(",") if x)
here = Path(__file__).resolve().parent
K = "/srv/opentallas-scratch2/claude/rt/b71c5218e0b5/tools/autopilot/kit_wave.py"
only = set(json.loads(Path(cand).read_bytes())["marker"]["config"]["only_items"])
with tempfile.TemporaryDirectory(prefix="w13guard-", dir=str(Path.home() / "tmp")) as td:
    p = subprocess.run(["python3", "-I", str(here / "w13_permit.py"), cand, td, holds, "hd_lep0N"],
                       capture_output=True, text=True, timeout=900)
    if p.returncode:
        print("GUARD FAIL: projection failed:", (p.stdout + p.stderr)[-800:]); sys.exit(3)
    q = subprocess.run(["python3", "-I", K, "plan", "--config", str(Path(td) / "projected_kit_wave.json"), "--probe"],
                       capture_output=True, text=True, timeout=1200, cwd=str(Path.home() / "coord/autopilot"))
    out = q.stdout + q.stderr
lines = out.splitlines()
try:
    i = next(n for n, ln in enumerate(lines) if ln.startswith("s81_head: "))
except StopIteration:
    print("GUARD FAIL: no s81_head block in plan output (rc %d)" % q.returncode); sys.exit(3)
if not lines[i].startswith("s81_head: ON"):
    print("GUARD FAIL: die not ON:", lines[i][:200]); sys.exit(3)
elig, flight, other = set(), set(), {}
for ln in lines[i + 1:]:
    if not ln.startswith("  "):
        break
    m = re.match(r"\s+eligible \d+: (.*)", ln)
    if m:
        elig |= {t.split("(")[0] for t in m.group(1).split()}
        continue
    m = re.match(r"\s+skip \d+ \[(.*?)\]: (.*)", ln)
    if m:
        names = set(m.group(2).split())
        if m.group(1) == "wave item in flight":
            flight |= names
        else:
            for n in names:
                other[n] = m.group(1)
bad = []
for t in sorted(only):
    if t in elig:
        continue
    if t in flight and t in allowed:
        continue
    bad.append((t, "in flight but type block changed" if t in flight else other.get(t, "not listed")))
pv = [ln for ln in lines if "WAIT-PLAN-VISUAL" in ln and "s81_head" in ln]
print("GUARD eligible", sorted(elig & only)); print("GUARD in-flight(unchanged)", sorted(flight & only))
if bad or pv:
    print("GUARD FAIL:", bad, pv[:3]); sys.exit(3)
print("GUARD PASS: %d only_items, 0 would WAIT outside the allowed unchanged W12f placed rows" % len(only))
