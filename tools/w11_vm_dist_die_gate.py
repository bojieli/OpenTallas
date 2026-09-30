#!/usr/bin/env python3
"""W11: the reduced V4.1 decode step through the die top with the distributed vector memory (VM_DIST).

The die part of tools/w11_vm_dist_gate.py with a build that finishes on a shared host: the die bench's
generated C++ is ~420 MB (283 files, the largest 14 MB), which gcc at -O1 compiled at ~1 file a minute on
the loaded local host (a ~30 h build); this driver compiles it at -O0 (the simulation is slower, the result
the same) with a chosen parallelism, and runs the variants it names.

For each variant: rtl/test/tb_chip_v41x_die_vmdist.sv (the die smoke bench with the die's VM_DIST and tree
stages), one reduced DeepSeek-V4.1 decode step (token 3582 at position 7, the smoke's image), the token against
the golden and every logit, the whole vector memory and the whole KV cache against the ISA model;
VM_DIST = 1 variants against VM_DIST = 0 on the same image: token identity and the cycle delta, split into the
x-gather issue stages (the sequencer holds every ME / QE / XU / HE op X_GATHER_STAGES cycles) and the rest
(result scatter / SU result trees on dependent ops).  Stage sets: `spec` (results/floorplan/v41_vm_dist_spec.json)
and `model` (tools/uarch_model.VM_DIST as that record carries it).

Writes results/rtl/w11_vm_dist_gate_die.json (a new record; never overwrites).
    python3 tools/w11_vm_dist_die_gate.py --scratch DIR --image DIR [--variants vm_dist_0,vm_dist_1_spec,...]
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures as cf
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import w11_vm_dist_gate as G               # noqa: E402

ds, core = G.ds, G.core
OUT = ROOT / "results/rtl/w11_vm_dist_gate_die.json"


def build(obj: Path, vd: int, st: dict, jobs: int) -> tuple[Path, dict]:
    obj.mkdir(parents=True, exist_ok=True)
    exe = obj / "Vtb_chip_v41x_die_vmdist"
    flags = [f"-GVM_DIST={vd}", *[f"-G{k}={v}" for k, v in st.items()]]
    if not vd:
        flags = ["-GVM_DIST=0"]
    srcs = G.die_sources() + [G.TB_DIE, G.HARNESS_DIE, core.SVH, core.VLT]
    if G.reusable(obj, exe, flags + ["-O0"], srcs):
        return exe, dict(reused=True)
    cmd = ["/usr/bin/time", "-v", ds.VERILATOR, "--cc", "--exe", "--build", "-O1", "-Wno-fatal", "-Wno-WIDTH",
           "-Wno-UNUSED", "-Wno-BLKSEQ", "-Wno-IMPORTSTAR", "-Wno-MODDUP", "-Wno-TIMESCALEMOD", "-Wno-VARHIDDEN",
           "-Wno-UNOPTFLAT", "-Wno-MULTIDRIVEN", "--top-module", "tb_chip_v41x_die_vmdist", "-DOT_VM_DIST", *flags,
           "-Mdir", str(obj), f"-I{core.SVH.parent}", str(core.VLT), *map(str, G.die_sources()), str(G.TB_DIE),
           str(G.HARNESS_DIE), "-CFLAGS", "-O0", "-j", str(jobs)]
    t0 = time.time()
    with (obj / "build.log").open("w") as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, cwd=ROOT)
    if r.returncode:
        raise SystemExit(f"die build failed ({obj}):\n" + (obj / "build.log").read_text()[-4000:])
    return exe, dict(reused=False, wall_s=round(time.time() - t0), cflags="-O0", jobs=jobs)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--image", type=Path, required=True, help="the smoke image (tools/hdc_program_v41.py --hbm)")
    ap.add_argument("--image-a128", type=Path, default=None,
                    help="the same image built with HDC_V41_VM_ALIGN=128 (option H's layout rule)")
    ap.add_argument("--variants", default="vm_dist_0,vm_dist_1_spec,vm_dist_1_model",
                    help="vm_dist_0, vm_dist_1_<set>; option H: flat_a128 (VM_DIST 0 on the aligned image), "
                         "h (the h set on the aligned image), h_free (the same with VM_DIST_H = 0)")
    ap.add_argument("--jobs", type=int, default=12)
    ap.add_argument("--parallel-builds", type=int, default=3)
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    if a.out.exists():
        raise SystemExit(f"{a.out} exists; records are never overwritten")
    ds.setup("dpi")
    sets = G.stage_sets()
    names = a.variants.split(",")
    variants, images = {}, {}
    for n in names:
        if n in ("vm_dist_0", "flat_a128"):
            variants[n] = (0, sets["spec"])
        elif n == "h":
            variants[n] = (1, sets["h"])
        elif n == "h_free":
            variants[n] = (1, dict(sets["h"], VM_DIST_H=0))
        else:
            variants[n] = (1, sets[n.rsplit("_", 1)[1]])
        images[n] = a.image_a128 if n in ("flat_a128", "h", "h_free") else a.image
    # one build serves every variant with the same parameters (flat on both images)
    bkey = {n: ("flat" if variants[n][0] == 0 else n) for n in names}
    t0 = time.time()
    with cf.ThreadPoolExecutor(a.parallel_builds) as ex:
        uniq = {bkey[k]: variants[k] for k in names}
        futs = {b: ex.submit(build, a.scratch / f"obj_{b}", vd, st, a.jobs) for b, (vd, st) in uniq.items()}
        bb = {b: f.result() for b, f in futs.items()}
    built = {k: bb[bkey[k]] for k in names}
    exes = {k: v[0] for k, v in built.items()}
    with cf.ThreadPoolExecutor(len(exes)) as ex:
        res = dict(zip(exes, ex.map(lambda k: G.die_run(exes[k], images[k]), exes)))
    base = res.get("vm_dist_0")
    for k, r in res.items():
        r["image"] = str(images[k].name)
        vr = [tuple(map(int, m.groups())) for m in G.VROT_RE.finditer(r.pop("_log", ""))]
        if vr:
            # (seq, hold, u, b, x, r, wr, wx, xi)
            r["h_ops"] = dict(ops=len(vr), network_ops=sum(1 for x in vr if x[4] or x[5] or x[6] or x[7]),
                              broadcast_ops=sum(1 for x in vr if x[3]), unpacked_ops=sum(1 for x in vr if x[2]),
                              x_ops=sum(1 for x in vr if x[4] or x[7]), hold_cycles=sum(x[1] for x in vr),
                              holds={str(h): c for h, c in sorted(collections.Counter(x[1] for x in vr).items())})
    fa, h, hf = res.get("flat_a128"), res.get("h"), res.get("h_free")
    if h and hf and h.get("status") == "pass" and hf.get("status") == "pass":
        # the networks' cost on this token: the same design and image with the networks free
        h["network_cycles_vs_h_free"] = h["step"]["cycles"] - hf["step"]["cycles"]
    if fa and h and fa.get("status") == "pass" and h.get("status") == "pass":
        h["cycle_delta_vs_flat_a128"] = h["step"]["cycles"] - fa["step"]["cycles"]
        h["token_identical_to_flat_a128"] = h["step"]["next_token"] == fa["step"]["next_token"]
    for k, r in res.items():
        r["build"] = built[k][1]
        r["stages"] = variants[k][1] if variants[k][0] else None
        if r["stages"] is not None and base and r.get("status") == "pass" and base.get("status") == "pass":
            r["token_identical_to_vm_dist_0"] = r["step"]["next_token"] == base["step"]["next_token"]
            r["cycle_delta_vs_vm_dist_0"] = r["step"]["cycles"] - base["step"]["cycles"]
            iss = r["issues"]
            xg = iss["me"] + iss["qe"] + iss["xu"] + iss["he"]
            r["x_gather_issue_cycles"] = xg * r["stages"]["X_GATHER_STAGES"]
            r["cycle_delta_beyond_x_gather"] = r["cycle_delta_vs_vm_dist_0"] - r["x_gather_issue_cycles"]
        print(k, r.get("status"), r.get("step"), r.get("cycle_delta_vs_vm_dist_0"), flush=True)
    ok = all(r.get("status") == "pass" for r in res.values()) and \
        all(r.get("token_identical_to_vm_dist_0", True) for r in res.values())
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT)
    srcs = sorted(set(G.die_sources() + G.DIST + [G.TB_DIE, G.HARNESS_DIE, core.SVH, core.VLT, G.SPEC,
                                                   ROOT / "rtl/hdc/v41/ot_hdc_isa_v41_profiles.svh",
                                                   Path(__file__), Path(G.__file__),
                                                   ROOT / "tools/rtl_chip_v41x_die_smoke.py",
                                                   ROOT / "tools/rtl_hdc_v41x_decode_campaign.py",
                                                   ROOT / "tools/hdc_program_v41.py", ROOT / "tools/hdc_images_v41x.py",
                                                   ROOT / "tools/hdc_isa_v41.py", ROOT / "tools/hdc_golden_v41.py"]),
                  key=str)
    rec = dict(
        schema="opentallas.rtl.w11_vm_dist_gate_die.v1", status="pass" if ok else "fail",
        git_head=head.stdout.strip() if head.returncode == 0 else os.environ.get("OT_GIT_HEAD", ""),
        host=os.uname().nodename, simulator=ds.tool_version(ds.VERILATOR), stage_sets=sets,
        die=dict(image=dict(args=["--hbm"], sha256={n: G.sha(a.image / n) for n in sorted(os.listdir(a.image))
                                                    if n.endswith((".hex", ".json", ".args"))}),
                 image_a128=None if a.image_a128 is None else dict(
                     args=["--hbm"], env={"HDC_V41_VM_ALIGN": "128"},
                     sha256={n: G.sha(a.image_a128 / n) for n in sorted(os.listdir(a.image_a128))
                             if n.endswith((".hex", ".json", ".args"))}),
                 runs=res),
        wall_seconds=round(time.time() - t0),
        claim_boundary=("One reduced V4.1 decode step (token 3582, position 7) through the die top in host mode "
                        "(the smoke's configuration: all units, X_IDX = 2, W_HBM = 1, KV_HBM = 1, DPI FP stand-ins, "
                        "HBM timing models) with the opt-in distributed vector memory: behavioural lane-group bank "
                        "models (NG = SUN/8 = 2 at the reduced SU width), the trees' register stages as parameters. "
                        "Collectives and the package controller are not exercised (host mode). No synthesis, no "
                        "place-and-route."),
        source_sha256={G.rel(p): G.sha(p) for p in srcs})
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print("wrote", a.out, rec["status"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
