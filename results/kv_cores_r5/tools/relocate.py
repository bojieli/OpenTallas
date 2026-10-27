"""KV-CORES-R5: make the R4-regenerated head core.json repo-relative (bind-cell + core RTL copied into results/,
repo sources mapped from the kv-kits-1 worktree only if byte-identical in this worktree)."""
import json, shutil, sys, filecmp, hashlib
from pathlib import Path
src, repo, outrel = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
KK = "/srv/opentallas-scratch2/claude/wt/kv-kits-1-1027/"
for d in sorted(src.iterdir()):
    mod = d.name; od = repo / outrel / mod; od.mkdir(parents=True, exist_ok=True)
    cj = json.load(open(d / f"{mod}_core.json"))
    nf = []
    for f in cj["files"]:
        if f.startswith(KK):
            rel = f[len(KK):]
            assert filecmp.cmp(f, repo / rel, shallow=False), f"differs from this worktree: {rel}"
            nf.append(rel)
        else:
            dst = od / Path(f).name
            shutil.copy2(f, dst); nf.append(str(dst.relative_to(repo)))
    cj["files"] = nf
    cj.setdefault("report", {})["kv_cores_r5_relocate"] = "files repo-relative (R4 corertl, kv-kits-1 b51 bind)"
    (od / f"{mod}_core.json").write_text(json.dumps(cj, indent=1) + "\n")
    print(mod, len(nf), "files", hashlib.sha256((od / f"{mod}.sv").read_bytes()).hexdigest()[:12])
