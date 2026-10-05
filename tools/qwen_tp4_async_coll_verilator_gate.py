#!/usr/bin/env python3
"""Cut-through (asynchronous) TP-4 all-reduce vs the legacy sequencer, under Verilator.

Four sequencers, the real collective (ot_rom_oneshot_allreduce: rank-order
binary32 fold, credits, LAT-cycle links) and a stub core that writes the
all-reduce region through ME result ports on a schedule while it runs
(rtl/test/tb_qwen_tp4_async_coll_vl.sv).  The region holds stale words until
the engine writes them, so a word sent early gives a wrong sum.  Every case is
checked word by word in RTL against tools/hdc_golden.fold, and the write logs
of three builds must be identical:

  legacy   ot_qwen_tp_seq_w12 (byte-identical reference)
  async0   ot_qwen_tp_seq_async_w12 ASYNC_COLL=1, descriptor without the cut bit
  async1   the same RTL, cut bit set (cut-through)

legacy and async0 must also take the same cycles.  Schedules: O-like rounds
(96 words a round, rounds 16 cycles apart), down-like rounds (48 apart), the
region written in reverse order (no gain, must stay exact), and half-word lane
masks in random order with writes outside the region.  Faults: an overflowing
sum faults identically in every mode; a corrupted `last` faults all four
sequencers in cut-through.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

import numpy as np
import hdc_golden as G
from qwen_tp4_ar256_verilator_gate import vectors

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ["rtl/rom/ot_qwen_tp_seq_async_w12.sv", "rtl/rom/ot_qwen_tp_seq_w12.sv", "rtl/rom/ot_rom_oneshot_allreduce.sv",
           "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/test/tb_qwen_tp4_async_coll_vl.sv",
           "tools/hdc_golden.py", "tools/qwen_tp4_ar256_verilator_gate.py", "tools/qwen_tp4_async_coll_verilator_gate.py"]
VERILATOR = os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator")
NP, TMAX = 12, 1024


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def schedule(kind, rng):
    """[(t, port, word, mask)]: the engine's result writes, t from the core's start."""
    ev = []
    if kind in ("rounds_o", "rounds_down", "reverse"):
        gap = 16 if kind == "rounds_o" else 48
        words = list(range(256))
        if kind == "reverse":
            words = words[::-1]
        for r in range(3):                       # 3 rounds of 96 words (the last one partly past 4,096 elements)
            rw = words[96 * r:96 * (r + 1)]
            for i, w in enumerate(rw):            # 12 ports, 8 interleave slots
                ev.append((120 + gap * r + i // NP, i % NP, w, 0xFFFF))
    elif kind == "partial":
        halves = [(w, m) for w in range(256) for m in (0x00FF, 0xFF00)]
        order = rng.permutation(len(halves))
        for i, j in enumerate(order):
            w, m = halves[j]
            ev.append((60 + i // 3, i % 3, w, m))
        for i in range(40):                       # writes outside the region (other result words)
            ev.append((60 + i, 3 + i % 4, 300 + i, 0xFFFF))
    else:
        raise ValueError(kind)
    assert max(t for t, *_ in ev) < TMAX
    return ev


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--result", type=Path, required=True)
    ap.add_argument("--lat", type=int, default=339)
    ap.add_argument("--depth", type=int, default=256)
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--sb-pipe", type=int, choices=(0, 1, 2, 3, 4), default=0, help="SB_PIPE of the asynchronous sequencer")
    args = ap.parse_args()
    if args.result.exists():
        raise SystemExit("Refusing to overwrite an existing verdict")
    args.work.mkdir(parents=True, exist_ok=False)
    pins = {p: sha(ROOT / p) for p in SOURCES}
    result = {"schema": "opentallas.qwen-tp4-async-coll-verilator-gate.v1", "status": "fail", "source_sha256": pins,
              "simulator": subprocess.check_output([VERILATOR, "--version"], text=True).strip(),
              "design_point": {"tp": 4, "lanes": 16, "elements": 4096, "lat": args.lat, "depth": args.depth,
                               "me_ports_in_bench": NP, "sb_pipe": args.sb_pipe},
              "builds": {}, "cases": {},
              "claim_boundary": "Real sequencers (legacy and asynchronous), VM word ports, rank-order binary32 "
                                "collective and links under Verilator; stub core with scheduled ME result writes. "
                                "No layer/token claim; no SS/FF sign-off."}
    bins = {}
    try:
        for legacy in (1, 0):
            mdir = args.work / f"obj_legacy{legacy}"
            t0 = time.monotonic()
            p = subprocess.run([VERILATOR, "--binary", "--timing", "-O3", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED",
                                "-Wno-TIMESCALEMOD", "-Wno-PINMISSING", "-Wno-INITIALDLY", "-Wno-BLKSEQ",
                                "--top-module", "tb_qwen_tp4_async_coll_vl", f"-GDEPTH={args.depth}",
                                f"-GLAT={args.lat}", f"-GLEGACY={legacy}", f"-GSB_PIPE={args.sb_pipe}", f"-GNP={NP}", f"-GTMAX={TMAX}",
                                "--Mdir", str(mdir), "-j", "8", *(str(ROOT / s) for s in SOURCES[:5])],
                               capture_output=True, text=True)
            (args.work / f"build_legacy{legacy}.log").write_text(p.stdout + p.stderr)
            result["builds"][f"legacy{legacy}"] = {"returncode": p.returncode, "seconds": round(time.monotonic() - t0, 1)}
            if p.returncode:
                raise RuntimeError(f"verilator build LEGACY={legacy} failed: {p.stderr[-2000:]}")
            bins[legacy] = mdir / "Vtb_qwen_tp4_async_coll_vl"

        def run(name, legacy, vec, cut, vw=0, nwords=256, inject=0, expect_fault=0):
            p = subprocess.run([str(bins[legacy]), f"+VEC={vec}", f"+CUT={cut}", f"+VW={vw}", f"+NWORDS={nwords}",
                                f"+INJECT_LAST={inject}", f"+EXPECT_FAULT={expect_fault}"],
                               capture_output=True, text=True, timeout=3600)
            log = args.work / f"{name}.log"
            log.write_text(p.stdout + p.stderr)
            m = re.search(r"QWEN_ASYNCVL PASS .*cycles=(\d+) core_done=(-?\d+) first_send=(-?\d+) last_write=(-?\d+) "
                          r"words=(\d+) mismatches=(\d+) seq_fault=([01]+) coll_fault=([01]+) codes=([0-9a-f]+) "
                          r"first_err_word=(-?\d+) stalls=(\d+)", p.stdout)
            if p.returncode or not m:
                raise RuntimeError(f"{name}: no PASS verdict\n{p.stdout[-1500:]}{p.stderr[-1500:]}")
            writes = [l for l in p.stdout.splitlines() if l.startswith("W ")]
            case = {"legacy": legacy, "cut": cut, "vw": vw, "words": nwords, "cycles": int(m[1]),
                    "core_done_cycle": int(m[2]), "first_send_cycle": int(m[3]), "last_result_write": int(m[4]),
                    "mismatches": int(m[6]), "seq_fault": m[7], "coll_fault": m[8], "fault_codes": m[9],
                    "first_err_word": int(m[10]), "link_stalls": int(m[11]),
                    "writes_sha256": hashlib.sha256("\n".join(writes).encode()).hexdigest(), "log_sha256": sha(log)}
            result["cases"][name] = case
            return case

        def emit(path, array):
            path.write_text("".join("".join(f"{int(v):08x}" for v in row[::-1]) + "\n" for row in array))

        def make(tag, parts, sched_kind, seed):
            vec = args.work / f"v_{tag}"
            vec.mkdir()
            rng = np.random.default_rng(777 + seed)
            with np.errstate(over="ignore"):
                summ = G.fold(parts)
            for d in range(4):
                emit(vec / f"part_die{d}.hex", G.bits(parts[d]))
                emit(vec / f"stale_die{d}.hex", G.bits(rng.uniform(-9, 9, (256, 16)).astype(np.float32)))
            emit(vec / "sum.hex", G.bits(summ))
            sched = np.zeros(TMAX * NP, dtype=object)
            for t, port, word, mask in schedule(sched_kind, rng):
                assert sched[t * NP + port] == 0
                sched[t * NP + port] = (1 << 40) | (word << 16) | mask
            (vec / "sched.hex").write_text("".join(f"{int(x):011x}\n" for x in sched))
            return vec, summ

        def triple(tag, vec, **kw):
            a = run(f"{tag}_legacy", 1, vec, 0, **kw)
            b = run(f"{tag}_async0", 0, vec, 0, **kw)
            c = run(f"{tag}_async1", 0, vec, 1, **kw)
            if not (a["writes_sha256"] == b["writes_sha256"] == c["writes_sha256"]):
                raise RuntimeError(f"{tag}: result writes differ between legacy, async0 and cut-through")
            if a["cycles"] != b["cycles"]:
                raise RuntimeError(f"{tag}: async RTL without the cut bit is not cycle-identical to legacy")
            return a, b, c

        summary = {}
        for sched_kind in ("rounds_o", "rounds_down", "reverse", "partial"):
            for kind, seed in [("uniform", s) for s in range(args.seeds)] + [("adversarial", s) for s in range(args.seeds)]:
                tag = f"{sched_kind}_{kind}{seed}"
                parts = vectors(kind, np.random.default_rng(20261003 + seed))
                vec, summ = make(tag, parts, sched_kind, seed)
                assert np.isfinite(summ).all()
                a, b, c = triple(tag, vec)
                summary.setdefault(sched_kind, {})[f"{kind}{seed}"] = {
                    "legacy_cycles": a["cycles"], "cut_cycles": c["cycles"], "saved": a["cycles"] - c["cycles"],
                    "core_done": c["core_done_cycle"], "cut_first_send": c["first_send_cycle"],
                    "legacy_first_send": a["first_send_cycle"]}
        # a sub-region (legacy 128-word count at VW 32): only its words are tracked and sent
        vec, _ = make("region_vw32_n128", vectors("uniform", np.random.default_rng(20261100)), "rounds_o", 9)
        a, b, c = triple("region_vw32_n128", vec, vw=32, nwords=128)
        summary["region_vw32_n128"] = {"legacy_cycles": a["cycles"], "cut_cycles": c["cycles"],
                                       "saved": a["cycles"] - c["cycles"]}
        # faults
        vec, summ = make("overflow", vectors("overflow", np.random.default_rng(20261003)), "rounds_o", 0)
        assert not np.isfinite(summ).all()
        f = [run(f"overflow_{n}", lg, vec, ct, expect_fault=1) for n, lg, ct in
             (("legacy", 1, 0), ("async0", 0, 0), ("async1", 0, 1))]
        if len({(x["first_err_word"], x["fault_codes"]) for x in f}) != 1:
            raise RuntimeError("fault behaviour differs between modes")
        vec = args.work / "v_rounds_o_uniform0"
        run("bad_last_async1", 0, vec, 1, inject=1)
        run("bad_last_legacy", 1, vec, 0, inject=1)
        result["summary"] = summary
        result["source_stable"] = pins == {p: sha(ROOT / p) for p in SOURCES}
        gain = summary["rounds_o"]["uniform0"]["saved"]
        if not result["source_stable"] or gain <= 0:
            raise RuntimeError("source instability or no cycle gain")
        result["status"] = "pass"
    except Exception as exc:  # the verdict is recorded either way
        result["error"] = str(exc)
    args.result.parent.mkdir(parents=True, exist_ok=True)
    with args.result.open("x") as f:
        f.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "summary": result.get("summary"), "error": result.get("error")},
                     indent=1))
    if result["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
