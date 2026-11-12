"""one-shot candidate from a base spec (opt best_spec or spec.json) + group moves. usage:
exp.py TYPE BASESPEC 'units:a,b,c:dx:dy;banks:pair5,pair6:dx:dy' [TAG]  -> lad + checks + route_supply p99 (+maps hotcl)"""
import json, sys, copy, re, os, subprocess, importlib.util
B = "/srv/opentallas-scratch3/claude/cpl-hbm-b1/lad"
tn, bs, ops = sys.argv[1:4]; tag = sys.argv[4] if len(sys.argv) > 4 else "x"
sys.argv = ["opt.py", tn, "0"]
spec_ = importlib.util.spec_from_file_location("o", f"{B}/opt2.py")
src = open(f"{B}/opt2.py").read().split("best, why = evaluate(sp")[0].replace('W_ = f"{B}/opt/{tn}"', f'W_ = f"{{B}}/exp/{tn}_{tag}"')
g = {"__name__": "o"}; exec(compile(src, "opt2", "exec"), g)
sp = json.load(open(bs)) if bs != "base" else g["sp"]
if bs != "base" and "banks" not in sp: sp["banks"] = g["sp"]["banks"]
c = copy.deepcopy(sp)
for op in filter(None, ops.split(";")):
    grp, names, dx, dy = op.split(":"); dx, dy = float(dx), float(dy)
    for n in names.split(","):
        e = c[grp][n] if grp != "rows" else c["rows"][int(n)]
        if grp == "units": e[1] = round(e[1] + dx, 3); e[2] = round(e[2] + dy, 3)
        elif grp == "banks": e[0] = round(e[0] + dx, 3); e[1] = round(e[1] + dy, 3)
        else: e["x0"] += dx; e["x1"] += dx; e["y"] = round(e["y"] + dy, 3)
v, w = g["evaluate"](c, "x")
print("RESULT", tn, tag, v, w)
if v is not None:
    json.dump(c, open(f"{g['W_']}/cand_spec.json", "w"), indent=1)
    W_ = g["W_"]
    subprocess.run(["python3", "-I", "tools/die_plan/route_supply.py", f"{W_}/mini/die_plan.json", "--die", "hbm", "--repo", ".", "--ref-dirs", f"{W_}/mini",
                    "--types", tn, "--maps", "--out", f"{W_}/rsm"], cwd=f"{B}/wt", capture_output=True)
    print(subprocess.run(["python3", "-I", f"{B}/hotcl.py", f"{W_}/rsm/hbm__{tn}.npz", "2.6"], capture_output=True, text=True).stdout)
