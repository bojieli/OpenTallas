import sys, json, math, re, subprocess, tempfile
from pathlib import Path
W = Path(sys.argv[1]); PLAN = Path(sys.argv[2]); SIDE = Path(sys.argv[3])
sys.path.insert(0, str(W / "tools/die_plan"))
import schema as S, reset_tree as RT
TN = "hd_mesh"
for it in range(40):
    with tempfile.TemporaryDirectory() as td:
        r = subprocess.run([sys.executable, "-I", str(W / "tools/die_plan/gen.py"), "phys", str(PLAN), "--clock-landing", str(SIDE),
                            "--types", TN, "--out", td, "--rtl-root", str(W), "--trial"], capture_output=True, text=True, cwd=str(W))
    out = r.stdout + r.stderr
    if r.returncode == 0:
        print("GEN OK after", it, "fixes"); sys.exit(0)
    m = re.search(r"landing_local_resets\.(\w+): consumer (\S+) reset (\S+) depth (\d+) != copy depth (\d+) \(raw (\w+)\)", out)
    if not m:
        print("UNHANDLED:", out[-600:]); sys.exit(2)
    name, cons, rnet, need, have, raw = m.group(1), m.group(2), m.group(3), int(m.group(4)), int(m.group(5)), m.group(6)
    P = json.load(open(PLAN)); t = P["partition_types"][TN]
    ent = [x for x in t["clock"]["landing_local_resets"] if x["name"] == name][0]
    tree = RT.for_type(S.Plan(P, PLAN), TN)
    c = [x for x in tree["relays"] if x.get("depth") == need - 1]
    n = min(c, key=lambda x: math.dist(x["xy"], ent["xy_um"]))
    print("FIX", name, "consumer", cons, "needs raw depth", need - 1, ent["raw"], "->", n["q"], n["xy"], "dist %.1f" % math.dist(n["xy"], ent["xy_um"]))
    ent["raw"] = n["q"]
    json.dump(P, open(PLAN, "w"), indent=1)
print("too many iterations"); sys.exit(3)
