"""DIE-QC-36 A0: byte-identity regression of tools/die_plan/core_infra.py (opt-in delta) against origin/main.

For every listed kit (its master_slice.json + small top-level kit files, copied twice to scratch), run
core_infra.install(kd, slice) and core_infra.kit_cts_hook(kd, config.mk lines) once with the BASE tool directory and
once with the NEW one (each in its own `python3 -I` process), then compare the sha256 of every file in the two kit
copies plus the returned cfg lines. Also records whether BASE reproduces the kit's own committed master_core_infra.tcl
(input sanity; informational).
    python3 -I regress_core_infra.py --base BASE/tools/die_plan --new NEW/tools/die_plan --list kits.txt --out out.tsv
"""
import argparse, hashlib, json, shutil, subprocess, sys, tempfile
from pathlib import Path

RUN = r'''
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import core_infra as CI
kd = Path(sys.argv[2])
sl = json.loads((kd / "master_slice.json").read_text())
old = kd / "core_infra_plan.json.kit"
if old.is_file():
    cp = json.loads(old.read_text()).get("core_clock_port")
    if cp and not (sl.get("core_clock_port") or (sl.get("core_tree") or {}).get("clock_port")) == cp:
        sl = dict(sl, core_clock_port=cp)
res = {}
try:
    res["install"] = CI.install(kd, sl)
except Exception as e:
    res["install_error"] = f"{type(e).__name__}: {e}"
cfg = (kd / "config.mk").read_text().splitlines() if (kd / "config.mk").is_file() else []
try:
    res["hook"] = CI.kit_cts_hook(kd, cfg)
except BaseException as e:
    res["hook_error"] = f"{type(e).__name__}: {e}"
res["cfg"] = cfg
(kd / "_result.json").write_text(json.dumps(res, sort_keys=True))
'''


def digest(d):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(d.iterdir()) if p.is_file()}


def copy_kit(src, dst):
    dst.mkdir(parents=True)
    for p in src.iterdir():
        if p.is_file() and p.stat().st_size < 8_000_000:
            shutil.copyfile(p, dst / p.name)
    if (dst / "core_infra_plan.json").is_file():
        shutil.copyfile(dst / "core_infra_plan.json", dst / "core_infra_plan.json.kit")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True); ap.add_argument("--new", required=True)
    ap.add_argument("--list", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--tmp", default=None)
    a = ap.parse_args()
    rows = ["kit\tdie\tcore_tree\tbase_install\tfiles\tidentical\tbase_matches_kit_master\tsha256_new_master"]
    nid = ntot = 0
    for line in Path(a.list).read_text().split():
        kd = Path(line).parent
        if not (kd / "master_slice.json").is_file():
            rows.append(f"#MISSING\t{kd}")
            continue
        with tempfile.TemporaryDirectory(dir=a.tmp) as t:
            t = Path(t)
            out = {}
            for tag, tool in (("base", a.base), ("new", a.new)):
                copy_kit(kd, t / tag)
                subprocess.run([sys.executable, "-I", "-c", RUN, tool, str(t / tag)], check=True, timeout=600)
                out[tag] = digest(t / tag)
            same = out["base"] == out["new"]
            r = json.loads((t / "base" / "_result.json").read_text())
            st = "ok" if r.get("install") else ("false" if "install_error" not in r else "ERR:" + r["install_error"][:60])
            tree = "-"
            if (t / "base" / "core_infra_plan.json").is_file():
                tree = "tree" if json.loads((t / "base" / "core_infra_plan.json").read_text()).get("core_tree") else "none"
            km = kd / "master_core_infra.tcl"
            match = "-" if not km.is_file() or "master_core_infra.tcl" not in out["base"] else \
                str(hashlib.sha256(km.read_bytes()).hexdigest() == out["base"]["master_core_infra.tcl"])
            die = next((d for d in ("s81", "head", "kv", "hbm", "qc", "qfd", "hd_", "hfd", "ot_s81", "dsdv")
                        if d in str(kd).lower()), "?")
            rows.append(f"{kd}\t{die}\t{tree}\t{st}\t{len(out['new'])}\t{same}\t{match}\t"
                        f"{out['new'].get('master_core_infra.tcl', '-')}")
            ntot += 1; nid += same
            if not same:
                diff = sorted(k for k in set(out["base"]) | set(out["new"]) if out["base"].get(k) != out["new"].get(k))
                rows.append(f"#DIFF\t{kd}\t{diff}")
    rows.append(f"# identical {nid}/{ntot}")
    Path(a.out).write_text("\n".join(rows) + "\n")
    print(f"identical {nid}/{ntot}")
    sys.exit(0 if nid == ntot else 1)


if __name__ == "__main__":
    main()
