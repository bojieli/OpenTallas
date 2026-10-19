#!/usr/bin/env python3
"""TOKEN-PASS-HBMDS (10-18): source bundle of the d4g die vehicle (git archive of the die_filelist selection at --rev,
die.v, the vehicle TB and run script) with the uniquified module variants renamed (renames.json of die_filelist.py).
    make_bundle.py --fl FLDIR --repo /home/ubuntu/OpenTallas --rev REV --die die.v --wt WORKTREE --out BUNDLE
"""
import argparse, json, re, shutil, subprocess, tarfile, io
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fl", required=True); ap.add_argument("--repo", default="/home/ubuntu/OpenTallas")
    ap.add_argument("--rev", required=True); ap.add_argument("--die", required=True)
    ap.add_argument("--wt", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--views", help="die views plan (env DEFINES per master), e.g. vplan_fast/views.json")
    a = ap.parse_args()
    fl, out = Path(a.fl), Path(a.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    files = [l for l in (fl / "files.f").read_text().split() if l]
    hdrs = [l for l in (fl / "headers.f").read_text().split() if l]
    tar = subprocess.run(["git", "-C", a.repo, "archive", "--format=tar", a.rev, *sorted(set(files + hdrs))],
                         capture_output=True, check=True).stdout
    tarfile.open(fileobj=io.BytesIO(tar)).extractall(out)
    for d in (fl / "incdirs.f").read_text().split():
        (out / d.replace("+incdir+", "")).mkdir(parents=True, exist_ok=True)
    ren = json.loads((fl / "renames.json").read_text())
    n = 0
    for f, r in ren.items():
        p = out / f
        t = p.read_text()
        for k, new in r.items():
            kind, m = k.split(":", 1)
            if kind == "def":
                t, c = re.subn(r"\b(module\s+)" + m + r"\b", r"\g<1>" + new, t)
            else:
                t, c = re.subn(r"(?m)(^|;|\bbegin\b|\belse\b|\bend\b)(\s*)" + m + r"\b(?=\s*(#|[A-Za-z_]\w*\s*[\(\[]))",
                               r"\g<1>\g<2>" + new, t)
            n += c
        p.write_text(t)
    for x in ("files.f", "incdirs.f", "filelist.json", "renames.json", "master_files.json"):
        shutil.copy(fl / x, out / x)
    shutil.copy(a.die, out / "die.v")
    (out / "rtl/test/hbm_layer").mkdir(parents=True, exist_ok=True)
    for tb in Path(a.wt, "rtl/hbm_next/vehicle").glob("*.sv"):
        shutil.copy(tb, out / "rtl/test/hbm_layer" / tb.name)
    for sh in list(Path(a.wt, "tools/hbm_next/vehicle").glob("run_*.sh")) + [Path(a.wt, "tools/hbm_next/vehicle/flatten_masters.py")]:
        shutil.copy(sh, out / sh.name)
    if a.views:
        shutil.copy(a.views, out / "views.json")
    print(f"BUNDLE {out} files={len(files)} renamed_sites={n}")


if __name__ == "__main__":
    main()
