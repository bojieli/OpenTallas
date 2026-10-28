"""filelist for lint / port-bind of a generated die top: generated wrappers + every type's leaf sources (repo-relative)."""
import json
import sys
from pathlib import Path

plan, gen, repo, out = map(Path, sys.argv[1:5])
sim = len(sys.argv) > 5 and sys.argv[5] == "sim"
P = json.loads(plan.read_text())
files = [str(f) for f in sorted(gen.glob("*.sv")) if not f.name.endswith("_top.sv")]
files.append(str(repo / "rtl/common/ot_dp_clk_landing.sv"))
seen = set(files)
for tn, t in sorted(P["partition_types"].items()):
    if t.get("hard"):
        continue
    subs = t.get("simulation_substitutions", {}) if sim else {}
    for s in t.get("sources", []):
        s = subs.get(s, s)
        f = str(repo / s)
        if f not in seen:
            seen.add(f)
            files.append(f)
    if sim:
        for s in subs.values():
            f = str(repo / s)
            if f not in seen:
                seen.add(f)
                files.append(f)
out.write_text("\n".join(files) + "\n")
print(len(files))
