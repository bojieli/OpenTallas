#!/usr/bin/env python3
"""Lever item 1 (b): same-x phase merge on the flat W17-runtime ROM-field RTL, every merged pair of one real layer.

Extends the free-levers audit bench (origin/claude/free-levers-audit-20261003:
results/uarch/free_levers_audit_20261003/bench/phase_merge_flat.py, which ran ONE expert pair and the attention pair)
to EVERY pair the emitter option merges in a real layer: the pairs come from tools/dsrom_lever_phase_merge.py
merge_program on that layer's die program, the matrices and rank row offsets from the die's weights.json.

Two images over ONE compiled model (rtl/w17_runtime/v41die/ot_v41_fieldtop, the reference of
tools/w17_runtime_v41_field_rt_gate.py):
  off  every matrix its own phase (the program as emitted: 2 phases per pair);
  on   every pair one phase (both matrices share x; rows land at obase + row tag).
Each pair reads its own x (seeded BF16, the gate's seed); every written row is compared with golden linear_q
(R-ARITH chunk8, tools/w17_runtime_v41_die_images.golden_phase) bit for bit.

Rows per matrix are a slice (--rows; the small NP field cannot hold a full 576-row rank slice in one stream beat
set): the phase's fixed cost, which the merge removes, does not depend on rows; die-shape stream beats are taken from
the merged die images (dsrom_lever_phase_merge.py images, phase_model).

  prep   (local: snapshot + numpy)  --images R3/images --rank 0 --snapshot S --out DIR
  run    (sim host)                 --dir DIR [--np 16 --regions 4 --nbf 8 --bst 17 --jobs 32]
  score  (local)                    --dir DIR --result OUT.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

PHW, VAW = 4, 16
VERILATOR = Path("~/.local/opentallas-tools/verilator-5.050/bin/verilator").expanduser()


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rtl_sources() -> list[Path]:
    import w17_runtime_v41_field_rt_gate as Gt
    return [*Gt.DIE, Gt.VIA_ROM, *Gt.COMMON, *Gt.W10]


def cmd_prep(a):
    import numpy as np
    import hdc_golden_v41 as G
    import w17_runtime_v41_die_images as I
    import w17_runtime_v41_field_rt_gate as Gt
    import dsrom_lever_phase_merge as PM
    from rtl_v41_rom_array import Ckpt, Mat
    G.set_arith("chunk8")
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    src = a.images / f"r{a.rank}"
    prog, _ = PM.read_prog(src / "prog.hex")
    _, merges = PM.merge_program(prog, True)
    wops = {o["pc"]: o for o in json.loads((src / "weights.json").read_text())}
    ck = Ckpt(a.snapshot)
    rng = np.random.default_rng(Gt.SEED)
    pairs = []
    for m in merges:
        o1, o2 = wops[m["pc_first"]], wops[m["pc_second"]]
        n = a.rows_fp8 if o1["fmt"] == "fp8" else a.rows
        mk = lambda o, n=n: Mat(ck, o["tensor"][:-len(".weight")], o["fmt"], n, o["cols"][1] - o["cols"][0],  # noqa: E731
                           r0=o["rows"][0], k0=o["cols"][0])
        pairs.append(dict(merge=m, ops=[o1, o2], mats=lambda o1=o1, o2=o2, mk=mk: (mk(o1), mk(o2))))
    # one x per pair, in VM from 0; outputs from 49152
    vm = np.zeros(1 << VAW, dtype=np.uint32)
    xs, xptr = [], 0
    for p in pairs:
        K = p["ops"][0]["cols"][1] - p["ops"][0]["cols"][0]
        x = G.to_bf16((rng.standard_normal(K) * 0.5).astype(G.F))
        vm[xptr: xptr + K] = G.bits(np.asarray(x, dtype=G.F))
        xs.append((xptr, K, x))
        xptr += K
    assert xptr <= 49152
    man = dict(rank=a.rank, rows=a.rows, rows_fp8=a.rows_fp8, seed=Gt.SEED, pairs=[], arms={})
    for arm in ("off", "on"):
        fld = I.Field(a.np, a.regions, a.nbf)
        ops, expect, cases, optr = [], {}, [], 49152
        for p, (xb, K, x) in zip(pairs, xs):
            m1, m2 = p["mats"]()
            groups = [[m1], [m2]] if arm == "off" else [[m1, m2]]
            for g in groups:
                ph = I.add_phase(fld, g, (False, False), 0)
                gold = I.golden_phase(g, np.asarray(x, dtype=G.F))
                for tag, (_f32, b16) in gold.items():
                    expect[optr + tag] = b16 << 16
                ops.append((ph["index"], 0, xb, K, optr, ph["nrows"]))
                cases.append(dict(pc_first=p["merge"]["pc_first"], mats=[mm.name for mm in g], phase=ph["index"],
                                  rows=ph["nrows"], K=K, stream_beats=ph["nbeat"], t_phase_model=ph["t_phase_model"],
                                  obase=optr))
                optr += ph["nrows"]
        img = out / f"img_{arm}"
        I.write_field(fld, img, PHW)
        (img / "vm.hex").write_text("".join(f"{int(v):08x}\n" for v in vm))
        (out / f"ops_{arm}.txt").write_text("".join(" ".join(map(str, o)) + "\n" for o in ops))
        (out / f"expect_{arm}.json").write_text(json.dumps({str(k): v for k, v in expect.items()}) + "\n")
        man["arms"][arm] = dict(cases=cases, phases=len(fld.phases))
    man["pairs"] = [dict(pc=[p["merge"]["pc_first"], p["merge"]["pc_second"]], tag=p["ops"][0]["tag"],
                         tensors=[o["tensor"] for o in p["ops"]], fmt=p["ops"][0]["fmt"],
                         rank_rows=[o["rows"] for o in p["ops"]]) for p in pairs]
    man["params"] = dict(np=a.np, regions=a.regions, nbf=a.nbf, phw=PHW, vaw=VAW)
    man["checkpoint_header_sha256"] = ck.pins
    man["die_images"] = str(src)
    man["die_prog_sha256"] = sha(src / "prog.hex")
    man["rtl_sources"] = [str(p.relative_to(ROOT)) for p in rtl_sources()]
    man["source_sha256"] = {str(p.relative_to(ROOT)): sha(p) for p in
                            [*rtl_sources(), Path(__file__).resolve(), ROOT / "tools/dsrom_lever_phase_merge.py",
                             ROOT / "tools/w17_runtime_v41_die_images.py", ROOT / "tools/hdc_golden_v41.py",
                             ROOT / "rtl/test/dsrom_sys/levers/phase_merge_flat_bench.cpp"]}
    (out / "manifest.json").write_text(json.dumps(man, indent=1, default=str) + "\n")
    print(f"prep: {len(pairs)} pairs; off {man['arms']['off']['phases']} phases, on {man['arms']['on']['phases']}")
    return 0


def cmd_run(a):
    """Sim host: verilate + build once, run both arms.  Paths in the manifest are relative to --root."""
    d = a.dir.resolve()
    man = json.loads((d / "manifest.json").read_text())
    root = a.root.resolve()
    mdir = d / "flat"
    steps = []
    vroot = re.search(r"VERILATOR_ROOT\s*=\s*(\S+)", subprocess.check_output([str(VERILATOR), "-V"], text=True)).group(1)

    def run(name, cmd, **kw):
        t0 = time.monotonic()
        p = subprocess.run(list(map(str, cmd)), cwd=d, capture_output=True, text=True, **kw)
        (d / f"{name}.log").write_text(p.stdout + p.stderr)
        steps.append(dict(name=name, seconds=round(time.monotonic() - t0, 2), returncode=p.returncode,
                          utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))
        if p.returncode:
            raise SystemExit(f"{name} failed:\n{(p.stdout + p.stderr)[-3000:]}")
        return p

    P = man["params"]
    if not (mdir / "Vflat__ALL.a").exists():
        run("verilate_flat", [VERILATOR, "--cc", "-O3", "-Wno-fatal", "-Wno-lint", "-Wno-style", "-Wno-TIMESCALEMOD",
                              "--top-module", "ot_v41_fieldtop", "--prefix", "Vflat", "--Mdir", mdir,
                              f"-GNP={P['np']}", f"-GR={P['regions']}", f"-GNBF={P['nbf']}", f"-GPHW={P['phw']}",
                              f"-GVAW={P['vaw']}", f"-GBST={a.bst}", *[root / s for s in man["rtl_sources"]]])
        run("build_flat", ["make", "-C", mdir, "-f", "Vflat.mk", f"-j{a.jobs}", "Vflat__ALL.a", "OPT_FAST=-O2",
                           "OPT_SLOW=-O1"])
    binp = d / "flat_bench"
    run("link", ["g++", "-std=c++20", "-O2", "-pthread", f"-DNR={P['regions']}", f"-DVAW={P['vaw']}",
                 f"-I{vroot}/include", f"-I{vroot}/include/vltstd", f"-I{mdir}",
                 root / "rtl/test/dsrom_sys/levers/phase_merge_flat_bench.cpp", *sorted(mdir.rglob("*.a")),
                 f"{vroot}/include/verilated.cpp", f"{vroot}/include/verilated_threads.cpp",
                 f"{vroot}/include/verilated_dpi.cpp", "-o", binp])
    for arm in ("off", "on"):
        t0 = time.monotonic()
        p = subprocess.run([str(binp), str(d / f"img_{arm}"), str(d / f"ops_{arm}.txt")], cwd=d, capture_output=True,
                           text=True)
        (d / f"simulate_{arm}.log").write_text(p.stdout + p.stderr)
        steps.append(dict(name=f"simulate_{arm}", seconds=round(time.monotonic() - t0, 2), returncode=p.returncode,
                          utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))
    host = subprocess.check_output(["hostname"], text=True).strip()
    (d / "run_steps.json").write_text(json.dumps(dict(host=host, bst=a.bst, steps=steps, simulator=subprocess.check_output(
        [str(VERILATOR), "--version"], text=True).strip(), rtl_sha256={s: sha(root / s) for s in man["rtl_sources"]},
        bench_cpp_sha256=sha(root / "rtl/test/dsrom_sys/levers/phase_merge_flat_bench.cpp")), indent=1) + "\n")
    return 0


def cmd_score(a):
    d = a.dir
    man = json.loads((d / "manifest.json").read_text())
    rs = json.loads((d / "run_steps.json").read_text())
    arms = {}
    for arm in ("off", "on"):
        log = (d / f"simulate_{arm}.log").read_text().splitlines()
        expect = {int(k): v for k, v in json.loads((d / f"expect_{arm}.json").read_text()).items()}
        writes = {}
        for ln in log:
            t = ln.split()
            if t and t[0] == "W":
                writes[int(t[1])] = int(t[2], 16)
        cases = [dict(c) for c in man["arms"][arm]["cases"]]
        for c, ln in zip(cases, [ln for ln in log if ln.startswith("OP ")]):
            g = dict(re.findall(r"(\w+)=(\d+)", ln))
            c.update(phase_cycles_rtl=int(g["cycles"]), wall_cycles_rtl=int(g["wall"]), wait_ready=int(g["wait_ready"]))
            c["golden_mismatch"] = sum(writes.get(r) != expect[r] for r in range(c["obase"], c["obase"] + c["rows"]))
        wrong = sorted(ad for ad, v in expect.items() if writes.get(ad) != v)
        extra = sorted(set(writes) - set(expect))
        arms[arm] = dict(verdict=log[-1] if log else None, cases=cases, golden_rows=len(expect),
                         golden_mismatch=len(wrong), unexpected_writes=len(extra), writes=writes,
                         passed=bool(log) and log[-1].startswith("PASS") and not wrong and not extra
                         and len(cases) == sum(1 for ln in log if ln.startswith("OP ")))
    per_pair = []
    for i, p in enumerate(man["pairs"]):
        s1, s2 = arms["off"]["cases"][2 * i], arms["off"]["cases"][2 * i + 1]
        m = arms["on"]["cases"][i]
        n1 = s1["rows"]
        ident = all(arms["off"]["writes"].get((s1 if t < n1 else s2)["obase"] + (t if t < n1 else t - n1))
                    == arms["on"]["writes"].get(m["obase"] + t) for t in range(m["rows"]))
        per_pair.append(dict(pc=p["pc"], tag=p["tag"], tensors=p["tensors"], fmt=p["fmt"], rows=[s1["rows"], s2["rows"]],
                             K=m["K"], split_wall_cycles=[s1["wall_cycles_rtl"], s2["wall_cycles_rtl"]],
                             merged_wall_cycles=m["wall_cycles_rtl"],
                             saved_cycles=s1["wall_cycles_rtl"] + s2["wall_cycles_rtl"] - m["wall_cycles_rtl"],
                             stream_beats_split=[s1["stream_beats"], s2["stream_beats"]], stream_beats_merged=m["stream_beats"],
                             golden_mismatch_split=s1["golden_mismatch"] + s2["golden_mismatch"],
                             golden_mismatch_merged=m["golden_mismatch"], rows_bit_identical_split_vs_merged=ident))
    for arm in arms.values():
        arm.pop("writes")
    ok = all(arms[k]["passed"] for k in arms) and all(p["rows_bit_identical_split_vs_merged"] for p in per_pair)
    src_now = {k: sha(ROOT / k) for k in man["source_sha256"]}
    rec = dict(schema="opentallas.dsrom_sys.lever.phase_merge_flat.v1", status="pass" if ok else "fail",
               claim_boundary=("Flat W17-runtime ROM-field RTL (ot_v41_fieldtop, small NP field) per-op cycles of every "
                               "same-x pair the default-off emitter option merges in one real layer, split (2 phases) vs "
                               "merged (1 phase), real checkpoint row slices of the die's rank, golden linear_q rows bit "
                               "for bit.  Row slices, not full rank rows; not a die/runtime composition or a token."),
               params=dict(man["params"], bst=rs["bst"]), rank=man["rank"], rows=man["rows"], rows_fp8=man["rows_fp8"],
               seed=man["seed"], die_prog_sha256=man["die_prog_sha256"], pairs=per_pair,
               total_saved_cycles=sum(p["saved_cycles"] for p in per_pair),
               arms={k: {kk: vv for kk, vv in v.items()} for k, v in arms.items()},
               host=rs["host"], steps=rs["steps"], simulator=rs["simulator"], rtl_sha256_on_host=rs["rtl_sha256"],
               checkpoint_header_sha256=man["checkpoint_header_sha256"], source_sha256=man["source_sha256"],
               source_stable=src_now == man["source_sha256"] and all(
                   rs["rtl_sha256"][k] == man["source_sha256"][k] for k in rs["rtl_sha256"]))
    a.result.parent.mkdir(parents=True, exist_ok=True)
    a.result.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(status=rec["status"], total_saved=rec["total_saved_cycles"],
                          pairs=[(p["pc"], p["split_wall_cycles"], p["merged_wall_cycles"], p["saved_cycles"],
                                  p["golden_mismatch_split"], p["golden_mismatch_merged"]) for p in per_pair],
                          off=arms["off"]["verdict"], on=arms["on"]["verdict"], source_stable=rec["source_stable"])))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("prep")
    p.add_argument("--images", type=Path, required=True)
    p.add_argument("--rank", type=int, default=0)
    p.add_argument("--snapshot", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--rows", type=int, default=12)
    p.add_argument("--rows-fp8", type=int, default=8)
    p.add_argument("--np", type=int, default=16)
    p.add_argument("--regions", type=int, default=4)
    p.add_argument("--nbf", type=int, default=8)
    p = sp.add_parser("run")
    p.add_argument("--dir", type=Path, required=True)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--bst", type=int, default=17)
    p.add_argument("--jobs", type=int, default=32)
    p = sp.add_parser("score")
    p.add_argument("--dir", type=Path, required=True)
    p.add_argument("--result", type=Path, required=True)
    a = ap.parse_args()
    return dict(prep=cmd_prep, run=cmd_run, score=cmd_score)[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
