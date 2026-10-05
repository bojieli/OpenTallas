#!/usr/bin/env python3
"""Bench of the default-off ROM-field system successors (FAULT_TIE, RET_CREDIT): lint, equivalence, backpressure.

    python3 rtl/test/dsrom_sys/run_field_sys_bench.py --snapshot <HF snapshot dba1be0a...> --workdir DIR \
        [--np 16 --regions 4 --nbf 8] [--jobs 4] [--result results/rtl/dsrom_system_rtl_20261003/field_sys_bench.json]

DUT: rtl/dsrom_sys/ot_v41_field_w17w10_sys.sv + rtl/dsrom_sys/ot_v41_spine_w17w10_sys.sv.
REF: the pinned rtl/v41die/ot_v41_field_w17w10.sv + rtl/v41die/ot_v41_spine_w17w10.sv (sha256 recorded, never edited).
Stimulus: the qualified W17 field gate's eight real DeepSeek-V4.1-Flash phases (tools/w17_w10_field_rt_gate.py
phases(): FP8, FP4, mixed, BF16 and an MTP-2 phase), its image writer and x seed, at its reduced but structurally
identical field (NP 16 pairs, R 4 regions, NBF 8; full shape NP 8192, R 128).  Golden rows:
tools/v41_die_images_w17w10.golden_phase (R-ARITH chunk8), FP32 or BF16 by the phase's row format.
Simulator: Verilator 5.050 (the field gate's; Icarus 11 cannot elaborate the field's $sformatf INSTANCE overrides).
One build holds REF and four DUT variants (rtl/test/dsrom_sys/tb_field_sys.sv: D0 default, D1 FAULT_TIE, D2 credit
with the proven headroom, D3 credit with a deliberately too-small headroom).

Checks (pass/fail each, in the record):
  lint             verilator --lint-only -Wall: UNDRIVEN on n_fault in the original and FAULT_TIE=0, none with FAULT_TIE=1.
  eq_default       D0 (both params 0) equals REF on every original spine and field port, every cycle, every run.
  eq_*_nostall     D1, D2, D3 with no stall equal REF on every port every cycle (field fault separately): zero added
                   cycles at full rate.
  fault_tie        D1..D3 field fault is 0 on every cycle of every run, including +verilator+rand+reset+2 runs (random
                   initial values for unassigned state: the 2-state image of X), where REF's field fault goes to 1.
  credit_stall_<p> D2 under p% random VM write stall: every row written exactly once, VM words bit-identical to REF's
                   no-stall run and to golden, no fault, no row-FIFO overflow, rows_retired = rows.
  contrast_stall_<p> D1 (RET_CREDIT=0) under the same stall: rows presented while not ready are lost (w_ovf): the
                   documented no-ACK hazard.
  stress_stall_<p> D3 (RET_H below the proven bound): reported, not gated: whether the hardware invariant (ret_ovf) fires.
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

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as G  # noqa: E402
import v41_die_images_w17w10 as I  # noqa: E402
import w17_w10_field_rt_gate as GATE  # noqa: E402
from rtl_v41_rom_array import Ckpt  # noqa: E402

VERILATOR = GATE.VERILATOR
HERE = Path(__file__).resolve().parent
TB = HERE / "tb_field_sys.sv"
MAIN = HERE / "tb_field_sys_main.cpp"
SYS = [ROOT / "rtl/dsrom_sys/ot_v41_field_w17w10_sys.sv", ROOT / "rtl/dsrom_sys/ot_v41_spine_w17w10_sys.sv"]
ORIG = [ROOT / f"rtl/v41die/{n}.sv" for n in ("ot_v41_pair_w17w10", "ot_v41_retn_w17w10", "ot_v41_field_w17w10",
                                             "ot_v41_spine_w17w10")]
DEPS = list(GATE.COMMON + GATE.W10 + [GATE.VIA_ROM, GATE.PP_VIA_ROM])
RTL = ORIG + SYS + DEPS
SOURCES = sorted(set(RTL + [TB, MAIN, HERE / "lint_blackboxes.sv", Path(__file__), ROOT / "tools/w17_w10_field_rt_gate.py",
                            ROOT / "tools/v41_die_images_w17w10.py", ROOT / "tools/rtl_v41_rom_array.py",
                            ROOT / "tools/v41_rom_ksplit_bankmap.py", ROOT / "tools/hdc_golden_v41.py",
                            ROOT / "tools/hdc_golden.py"]))
PHW, VAW = GATE.PHW, GATE.VAW
NSEG = 8


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(Path(p).resolve().relative_to(ROOT))


def images(a, out: Path):
    """The W17 field gate's images, x vectors and golden rows (same phases, seed and writer), plus the exact rows
    every region's root finishes in every phase (from the configuration words: one segment 0 per row)."""
    G.set_arith("chunk8")
    ck = Ckpt(a.snapshot)
    rng = np.random.default_rng(GATE.SEED)
    fld = I.Field(a.np, a.regions, a.nbf, pp=False, fast=False)
    vm = np.zeros(1 << VAW, dtype=np.uint32)
    ops, expect, cases = [], {}, []
    xptr, optr = 0, 32768
    for name, mats, fmts, rsplit, npos in GATE.phases(ck):
        ph = I.add_phase(fld, mats, fmts, rsplit)
        K, bf = ph["K"], ph["bf"]
        for p in range(npos):
            if bf:
                x = (rng.standard_normal(K) * 0.37).astype(np.float32)
            else:
                x = G.to_bf16((rng.standard_normal(K) * 0.5).astype(G.F))
            vm[xptr + p * K: xptr + p * K + K] = G.bits(np.asarray(x, dtype=G.F))
            gold = I.golden_phase(mats, np.asarray(x, dtype=G.F))
            for tag, (f32, b16) in gold.items():
                fp32 = fmts[0] if tag < rsplit else fmts[1]
                expect[optr + tag + p * ph["nrows"]] = f32 if fp32 else (b16 << 16)
        cfg = fld.cfg[ph["index"]]
        per = a.np // a.regions
        reg_rows = [set() for _ in range(a.regions)]
        for pp in range(a.np):
            for s in range(NSEG):
                w = cfg[pp][s]
                if (w >> 21) & 31 == 0 or (w >> 16) & 31 != 0:
                    continue
                for t in (w & 0xFFFF, cfg[pp][2 * NSEG + 1 + s] & 0xFFFF):
                    if not t & I.SENT:
                        reg_rows[pp // per].add(t)
        assert sum(map(len, reg_rows)) == ph["nrows"], (name, list(map(len, reg_rows)), ph["nrows"])
        ops.append((ph["index"], npos - 1, xptr, K, optr, ph["nrows"]))
        cases.append(dict(name=name, phase=ph["index"], positions=npos, rows=ph["nrows"], K=K, bf16=bf,
                          stream_beats=ph["nbeat"], rows_per_region=[len(r) * npos for r in reg_rows]))
        xptr += npos * K
        optr += npos * ph["nrows"]
        assert xptr < 32768 and optr < (1 << VAW)
    img = out / "img"
    I.write_field(fld, img, PHW)
    (img / "vm.hex").write_text("".join(f"{int(v):08x}\n" for v in vm))
    (out / "ops.txt").write_text("".join(" ".join(map(str, o)) + "\n" for o in ops))
    return img, out / "ops.txt", expect, cases


def sh(cmd, log: Path, cwd=None):
    t0 = time.monotonic()
    p = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, cwd=cwd)
    log.write_text(p.stdout + p.stderr)
    return p.returncode, p.stdout + p.stderr, round(time.monotonic() - t0, 2)


YOSYS = Path.home() / ".local/opentallas-tools/yosys-0.68/bin/yosys"
BLACKBOX = HERE / "lint_blackboxes.sv"
LINT_CASES = (("original", "ot_v41_field_w17w10", ROOT / "rtl/v41die/ot_v41_field_w17w10.sv", {}),
              ("sys_tie0_credit0", "ot_v41_field_w17w10_sys", SYS[0], dict(FAULT_TIE=0, RET_CREDIT=0)),
              ("sys_tie1_credit0", "ot_v41_field_w17w10_sys", SYS[0], dict(FAULT_TIE=1, RET_CREDIT=0)),
              ("sys_tie1_credit1", "ot_v41_field_w17w10_sys", SYS[0], dict(FAULT_TIE=1, RET_CREDIT=1)))


def lint(a, out: Path):
    """Structural lint of the field (original vs successor).  Gate: yosys 'check' with the pair, return node and root
    blackboxed (port-exact, rtl/test/dsrom_sys/lint_blackboxes.sv) lists every bit that is used but has no driver.
    Context only: verilator 5.050 --lint-only -Wall with the real submodules (it does NOT report these bits)."""
    res = {}
    for key, top, f, prm in LINT_CASES:
        sets = " ".join(f"-set {k} {v}" for k, v in dict(NP=a.np, R=a.regions, NBF=a.nbf, PHW=PHW, **prm).items())
        script = f"read_verilog -sv {BLACKBOX} {f}; chparam {sets} {top}; hierarchy -top {top}; proc; check"
        cmd = [YOSYS, "-p", script]
        rc, txt, s = sh(cmd, out / f"yosys_check_{key}.log")
        nodrv = [ln.strip() for ln in txt.splitlines() if "has no driver" in ln]
        bits = sorted(int(m.group(1)) for ln in nodrv for m in [re.search(r"n_fault \[(\d+)\]", ln)] if m)
        res[key] = dict(yosys_command=" ".join(map(str, cmd)), returncode=rc, seconds=s, no_driver_warnings=nodrv,
                        n_fault_undriven_bits=bits, n_fault_undriven=bool(bits))
    deps = [str(p) for p in DEPS] + [str(ROOT / "rtl/v41die/ot_v41_pair_w17w10.sv"),
                                     str(ROOT / "rtl/v41die/ot_v41_retn_w17w10.sv")]
    for key, top, f, prm in (LINT_CASES[0], LINT_CASES[2]):
        cmd = [VERILATOR, "--lint-only", "-Wall", "-Wno-fatal", "-Wno-DECLFILENAME", "-Wno-TIMESCALEMOD",
               "--top-module", top, f"-GNP={a.np}", f"-GR={a.regions}", f"-GNBF={a.nbf}", f"-GPHW={PHW}",
               *[f"-G{k}={v}" for k, v in prm.items()], str(f), *deps]
        rc, txt, s = sh(cmd, out / f"verilator_lint_{key}.log")
        own = [ln for ln in txt.splitlines() if ln.startswith("%Warning") and Path(f).name in ln]
        res[key].update(verilator_command=" ".join(map(str, cmd)), verilator_returncode=rc,
                        verilator_own_file_warnings=own,
                        verilator_reports_n_fault_undriven=any("UNDRIVEN" in ln and "n_fault" in ln for ln in own))
    return res


def build(a, out: Path, params: dict):
    mdir = out / "obj"
    steps = []
    vcmd = [VERILATOR, "--cc", "--exe", "-O3", "-fno-inline", "-Wno-fatal", "-Wno-lint", "-Wno-style", "-Wno-TIMESCALEMOD",
            "--x-initial", "unique", "--top-module", "tb_field_sys", "--prefix", "Vtb", "--Mdir", mdir,
            *[f"-G{k}={v}" for k, v in params.items()], *RTL, TB, MAIN]
    rc, txt, s = sh(vcmd, out / "verilate.log")
    steps.append(dict(name="verilate", command=" ".join(map(str, vcmd)), seconds=s, returncode=rc))
    if rc:
        raise SystemExit(f"verilate failed:\n{txt[-4000:]}")
    mcmd = ["make", "-C", mdir, "-f", "Vtb.mk", f"-j{a.jobs}", "Vtb", "OPT_FAST=-O1", "OPT_SLOW=-O1"]
    rc, txt, s = sh(mcmd, out / "make.log")
    steps.append(dict(name="make", command=" ".join(map(str, mcmd)), seconds=s, returncode=rc))
    if rc:
        raise SystemExit(f"make failed:\n{txt[-4000:]}")
    return mdir / "Vtb", steps


def parse(path: Path):
    w, lost, opl, summ = [], [], [], {}
    for ln in path.read_text().splitlines():
        t = ln.split()
        if not t:
            continue
        if t[0] == "W":
            w.append((int(t[1]), int(t[2]), int(t[3], 16), int(t[4], 16)))
        elif t[0] == "L":
            lost.append((int(t[1]), int(t[2]), int(t[3], 16), int(t[4], 16)))
        elif t[0] == "O":
            opl.append(dict(op=int(t[1]), phase_cycles=int(t[2]), wall=int(t[3]), rows_per_region=list(map(int, t[4:]))))
        elif t[0] == "S":
            for kv in t[1:]:
                k, v = kv.split("=", 1)
                summ[k] = v
    return w, lost, opl, summ


def parse_tb(path: Path):
    s, c = {}, {}
    for ln in path.read_text().splitlines():
        t = ln.split()
        if t and t[0] == "S":
            s = dict(kv.split("=", 1) for kv in t[1:])
        elif t and t[0] == "C":
            c[t[1]] = dict(kv.split("=", 1) for kv in t[2:])
    return s, c


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--snapshot", type=Path, required=True)
    ap.add_argument("--workdir", type=Path, required=True)
    ap.add_argument("--np", type=int, default=16)
    ap.add_argument("--regions", type=int, default=4)
    ap.add_argument("--nbf", type=int, default=8)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--stalls", default="30,70")
    ap.add_argument("--seed", type=int, default=20261003)
    ap.add_argument("--xseeds", default="1,2,3,4")
    ap.add_argument("--result", type=Path)
    a = ap.parse_args()
    out = a.workdir.resolve()
    if out.exists() and any(out.iterdir()):
        raise SystemExit("Use a unique empty workdir")
    out.mkdir(parents=True, exist_ok=True)
    pins0 = {rel(p): sha(p) for p in SOURCES}
    t0 = time.monotonic()
    img, ops, expect, cases = images(a, out)
    # proven headroom: rows a region can still emit after its last issued beat <= its rows in the phase (the FIFO is
    # empty at a phase start: the spine finishes a phase only when its last row is written); +1: registered gate
    rmax = max(max(c["rows_per_region"]) for c in cases)
    H2 = rmax + 1
    OD2 = 1 << (H2 - 1).bit_length()
    OD3 = H3 = 2
    params = dict(NP=a.np, R=a.regions, NBF=a.nbf, PHW=PHW, VAW=VAW, OD2=OD2, H2=H2, OD3=OD3, H3=H3)
    with cf.ThreadPoolExecutor(max_workers=2) as ex:
        f_lint = ex.submit(lint, a, out)
        f_build = ex.submit(build, a, out, params)
        lint_res = f_lint.result()
        exe, steps = f_build.result()
    stalls = [0] + [int(x) for x in a.stalls.split(",") if x]
    xseeds = [int(x) for x in a.xseeds.split(",") if x]
    runs = [(f"stall{p}", p, 0, 0) for p in stalls] + [(f"xinit{s}", 0, 2, s) for s in xseeds]

    def sim(name, stall, rr, vs):
        cmd = [exe, f"+OT_ROM_DIR={img}", f"+OPS={ops}", f"+LOG={out / name}", f"+STALL={stall}", f"+SEED={a.seed}",
               f"+verilator+rand+reset+{rr}", f"+verilator+seed+{max(vs, 1)}"]
        rc, txt, s = sh(cmd, out / f"{name}.sim.log")
        return dict(name=name, stall=stall, rand_reset=rr, xseed=vs, command=" ".join(map(str, cmd)), returncode=rc,
                    seconds=s)

    with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
        sims = list(ex.map(lambda r: sim(*r), runs))

    def vm_of(w):
        m, cnt = {}, {}
        for _, _, ad, d in w:
            m[ad] = d
            cnt[ad] = cnt.get(ad, 0) + 1
        return m, cnt

    data = {}
    for r in sims:
        n = r["name"]
        tb_s, tb_c = parse_tb(out / f"{n}.tb.log")
        sysd = {}
        for sname in ("ref", "d0", "d1", "d2", "d3"):
            w, lost, opl, s = parse(out / f"{n}.{sname}.log")
            vm, cnt = vm_of(w)
            sysd[sname] = dict(w=w, lost=lost, ops=opl, s=s, vm=vm, cnt=cnt)
        data[n] = dict(run=r, tb=tb_s, cmp=tb_c, sys=sysd)
    ref = data["stall0"]["sys"]["ref"]
    ref_vm, ref_cnt, ref_ops = ref["vm"], ref["cnt"], ref["ops"]
    golden_ref_mism = sum(1 for ad, v in expect.items() if ref_vm.get(ad) != v)
    root_rows_match_bound = [o["rows_per_region"] for o in ref_ops] == [c["rows_per_region"] for c in cases]

    def sysrec(d, sname):
        x = d["sys"][sname]
        s = x["s"]
        rec = dict(summary=s, writes_accepted=len(x["w"]), writes_lost=len(x["lost"]),
                   golden_mismatch=sum(1 for ad, v in expect.items() if x["vm"].get(ad) != v),
                   vm_equal_ref=x["vm"] == ref_vm,
                   every_row_written_once=all(c == 1 for c in x["cnt"].values()) and set(x["cnt"]) == set(ref_cnt),
                   rows_missing_or_wrong_vs_ref=sum(1 for ad, v in ref_vm.items() if x["vm"].get(ad) != v),
                   ops=x["ops"], added_cycles_per_op=[o["wall"] - b["wall"] for o, b in zip(x["ops"], ref_ops)])
        rec["added_cycles_total"] = sum(rec["added_cycles_per_op"])
        return rec

    checks = {}
    # equivalence of the default (D0) on every run, and of D1..D3 on the no-stall runs
    for n, d in data.items():
        if d["run"]["rand_reset"]:      # random initial values differ per instance: these runs check only the fault
            continue
        alld = d["tb"].get("main_done") == "1"      # REF, D0, D1, D2 (D3 is the stress variant)
        c0 = d["cmp"]["d0"]
        r0 = sysrec(d, "d0")
        checks[f"eq_default_{n}"] = dict(
            pass_=alld and c0["mismatches"] == "0" and int(c0["checks"]) > 0 and r0["vm_equal_ref"]
            and r0["golden_mismatch"] == 0 and r0["added_cycles_total"] == 0,
            run=d["run"], compare=c0, d0=r0)
        if d["run"]["stall"] == 0:
            for dn in ("d1", "d2", "d3"):
                c = d["cmp"][dn]
                rr = sysrec(d, dn)
                checks[f"eq_{dn}_nostall_{n}"] = dict(
                    pass_=alld and c["mismatches"] == "0" and int(c["checks"]) > 0 and rr["vm_equal_ref"]
                    and rr["golden_mismatch"] == 0 and rr["added_cycles_total"] == 0
                    and rr["summary"]["gate_cycles"] == "0" and rr["summary"]["ret_ovf"] == "0",
                    run=d["run"], compare=c, dut=rr)
    # FAULT_TIE: field fault 0 on every cycle of every run for D1..D3 (rand-reset runs included)
    ft = []
    for n, d in data.items():
        for dn in ("d1", "d2", "d3"):
            s = d["sys"][dn]["s"]
            ok = s["field_fault_cycles"] == "0" and s["field_fault"] == "0"
            if dn == "d3" and s["ret_ovf"] == "1":     # a stress overflow is a real fault, not an X
                ok = True
            ft.append(dict(run=n, sys=dn, field_fault_cycles=int(s["field_fault_cycles"]), ok=ok))
    ref_x = {n: int(d["tb"]["ref_field_fault_cycles"]) for n, d in data.items()}
    checks["fault_tie"] = dict(pass_=all(x["ok"] for x in ft), per_run=ft,
                               ref_field_fault_cycles_per_run=ref_x,
                               original_spurious_fault_under_random_init=any(v > 0 for k, v in ref_x.items() if k.startswith("xinit")),
                               note=("Verilator is 2-state: the original's undriven n_fault bits take the simulator's initial "
                                     "value; +verilator+rand+reset+2 randomises it (the 2-state image of 4-state X)."))
    for p in stalls[1:]:
        d = data[f"stall{p}"]
        alld = d["tb"].get("main_done") == "1" and d["sys"]["d2"]["s"].get("done") == "1"
        r2 = sysrec(d, "d2")
        s2 = r2["summary"]
        checks[f"credit_stall_{p}"] = dict(
            pass_=alld and r2["vm_equal_ref"] and r2["every_row_written_once"] and r2["golden_mismatch"] == 0
            and s2["ret_ovf"] == "0" and s2["w_ovf"] == "0" and s2["field_fault"] == "0" and s2["spine_fault"] == "0"
            and int(s2["rows_retired"]) == len(expect) and r2["writes_lost"] == 0,
            run=d["run"], dut=r2)
        r1 = sysrec(d, "d1")
        s1 = r1["summary"]
        checks[f"contrast_stall_{p}"] = dict(
            pass_=s1["w_ovf"] == "1" and r1["writes_lost"] > 0 and not r1["vm_equal_ref"],
            meaning="pass = the hazard is reproduced (RET_CREDIT=0 loses rows under VM write stall)",
            run=d["run"], dut=r1)
        r3 = sysrec(d, "d3")
        checks[f"stress_stall_{p}"] = dict(
            pass_=None, informational=True,
            meaning=("RET_H below the proven bound: the hardware invariant must either hold (no ret_ovf, rows exact) "
                     "or flag the overflow; a silent wrong row would be a failure"),
            silent_corruption=(r3["summary"]["ret_ovf"] == "0" and not r3["vm_equal_ref"]),
            run=d["run"], dut=r3)
    expect_bits = list(range(2 * a.np - a.regions, 2 * a.np - 1))      # NL-R .. NL-2
    lint_pass = (lint_res["original"]["n_fault_undriven_bits"] == expect_bits
                 and lint_res["sys_tie0_credit0"]["n_fault_undriven_bits"] == expect_bits
                 and not lint_res["sys_tie1_credit0"]["no_driver_warnings"]
                 and not lint_res["sys_tie1_credit1"]["no_driver_warnings"])
    stress_ok = all(not v["silent_corruption"] for k, v in checks.items() if k.startswith("stress"))
    pins1 = {rel(p): sha(p) for p in SOURCES}
    for v in checks.values():
        v["pass"] = v.pop("pass_")
    allpass = (lint_pass and stress_ok and golden_ref_mism == 0 and root_rows_match_bound and pins0 == pins1
               and all(v["pass"] for v in checks.values() if v["pass"] is not None))
    lat = checks["eq_d2_nostall_stall0"]["dut"]["added_cycles_per_op"]
    rec = dict(
        schema="opentallas.rtl.dsrom_field_sys_bench.v1",
        status="pass" if allpass else "fail",
        claim_boundary=("Simulation-only (Verilator 5.050, 2-state) evidence for default-off successors of the W17 ROM "
                        "field and spine (gap review D1/S1, B2a) at the field gate's reduced, structurally identical field "
                        "(same module code; full shape NP 8192, R 128). No adoption, clock, area or rate claim. RET_H is "
                        "proven only for these images (rows/region/phase bound); a product RET_H needs the issue/return "
                        "calendar walker or the full-shape rows/region/phase."),
        config=dict(np=a.np, regions=a.regions, nbf=a.nbf, phw=PHW, vaw=VAW, fast=0, pp=0, bp=0, bst=2, rst=1, rd=64,
                    root_d=128, n_fault_width=2 * a.np, undriven_n_fault_bits_original=a.regions - 1,
                    d2=dict(FAULT_TIE=1, RET_CREDIT=1, RET_OD=OD2, RET_H=H2),
                    d3=dict(FAULT_TIE=1, RET_CREDIT=1, RET_OD=OD3, RET_H=H3),
                    rows_region_phase_max=rmax, stalls=stalls, stall_seed=a.seed, x_seed=GATE.SEED,
                    rand_reset_seeds=xseeds, build_params=params),
        mechanism=("RET_CREDIT=1: per-region fall-through row FIFO (RET_OD) after each root; the spine's VM write port is "
                   "valid/ready (vm_w_ready), w_we holds a row until accepted and the spine pops the field (r_ready) only "
                   "when its write register is free or being accepted; the stream stops issuing beats while any region "
                   "has fewer than RET_H free row slots (registered once in the spine). Roots and nodes are never "
                   "stalled. ACK: w_ack, ack_row/ack_pos, rows_retired. FAULT_TIE=1 ties n_fault[NL-2:NL-R]."),
        why_not_per_row_credit=("The elements have no stall input and the beat->row map lives in the per-element "
                                "configuration ROMs, so the spine cannot reserve a slot per row before the row's first "
                                "beat; the credit reserves RET_H row slots per region instead. Sound when RET_H >= F+1, "
                                "F = rows a region can still emit after the last issued beat; F <= rows/region/phase."),
        lint=lint_res, lint_pass=lint_pass, lint_expected_undriven_bits_original=expect_bits,
        equivalence_gate=("this bench's own side-by-side comparison (pinned original spine+field vs successor, every port, "
                          "every cycle, same stimulus); tools/v41_field_rt_gate.py is NOT used (it fails at HEAD: its pass "
                          "record pins e9bd212f9). Only phases()/constants of tools/w17_w10_field_rt_gate.py are imported."),
        checks=checks, stress_no_silent_corruption=stress_ok,
        ref_golden_mismatch=golden_ref_mism, golden_rows=len(expect),
        root_rows_per_region_equal_config_bound=root_rows_match_bound, cases=cases,
        latency_cost_ret_credit_full_rate_cycles_per_op=lat,
        runs=[d["run"] for d in data.values()], build_steps=steps,
        source_sha256=pins1, source_stable=pins0 == pins1,
        tools=dict(verilator=subprocess.run([VERILATOR, "--version"], capture_output=True, text=True).stdout.strip()),
        command=" ".join([sys.executable, *sys.argv]), wall_seconds=round(time.monotonic() - t0, 1),
        checkpoint_revision=a.snapshot.resolve().name)
    js = json.dumps(rec, indent=1, default=str) + "\n"
    (out / "field_sys_bench.json").write_text(js)
    if a.result:
        a.result.parent.mkdir(parents=True, exist_ok=True)
        a.result.write_text(js)
    print(rec["status"], "lint", lint_pass, {k: v["pass"] for k, v in checks.items()})
    return 0 if allpass else 1


if __name__ == "__main__":
    sys.exit(main())
