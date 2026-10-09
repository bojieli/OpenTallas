#!/usr/bin/env python3
"""FLOW-FIX-0410 2026-10-09: which (* keep *) register copies does the ORFS yosys fold back into one flop?

For every RTL file (rtl/, physical/) that declares a register with a keep attribute, each module that holds such a
declaration is elaborated alone (its submodules stay black boxes) with the ORFS image's yosys at default parameters:
  A  read_verilog -sv -DSYNTHESIS; hierarchy -top M; proc; flatten; opt_clean        (every declared copy)
  B  ... ; synth -top M -flatten -run coarse:fine                                          (the ORFS coarse pass, opt_merge; begin skipped so absent submodules stay black boxes)
  C  as B with physical/common_flow/ot_keep_regs.tcl run after hierarchy               (the fix)
and counts the distinct flip-flop bits that drive keep-wire bits.  folded = A - B; C must equal A.
Limits: default parameters only (a REPL / copy-count parameter set by the route is not applied), single-file
elaboration (a module that needs another file's package or include reports an error row).

  keep_reg_fold_scan.py [--files F ...] [--jobs 8] [--image openroad/orfs:latest] --output scan.json
"""
import argparse, json, os, re, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
YOSYS = "/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys"
KEEP_RE = re.compile(r'\(\*\s*keep\s*(?:=\s*"?(?:1|true|yes)"?)?\s*\*\)\s*(?:reg|logic)\b')
MOD_RE = re.compile(r"^\s*module\s+(\w+)", re.M)
HOOK = ROOT / "physical/common_flow/ot_keep_regs.tcl"


def candidates():
    out = subprocess.run(["git", "grep", "-l", "-P", KEEP_RE.pattern, "--", "rtl", "physical"], cwd=ROOT,
                         capture_output=True, text=True).stdout.split()
    return [f for f in out if f.endswith((".v", ".sv"))]


def keep_modules(text):
    starts = [(m.start(), m.group(1)) for m in MOD_RE.finditer(text)]
    mods = []
    for k, (s, name) in enumerate(starts):
        e = starts[k + 1][0] if k + 1 < len(starts) else len(text)
        if KEEP_RE.search(text[s:e]):
            mods.append(name)
    return mods


def ff_bits(js, top):
    """distinct FF output bits that drive a bit of a keep wire"""
    mod = js["modules"].get(top) or next(iter(js["modules"].values()))
    keep_bits = set()
    for n in mod.get("netnames", {}).values():
        if str(n.get("attributes", {}).get("keep", "0")).strip("0") != "":
            keep_bits.update(b for b in n["bits"] if isinstance(b, int))
    drv = set()
    for c in mod.get("cells", {}).values():
        if "dff" in c["type"].lower() or "dlatch" in c["type"].lower():
            for p in ("Q",):
                for b in c["connections"].get(p, []):
                    if isinstance(b, int) and b in keep_bits:
                        drv.add(b)
    return len(drv)


def run_one(image, rel, top):
    with tempfile.TemporaryDirectory(prefix="krfs_") as d:
        os.chmod(d, 0o777)
        base = [f"read_verilog -sv -DSYNTHESIS /src/{rel}", f"hierarchy -top {top}"]
        scripts = {
            "A": base + ["proc", "flatten", "opt_clean", f"write_json /t/A.json"],
            "B": base + [f"synth -top {top} -flatten -run coarse:fine", f"write_json /t/B.json"],
            "C": base + ["tcl /t/hook.tcl", f"synth -top {top} -flatten -run coarse:fine", f"write_json /t/C.json"],
        }
        Path(d, "hook.tcl").write_text(HOOK.read_text())
        res = {"file": rel, "module": top}
        for k, s in scripts.items():
            Path(d, f"{k}.ys").write_text("\n".join(s) + "\n")
            r = subprocess.run(["docker", "run", "--rm", "-v", f"{ROOT}:/src:ro", "-v", f"{d}:/t", image,
                                YOSYS, "-q", "-s", f"/t/{k}.ys"], capture_output=True, text=True, timeout=3600)
            jp = Path(d, f"{k}.json")
            if r.returncode or not jp.exists():
                err = [l for l in (r.stdout + r.stderr).splitlines() if "ERROR" in l][:2]
                res["error"] = f"{k}: " + (" | ".join(err) or f"rc {r.returncode}")
                return res
            res[k] = ff_bits(json.loads(jp.read_text()), top)
        res["folded"] = res["A"] - res["B"]
        res["fixed"] = res["C"] == res["A"]
        return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", nargs="*")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--image", default="openroad/orfs:latest")
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    files = a.files or candidates()
    work = [(f, m) for f in files for m in keep_modules((ROOT / f).read_text(errors="replace"))]
    with ThreadPoolExecutor(a.jobs) as ex:
        rows = list(ex.map(lambda fm: run_one(a.image, *fm), work))
    rows.sort(key=lambda r: (-r.get("folded", -1), r["file"], r["module"]))
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    a.output.write_text(json.dumps(dict(schema="opentallas.keep_reg_fold_scan.v1", source_commit=head,
                                        image=a.image, rows=rows), indent=1) + "\n")
    for r in rows:
        print(f"{r.get('folded', 'ERR'):>6} {r.get('A', '-'):>6} {r.get('B', '-'):>6} {r.get('C', '-'):>6} "
              f"{r['module']} {r['file']} {r.get('error', '')}")


if __name__ == "__main__":
    main()
