# runs ON the fleet host (python3 - <<), reads job list JSON from stdin-embedded env OT_INV
import json, os, glob, sys
jobs = json.loads(os.environ["OT_INV"])
FINAL = ("6_final.odb", "6_final.def", "6_final.gds", "6_final.gds.gz", "6_final.oas", "6_final.v", "6_final.sdc",
         "6_final.spef", "6_1_merged.gds", "6_final.cdl")
def sz(p):
    try:
        return os.path.getsize(p)
    except OSError:
        return -1
out = {}
for j in jobs:
    run = (j.get("run") or "").rstrip("/")
    r = dict(run_exists=os.path.isdir(run), files={}, final_base=None, route_base=None)
    out[j["job"]] = r
    if not r["run_exists"]:
        continue
    files = r["files"]
    def add(p):
        if os.path.isfile(p) and not os.path.islink(p) or os.path.islink(p) and os.path.isfile(os.path.realpath(p)):
            files[os.path.relpath(p, run)] = sz(p)
    od = (j.get("orfs_dir") or "").rstrip("/")
    route_orfs = sorted(glob.glob(run + "/routes/*/work/orfs")) + sorted(glob.glob(run + "/route")) + sorted(glob.glob(run + "/routes/*/signoff"))
    cands = ([od] if od else []) + route_orfs
    bases = []
    for o in cands:
        for b in sorted(glob.glob(o + "/results/*/*/base")):
            bases.append((o, b))
    if bases:
        o, b = bases[0]
        r["final_base"] = os.path.relpath(b, run)
        for f in FINAL:
            add(os.path.join(b, f))
        for f in glob.glob(b + "/*.sdc") + glob.glob(b + "/*.rpt") + glob.glob(b + "/*.lef") + glob.glob(b + "/*.lib"):
            add(f)
        nick = os.path.basename(os.path.dirname(b))
        for f in glob.glob(f"{o}/reports/*/{nick}/base/*") + glob.glob(f"{o}/logs/*/{nick}/base/*.json") + \
                 glob.glob(f"{o}/logs/*/{nick}/base/6_report.log") + glob.glob(o + "/*.log") + glob.glob(o + "/*.sdc") + \
                 glob.glob(o + "/config*.mk") + glob.glob(o + "/hooks/*.sdc"):
            if sz(f) < 200 << 20:
                add(f)
        if o != route_orfs[0] if route_orfs else False:
            rb = glob.glob(route_orfs[0] + "/results/*/*/base")
            if rb:
                r["route_base"] = os.path.relpath(rb[0], run)
                add(os.path.join(rb[0], "klayout.lyt"))
                nick2 = os.path.basename(os.path.dirname(rb[0]))
                for f in glob.glob(f"{route_orfs[0]}/reports/*/{nick2}/base/*") + glob.glob(f"{route_orfs[0]}/logs/*/{nick2}/base/*.json") + \
                         glob.glob(route_orfs[0] + "/config*.mk"):
                    if sz(f) < 200 << 20:
                        add(f)
    for rd in glob.glob(run + "/routes/*"):
        for f in ("corner_sta.json", "physical.json", "signoff.sdc", "status", "sta.log", "flow.log"):
            p = os.path.join(rd, f)
            if sz(p) < 50 << 20:
                add(p)
        for f in glob.glob(rd + "/physical_artifacts/*"):
            if r["final_base"] and f.endswith((".odb", ".def", ".gds", ".spef", ".oas")):
                continue
            add(f)
    for f in glob.glob(run + "/cl/*.json") + glob.glob(run + "/cl/*.sdc") + glob.glob(run + "/cl/*.rpt") + [run + "/STATUS"]:
        if sz(f) < 50 << 20:
            add(f)
    for root, ds, fs in os.walk(run + "/record"):
        for f in fs:
            add(os.path.join(root, f))
    # abstract views produced by the job (not the imported source tree)
    for root, ds, fs in os.walk(run):
        rel = os.path.relpath(root, run)
        if os.path.basename(root) in ("work", "objects") or rel.split("/")[0] in ("src", "record") or rel.startswith("bench_src") or "/objects/" in root or rel.split("/")[0] == "bench":
            ds[:] = []
            continue
        for f in fs:
            if f.endswith((".lef", ".lib", ".lib.gz")) and ("views" in rel or "abstract" in rel or "view" in rel or f.startswith(j.get("block") or "\0")):
                add(os.path.join(root, f))
print("INV_JSON" + json.dumps(out))
