#!/usr/bin/env python3
"""Build and run the sliced runtime-composition equivalence gate for ot_hdc_matvec.

The composition (rtl/test/qwen_runtime/*.sv + qwen_rt_matvec.hpp) splits the
matrix engine into one G-independent sequencer model, one per-group slice model
(instantiated G times), split-tree cell models and argmax subtree models, so the
G6144 engine compiles in O(1) model size.  This gate compares every public port
against the unmodified rtl/hdc/ot_hdc_matvec.sv on every checked cycle, then
requires the wrong-edge negative control to fail.  Simulation-only: no RTL,
queue, register or cycle is added to hardware.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RT = ROOT / "rtl/test/qwen_runtime"
COMMON = [ROOT / f"rtl/hdc/{n}.sv" for n in ("ot_hdc_fpu", "ot_hdc_fp32_mul_pipe", "ot_hdc_fastfp",
                                            "ot_hdc_delay", "ot_hdc_sfu")] + [ROOT / "rtl/proto/ot_fp32_add_rne_pipe.sv"]
REFERENCE = ROOT / "rtl/hdc/ot_hdc_matvec.sv"
SOURCES = [REFERENCE, *COMMON, RT / "ot_qwen_rt_matvec_seq.sv", RT / "ot_qwen_rt_matvec_slice.sv",
           RT / "ot_qwen_rt_tree.sv", RT / "qwen_rt_matvec.hpp", RT / "qwen_rt_matvec_gate.cpp", Path(__file__)]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def levels(groups: int) -> int:
    lg = 0
    while (1 << lg) < groups:
        lg += 1
    return lg


def verilator_root(verilator: str) -> str:
    out = subprocess.check_output([verilator, "-V"], text=True)
    return re.search(r"VERILATOR_ROOT\s*=\s*(\S+)", out).group(1)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--groups", type=int, required=True)
    ap.add_argument("--count-width", type=int, choices=(16, 18), default=16)
    ap.add_argument("--scale-wcs-base", type=int, choices=(0, 1), default=0)
    ap.add_argument("--workdir", type=Path, required=True)
    ap.add_argument("--verilator", default=os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator"))
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--hier-reference", action="store_true",
                    help="build the reference with fmul/qadd hierarchical leaves (needed for G>=64)")
    ap.add_argument("--no-reference", action="store_true", help="build composition only (G6144 smoke)")
    ap.add_argument("--result", type=Path)
    ap.add_argument("--reuse", action="store_true", help="reuse already built model archives in --workdir")
    args = ap.parse_args()
    G, NW = args.groups, args.count_width
    LG = levels(G)
    LO = min(LG, 7)
    HI = LG - LO
    out = args.workdir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    start_pins = {str(p.relative_to(ROOT)): sha(p) for p in SOURCES}
    vroot = verilator_root(args.verilator)
    steps = []

    def run(name, cmd, cwd=out):
        t0 = time.monotonic()
        p = subprocess.run(["/usr/bin/time", "-f", "%M", "-o", str(out / f"{name}.rss"), *map(str, cmd)],
                           cwd=cwd, capture_output=True, text=True)
        (out / f"{name}.log").write_text(p.stdout + p.stderr)
        steps.append({"name": name, "seconds": round(time.monotonic() - t0, 2), "returncode": p.returncode,
                      "max_rss_kib": int((out / f"{name}.rss").read_text().split()[-1]) if (out / f"{name}.rss").exists() else None})
        if p.returncode:
            raise SystemExit(f"{name} failed; see {out / (name + '.log')}\n{(p.stdout + p.stderr)[-3000:]}")
        return p.stdout

    common = [str(p) for p in COMMON]
    params_core = [f"-GG={G}", "-GW=16", f"-GNW={NW}", "-GINT8_WEIGHT=1"]
    models = [
        ("seq", "ot_qwen_rt_matvec_seq", [str(RT / "ot_qwen_rt_matvec_seq.sv")],
         params_core + [f"-GINT8_SCALE_WCS_BASE={args.scale_wcs_base}"], []),
        ("slice", "ot_qwen_rt_matvec_slice", [str(RT / "ot_qwen_rt_matvec_slice.sv")], params_core, []),
        ("cella", "ot_qwen_rt_tree_cell", [str(RT / "ot_qwen_rt_tree.sv")], ["-GW=16", "-GADDS=1"], []),
        ("amaxlo", "ot_qwen_rt_amax_tree", [str(RT / "ot_qwen_rt_tree.sv")], [f"-GNW={NW}", f"-GLEVELS={LO}"], []),
    ]
    if HI:
        models.append(("amaxhi", "ot_qwen_rt_amax_tree", [str(RT / "ot_qwen_rt_tree.sv")], [f"-GNW={NW}", f"-GLEVELS={HI}"], []))
    if not args.no_reference:
        hier = []
        if args.hier_reference:
            (out / "leaf.vlt").write_text('`verilator_config\nhier_block -module "ot_hdc_fmul"\nhier_block -module "ot_hdc_qadd"\n')
            hier = ["--hierarchical", str(out / "leaf.vlt"), "--unroll-count", "131072", "--unroll-limit", "131072"]
        models.append(("ref", "ot_hdc_matvec", [str(REFERENCE)],
                       params_core + [f"-GINT8_SCALE_WCS_BASE={args.scale_wcs_base}"], hier))
    for prefix, top, files, params, extra in models:
        mdir = out / prefix
        if args.reuse and (mdir / f"V{prefix}__ALL.a").exists():
            continue
        run(f"verilate_{prefix}", [args.verilator, "--cc", "-O3", "-Wno-fatal", "-Wno-TIMESCALEMOD", "--top-module", top,
                                   "--prefix", f"V{prefix}", "--Mdir", mdir, *params, *files, *common, *extra])
        run(f"build_{prefix}", ["make", "-C", mdir, "-f", f"V{prefix}.mk", f"-j{args.jobs}", f"V{prefix}__ALL.a",
                                "OPT_FAST=-O2", "OPT_SLOW=-O1"])
    archives, includes = [], {f"-I{vroot}/include", f"-I{vroot}/include/vltstd", f"-I{RT}"}
    for prefix, *_ in models:
        for a in sorted((out / prefix).rglob("*.a")):
            if a.name not in [x.name for x in archives]:
                archives.append(a)
        for h in (out / prefix).rglob("V*.h"):
            includes.add(f"-I{h.parent}")
    runtime = [f"{vroot}/include/verilated.cpp", f"{vroot}/include/verilated_threads.cpp"]
    if args.hier_reference:
        runtime.append(f"{vroot}/include/verilated_dpi.cpp")
    gate = out / "gate"
    main_cpp = RT / "qwen_rt_matvec_gate.cpp"
    if args.no_reference:
        raise SystemExit("composition models built (no reference); link skipped")
    run("link", ["g++", "-std=c++20", "-O2", "-pthread", f"-DGROUPS={G}", f"-DCOUNTWIDTH={NW}",
                 f"-DLOLEVELS={LO}", f"-DHILEVELS={HI}", *sorted(includes), main_cpp,
                 "-Wl,--start-group", *archives, "-Wl,--end-group", *runtime, "-o", gate])
    env = dict(os.environ, RT_THREADS=str(args.threads))
    t0 = time.monotonic()
    p = subprocess.run([str(gate)], cwd=out, capture_output=True, text=True, env=env)
    sim_seconds = time.monotonic() - t0
    (out / "simulate.log").write_text(p.stdout + p.stderr)
    m = subprocess.run([str(gate), "--wrong-edge"], cwd=out, capture_output=True, text=True, env=env)
    (out / "mutant.log").write_text(m.stdout + m.stderr)
    verdict = p.stdout.strip().splitlines()[-1] if p.stdout.strip() else p.stderr[-500:]
    passed = p.returncode == 0 and verdict.startswith("PASS")
    mutant_rejected = m.returncode != 0 and "FAIL case=" in m.stdout
    end_pins = {str(p_.relative_to(ROOT)): sha(p_) for p_ in SOURCES}
    stable = end_pins == start_pins
    result = {
        "schema": "opentallas.qwen-rt-matvec-gate.v1",
        "status": "pass" if (passed and mutant_rejected and stable) else "fail",
        "groups": G, "count_width": NW, "scale_wcs_base": args.scale_wcs_base, "tree_levels": LG,
        "amax_split": [LO, HI], "hier_reference": args.hier_reference,
        "verdict": verdict, "negative_control": (m.stdout.strip().splitlines() or [""])[-1],
        "negative_control_rejected": mutant_rejected, "simulate_seconds": round(sim_seconds, 2),
        "threads": args.threads, "steps": steps, "source_sha256": start_pins, "source_stable": stable,
        "gate_binary_sha256": sha(gate),
        "verilator": subprocess.check_output([args.verilator, "--version"], text=True).strip(),
        "claim_boundary": ("Simulation-only decomposition equivalence: every public ot_hdc_matvec port of the "
                           "sliced runtime composition equals the unmodified RTL on every checked cycle for the "
                           "listed synthetic/random stimulus. Not a checkpoint, token, timing or physical result."),
    }
    target = args.result or (out / "result.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: result[k] for k in ("status", "verdict", "negative_control", "simulate_seconds")}, indent=2))
    if result["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
