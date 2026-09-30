#!/usr/bin/env python3
"""W11: exactness and cycle gate of the DISTRIBUTED VECTOR MEMORY (VM_DIST) of the V4.1 die.

The RTL (opt-in, default 0 = the flat memory, bit- and cycle-identical):
  rtl/chip/ot_v41_vm_dist.sv (+ _group, _bank, _pipe)  NG lane-group banks, one module a group, replicated by
                              generate; element e in group e mod NG, 2 banks of 8-element rows a group
                              (results/floorplan/v41_vm_dist_spec.json)
  ot_hdc_v41x_vec RES_STAGES  the SU reducer's result tree (cr_rseq / idle follow its last stage); VMD_NG option H
  ot_hdc_core_v41x VM_DIST    x-gather stages (ME / QE / XU / HE ops issue X_GATHER_STAGES later), result-
                              scatter stages (their writes land RET_SCATTER_STAGES later; idle / ready wait)
  ot_chip_v41x_tile VM_DIST   the banks in place of the flat vm array, the collective write tree
                              (COLL_WRITE_STAGES; coll_busy holds until the writes land)

Parts (each run with VM_DIST = 0, the reference on the same programs, and VM_DIST = 1):
  su     the vector unit's campaigns on its bench (rtl/test/tb_hdc_v41x_vec.sv VM_DIST = 1: the bench's vector
         memory is ot_v41_vm_dist, the external producer's writes and credits cross the scatter tree):
         tools/rtl_hdc_v41x_vec_campaign.py random (N16/M8 x 24 seeds, N64/M16 x 16 seeds), vehicle (N64/M16,
         every stream op of the reduced vehicle) and perf64; the attention softmax chain of
         tools/w11_su_softmax_spec.py (serial_vec and chained, T128 / T640) at N16/M8.
  su1024 the same at N1024/M256: random (16-op programs that fit), perf and the softmax chain.  Every case: the whole vector memory and KV against the reference, no fault.
  die    the reduced V4.1 decode step through the die top (rtl/test/tb_chip_v41x_die_vmdist.sv: the smoke
         bench with the die's VM_DIST): token against the golden and every logit, the whole vector memory and
         the whole KV cache against the ISA model; cycles against VM_DIST = 0 on the same image.  Stage sets:
         `spec` (this repo's spec record) and `model` (tools/uarch_model.VM_DIST, as the spec record carries it).

Writes results/rtl/w11_vm_dist_gate_<parts>.json (new records; an existing one is never overwritten).
    python3 tools/w11_vm_dist_gate.py --scratch DIR [--parts su,su1024,die]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_hdc_v41x_vec_campaign as C      # noqa: E402
import w11_su_softmax_spec as SM           # noqa: E402
import rtl_chip_v41x_die_smoke as ds       # noqa: E402

core = ds.core
OUT = ROOT / "results/rtl/w11_vm_dist_gate.json"
SPEC = ROOT / "results/floorplan/v41_vm_dist_spec.json"
DIST = [ROOT / f"rtl/chip/{n}.sv" for n in ("ot_v41_vm_dist_bank", "ot_v41_vm_dist_group", "ot_v41_vm_dist",
                                            "ot_v41_vm_dist_pipe")]
TB_DIE = ROOT / "rtl/test/tb_chip_v41x_die_vmdist.sv"
HARNESS_DIE = ROOT / "rtl/test/chip_v41x_die_vmdist_harness.cpp"
VMDIST = re.compile(r"VMDIST ng=(\d+) reads=([\d,]+) remote=([\d,]+) writes_e=(\d+) remote_e=(\d+) writes=(\d+) "
                    r"rconf=([\d,]+) rconf_group_cycles=(\d+) wextra=(\d+) wrows_max=(\d+) occ_max=(\d+) fault=(\d+)")
ISSUES = re.compile(r"ISSUES me=(\d+) su=(\d+) qe=(\d+) xu=(\d+) he=(\d+) coll=(\d+)")
CLASSES = ("A", "B", "C", "D", "G", "X")


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(Path(p).resolve().relative_to(ROOT))


def stage_sets():
    spec = json.loads(SPEC.read_text())["trees"]
    return {"spec": dict(X_GATHER_STAGES=spec["x_gather"]["stages"], RET_SCATTER_STAGES=spec["ret_scatter"]["stages"],
                         SU_RES_STAGES=spec["su_results"]["stages"], COLL_WRITE_STAGES=spec["coll_write"]["stages"]),
            # tools/uarch_model.VM_DIST, as the spec record carries it (model_stages)
            "model": dict(X_GATHER_STAGES=spec["x_gather"]["model_stages"],
                          RET_SCATTER_STAGES=spec["ret_scatter"]["model_stages"],
                          SU_RES_STAGES=spec["su_results"]["model_stages"],
                          COLL_WRITE_STAGES=spec["coll_write"]["model_stages"])}


def vmdist_fields(text: str):
    m = VMDIST.search(text or "")
    if not m:
        return None
    g = m.groups()
    ints = lambda s: list(map(int, s.split(",")))
    return dict(groups=int(g[0]), reads=dict(zip(CLASSES, ints(g[1]))), remote_reads=dict(zip(CLASSES, ints(g[2]))),
                su_element_writes=int(g[3]), su_element_writes_remote=int(g[4]), writes=int(g[5]),
                read_rule_extra_rows=dict(zip(CLASSES, ints(g[6]))), read_rule_group_cycles=int(g[7]),
                write_rows_beyond_port=int(g[8]), write_rows_max_bank_cycle=int(g[9]),
                write_buffer_occupancy_max=int(g[10]), fault=int(g[11]))


# ---- the vector unit ---------------------------------------------------------------------------------------
_orig_parse, _orig_compare = C.parse_trace, C.compare


def _parse(text):
    tr = _orig_parse(text)
    tr["vmdist"] = vmdist_fields(text)
    return tr


def _compare(tr, mref):
    c = _orig_compare(tr, mref)
    c["vmdist"] = tr.get("vmdist")
    if c["vmdist"] is not None and c["vmdist"]["fault"]:
        c["pass_"] = False
    return c


def su_setup():
    C.parse_trace, C.compare = _parse, _compare
    for p in DIST:
        if p not in C.RTL:
            C.RTL.append(p)


def su_flags(vd, st):
    return f"-GVM_DIST={vd} -GSU_RES_STAGES={st['SU_RES_STAGES']} -GRET_SCATTER_STAGES={st['RET_SCATTER_STAGES']}"


def reusable(obj: Path, exe: Path, flags, sources) -> bool:
    """A build in obj made with every flag in `flags` (Verilator records its command line in *__verFiles.dat)
    and newer than every source it read."""
    dat = next(iter(obj.glob("*__verFiles.dat")), None)
    if not exe.exists() or dat is None:
        return False
    cmdline = dat.read_text(errors="replace").splitlines()[1] if len(dat.read_text().splitlines()) > 1 else ""
    built = exe.stat().st_mtime
    return all(f in cmdline.split() for f in flags) and all(Path(p).stat().st_mtime < built for p in sources)


BIG = ["--unroll-count", "4", "-fno-dfg"]      # N = 1,024: the flags that keep Verilator near 31 GiB


def su_build(N, M, obj, vd, st):
    """rtl_hdc_v41x_vec_campaign.build with the VM_DIST flags passed explicitly (its OT_VFLAGS environment
    variable is process-wide: parallel builds with different flags race on it)."""
    C.write_fields_svh()
    obj.mkdir(parents=True, exist_ok=True)
    flags = su_flags(vd, st).split() + (BIG if N >= 1024 else [])
    srcs = [*C.LIB, *C.RTL, C.TB, C.HARNESS, C.FIELDS_SVH]
    exe = obj / "Vtb"
    if reusable(obj, exe, flags + [f"-GN={N}", f"-GM={M}"], srcs):
        return exe, 0.0
    cmd = [C.VERILATOR, "--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ",
           "-Wno-UNOPTFLAT", "-Wno-MULTIDRIVEN", *flags, "--top-module", "tb_hdc_v41x_vec", "--prefix", "Vtb",
           "-Mdir", str(obj), f"-GN={N}", f"-GM={M}", "-GPMAX=4096", f"-GVMA={C.VMA}", f"-GKVA={C.KVA}",
           f"-GCRA={C.CRA}", f"-GWRA={C.WRA}", f"-GXBA={C.XBA}", f"-I{ROOT / 'rtl/test'}",
           *map(str, C.LIB), *map(str, C.RTL), str(C.TB), str(C.HARNESS), "-CFLAGS", "-O1", "-j", "8"]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stdout[-4000:] + r.stderr[-4000:])
    return exe, time.time() - t0


def su_part(scratch: Path, st, n1024: bool, jobs: int, small: bool = True):
    su_setup()
    out = dict(stages=dict(SU_RES_STAGES=st["SU_RES_STAGES"], RET_SCATTER_STAGES=st["RET_SCATTER_STAGES"]),
               builds={}, campaigns={}, softmax={})
    cfgs = ([(16, 8), (64, 16)] if small else []) + ([(1024, 256)] if n1024 else [])
    exes = {}
    with cf.ThreadPoolExecutor(6) as ex:
        futs = {(N, M, vd): ex.submit(su_build, N, M, scratch / f"vec_vd{vd}_N{N}_M{M}", vd, st)
                for N, M in cfgs for vd in (0, 1)}
        for k, f in futs.items():
            exes[k], secs = f.result()
            out["builds"][f"vec_N{k[0]}_M{k[1]}_vd{k[2]}"] = round(secs, 1)
    recs, cr, wrom, meta = C.vehicle_records() if small else (None, None, None, None)
    rng_seed = 20260926
    for vd in (0, 1):
        tag = f"vm_dist_{vd}"
        res = {}
        if small:
            res["random_N16_M8"] = C.random_campaign(exes[(16, 8, vd)], 16, 8, list(range(1, 25)), 40,
                                                     scratch / f"r16_vd{vd}")
            res["random_N64_M16"] = C.random_campaign(exes[(64, 16, vd)], 64, 16, list(range(101, 117)), 40,
                                                      scratch / f"r64_vd{vd}")
            res["vehicle_N64_M16"] = C.vehicle_campaign(exes[(64, 16, vd)], 64, 16, scratch / f"veh_vd{vd}", recs, cr,
                                                        wrom)
            rng = np.random.default_rng(rng_seed)
            e = exes[(64, 16, vd)]
            res["perf_N64_M16"] = dict(hc_post=C.perf_hcpost(e, 64, 16, scratch / f"p64_vd{vd}", rng),
                                       depths=C.perf_depths(e, 64, 16, scratch / f"p64_vd{vd}", rng),
                                       chain_ext=C.perf_chain_ext(e, 64, 16, scratch / f"p64_vd{vd}", rng),
                                       mixed_classes=C.perf_mix(e, 64, 16, scratch / f"p64_vd{vd}", rng))
        if n1024:
            e = exes[(1024, 256, vd)]
            # 16-op random programs that fit the bench's 2^18-word memory at N = 1,024 (the campaign's rule)
            fits = []
            for sd in range(1001, 1009):
                try:
                    C.random_program(np.random.default_rng(sd), 1024, 256, 16, C.Alloc(64, (1 << C.VMA) - 64))
                    fits.append(sd)
                except AssertionError:
                    pass
            res["random_N1024_M256"] = C.random_campaign(e, 1024, 256, fits, 16, scratch / f"r1024_vd{vd}")
            rng = np.random.default_rng(rng_seed)
            res["perf_N1024_M256"] = dict(hc_post=C.perf_hcpost(e, 1024, 256, scratch / f"p1024_vd{vd}", rng),
                                          depths=C.perf_depths(e, 1024, 256, scratch / f"p1024_vd{vd}", rng),
                                          chain_ext=C.perf_chain_ext(e, 1024, 256, scratch / f"p1024_vd{vd}", rng),
                                          mixed_classes=C.perf_mix(e, 1024, 256, scratch / f"p1024_vd{vd}", rng))
        out["campaigns"][tag] = res
        print("su campaigns", tag, {k: (sum(x["pass_"] for x in v), len(v)) for k, v in res.items()
                                    if isinstance(v, list)}, flush=True)
    if small:
        out["vehicle_meta"] = meta
    # softmax chain (tools/w11_su_softmax_spec.py fixture), vec-bench variants
    sm_cfgs = ([(16, 8)] if small else []) + ([(1024, 256)] if n1024 else [])
    for N, M in sm_cfgs:
        for vd in (0, 1):
            vflags = su_flags(vd, st).split() + (["--unroll-count", "4", "-fno-dfg"] if N >= 1024 else [])
            exe, info = SM.build("vec", N, M, 7, scratch / f"sm_vd{vd}_N{N}", jobs, vflags)
            out["builds"][f"softmax_vec_N{N}_M{M}_vd{vd}"] = info
            cres = {}
            for T in (128, 640):
                mem, expected, regions, cl = SM.cases(N, M, T)
                for variant, kind, ops, mref in cl:
                    if kind != "vec":
                        continue
                    r = SM.run_one(exe, scratch / f"sm_vd{vd}_N{N}_T{T}_{variant}", mem, ops, expected, regions,
                                   mref, N, M)
                    tr_text = None
                    r.pop("ops", None)
                    cres[f"T{T}_{variant}"] = r
                    print("softmax", N, M, vd, T, variant, r["pass_"], r["end_cycle"], flush=True)
            out["softmax"][f"N{N}_M{M}_vm_dist_{vd}"] = cres
    return out


def su_summary(out):
    """Exactness of every case and the VM_DIST = 1 - VM_DIST = 0 cycle deltas on the same programs."""
    c0, c1 = out["campaigns"]["vm_dist_0"], out["campaigns"]["vm_dist_1"]
    s = dict(all_pass=True, cases=0, deltas={}, monitors={})
    for key in ("random_N16_M8", "random_N64_M16", "vehicle_N64_M16", "random_N1024_M256"):
        if key not in c0:
            continue
        a, b = c0[key], c1[key]
        s["cases"] += len(a) + len(b)
        s["all_pass"] &= all(x["pass_"] for x in a + b)
        d = [y["cycles"] - x["cycles"] for x, y in zip(a, b) if x["cycles"] is not None and y["cycles"] is not None]
        s["deltas"][key] = dict(min=min(d), max=max(d), total=sum(d), cases=len(d)) if d else None
        mons = [y["vmdist"] for y in b if y.get("vmdist")]
        s["monitors"][key] = dict(
            reads={k: sum(m["reads"][k] for m in mons) for k in CLASSES},
            remote_reads={k: sum(m["remote_reads"][k] for m in mons) for k in CLASSES},
            su_element_writes=sum(m["su_element_writes"] for m in mons),
            su_element_writes_remote=sum(m["su_element_writes_remote"] for m in mons),
            read_rule_extra_rows={k: sum(m["read_rule_extra_rows"][k] for m in mons) for k in CLASSES},
            write_rows_beyond_port=sum(m["write_rows_beyond_port"] for m in mons),
            write_buffer_occupancy_max=max((m["write_buffer_occupancy_max"] for m in mons), default=0),
            write_rows_max_bank_cycle=max((m["write_rows_max_bank_cycle"] for m in mons), default=0),
            faults=sum(m["fault"] for m in mons))
    s["perf"] = {}
    for tag, camp in out["campaigns"].items():
        for key, perf in camp.items():
            if not key.startswith("perf_"):
                continue
            for part, v in perf.items():
                ok = bool(v["check"]["pass_"])
                s["cases"] += 1
                s["all_pass"] &= ok
                s["perf"][f"{tag}.{key}.{part}"] = dict(pass_=ok, cycles=v["check"]["cycles"])
        s["perf_chain_ext_write_to_emit"] = s.get("perf_chain_ext_write_to_emit", {})
        for key, perf in camp.items():
            if key.startswith("perf_"):
                s["perf_chain_ext_write_to_emit"][f"{tag}.{key}"] = perf["chain_ext"]["max_write_to_emit"]
    for k, v in out["softmax"].items():
        for case, r in v.items():
            s["cases"] += 1
            s["all_pass"] &= r["pass_"]
    for cfg in {k.rsplit("_vm_dist_", 1)[0] for k in out["softmax"]}:
        a, b = out["softmax"][f"{cfg}_vm_dist_0"], out["softmax"][f"{cfg}_vm_dist_1"]
        s["deltas"][f"softmax_{cfg}"] = {case: b[case]["end_cycle"] - a[case]["end_cycle"] for case in a}
    return s


# ---- the die ---------------------------------------------------------------------------------------------
def die_sources():
    out = ds.sources("dpi", build=True)
    return out + [p for p in DIST if p not in out]


def die_build(obj: Path, vd: int, st: dict) -> Path:
    obj.mkdir(parents=True, exist_ok=True)
    exe = obj / "Vtb_chip_v41x_die_vmdist"
    flags = [f"-GVM_DIST={vd}", *[f"-G{k}={v}" for k, v in st.items()]]
    if reusable(obj, exe, flags, die_sources() + [TB_DIE, HARNESS_DIE, core.SVH, core.VLT]):
        return exe
    cmd = ["/usr/bin/time", "-v", ds.VERILATOR, "--cc", "--exe", "--build", "-O1", "-Wno-fatal", "-Wno-WIDTH",
           "-Wno-UNUSED", "-Wno-BLKSEQ", "-Wno-IMPORTSTAR", "-Wno-MODDUP", "-Wno-TIMESCALEMOD", "-Wno-VARHIDDEN",
           "-Wno-UNOPTFLAT", "-Wno-MULTIDRIVEN", "--top-module", "tb_chip_v41x_die_vmdist", f"-GVM_DIST={vd}",
           *[f"-G{k}={v}" for k, v in st.items()], "-Mdir", str(obj), f"-I{core.SVH.parent}", str(core.VLT),
           *map(str, die_sources()), str(TB_DIE), str(HARNESS_DIE), "-CFLAGS", "-O1", "-j", "8"]
    t0 = time.time()
    with (obj / "build.log").open("w") as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, cwd=ROOT)
    if r.returncode:
        raise SystemExit(f"die build failed ({obj}):\n" + (obj / "build.log").read_text()[-4000:])
    return exe


def die_run(exe: Path, img: Path) -> dict:
    args = (img / "run.args").read_text().split()
    t0 = time.time()
    sim = subprocess.run([str(exe), f"+DIR={img}", *args, "+QRATE=32"], capture_output=True, text=True,
                         timeout=8 * 3600, cwd=ROOT)
    log = sim.stdout + sim.stderr
    m = core.SINGLE.search(log)
    if m is None:
        return dict(status="fail", simulation_exit=sim.returncode, tail=log[-3000:])
    names = ("input_token", "position", "next_token", "isa_next_token", "cycles", "fault", "logit_mismatches",
             "vm_mismatches", "kv_mismatches")
    step = dict(zip(names, map(int, m.groups())))
    die = re.search(r"DIE fault=([01]+)", log)
    iss = ISSUES.search(log)
    rec = dict(step=step, die_fault_bits=die.group(1) if die else None,
               issues=dict(zip(("me", "su", "qe", "xu", "he", "coll"), map(int, iss.groups()))) if iss else None,
               vmdist=vmdist_fields(log), unit_counters=core.counters(log), simulation_exit=sim.returncode,
               simulation_wall_seconds=round(time.time() - t0, 1),
               simulation_log_sha256=hashlib.sha256(log.encode()).hexdigest(), simulation_tail=log[-1500:])
    ok = (sim.returncode == 0 and "PASS" in log and step["next_token"] == step["isa_next_token"] and
          step["fault"] == 0 and step["logit_mismatches"] == step["vm_mismatches"] == step["kv_mismatches"] == 0
          and die is not None and int(die.group(1), 2) == 0 and "VMDIST_FAULT" not in log)
    if rec["vmdist"] is not None:
        ok = ok and rec["vmdist"]["fault"] == 0
    rec["status"] = "pass" if ok else "fail"
    return rec


def die_part(scratch: Path, sets: dict, reuse_images: bool):
    ds.setup("dpi")
    img = scratch / "img_pos7"
    variants = {"vm_dist_0": (0, sets["spec"])}
    for name, st in sets.items():
        variants[f"vm_dist_1_{name}"] = (1, st)
    with cf.ThreadPoolExecutor(4) as ex:
        fi = None if reuse_images and (img / "run.args").exists() else ex.submit(core.images, img, "--hbm")
        futs = {k: ex.submit(die_build, scratch / f"obj_{k}", vd, st) for k, (vd, st) in variants.items()}
        if fi is not None:
            fi.result()
        exes = {k: f.result() for k, f in futs.items()}
    with cf.ThreadPoolExecutor(len(exes)) as ex:
        res = dict(zip(exes, ex.map(lambda k: die_run(exes[k], img), exes)))
    base = res["vm_dist_0"]
    for k, r in res.items():
        r["stages"] = variants[k][1] if variants[k][0] else None
        if k != "vm_dist_0" and r.get("status") == "pass" and base.get("status") == "pass":
            r["token_identical_to_vm_dist_0"] = r["step"]["next_token"] == base["step"]["next_token"]
            r["cycle_delta_vs_vm_dist_0"] = r["step"]["cycles"] - base["step"]["cycles"]
            iss = r["issues"]
            xg = iss["me"] + iss["qe"] + iss["xu"] + iss["he"]
            r["x_gather_issue_cycles"] = xg * r["stages"]["X_GATHER_STAGES"]
            r["cycle_delta_beyond_x_gather"] = r["cycle_delta_vs_vm_dist_0"] - r["x_gather_issue_cycles"]
    return dict(image=dict(args=["--hbm"], sha256={n: sha(img / n) for n in sorted(os.listdir(img))
                                                   if n.endswith((".hex", ".json", ".args"))}),
                runs=res)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--parts", default="su,die",
                    help="su (N16/M8, N64/M16 campaigns, N16 softmax), su1024 (N1024/M256 random, perf, softmax: "
                         "~31 GiB a build), die")
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--reuse-images", action="store_true")
    ap.add_argument("--out", type=Path, default=None,
                    help="default results/rtl/w11_vm_dist_gate_<parts>.json")
    a = ap.parse_args()
    if a.out is None:
        a.out = OUT.with_name(f"w11_vm_dist_gate_{'_'.join(sorted(a.parts.split(',')))}.json")
    if a.out.exists():
        raise SystemExit(f"{a.out} exists; records are never overwritten")
    a.scratch.mkdir(parents=True, exist_ok=True)
    parts = set(a.parts.split(","))
    sets = stage_sets()
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT)
    rec = dict(schema="opentallas.rtl.w11_vm_dist_gate.v1", stage_sets=sets,
               git_head=head.stdout.strip() if head.returncode == 0 else os.environ.get("OT_GIT_HEAD", ""),
               host=os.uname().nodename, simulator=ds.tool_version(ds.VERILATOR))
    t0 = time.time()
    with cf.ThreadPoolExecutor(2) as ex:
        fs = (ex.submit(su_part, a.scratch / "su", sets["spec"], "su1024" in parts, a.jobs, "su" in parts)
              if parts & {"su", "su1024"} else None)
        fd = ex.submit(die_part, a.scratch / "die", sets, a.reuse_images) if "die" in parts else None
        if fs is not None:
            rec["su"] = fs.result()
            rec["su_summary"] = su_summary(rec["su"])
        if fd is not None:
            rec["die"] = fd.result()
    ok = True
    if "su_summary" in rec:
        ok &= rec["su_summary"]["all_pass"]
    if "die" in rec:
        ok &= all(r.get("status") == "pass" for r in rec["die"]["runs"].values())
        ok &= all(r.get("token_identical_to_vm_dist_0", True) for r in rec["die"]["runs"].values())
    srcs = sorted(set(die_sources() + list(C.LIB) + list(C.RTL) + DIST +
                      [C.TB, C.HARNESS, SM.TB_VEC, TB_DIE, HARNESS_DIE, core.SVH, core.VLT, SPEC,
                       ROOT / "rtl/hdc/v41/ot_hdc_isa_v41_profiles.svh", Path(__file__),
                       ROOT / "tools/rtl_hdc_v41x_vec_campaign.py", ROOT / "tools/w11_su_softmax_spec.py",
                       ROOT / "tools/rtl_v41x_su_softmax_campaign.py", ROOT / "tools/rtl_chip_v41x_die_smoke.py",
                       ROOT / "tools/rtl_hdc_v41x_decode_campaign.py", ROOT / "tools/hdc_program_v41.py",
                       ROOT / "tools/hdc_images_v41x.py", ROOT / "tools/hdc_isa_v41.py",
                       ROOT / "tools/hdc_golden_v41.py", ROOT / "tools/hdc_golden.py"]), key=str)
    rec.update(status="pass" if ok else "fail", wall_seconds=round(time.time() - t0),
               claim_boundary=("RTL simulation of the opt-in distributed vector memory: behavioural lane-group "
                               "bank models (ot_v41_vm_dist_bank: one row store with the macro's port shape; the "
                               "replicas, write buffer and lane <-> group network are modelled as ports and "
                               "counted by monitors, not built), tree register stages as parameters.  Exactness "
                               "against the flat memory / ISA model on the listed programs; no synthesis or "
                               "place-and-route."),
               source_sha256={rel(p): sha(p) for p in srcs})
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n")
    print("wrote", a.out, rec["status"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
