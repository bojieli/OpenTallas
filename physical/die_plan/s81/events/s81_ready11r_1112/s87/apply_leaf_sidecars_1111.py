"""DIE-S81-87 (DO_NOT_COUNT): apply CPL-S81-LEAF-2/-3 clean-slate leaf sidecars (<fam>.types_after.json: hard_cores, internal_stations, clock per type)
by type identity onto the current plan. usage: IN OUT REPORT DIR[,DIR...] [--skip TYPE,...]
A type is applied only if its hard_cores instance+module set equals the plan's (else SKIPPED and reported, never forced)."""
import glob, json, sys
inp, out, rep, dirs = sys.argv[1:5]
skip = set(sys.argv[6].split(",")) if len(sys.argv) > 6 and sys.argv[5] == "--skip" else set()
P = json.load(open(inp)); T = P["partition_types"]
applied, skipped = {}, {}
files = sorted(f for d in dirs.split(",") for f in glob.glob(d + "/**/*.types_after.json", recursive=True))
for f in files:
    for t, v in json.load(open(f)).items():
        if t in skip: skipped[t] = "listed skip"; continue
        if t not in T: skipped[t] = "type not in plan"; continue
        a = sorted((h["inst"], h["module"]) for h in T[t]["hard_cores"]); b = sorted((h["inst"], h["module"]) for h in v["hard_cores"])
        if a != b: skipped[t] = "hard_cores identity differs"; continue
        for k in ("hard_cores", "internal_stations", "clock"):
            if k in v: T[t][k] = v[k]
        applied[t] = f.split("/")[-1]
json.dump(P, open(out, "w"), indent=1)
json.dump(dict(applied=applied, skipped=skipped, n_files=len(files)), open(rep, "w"), indent=1)
print(len(applied), "applied", len(skipped), "skipped", skipped)
