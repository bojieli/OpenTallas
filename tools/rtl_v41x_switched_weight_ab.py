#!/usr/bin/env python3
"""Matched ROM/QE-HBM weight-source A/B on the all-unit switched V4.1x array.

The five-package (three body plus two split-head), two-user bench checks every token, logit, KV and VM state
against the same ISA pipeline and golden in both arms.  Memories are behavioural;
this is a reduced-array cycle comparison, not a 99-die throughput measurement.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
old_argv, sys.argv = sys.argv, [sys.argv[0], "--all-unit"]
import rtl_hdc_v41x_array_campaign as AC  # noqa: E402
sys.argv = old_argv
import rtl_v41x_matched_weight_ab as AB  # noqa: E402

NAME = "b3_h2_switch_stall"
BODY, HP, HMC, SHARED, FABRIC, USERS, _, STALL, PLEN, NGEN, _ = AC.CONFIGS[NAME]
LINK_CH = 109
OUT = ROOT / "results/rtl/hdc_v41x_switched_weight_ab.json"
HBM_NODE = AB.HBM_NODE


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sources():
    return sorted({*map(Path, AC.sources()), Path(__file__).resolve(),
                   ROOT / "tools/rtl_v41x_matched_weight_ab.py"}, key=str)


def source_hashes():
    return {str(p.relative_to(ROOT)): sha(p) for p in sources()}


def files(root):
    return {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob("*")) if p.is_file()}


def prepare(scratch):
    import numpy as np
    V, I, P, A, ximg = AC.V, AC.I, AC.P, AC.A, AC.ximg
    scratch.mkdir(parents=True, exist_ok=True)
    model = V.Model()
    lay = P.Layout(model)
    A.place_head_parts(lay)
    roms = scratch / "roms"
    A.write_roms(roms, lay)
    ximg.write_banked(roms / "hbank.hex", ximg.hbank_image(lay, 8), 32, 8)
    ximg.write(roms, lay, hhw=8, mg=8)
    sectors, first = P.qe_hbm_image(lay)
    (roms / "hbm_q.hex").write_text(P.hexwords(sectors, P.QSEC))
    base = P.Machine(lay, np.zeros(I.KV_WORDS * I.W_LANES, dtype=np.float32),
                     np.zeros(I.VM_ELEMS, dtype=np.float32))
    gold = A.golden_runs(model, NGEN, scratch / "gold.json", PLEN)
    plan = A.Plan(lay, A.split(model, BODY), HP, HMC, SHARED)
    progs = [A.StageBuilder(plan.lay, qchunk=P.QCHUNK).stage(plan, k) for k in range(plan.n)]
    recs, states = A.run_pipeline(plan, progs, base, gold)
    if not all(r["logits_bit_exact_every_step"] and r["argmax_and_value_every_step"] for r in recs):
        raise RuntimeError(f"ISA pipeline differs from golden: {recs}")
    img = scratch / f"cfg_{NAME}"
    steps = A.write_config(img, plan, progs, gold, states)
    for k, prog in enumerate(progs):
        ents = P.qe_fetch_list(lay, prog, first)
        (img / f"qlist_stage{k:02d}.hex").write_text(P.hexwords(P.encode_list(ents), P.LIST_BITS))
        if not ents and k < plan.nb:
            raise RuntimeError(f"body stage {k}: empty QE fetch list")
    (scratch / "v41_array_cfg.svh").write_text(AC.config_svh(plan, lay, FABRIC))
    eq = AB.weight_equivalence(lay, roms)
    if not eq["pass_"]:
        raise RuntimeError(f"ROM and HBM weight words differ: {eq}")
    images = {**{f"roms/{k}": v for k, v in files(roms).items()},
              **{f"cfg_{NAME}/{k}": v for k, v in files(img).items()},
              "v41_array_cfg.svh": sha(scratch / "v41_array_cfg.svh")}
    man = dict(schema="opentallas.v41x-switched-weight-ab.images.v1", source_commit=AB.git_head(),
               source_sha256=source_hashes(), image_sha256=images,
               model_checkpoint_sha256=sha(V.CHECKPOINT), model_config_sha256=sha(V.CONFIG),
               weight_equivalence=eq, isa_pipeline=recs,
               golden_tokens={str(u): [s["argmax"] for s in g["steps"]] for u, g in enumerate(gold)},
               packages=plan.n, users=USERS, prompt_tokens=PLEN, generated_tokens=NGEN,
               steps_per_user=steps, program_instructions=[len(p) for p in progs],
               verilator_makeflags="OPT_FAST=-O0 OPT_GLOBAL=-O0")
    (scratch / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    return man


def build_cmd(obj, whbm, jobs):
    I, core = AC.I, AC.core
    return ["verilator", "--cc", "--exe", "--build", "-O1", "-Wno-fatal", "-Wno-WIDTH",
            "-Wno-UNUSED", "-Wno-BLKSEQ", "-Wno-IMPORTSTAR", "-Wno-MULTIDRIVEN",
            "-Wno-TIMESCALEMOD", "-Wno-MODDUP", "-Wno-VARHIDDEN", "-Wno-UNOPTFLAT",
            "-Wno-PINMISSING", "--top-module", "tb_hdc_v41x_array",
            f"-GUSERS={USERS}", f"-GSTALL={STALL}", "-Mdir", str(obj), f"-I{obj}",
            f"-I{core.SVH.parent}", str(core.VLT), f"+define+HDC_SW={I.SU_LANES}",
            *[f"+define+HDC_X_{x}={2 if x == 'IDX' else 1}" for x in
              ("HE", "ME", "ATT", "IDX", "SEL", "EG", "SU")],
            f"+define+HDC_W_HBM={whbm}", *map(str, core.rtl_sources(True)),
            *map(str, AC.BENCH_AUX_RTL), str(AC.LINK), str(AC.ROUTER), str(AC.CTRL),
            str(AC.TB), str(AC.HARNESS), "-CFLAGS", "-O1", "-MAKEFLAGS",
            "OPT_FAST=-O0 OPT_GLOBAL=-O0", "-j", str(jobs)]


def parse(log, whbm, man):
    result = AC.parse(log, USERS, man["steps_per_user"], NGEN)
    hbm = [dict(zip(("node", "q_bad", "q_words", "q_reads", "q_fault", "idx_records", "idx_writes",
                     "idx_read_stalls", "idx_writer_stalls", "idx_refresh"), map(int, m.groups())))
           for m in HBM_NODE.finditer(log)]
    observed = {str(u): [t["token"] for t in result["tokens"] if t["user"] == u]
                for u in range(USERS)}
    checks = dict(core_exact=result["pass"], tokens_exact=observed == man["golden_tokens"],
                  all_packages_seen=len(hbm) == man["packages"],
                  index_hbm_clean=all(h["idx_records"] > 0 for h in hbm[:BODY]) and
                                  all(h["idx_writes"] == 12*h["idx_records"] for h in hbm),
                  weight_faults_zero=all(h["q_bad"] == h["q_fault"] == 0 for h in hbm),
                  weight_path_as_armed=(all(h["q_reads"] > 0 and h["q_words"] > 0 for h in hbm[:BODY])
                                        and all(h["q_bad"] == h["q_fault"] == 0 for h in hbm)
                                        if whbm else all(h["q_reads"] == h["q_words"] == 0 for h in hbm)))
    return dict(whbm=whbm, result=result, hbm_node=hbm, checks=checks, pass_=all(checks.values()))


def arm(whbm, images, scratch, jobs):
    man = json.loads((images / "manifest.json").read_text())
    if source_hashes() != man["source_sha256"] or {k: sha(images/k) for k in man["image_sha256"]} != man["image_sha256"]:
        raise RuntimeError("source or image changed since prepare")
    scratch.mkdir(parents=True, exist_ok=True)
    obj = scratch / "obj"
    obj.mkdir(exist_ok=True)
    (obj / "v41_array_cfg.svh").write_bytes((images / "v41_array_cfg.svh").read_bytes())
    cmd = build_cmd(obj, whbm, jobs)
    build = AB.measured(cmd, scratch / "build.log")
    if build["returncode"]:
        raise RuntimeError((scratch / "build.log").read_text()[-4000:])
    exe = obj / "Vtb_hdc_v41x_array"
    run_cmd = ["stdbuf", "-oL", str(exe), f"+DIR={images / f'cfg_{NAME}'}",
               f"+ROMS={images/'roms'}", f"+NUSERS={USERS}", f"+NPROMPT={PLEN}",
               f"+NGEN={NGEN}", f"+LINK_CH={LINK_CH}", "+HB=1000000"]
    binary_sha = sha(exe)
    run = AB.measured(run_cmd, scratch / "run.log")
    rec = parse((scratch / "run.log").read_text(), whbm, man)
    rec["checks"].update(simulator_exit_zero=run["returncode"] == 0,
                         binary_unchanged=sha(exe) == binary_sha)
    rec["pass"] = all(rec["checks"].values())
    rec.update(build=build, run=run, build_command=cmd, run_command=run_cmd,
               verilator_version=subprocess.run(["verilator", "--version"], capture_output=True,
                                                text=True, check=True).stdout.strip(),
               source_sha256=man["source_sha256"], image_sha256=man["image_sha256"],
               binary_sha256=binary_sha, build_log_sha256=sha(scratch/"build.log"),
               run_log_sha256=sha(scratch/"run.log"), host=os.uname().nodename)
    (scratch / "arm.json").write_text(json.dumps(rec, indent=1) + "\n")
    return rec


def combine(images, arm_a, arm_b, output):
    man = json.loads((images / "manifest.json").read_text())
    a = json.loads((arm_a / "arm.json").read_text())
    b = json.loads((arm_b / "arm.json").read_text())
    def portable_build(rec, scratch):
        source_file = next(x for x in rec["build_command"]
                           if x.endswith("/rtl/test/tb_hdc_v41x_array.sv"))
        source_root = str(Path(source_file).parents[2])
        cmd = [x.replace(str(scratch), "ARM").replace(source_root, "SOURCE")
               for x in rec["build_command"]]
        # Compilation parallelism is a host resource choice, not part of the
        # elaborated design.  Preserve the actual job counts in each arm.
        cmd[cmd.index("-j") + 1] = "JOBS"
        return cmd

    def portable_run(rec, scratch):
        return [("+DIR=IMAGES/" + Path(x[5:]).name if x.startswith("+DIR=") else
                 "+ROMS=IMAGES/roms" if x.startswith("+ROMS=") else
                 x.replace(str(scratch), "ARM")) for x in rec["run_command"]]

    ca, cb = portable_build(a, arm_a), portable_build(b, arm_b)
    matched = dict(same_sources=a["source_sha256"] == b["source_sha256"] == man["source_sha256"],
                   same_images=a["image_sha256"] == b["image_sha256"] == man["image_sha256"],
                   same_weight_words=man["weight_equivalence"]["pass_"],
                   same_verilator_version=a["verilator_version"] == b["verilator_version"],
                   all_split_head_steps_checked=all(
                       rec["result"].get("lm_head_steps_checked") == HP * USERS * man["steps_per_user"]
                       for rec in (a, b)),
                   only_weight_source_diff=len(ca) == len(cb) and
                   [(x, y) for x, y in zip(ca, cb) if x != y] ==
                   [("+define+HDC_W_HBM=0", "+define+HDC_W_HBM=1")],
                   same_run_args=portable_run(a, arm_a) == portable_run(b, arm_b))
    ok = a["pass"] and b["pass"] and all(matched.values())
    ac, bc = a["result"]["total_cycles"], b["result"]["total_cycles"]
    rec = dict(schema="opentallas.rtl.hdc_v41x_switched_weight_ab.v1",
               created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
               status="pass" if ok else "fail", claim_boundary=__doc__.strip(),
               configuration=dict(name=NAME, packages=man["packages"], users=USERS,
                                  prompt_tokens=PLEN, generated_tokens=NGEN,
                                  link_channel_cycles=LINK_CH, stall_percent=STALL),
               matching=matched, image_sha256=man["image_sha256"],
               source_sha256=man["source_sha256"], manifest_sha256=sha(images/"manifest.json"),
               combine_tool_sha256=sha(Path(__file__).resolve()),
               arms=dict(A=a, B=b),
               delta=(dict(A_cycles=ac, B_cycles=bc, cycles=bc-ac,
                           percent=round(100*(bc-ac)/ac, 4)) if ok else None))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(rec, indent=1) + "\n")
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare"); p.add_argument("--scratch", type=Path, required=True)
    p = sub.add_parser("arm"); p.add_argument("--whbm", type=int, choices=(0,1), required=True)
    p.add_argument("--images", type=Path, required=True); p.add_argument("--scratch", type=Path, required=True)
    p.add_argument("--jobs", type=int, default=8)
    p = sub.add_parser("combine"); p.add_argument("--images", type=Path, required=True)
    p.add_argument("--arm-a", type=Path, required=True); p.add_argument("--arm-b", type=Path, required=True)
    p.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()
    if args.cmd == "prepare":
        r = prepare(args.scratch)
        print(json.dumps({k:r[k] for k in ("packages","users","golden_tokens","weight_equivalence")}, indent=1))
    elif args.cmd == "arm":
        r = arm(args.whbm, args.images, args.scratch, args.jobs)
        print(json.dumps({"pass":r["pass"],"checks":r["checks"],"cycles":r["result"]["total_cycles"]}))
        return 0 if r["pass"] else 1
    else:
        r = combine(args.images, args.arm_a, args.arm_b, args.output)
        print(json.dumps({"status":r["status"],"delta":r["delta"],"matching":r["matching"]}))
        return 0 if r["status"] == "pass" else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
