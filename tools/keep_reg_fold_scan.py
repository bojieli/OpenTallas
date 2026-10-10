#!/usr/bin/env python3
"""FLOW-FIX-0410 2026-10-09: which (* keep *) register copies does the ORFS yosys fold back into one flop?

For every RTL file (rtl/, physical/) that declares a register with a keep attribute, each module that holds such a
declaration is elaborated alone (its submodules stay black boxes) with the ORFS image's yosys at default parameters:
  A  read_verilog -sv -DSYNTHESIS; hierarchy -top M; proc; flatten; opt_clean        (every declared copy)
  B  ... ; synth -top M -flatten -run coarse:fine                                          (the ORFS coarse pass, opt_merge; begin skipped so absent submodules stay black boxes)
  C  as B with physical/common_flow/ot_keep_regs.tcl run after hierarchy               (the fix)
and maps every keep-wire bit to its driver.  folded = declared FF copies (distinct A drivers) that share one net in B
(the opt_merge fold; copies absorbed into a memory read port or removed are not counted); folded_hook = the same in C
(must be 0).  Output columns: folded, A (declared FF bits driving keep wires), folded_hook, module, file.
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
TIMEOUT_S = 900
SYN = "synth -top {top} -flatten -run coarse:fine"
DEPS = False   # --deps: declare instantiated submodules as -lib black boxes


def candidates():
    out = subprocess.run(["git", "grep", "-l", "-P", KEEP_RE.pattern, "--", "rtl", "physical"], cwd=ROOT,
                         capture_output=True, text=True).stdout.split()
    return [f for f in out if f.endswith((".v", ".sv"))]


_INDEX = None


def module_index():
    """module name -> defining files (rtl/ before physical/), for black-box port declarations"""
    global _INDEX
    if _INDEX is None:
        out = subprocess.run(["git", "grep", "-n", "-P", r"^\s*module\s+\w+", "--", "rtl/*.v", "rtl/*.sv", "physical/*.v",
                              "physical/*.sv"], cwd=ROOT, capture_output=True, text=True).stdout
        _INDEX = {}
        for line in out.splitlines():
            f, _, rest = line.split(":", 2)
            m = re.match(r"\s*module\s+(\w+)", rest)
            if m and "/tb_" not in f and not Path(f).name.startswith("tb_") and not f.startswith("rtl/test/"):
                _INDEX.setdefault(m.group(1), []).append(f)
    return _INDEX


def lib_deps(rel):
    """files declaring (as -lib black boxes) the modules the file instantiates but does not define: a keep reg fed by
    a missing submodule would otherwise look undriven and be optimised away (a scan artifact, not a fold)"""
    text = (ROOT / rel).read_text(errors="replace")
    own = set(MOD_RE.findall(text))
    idx = module_index()
    deps = []
    for name in sorted(set(re.findall(r"\b([A-Za-z_]\w*)\s*(?:#\s*\(|\s+[A-Za-z_\\][\w\[\]\.]*\s*\()", text)) - own):
        fs = idx.get(name)
        if not fs:
            continue
        same = [f for f in fs if Path(f).parent == Path(rel).parent]
        pick = (same or [f for f in fs if f.startswith("rtl/")] or fs)[0]
        if pick != rel and pick not in deps:
            deps.append(pick)
    return deps


def keep_modules(text):
    starts = [(m.start(), m.group(1)) for m in MOD_RE.finditer(text)]
    mods = []
    for k, (s, name) in enumerate(starts):
        e = starts[k + 1][0] if k + 1 < len(starts) else len(text)
        if KEEP_RE.search(text[s:e]):
            mods.append(name)
    return mods


def keep_map(js, top, ff_only):
    """{(keep wire, bit index): driver bit id}; ff_only: only bits driven by a flip-flop / latch Q"""
    mod = js["modules"].get(top) or next(iter(js["modules"].values()))
    ffq = set()
    for c in mod.get("cells", {}).values():
        if "dff" in c["type"].lower() or "dlatch" in c["type"].lower():
            ffq.update(b for b in c["connections"].get("Q", []) if isinstance(b, int))
    out = {}
    for name, n in mod.get("netnames", {}).items():
        if str(n.get("attributes", {}).get("keep", "0")).strip("0") == "":
            continue
        for i, b in enumerate(n["bits"]):
            if isinstance(b, int) and (not ff_only or b in ffq):
                out[(name, i)] = b
    return out


def folded(a_map, x_map):
    """declared flip-flop copies (distinct A drivers) that now share one net: the opt_merge fold.  A copy absorbed
    into a memory read port or removed keeps or loses its own net and is not counted here."""
    keys = [k for k in a_map if k in x_map]
    groups = {}
    for k in keys:
        groups.setdefault(x_map[k], set()).add(a_map[k])
    return sum(len(g) - 1 for g in groups.values())


FULL = False   # --full: synth through memory_map / techmap (-noabc) instead of the coarse pass


def run_one(image, rel, top):
    with tempfile.TemporaryDirectory(prefix="krfs_") as d:
        os.chmod(d, 0o777)
        libs = [f"read_verilog -sv -DSYNTHESIS -lib /src/{f}" for f in lib_deps(rel)] if DEPS else []
        base = [*libs, f"read_verilog -sv -DSYNTHESIS /src/{rel}", f"hierarchy -top {top}"]
        scripts = {
            "A": base + ["proc", "flatten", "opt_clean", f"write_json /t/A.json"],
            "B": base + [SYN.format(top=top), f"write_json /t/B.json"],
            "C": base + ["tcl /t/hook.tcl", SYN.format(top=top), f"write_json /t/C.json"],
        }
        Path(d, "hook.tcl").write_text(HOOK.read_text())
        res = {"file": rel, "module": top}
        maps = {}
        for k, s in scripts.items():
            Path(d, f"{k}.ys").write_text("\n".join(s) + "\n")
            cname = f"krfs_{os.getpid()}_{abs(hash((rel, top, k)))}"
            try:
                r = subprocess.run(["docker", "run", "--rm", "--name", cname, "-v", f"{ROOT}:/src:ro", "-v", f"{d}:/t",
                                    image, YOSYS, "-q", "-s", f"/t/{k}.ys"], capture_output=True, text=True,
                                   timeout=TIMEOUT_S)
            except subprocess.TimeoutExpired:
                subprocess.run(["docker", "kill", cname], capture_output=True)
                res["error"] = f"{k}: timeout {TIMEOUT_S} s (memory-array module; elaborate it in its routed context)"
                return res
            jp = Path(d, f"{k}.json")
            if r.returncode or not jp.exists():
                err = [l for l in (r.stdout + r.stderr).splitlines() if "ERROR" in l][:2]
                res["error"] = f"{k}: " + (" | ".join(err) or f"rc {r.returncode}")
                return res
            maps[k] = keep_map(json.loads(jp.read_text()), top, k == "A")
        res["A"] = len(set(maps["A"].values()))
        res["folded"] = folded(maps["A"], maps["B"])
        res["folded_hook"] = folded(maps["A"], maps["C"])
        res["fixed"] = res["folded_hook"] == 0
        return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", nargs="*")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--image", default="openroad/orfs:latest")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--deps", action="store_true", help="read instantiated submodules' files as -lib black boxes")
    ap.add_argument("--full", action="store_true", help="B/C through memory_map + techmap (synth -noabc), not coarse only")
    a = ap.parse_args()
    global SYN, DEPS
    DEPS = a.deps
    if a.full:
        SYN = "synth -top {top} -flatten -noabc -run coarse:check"
    files = a.files or candidates()
    work = [(f, m) for f in files for m in keep_modules((ROOT / f).read_text(errors="replace"))]
    rows = []
    part = a.output.with_suffix(".partial.jsonl")
    with ThreadPoolExecutor(a.jobs) as ex, open(part, "w") as pf:
        for r in ex.map(lambda fm: run_one(a.image, *fm), work):
            rows.append(r)
            pf.write(json.dumps(r) + "\n")
            pf.flush()
    rows.sort(key=lambda r: (-r.get("folded", -1), r["file"], r["module"]))
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    a.output.write_text(json.dumps(dict(schema="opentallas.keep_reg_fold_scan.v1", source_commit=head,
                                        image=a.image, rows=rows), indent=1) + "\n")
    for r in rows:
        print(f"{r.get('folded', 'ERR'):>6} {r.get('A', '-'):>6} {r.get('folded_hook', '-'):>6} "
              f"{r['module']} {r['file']} {r.get('error', '')}")


if __name__ == "__main__":
    main()
