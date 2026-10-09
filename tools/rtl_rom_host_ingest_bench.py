#!/usr/bin/env python3
"""End-to-end exact bench of the ROM dies' host block (rtl/hdc/ingest/ot_rom_host_ingest.sv).

host link stream (clk_h) -> CDC -> KV ingest engine (clk_i = ck/2) -> CDC -> die fabric (ck) -> HBM image, compared
sector by sector with the golden image of tools/kv_ingest_ref.py (the decode core's own layout functions), on the
cases of tools/rtl_hdc_kv_ingest_campaign.py plus the per-die Qwen3-8B TP4 geometry (2 KV heads x 128).  Mutants
must FAIL: a payload bit flipped in the CDC path (MUT 1), completion tags off by one (MUT 2), and a QKV descriptor
sent to a QKV_EN 0 (V4.1 / boot) block must fail closed (fault word, nothing written).

    python3 tools/rtl_rom_host_ingest_bench.py [--output PATH] [--work DIR] [--quick]
Icarus Verilog (three free-running clocks); keep --work short (Icarus truncates long $readmemh paths).
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
import rtl_hdc_kv_ingest_campaign as C  # noqa: E402
import kv_ingest_ref as R  # noqa: E402

OUT = ROOT / "results/rtl/rom_host_ingest_20261008/bench.json"
RTL = [ROOT / p for p in ("rtl/lib/ot_reset_sync.sv", "rtl/link/ot_link_afifo.sv", "rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv",
                          "rtl/hdc/ingest/ot_hdc_kv_ingest.sv", "rtl/hdc/ingest/ot_rom_host_ingest.sv")]
TB = ROOT / "rtl/test/tb_rom_host_ingest.sv"
RE = re.compile(r"HING descs=(\d+) beats=(\d+)/(\d+) sectors=(\d+) reads=(\d+) errors=(\d+) oob=(\d+) "
                r"dones=(\d+)/(\d+) tag_err=(\d+) fault_words=(\d+) fault=(\d+) ck_cycles=(\d+) timeout=(\d+) share=(\d+) first_o=(-?\d+) last_o=(\d+)")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def qkv_nb(ref, ks, vs, fmt, t0=0):
    """Payload beats of each descriptor of C.qwen_blocks (same walk)."""
    nb = []
    T = ks[0].shape[0]
    for L in range(ref.L):
        for j in range(t0 // 16, -(-T // 16)):
            lo, hi = max(t0, 16 * j) - 16 * j, min(T, 16 * j + 16) - 16 * j
            nb.append(len(R.beats_of(R.qkv_payload(ks[L][16 * j + lo:16 * j + hi], vs[L][16 * j + lo:16 * j + hi], fmt))))
    return nb


def stream_nb(descs):
    return [(d >> 240) & 0xFFFF for d in descs]


def case_die_geom(rng, layers=2, T=64, fmt=R.FMT_BF16):
    """Qwen3-8B per-die geometry under TP4: 2 KV heads x head_dim 128, FP8 edge values on a BF16 wire."""
    ref = R.QwenKV(layers, 2, 128, T)
    ks = [C.edge_values(rng, T * 2 * 128).reshape(T, 2, 128) for _ in range(layers)]
    vs = [C.edge_values(rng, T * 2 * 128).reshape(T, 2, 128) for _ in range(layers)]
    descs, beats = C.qwen_blocks(ref, ks, vs, fmt)
    exp = ref.image([R.fp8_code(C.wire_values(k, fmt)) for k in ks], [R.fp8_code(C.wire_values(v, fmt)) for v in vs])
    return dict(descs=descs, beats=beats, nb=qkv_nb(ref, ks, vs, fmt), init=np.zeros_like(exp), exp=exp, hd=128, kvh=2,
                meta=dict(layers=layers, positions=T, kv_heads=2, head_dim=128, wire="bf16"))


def cases(quick):
    rng = np.random.default_rng(20261008)
    cap = C.qwen_capture()
    model, prompt, cache, ks, vs = cap
    cfg = model.cfg
    ref = R.QwenKV(cfg["num_hidden_layers"], cfg["num_key_value_heads"], cfg["head_dim"], 64)
    out = {}
    for name, fmt in (("qwen_reduced_fp32", R.FMT_FP32), ("qwen_reduced_bf16", R.FMT_BF16)):
        c = C.case_qwen_reduced(fmt, cap)
        c["nb"] = qkv_nb(ref, ks, vs, fmt)
        out[name] = dict(c, qkv=1)
    c = C.case_qwen_append(cap)
    c["nb"] = qkv_nb(ref, ks, vs, R.FMT_FP32, t0=40)
    out["qwen_append_rmw"] = dict(c, qkv=1)
    out["qwen_die_geom_bf16"] = dict(case_die_geom(rng), qkv=1)
    for name, c in (("v41_ckv", C.case_rows(rng, "ckv", 400 if quick else 1000, first=48)),
                    ("v41_win", C.case_rows(rng, "win", 200, first=0)),
                    ("v41_ikey", C.case_ikey(rng, 1024 if quick else 4096)),
                    ("raw_boot", C.case_raw(rng, 300))):
        c["nb"] = stream_nb(c["descs"])
        out[name] = dict(c, qkv=0, hd=16, kvh=1)
    return out


def build(work: Path, tag, memw, nd, np_, hd, kvh, qkv, mut=0):
    exe = work / f"sim_{tag}.vvp"
    cmd = ["iverilog", "-g2012", "-o", str(exe), "-s", "tb_rom_host_ingest",
           *(f"-Ptb_rom_host_ingest.{k}={v}" for k, v in dict(MEMW=memw, ND=nd, NP=np_, HDMAX=hd, KVHMAX=kvh,
                                                                  QKV_EN=qkv, MUT=mut).items()),
           *map(str, RTL), str(TB)]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return exe


def final_image(d, nbytes):
    """Icarus $writememh output (it adds // address comments) -> image bytes."""
    words = []
    for ln in (d / "final.mem").read_text().splitlines():
        ln = ln.split("//")[0].strip()
        if ln and not ln.startswith("@"):
            words += [int(x, 16) for x in ln.split()]
    b = b"".join(w.to_bytes(32, "little") for w in words)
    return np.frombuffer(b[:nbytes], dtype=np.uint8)


def write_case(d: Path, case, memw):
    C.write_case(d, case, memw)
    (d / "nb.mem").write_text("".join(f"{x:08x}\n" for x in case["nb"]))


def run(exe, d, nd, np_, **pa):
    t = time.time()
    p = subprocess.run(["vvp", "-n", str(exe), f"+ND={nd}", f"+NP={np_}", *(f"+{k}={v}" for k, v in pa.items())],
                       cwd=d, capture_output=True, text=True, timeout=14400)
    m = RE.search(p.stdout)
    if not m:
        return {"pass": False, "stdout": p.stdout[-1500:], "stderr": p.stderr[-800:]}
    (descs, beats, npay, secs, reads, err, oob, dones, nfence, tag_err, fw, fault, cyc, tmo, shr, f0, f1) = map(int, m.groups())
    span = max(1, f1 - f0 + 1)
    ok = (err == 0 and oob == 0 and tmo == 0 and beats == npay and descs == nd and dones == nfence and tag_err == 0
          and fw == 0 and fault == 0)
    return {"pass": ok, "errors": err, "oob": oob, "timeout": bool(tmo), "descriptors": descs, "beats": beats,
            "sectors_written": secs, "rmw_reads": reads, "fenced_done": dones, "fenced": nfence, "tag_errors": tag_err,
            "fault_words": fw, "fault": fault, "ck_cycles": cyc, "share_seen_x256": shr,
            "fabric_active_ck_cycles": span, "sectors_per_ck": round((secs + reads) / span, 4), "plusargs": pa, "wall_s": round(time.time() - t, 1),
            "first_mismatch": [ln for ln in p.stdout.splitlines() if ln.startswith("MISMATCH")][:2]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--output", type=Path, default=OUT)
    ap.add_argument("--work", type=Path, default=Path("/tmp/hing"))
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    work = args.work
    work.mkdir(parents=True, exist_ok=True)
    cs = cases(args.quick)
    rec = {"schema": "opentallas.rtl-rom-host-ingest.v1", "tool": "tools/rtl_rom_host_ingest_bench.py",
           "dut": "rtl/hdc/ingest/ot_rom_host_ingest.sv", "clocks_ps": dict(clk_h=1000, clk_i=1666, ck=833),
           "cases": {}, "traffic": {}, "mutations": {}}
    exes = {}
    ok = True

    def exe_for(case, mut=0, qkv=None):
        memw = C.pow2(max(case["exp"].size // 32 + 1, 1024 + 64))
        q = case["qkv"] if qkv is None else qkv
        key = (memw, C.pow2(len(case["descs"])), C.pow2(len(case["beats"])), case["hd"], case["kvh"], q, mut)
        if key not in exes:
            exes[key] = build(work, len(exes), *key)
        return exes[key], memw

    for name, case in cs.items():
        exe, memw = exe_for(case)
        d = work / name
        write_case(d, case, memw)
        r = run(exe, d, len(case["descs"]), len(case["beats"]))
        r.update(case["meta"])
        if r["pass"] and name.startswith("qwen_reduced"):
            r["decode_from_ingested_image"] = C.isa_decode_from_image(case, final_image(d, case["exp"].size))
        rec["cases"][name] = r
        ok &= r["pass"]
        print(name, {k: r.get(k) for k in ("pass", "errors", "sectors_written", "ck_cycles", "wall_s")}, flush=True)
        if not args.quick and name in ("qwen_append_rmw", "qwen_die_geom_bf16", "v41_ikey"):
            rows = []
            for share, hgap, mst, seed in ((64, 0, 0, 2), (64, 30, 30, 3), (16, 10, 50, 4)):
                rr = run(exe, d, len(case["descs"]), len(case["beats"]), SHARE=share, HGAP=hgap, MSTALL=mst, SEED=seed)
                rr.update(share_x256=share, host_gap_pct=hgap, fabric_stall_pct=mst)
                rows.append(rr)
                ok &= rr["pass"]
                print("  traffic", name, share, hgap, mst, rr["pass"], rr.get("ck_cycles"), flush=True)
            rec["traffic"][name] = rows
    # mutants: each must FAIL
    base = cs["qwen_reduced_fp32"]
    for mname, mut in (("payload_bit_flip_in_cdc", 1), ("done_tag_plus_one", 2)):
        exe, memw = exe_for(base, mut=mut)
        d = work / ("mut_" + mname)
        write_case(d, base, memw)
        r = run(exe, d, len(base["descs"]), len(base["beats"]), MAXCYC=400000)
        det = not r.get("pass", False)
        rec["mutations"][mname] = dict(detected=det, errors=r.get("errors"), tag_errors=r.get("tag_errors"))
        ok &= det
        print("mutant", mname, "detected" if det else "NOT DETECTED", flush=True)
    # fail closed: a QKV descriptor on a QKV_EN 0 block
    exe, memw = exe_for(base, qkv=0)
    d = work / "failclosed_qkv_on_v41"
    write_case(d, base, memw)
    r = run(exe, d, len(base["descs"]), len(base["beats"]), MAXCYC=400000)
    fc = (not r.get("pass", False)) and r.get("fault_words") == 1 and r.get("sectors_written") == 0
    rec["mutations"]["qkv_descriptor_on_qkv_en0_fails_closed"] = dict(
        detected=fc, fault_words=r.get("fault_words"), sectors_written=r.get("sectors_written"))
    ok &= fc
    print("fail-closed qkv on QKV_EN 0:", fc, flush=True)
    rec["pass"] = bool(ok)
    rec["input_sha256"] = {str(p.relative_to(ROOT)): sha(p) for p in RTL + [TB, Path(__file__), ROOT / "tools/kv_ingest_ref.py",
                                                                            ROOT / "tools/rtl_hdc_kv_ingest_campaign.py"]}
    rec["git_head"] = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    print("pass:", rec["pass"], "->", args.output)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
