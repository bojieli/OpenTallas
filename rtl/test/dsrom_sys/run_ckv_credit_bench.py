#!/usr/bin/env python3
"""Gap D3 bench: ot_chip_v41x_ckv_die_service_cr (rtl/dsrom_sys/) on the W17 L20 selection, four dies TP-4,
through rtl/test/dsrom_sys/tb_dsrom_ckv_credit.sv (successor of rtl/test/tb_w11_ckvdie_service.sv).

Cases:
  a  AG_CREDIT=0 reproduces the original bench (original module + original tb, same vectors): identical
     ROW/HBMW lines and CKVDIE summary, and both pass the original gate's golden checks (tools/w11_ckvdie_gate.check);
  b  AG_CREDIT=1, no stall: same golden checks, canonical ROW/HBMW set equal to the original's, added cycles;
  c  AG_CREDIT=1 under random collector write-port unavailability (30%/70%) and link/credit jitter: bit-exact,
     zero faults;
  d  contrast: AG_CREDIT=0 under the same receive stall (no ready: rows presented in a stalled cycle are lost):
     hazard shown when rows are lost and the run does not pass;
  e  mutants: one remote row with a wrong gid / wrong owner die / stale generation is caught by the identity check,
     never written (die 0 present bit of that rank stays 0); the original module is run as contrast.
Vectors come from tools/w11_ckvdie_gate.prep (W17 images + golden); checks from tools/w11_ckvdie_gate.check.
Never overwrites a failed verdict.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import w11_ckvdie_gate as G  # noqa: E402

COMMON = ["rtl/chip/ot_chip_v41x_ckv_row_encoder.sv", "rtl/chip/ot_chip_v41x_ckv_sel_ids.sv",
          "rtl/chip/ot_chip_v41x_ckv_sel_fetch.sv", "rtl/chip/ot_chip_v41x_ckv_selected_dma.sv",
          "rtl/chip/ot_chip_v41x_ckv_fp4_decode.sv", "rtl/chip/ot_chip_v41x_ckv_stream_merge.sv"]
ORIG_SRC = ["rtl/chip/ot_chip_v41x_ckv_die_service.sv", *COMMON, "rtl/test/tb_w11_ckvdie_service.sv"]
NEW_SRC = ["rtl/dsrom_sys/ot_chip_v41x_ckv_die_service_cr.sv", *COMMON, "rtl/test/dsrom_sys/tb_dsrom_ckv_credit.sv"]
TOOLS = ["rtl/test/dsrom_sys/run_ckv_credit_bench.py", *G.TOOLS]
VL = G.VL
REC = ROOT / "results/rtl/dsrom_system_rtl_20261003/ckv_credit_bench.json"

BUILDS = {  # name: (sources, top, params)
    "orig": (ORIG_SRC, "tb_w11_ckvdie_service", {}),
    "ag0": (NEW_SRC, "tb_dsrom_ckv_credit", {"AG_CREDIT": 0}),
    "cr_q16_w5": (NEW_SRC, "tb_dsrom_ckv_credit", {"AG_CREDIT": 1, "RXQ": 16, "NWP": 5}),
    "cr_q16_w1": (NEW_SRC, "tb_dsrom_ckv_credit", {"AG_CREDIT": 1, "RXQ": 16, "NWP": 1}),
    "cr_q64_w5": (NEW_SRC, "tb_dsrom_ckv_credit", {"AG_CREDIT": 1, "RXQ": 64, "NWP": 5}),
    "cr_q160_w5": (NEW_SRC, "tb_dsrom_ckv_credit", {"AG_CREDIT": 1, "RXQ": 160, "NWP": 5}),
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build_cmd(name, obj):
    src, top, prm = BUILDS[name]
    return [str(VL), "--binary", "--timing", "-j", "4", "-Wno-fatal", "-Wno-WIDTH", "-Wno-TIMESCALEMOD",
            "-Mdir", str(obj), "--top-module", top, "--x-assign", "unique", "--x-initial", "unique",
            *[f"-G{k}={v}" for k, v in prm.items()], *[str(ROOT / s) for s in src], "-CFLAGS", "-O1"]


def build(name, scratch):
    """Build, or reuse an object dir whose stamp records the same command and source digests."""
    obj = scratch / f"obj_{name}"
    cmd = build_cmd(name, obj)
    exe = obj / f"V{BUILDS[name][1]}"
    stamp = dict(cmd=cmd, src={s: sha(ROOT / s) for s in BUILDS[name][0]})
    sp = obj / "stamp.json"
    if exe.is_file() and sp.is_file() and json.loads(sp.read_text()) == stamp:
        return name, exe, cmd, 0.0
    if obj.exists():
        shutil.rmtree(obj)
    t = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(f"build {name} failed:\n{p.stderr[-4000:]}")
    sp.write_text(json.dumps(stamp))
    return name, exe, cmd, round(time.time() - t, 1)


def canon(stdout):
    rows = sorted(x for x in stdout.splitlines() if x.startswith("ROW "))
    hbmw = sorted(x for x in stdout.splitlines() if x.startswith("HBMW "))
    return hashlib.sha256("\n".join(rows + hbmw).encode()).hexdigest()


def run(exe, vec, info, plus):
    cmd = [str(exe), f"+dir={vec}", *[f"+{k}={v}" for k, v in plus.items()]]
    t = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=6 * 3600)
    res = G.check(vec, p.stdout, info)
    f = res["fields"]
    mut = re.findall(r"MUT mutant=(\d+) rank=(-?\d+) present=(\d+)", p.stdout)
    gate_ok = (p.returncode == 0 and res["row_errors"] == 0 and res["fmt_errors"] == 0 and
               res["rows_checked"] == 4 * 2 * 512 and f.get("hbm_miss") == "0" and f.get("timeout") == "0" and
               f.get("faults") == "0,0,0,0" and res["own_row_write_exact"])
    core = [x for x in p.stdout.splitlines() if x.startswith(("ROW ", "HBMW "))]
    summ = [x for x in p.stdout.splitlines() if x.startswith("CKVDIE ")]
    return dict(cmd=" ".join(cmd), plus=plus, rc=p.returncode, gate_checks_pass=gate_ok,
                cycles=int(f.get("cycles", -1)), fields=f, rows_checked=res["rows_checked"],
                row_errors=res["row_errors"], fmt_errors=res["fmt_errors"],
                own_row_write_exact=res["own_row_write_exact"], canon_sha256=canon(p.stdout),
                stream_sha256=hashlib.sha256("\n".join(core).encode()).hexdigest(),
                summary_line=summ[-1] if summ else None,
                mutant=dict(zip(("mutant", "rank", "present"), map(int, mut[-1]))) if mut else None,
                wall_s=round(time.time() - t, 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", type=Path, default=Path("/home/ubuntu/w17work/die/ctx1048576_s20260930_L20"))
    ap.add_argument("--golden", type=Path, default=Path("/home/ubuntu/w17work/isa/scratch_s20260930/ctx1048576_L20.npz"))
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--vec", type=Path, help="short path for the vectors ($readmemh path limit); default scratch/vec")
    ap.add_argument("--record", type=Path, default=REC)
    ap.add_argument("--par", type=int, default=3)
    ap.add_argument("--build-only", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    if a.build_only:
        a.scratch.mkdir(parents=True, exist_ok=True)
        with cf.ThreadPoolExecutor(2) as ex:
            for name, exe, cmd, w in ex.map(lambda n: build(n, a.scratch), list(BUILDS)):
                print("built", name, w, flush=True)
        return
    a.scratch.mkdir(parents=True, exist_ok=True)
    vec = a.vec or (a.scratch / "vec")
    if (vec / "info.json").is_file():
        info = json.loads((vec / "info.json").read_text())
    else:
        info = G.prep(a, vec)
        (vec / "info.json").write_text(json.dumps(info))
    assert len(str(vec)) + 12 < 128, "vector path too long for the bench's 1024-bit +dir"
    exes, bcmd, bwall = {}, {}, {}
    with cf.ThreadPoolExecutor(2) as ex:
        for name, exe, cmd, w in ex.map(lambda n: build(n, a.scratch), list(BUILDS)):
            exes[name], bcmd[name], bwall[name] = exe, " ".join(cmd), w
            print("built", name, w, flush=True)
    cases = []   # (id, group, build, plusargs, expectation)
    for lat in (100, 259):
        cases.append((f"a_orig_lat{lat}", "a", "orig", dict(lat=lat, ri=2), "pass"))
        cases.append((f"a_ag0_lat{lat}", "a", "ag0", dict(lat=lat, ri=2), "pass"))
        for b in ("cr_q16_w5", "cr_q64_w5", "cr_q160_w5"):
            cases.append((f"b_{b}_lat{lat}", "b", b, dict(lat=lat, ri=2), "pass"))
    for b in ("cr_q16_w5", "cr_q16_w1"):
        for st in (300, 700):
            for jit in (0, 300):
                for seed in (1, 2):
                    cases.append((f"c_{b}_st{st}_j{jit}_s{seed}", "c", b,
                                  dict(lat=100, ri=2, wpstall=st, jitter=jit, seed=seed), "pass"))
    cases.append(("c_cr_q16_w1_lat259_st700_j300_s3", "c", "cr_q16_w1",
                  dict(lat=259, ri=2, wpstall=700, jitter=300, seed=3), "pass"))
    # receive-side limited (credits not RTT-bound): the slow writer itself must back-pressure the senders
    for st, jit in ((300, 300), (700, 300), (950, 0), (950, 300)):
        cases.append((f"c_cr_q160_w5_st{st}_j{jit}_s4", "c", "cr_q160_w5",
                      dict(lat=100, ri=2, wpstall=st, jitter=jit, seed=4), "pass"))
    for st in (950, 990):
        cases.append((f"c_cr_q16_w1_st{st}_j300_s5", "c", "cr_q16_w1",
                      dict(lat=100, ri=2, wpstall=st, jitter=300, seed=5), "pass"))
    for st in (300, 700):
        cases.append((f"d_ag0_st{st}_s1", "d", "ag0", dict(lat=100, ri=2, wpstall=st, seed=1, maxcyc=20000), "hazard"))
    for m in (1, 2, 3):
        cases.append((f"e_cr_q16_w5_mut{m}", "e", "cr_q16_w5", dict(lat=100, ri=2, mutant=m), f"caught{m}"))
        cases.append((f"e_ag0_mut{m}", "e", "ag0", dict(lat=100, ri=2, mutant=m), f"contrast{m}"))
    with cf.ThreadPoolExecutor(a.par) as ex:
        futs = {cid: ex.submit(run, exes[b], vec, info, plus) for cid, _, b, plus, _ in cases}
        out = {cid: futs[cid].result() for cid, *_ in cases}
    ref = {lat: out[f"a_orig_lat{lat}"] for lat in (100, 259)}
    want_cr = {1: "4,0,0,0", 2: "c,0,0,0", 3: "10,0,0,0"}
    results = []
    for cid, grp, b, plus, exp in cases:
        r = out[cid]
        f = r["fields"]
        lat = plus["lat"]
        crz = f.get("crfault", "0,0,0,0") == "0,0,0,0"
        if exp == "pass":
            same = r["canon_sha256"] == ref[lat]["canon_sha256"]
            ok = r["gate_checks_pass"] and crz and same
            extra = dict(canon_equal_to_original=same, added_cycles=r["cycles"] - ref[lat]["cycles"])
            if grp == "a" and b == "ag0":
                o = ref[lat]
                core_same = r["stream_sha256"] == o["stream_sha256"]
                summ_same = (r["summary_line"] or "").startswith(o["summary_line"] or "\0")
                extra.update(stream_identical_to_original=core_same, summary_prefix_identical=summ_same)
                ok = ok and core_same and summ_same
        elif exp == "hazard":
            lost = int(f.get("lost", 0))
            ok = lost > 0 and not r["gate_checks_pass"]
            extra = dict(rows_lost=lost, hazard_demonstrated=ok, timeout=f.get("timeout"))
        elif exp.startswith("caught"):
            m = int(exp[-1])
            mu = r["mutant"] or {}
            ok = (f.get("crfault") == want_cr[m] and mu.get("present") == 0 and f.get("faults", "").split(",")[0] != "0"
                  and all(x == "0" for x in f.get("faults", "").split(",")[1:]))
            extra = dict(expected_crfault=want_cr[m], mutant_row_written=mu.get("present"))
        else:  # contrast: record what the original does
            mu = r["mutant"] or {}
            ok = True
            extra = dict(original_fault_die0=f.get("faults", "").split(",")[0], mutant_row_written=mu.get("present"),
                         original_detects=f.get("faults", "").split(",")[0] != "0",
                         original_writes_faulty_row=mu.get("present") == 1)
        results.append(dict(id=cid, group=grp, build=b, expectation=exp, verdict="pass" if ok else "fail",
                            **extra, **r))
        print(cid, "pass" if ok else "FAIL", r["cycles"], f.get("faults"), f.get("crfault"), f.get("lost"),
              extra, flush=True)
    if a.record.is_file() and json.loads(a.record.read_text()).get("status") != "pass":
        raise SystemExit(f"{a.record} holds a failed verdict")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    srcs = sorted(set(ORIG_SRC + NEW_SRC + TOOLS))
    dirty = subprocess.check_output(["git", "status", "--porcelain", "--", *srcs], cwd=ROOT, text=True).strip()
    vl = subprocess.run([str(VL), "--version"], capture_output=True, text=True).stdout.strip()
    gxx = subprocess.run(["g++", "--version"], capture_output=True, text=True).stdout.splitlines()[0]
    rec = dict(
        schema="dsrom_ckv_credit_bench/1",
        gap="D3 (/tmp/claude-review-20261003/rombridge/partB.md): ag_rx_* always taken, no ready/credit",
        scope=("Four dies' ot_chip_v41x_ckv_die_service_cr on the W17 L20 selection (1M context, seed 20260930), "
               "behavioural HBM and all-gather links as in tb_w11_ckvdie_service; credits returned on the reverse "
               "link with the forward latency. Receive stall = collector write-port unavailability (wp_stall); "
               "NWP = collector write ports per cycle. Not the installed die (rtl/chip/ckvsel/ot_chip_v41x_die.sv "
               "still instantiates the original), no CDC/physical link, no area/timing."),
        git_head=head, sources_dirty_vs_head=dirty.splitlines(),
        source_sha256={s: sha(ROOT / s) for s in srcs},
        images=str(a.images), golden=str(a.golden), golden_sha256=sha(a.golden),
        selection=dict(n_rows_before=info["n"], own_row_selected=info["new_selected"], owned_per_die=info["owned"]),
        vectors=dict(dir=str(vec), **{k: v for k, v in info.items() if k not in ("ids", "n", "new_selected", "owned")},
                     sha256={p.name: sha(p) for p in sorted(vec.iterdir()) if p.name != "info.json"}),
        tools=dict(verilator=vl, verilator_path=str(VL), gxx=gxx, python=sys.version.split()[0]),
        builds={k: dict(cmd=bcmd[k], params=BUILDS[k][2], wall_s=bwall[k]) for k in BUILDS},
        runner_cmd=" ".join([sys.executable, *sys.argv]),
        cases=results, wall_s=round(time.time() - t0, 1),
        status="pass" if all(r["verdict"] == "pass" for r in results) else "fail")
    a.record.parent.mkdir(parents=True, exist_ok=True)
    a.record.write_text(json.dumps(rec, indent=1) + "\n")
    print(rec["status"])


if __name__ == "__main__":
    main()
