#!/usr/bin/env python3
"""Exact bench of the HBM accelerator die's GPU-prefill KV-ingest master (physical/rom_host_ingest/rtl/hfd_host_ingest.sv
= ot_rom_host_ingest ROWS / RAW + ot_hbm_ingest_xlat), against the DS-V4.1 DECODE KV layout of the per-token write-back
ot_hbm_accel_dskv_wb, computed by the independent golden map of tools/hbm_accel_dskv_wb.py (sector_addr, owner_k; W19
TP-96: window ring replicated, compressed rows and index keys sharded by group, 8-group blocks over 96 dies).

A prompt of P positions on die DIE: the window ring of one layer (the last 128 positions, ROWS ring 128 pitch 17), the
compressed rows of two index-source slots (ratio 1 and ratio 2; the die's own groups in die-local row order, ROWS pitch 9)
and their index keys (packed 68 B back to back in whole 8-key blocks, the last block zero padded, RAW).  Records are the
storage formats (kv_ingest_ref encode_window / encode_ckv / encode_ikey: 528 / 288 / 68 B).  Every stack write request
(stack, PC, bank, row, column, 32 B) is compared with the golden set; host gaps and fabric stalls; a translator mutant
(window ring slot off by one) must FAIL.

    python3 tools/rtl_hbm_host_ingest_bench.py [--output PATH] [--work DIR]
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

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import kv_ingest_ref as R  # noqa: E402
import hbm_accel_dskv_wb as H  # noqa: E402  (the independent golden address map)

OUT = ROOT / "results/rtl/rom_host_ingest_20261008/hbm_ingest_bench.json"
RTL = [ROOT / p for p in ("rtl/lib/ot_reset_sync.sv", "rtl/link/ot_link_afifo.sv", "rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv",
                          "rtl/hdc/ingest/ot_hdc_kv_ingest.sv", "rtl/hdc/ingest/ot_rom_host_ingest.sv",
                          "rtl/hdc/ingest/ot_hbm_ingest_xlat.sv", "physical/rom_host_ingest/rtl/hfd_host_ingest.sv")]
TB = ROOT / "rtl/test/tb_hbm_host_ingest.sv"
RE = re.compile(r"HHING descs=(\d+) beats=(\d+)/(\d+) writes=(\d+) dones=(\d+)/(\d+) fault_words=(\d+) fault=(\d+) "
                r"ck_cycles=(\d+) timeout=(\d+) landed=(\d+) stale=(\d+) fence_stall=(\d+) slot_dones=(\d+)")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def case(rng, die=5, P=4652, win_layer=20, slots=((3, False), (1, True))):
    descs, beats, nb, exp, cnt = [], [], [], {}, []

    def add(d, payload):
        b = R.beats_of(payload)
        cnt.append(len(exp))
        descs.append(d)
        beats.extend(b)
        nb.append(len(b))

    def put(key, data):
        assert key not in exp or exp[key] == data
        exp[key] = data

    # window ring of one layer: the last 128 positions
    recs = [R.encode_window((rng.standard_normal(512) * np.exp2(rng.integers(-10, 10))).astype(np.float32))
            for _ in range(128)]
    first = P - 128
    add(R.desc(R.M_ROWS, fence=1, tag=1, a0=(0 << 30) | (win_layer << 24), a1=0, a2=17, a3=128, n0=first, n1=528, n2=128,
               nb=len(R.beats_of(b"".join(recs)))), b"".join(recs))
    for i, rec in enumerate(recs):
        w = (first + i) % 128
        data = rec + bytes(16)
        for t in range(17):
            put((w >> 5, w & 31, *H.sector_addr(0, win_layer, t)), data[32 * t:32 * t + 32])
    meta = dict(die=die, positions=P, window_layer=win_layer, slots=[])
    tag = 2
    for slot, r2 in slots:
        G = P >> 1 if r2 else P
        own = []
        for n in range(G):
            o, k, nn = H.owner_k(n << 1 if r2 else n, r2)
            assert nn == n
            if o == die:
                own.append((k, n))
        assert [k for k, _ in own] == list(range(len(own))), "die-local rows are contiguous from 0"
        ckv = [R.encode_ckv((rng.standard_normal(512) * np.exp2(rng.integers(-12, 8))).astype(np.float32)) for _ in own]
        keys = [R.encode_ikey((rng.standard_normal(128) * np.exp2(rng.integers(-12, 12))).astype(np.float32)) for _ in own]
        add(R.desc(R.M_ROWS, fence=1, tag=tag, a0=(1 << 30) | (slot << 24), a1=0, a2=9, a3=0, n0=0, n1=288, n2=len(own),
                   nb=len(R.beats_of(b"".join(ckv)))), b"".join(ckv))
        tag += 1
        for k, rec in enumerate(ckv):
            for t in range(9):
                S = 9 * k + t
                put((S % 128 >> 5, S % 32, *H.sector_addr(1, slot, S >> 7)), rec[32 * t:32 * t + 32])
        nblk = -(-len(keys) // H.KEY_BLOCK)
        kb = b"".join(keys)
        kb += bytes(nblk * 17 * 32 - len(kb))
        add(R.desc(R.M_RAW, fence=1, tag=tag, a0=(2 << 30) | (slot << 24), n0=17 * nblk, nb=len(R.beats_of(kb))), kb)
        tag += 1
        for S in range(17 * nblk):
            put((S % 128 >> 5, S % 32, *H.sector_addr(2, slot, S >> 7)), kb[32 * S:32 * S + 32])
        meta["slots"].append(dict(slot=slot, ratio=2 if r2 else 1, groups=G, owned_rows=len(own), key_blocks=nblk,
                                  partial_last_block=len(keys) % 8 != 0))
    meta["expected_sectors"] = len(exp)
    # cumulative sectors once descriptor i is complete (descriptor i's sectors are added after add(i) is called)
    cum = cnt[1:] + [len(exp)]
    return dict(descs=descs, beats=beats, nb=nb, exp=exp, cum=cum, meta=meta)


def build(work: Path, tag, nd, np_, srcs, fence=1):
    exe = work / f"hh_{tag}.vvp"
    subprocess.run(["iverilog", "-g2012", *__import__("os").environ.get("OT_HING_DEFS", "").split(), "-o", str(exe), "-s", "tb_hbm_host_ingest", f"-Ptb_hbm_host_ingest.ND={nd}",
                    f"-Ptb_hbm_host_ingest.FENCE={fence}",
                    f"-Ptb_hbm_host_ingest.NP={np_}", *map(str, srcs), str(TB)], check=True, capture_output=True, text=True)
    return exe


def write_case(d: Path, c):
    d.mkdir(parents=True, exist_ok=True)
    (d / "desc.mem").write_text("".join(f"{x:064x}\n" for x in c["descs"]))
    (d / "pay.mem").write_text("".join(f"{x:0128x}\n" for x in c["beats"]))
    (d / "nb.mem").write_text("".join(f"{x:08x}\n" for x in c["nb"]))
    (d / "cum.mem").write_text("".join(f"{x:08x}\n" for x in c["cum"]))


def run(exe, d, c, **pa):
    t = time.time()
    p = subprocess.run(["vvp", "-n", str(exe), f"+ND={len(c['descs'])}", f"+NP={len(c['beats'])}",
                        *(f"+{k}={v}" for k, v in pa.items())], cwd=d, capture_output=True, text=True, timeout=7200)
    m = RE.search(p.stdout)
    if not m:
        return {"pass": False, "stdout": p.stdout[-1200:], "stderr": p.stderr[-600:]}
    descs, beats, npay, writes, dones, nf, fw, fault, cyc, tmo, landed, stale, fstall, sdones = map(int, m.groups())
    got, dup_conflict = {}, 0
    for ln in (d / "wq.txt").read_text().splitlines():
        s, pc, bk, rw, cl, hx = ln.split()
        key = (int(s), int(pc), int(bk), int(rw), int(cl))
        data = int(hx, 16).to_bytes(32, "little")
        if key in got and got[key] != data:
            dup_conflict += 1
        got[key] = data
    exp = c["exp"]
    missing = sum(1 for k in exp if k not in got)
    extra = sum(1 for k in got if k not in exp)
    wrong = sum(1 for k in exp if k in got and got[k] != exp[k])
    ok = (missing == extra == wrong == dup_conflict == 0 and writes == len(exp) and dones == nf and fw == 0
          and fault == 0 and tmo == 0 and beats == npay and stale == 0 and sdones == nf and landed == writes)
    return {"pass": ok, "writes": writes, "expected": len(exp), "missing": missing, "extra": extra, "wrong_data": wrong,
            "duplicate_conflicts": dup_conflict, "fenced_done": dones, "fenced": nf, "fault_words": fw, "fault": fault,
            "ck_cycles": cyc, "timeout": bool(tmo), "landed": landed, "stale_slot_reads": stale,
            "fence_stall_ck_cycles": fstall, "slot_dones": sdones, "plusargs": pa, "wall_s": round(time.time() - t, 1)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--output", type=Path, default=OUT)
    ap.add_argument("--work", type=Path, default=Path("/tmp/hhing"))
    args = ap.parse_args()
    args.work.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20261008)
    c = case(rng)
    exe = build(args.work, "dut", len(c["descs"]), len(c["beats"]), RTL)
    d = args.work / "case"
    write_case(d, c)
    rec = {"schema": "opentallas.rtl-hbm-host-ingest.v1", "tool": "tools/rtl_hbm_host_ingest_bench.py",
           "dut": "physical/rom_host_ingest/rtl/hfd_host_ingest.sv", "golden": "tools/hbm_accel_dskv_wb.py (sector_addr, owner_k)",
           "meta": c["meta"], "runs": [], "mutations": {}}
    ok = True
    for pa in ({}, {"WQSTALL": 50, "SEED": 3}, {"WQSTALL": 80, "SEED": 7},
               {"ACKDLY": 3000, "ACKJ": 2000, "SEED": 11}, {"ACKDLY": 800, "ACKJ": 400, "WQSTALL": 30, "SEED": 13}):
        r = run(exe, d, c, **pa)
        rec["runs"].append(r)
        ok &= r["pass"]
        print("run", pa, {k: r.get(k) for k in ("pass", "writes", "expected", "missing", "wrong_data", "stale_slot_reads",
                                                 "fence_stall_ck_cycles", "ck_cycles")},
              flush=True)
    # mutant: window ring slot off by one in the translator
    src = (ROOT / "rtl/hdc/ingest/ot_hbm_ingest_xlat.sv").read_text()
    mut = src.replace("wire [6:0]  pcg = (k1 == 2'd0) ? w1[6:0] : S1[6:0];", "wire [6:0]  pcg = (k1 == 2'd0) ? w1[6:0] + 7'd1 : S1[6:0];")
    # sys-takeover 2026-10-10: the same mutation on the XPIPE path (stage b window PC), when present
    mut = mut.replace("wire [6:0]  pca  = (ka == 2'd0) ? wa[6:0] : Sa[6:0];", "wire [6:0]  pca  = (ka == 2'd0) ? wa[6:0] + 7'd1 : Sa[6:0];")
    assert mut != src
    mp = args.work / "xlat_mut.sv"
    mp.write_text(mut)
    exe_m = build(args.work, "mut", len(c["descs"]), len(c["beats"]),
                  [p if p.name != "ot_hbm_ingest_xlat.sv" else mp for p in RTL])
    r = run(exe_m, d, c)
    rec["mutations"]["window_ring_slot_plus_one"] = dict(detected=not r["pass"], wrong_or_missing=r.get("missing", 0) + r.get("wrong_data", 0))
    ok &= not r["pass"]
    print("mutant window_ring_slot_plus_one", "detected" if not r["pass"] else "NOT DETECTED", flush=True)
    # fence mutant: completions released without waiting for the ACKs; with delayed ACKs decode reads stale slots
    exe_f = build(args.work, "nofence", len(c["descs"]), len(c["beats"]), RTL, fence=0)
    r = run(exe_f, d, c, ACKDLY=3000, ACKJ=2000, SEED=11)
    det = not r["pass"] and r.get("stale_slot_reads", 0) > 0
    rec["mutations"]["completion_fence_removed"] = dict(detected=det, stale_slot_reads=r.get("stale_slot_reads"),
                                                        fence_stall_ck_cycles=r.get("fence_stall_ck_cycles"))
    ok &= det
    print("mutant completion_fence_removed", "detected" if det else "NOT DETECTED", r.get("stale_slot_reads"), flush=True)
    rec["pass"] = bool(ok)
    rec["input_sha256"] = {str(p.relative_to(ROOT)): sha(p) for p in RTL + [TB, Path(__file__), ROOT / "tools/hbm_accel_dskv_wb.py",
                                                                            ROOT / "tools/kv_ingest_ref.py"]}
    rec["git_head"] = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    print("pass:", rec["pass"], "->", args.output)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
