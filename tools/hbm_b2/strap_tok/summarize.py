#!/usr/bin/env python3
"""TOK-HBM 10-25 strap token test, last step: verdict + repo-relative provenance manifest.

    python3 tools/hbm_b2/strap_tok/summarize.py REPO OUT

Reads OUT/ties.json and OUT/bench/<old_module>/{sim.log,files.f,tb.sv,rtl/}.  PASS needs, for every distinct plan tie
value: RESULT ... PASS (strap master == old constant variant on every output bit every cycle, outputs toggle, strap
bit-0 mutant caught); every plan instance covered; >= 2 distinct values per master.  The manifest names every bench
source file by git blob: 'repo' = byte-identical to a tracked file at source_commit (repo-relative path), 'generated' =
written by the repo kit generator (physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py) or gen_bench.py at that commit.
The strap master wrapper must be 'repo'."""
import hashlib, json, re, subprocess, sys
from pathlib import Path
R, OUT = Path(sys.argv[1]), Path(sys.argv[2])
commit = (OUT / "source_commit.txt").read_text().strip()
ties = json.load(open(OUT / "ties.json"))
views = {v["module"]: v for v in json.load(open(R / "physical/die_plan/hbm_arch_cores/views_b2n_strap.json"))["view_list"]}
tree = {}
for ln in subprocess.run(["git", "-C", str(R), "ls-tree", "-r", commit, "--", "rtl", "physical"], capture_output=True,
                         text=True, check=True).stdout.splitlines():
    meta, path = ln.split("\t", 1)
    tree.setdefault(meta.split()[2], []).append(path)
def blob(p):
    d = p.read_bytes(); return hashlib.sha1(b"blob %d\0" % len(d) + d).hexdigest(), hashlib.sha256(d).hexdigest()
rows, err, manifest = [], [], {}
for b in ties["benches"]:
    d = OUT / "bench" / b["old_module"]
    res = [l for l in (d / "sim.log").read_text(errors="replace").splitlines() if l.startswith("RESULT")] if (d / "sim.log").exists() else []
    ok = len(res) == 1 and res[0].endswith(" PASS")
    m = re.search(r"dut_vs_ref_diffs=(\d+) mutant_diffs=(\d+) ref_output_changes=(\d+)", res[0]) if res else None
    rows.append(dict(master=b["master"], old_module=b["old_module"], straps=b["straps"], plan_instances=b["plan_instances"],
                     verdict="PASS" if ok else "FAIL", dut_vs_ref_diffs=int(m.group(1)) if m else None,
                     mutant_diffs=int(m.group(2)) if m else None, ref_output_changes=int(m.group(3)) if m else None))
    if not ok:
        err.append(f"{b['old_module']}: {res[0] if res else 'no RESULT'}"); continue
    wrap = Path(views[b["master"]]["strap_master"]["wrapper"])
    for f in sorted((d / "rtl").iterdir()) + [d / "tb.sv"]:
        g, s = blob(f)
        rec = manifest.setdefault(s, dict(name=f.name, sha256=s, benches=0))
        rec["benches"] += 1
        if g in tree:
            rec["repo"] = sorted(tree[g])[0]
        else:
            rec["generated"] = "gen_bench.py" if f.name == "tb.sv" else "gen_core_kit_hbm.py"
        if f.name == wrap.name and rec.get("repo") != str(wrap):
            err.append(f"{b['old_module']}: strap master wrapper {f.name} is not byte-identical to repo {wrap}")
per = {}
for r in rows:
    p = per.setdefault(r["master"], dict(pass_values=0, fail_values=0, plan_instances_covered=0))
    p["pass_values" if r["verdict"] == "PASS" else "fail_values"] += 1
    if r["verdict"] == "PASS":
        p["plan_instances_covered"] += len(r["plan_instances"])
for mname, p in per.items():
    if p["pass_values"] < 2:
        err.append(f"{mname}: {p['pass_values']} PASS values (< 2)")
    if p["plan_instances_covered"] != ties["per_master"][mname]["plan_instances"]:
        err.append(f"{mname}: {p['plan_instances_covered']}/{ties['per_master'][mname]['plan_instances']} plan instances covered")
if ties["verdict"] != "PASS":
    err.append("ties.json verdict FAIL")
s = dict(test="TOK-HBM strap token test: every HBM B2n plan strap_* tie value, strap master vs the old constant variant",
         source_commit=commit, plan=ties["plan"], plan_ties=ties["plan_ties"], per_master=per, benches=rows,
         manifest_files=len(manifest), manifest_repo=sum(1 for r in manifest.values() if "repo" in r),
         manifest_generated=sum(1 for r in manifest.values() if "generated" in r), errors=err,
         verdict="PASS" if not err else "FAIL")
json.dump(s, open(OUT / "summary.json", "w"), indent=1)
json.dump(sorted(manifest.values(), key=lambda r: r["name"]), open(OUT / "source_manifest.json", "w"), indent=1)
print(json.dumps(dict(verdict=s["verdict"], per_master=per, manifest=[s["manifest_files"], s["manifest_repo"], s["manifest_generated"]], errors=err[:6])))
sys.exit(0 if not err else 1)
