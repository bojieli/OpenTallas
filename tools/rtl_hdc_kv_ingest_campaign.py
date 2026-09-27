#!/usr/bin/env python3
"""RTL campaign of the KV ingest engine (rtl/hdc/ingest/ot_hdc_kv_ingest.sv) and its HBM port
arbiter (ot_hdc_ingest_arb.sv), against the spec (docs/ARCH_SPEC_PREFILL.md section 6).

Bit-exact cases (the whole HBM image compared, sector by sector, with the golden's image from
tools/kv_ingest_ref.py -- itself derived from the decode core's own layout functions):

* qwen_reduced_{fp32,bf16,fp8}: the reduced Qwen3 vehicle's REAL prefill KV (every K/V row the golden
  computes for the 63-position context, captured before its FP8 rounding), sent block by block in the
  serving engine's page order and format.  The FP32 case must reproduce the image of the golden's own
  FP8 cache exactly; the decoded image then drives the ISA machine for the next token, which must be
  bit-exact with the golden decode on its own cache (the correctness contract: decode is bit-exact
  given the ingested KV).  The BF16 case measures what BF16-on-the-wire does to the FP8 values (double
  rounding) and whether the next token still matches.
* qwen_append_rmw: a turn appended mid-tile (positions 40..63 onto a resident 0..39), read-modify-write
  of the open tile.
* qwen_shipped_geom: Qwen3-8B geometry (8 KV heads x 128), 2 layers, 256 positions, random values with
  the FP8 edge cases (saturation, ties, subnormals, signed zeros), BF16 on the wire -- the performance
  row (beats and sectors per cycle).
* v41_ckv / v41_win / v41_ikey: V4.1 compressed rows (288 B, pitch 9), window rows (528 B, pitch 17,
  ring 128) and index keys (68-B records encoded from vectors by the release's fp4_act_quant, whose
  decode is checked equal to hdc_golden_v41.qdq_fp4_e8m0), split over a 4-die tensor group and 4
  stacks.
* raw.
Flow control: the same cases under decode traffic (the arbiter's share, bursts, memory stalls); the
record keeps decode sectors granted vs requested and the ingest rate.  Mutations (a wrong die, swapped
K/V bases, t_lo off by one) must fail.

    python3 tools/rtl_hdc_kv_ingest_campaign.py [--output PATH] [--quick]
    python3 tools/rtl_hdc_kv_ingest_campaign.py --cross-superblock-only --output PATH
Heavy (Verilator builds): run through /tmp/claude-1000/remote_gate.sh.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
os.environ.setdefault("HDC_KV_FMT", "fp8")
import kv_ingest_ref as R  # noqa: E402

OUT = ROOT / "results/rtl/hdc_kv_ingest_campaign.json"
RTL = [ROOT / "rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv", ROOT / "rtl/hdc/ingest/ot_hdc_kv_ingest.sv",
       ROOT / "rtl/hdc/ingest/ot_hdc_ingest_arb.sv"]
TB = ROOT / "rtl/test/tb_hdc_kv_ingest.sv"
HARNESS = ROOT / "rtl/test/hdc_v41_tb_harness.cpp"
TOOLS = [ROOT / "tools/kv_ingest_ref.py", Path(__file__)]
VL = ("--cc", "--exe", "--build", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKSEQ",
      "-Wno-MULTIDRIVEN", "--x-assign", "0", "--x-initial", "0")
RE_ING = re.compile(r"ING descs=(\d+) beats=(\d+)/(\d+) sectors=(\d+) errors=(\d+) oob=(\d+) dones=(\d+) "
                    r"cycles=(\d+) first=(-?\d+) last=(\d+) dec_req=(\d+) dec_grant=(\d+) ing_grant=(\d+) "
                    r"dec_wait=(\d+) timeout=(\d+)")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# -- cases ------------------------------------------------------------------------------
def qwen_capture():
    """The reduced Qwen3 vehicle's prefill: FP32 K/V rows before the cache's FP8 rounding."""
    import hdc_golden as G
    import hdc_program as P
    rec = []
    orig = G.kv_round

    def spy(x):
        rec.append(np.array(x, dtype=np.float32))
        return orig(x)
    G.kv_round = spy
    try:
        model, prompt, expected, cache = P.golden_state(64)
    finally:
        G.kv_round = orig
    L = model.layers
    T = len(prompt) - 1
    ks = [np.stack([rec[2 * (p * L + l)] for p in range(T)]) for l in range(L)]
    vs = [np.stack([rec[2 * (p * L + l) + 1] for p in range(T)]) for l in range(L)]
    return model, prompt, cache, ks, vs


def qwen_blocks(ref, ks, vs, fmt, t0=0, rmw=False):
    """Descriptors and payload beats for positions t0 .. T-1 of every layer."""
    descs, beats = [], []
    T = ks[0].shape[0]
    tag = 0
    for L in range(ref.L):
        for j in range(t0 // 16, -(-T // 16)):
            lo, hi = max(t0, 16 * j) - 16 * j, min(T, 16 * j + 16) - 16 * j
            k = ks[L][16 * j + lo:16 * j + hi]
            v = vs[L][16 * j + lo:16 * j + hi]
            descs.append(ref.block_desc(L, j, lo, hi, fmt, rmw=int(rmw and lo > 0), fence=1, tag=tag & 255))
            beats += R.beats_of(R.qkv_payload(k, v, fmt))
            tag += 1
    return descs, beats


def wire_values(x, fmt):
    import hdc_golden as G
    if fmt == R.FMT_FP32:
        return G.to_fp8(x)
    if fmt == R.FMT_BF16:
        return G.to_fp8(G.to_bf16(x))
    return x


def case_qwen_reduced(fmt, cap):
    import hdc_golden as G
    model, prompt, cache, ks, vs = cap
    c = model.cfg
    ref = R.QwenKV(c["num_hidden_layers"], c["num_key_value_heads"], c["head_dim"], 64)
    send_k = ks if fmt != R.FMT_FP8 else [G.to_fp8(k) for k in ks]
    send_v = vs if fmt != R.FMT_FP8 else [G.to_fp8(v) for v in vs]
    descs, beats = qwen_blocks(ref, send_k, send_v, fmt)
    ck = [R.fp8_code(wire_values(k, fmt)) for k in send_k]
    cv = [R.fp8_code(wire_values(v, fmt)) for v in send_v]
    exp = ref.image(ck, cv)
    # the golden's own FP8 cache as the decode core holds it
    gk = [R.fp8_code(np.stack([kv[0] for kv in cache[L]])) for L in range(ref.L)]
    gv = [R.fp8_code(np.stack([kv[1] for kv in cache[L]])) for L in range(ref.L)]
    own = ref.image(gk, gv)
    meta = dict(elements=int(2 * sum(k.size for k in ks)),
                elements_differing_from_golden_cache=int(np.count_nonzero(exp != own)),
                image_equals_golden_cache=bool(np.array_equal(exp, own)))
    return dict(descs=descs, beats=beats, init=np.zeros_like(exp), exp=exp, hd=16, kvh=2, meta=meta,
                qwen=dict(ref=ref, cap=cap))


def case_qwen_append(cap):
    import hdc_golden as G
    model, prompt, cache, ks, vs = cap
    c = model.cfg
    ref = R.QwenKV(c["num_hidden_layers"], c["num_key_value_heads"], c["head_dim"], 64)
    t0 = 40
    ck = [R.fp8_code(G.to_fp8(k)) for k in ks]
    cv = [R.fp8_code(G.to_fp8(v)) for v in vs]
    init = ref.image([k[:t0] for k in ck], [v[:t0] for v in cv])
    exp = ref.image(ck, cv)
    descs, beats = qwen_blocks(ref, ks, vs, R.FMT_FP32, t0=t0, rmw=True)
    return dict(descs=descs, beats=beats, init=init, exp=exp, hd=16, kvh=2,
                meta=dict(resident_positions=t0, appended_positions=int(ks[0].shape[0] - t0),
                          open_tile_rmw=True), qwen=dict(ref=ref, cap=cap))


def edge_values(rng, n):
    base = rng.standard_normal(n).astype(np.float32) * np.float32(4.0) ** rng.integers(-6, 5, n).astype(np.float32)
    sp = np.float32([0.0, -0.0, 448, -448, 464, 480, 500, 1e6, -1e30, 2 ** -6, 2 ** -9, 2 ** -10, 3 * 2 ** -11,
                     1.0625, 1.1875, 2 ** -7 * 1.0625, -2 ** -8, 1e-30, 239.99])
    base[:len(sp)] = sp
    rng.shuffle(base)
    return base


def case_shipped(rng, layers=2, T=256, fmt=R.FMT_BF16):
    import hdc_golden as G
    ref = R.QwenKV(layers, 8, 128, T)
    ks = [edge_values(rng, T * 8 * 128).reshape(T, 8, 128) for _ in range(layers)]
    vs = [edge_values(rng, T * 8 * 128).reshape(T, 8, 128) for _ in range(layers)]
    descs, beats = qwen_blocks(ref, ks, vs, fmt)
    exp = ref.image([R.fp8_code(wire_values(k, fmt)) for k in ks], [R.fp8_code(wire_values(v, fmt)) for v in vs])
    return dict(descs=descs, beats=beats, init=np.zeros_like(exp), exp=exp, hd=128, kvh=8,
                meta=dict(layers=layers, positions=T, kv_heads=8, head_dim=128,
                          payload_bytes=int(len(beats) * 64), fp8_bytes=int(exp.size)))


def case_rows(rng, kind, nrows, first=32, ndie=4, die=1, ns=4):
    rb, pitch, ring = (288, 9, 0) if kind == "ckv" else (528, 17, 128)
    extra = {}
    if kind == "ckv":
        # real records: the release's fp4_act_quant with a saturating E4M3 scale (R-P5); a quarter of the rows
        # above |x| = 2,688, where the scale saturates at 448 and the codes clamp
        import hdc_golden as G
        import hdc_golden_v41 as G4
        xs = [(rng.standard_normal(512) * np.exp2(rng.integers(-12, 16 if i % 4 == 0 else 6))).astype(np.float32)
              for i in range(nrows)]
        rows = [R.encode_ckv(x) for x in xs]
        extra = dict(record_decode_equals_golden_qdq_fp4_e4m3=all(
            np.array_equal(G.bits(R.decode_ckv(r)), G.bits(G4.qdq_fp4_e4m3(x))) for r, x in zip(rows, xs)),
            rows_above_2688=int(sum(np.max(np.abs(x)) > 2688 for x in xs)))
    elif kind == "win":
        import hdc_golden as G
        import hdc_golden_v41 as G4
        xs = [(rng.standard_normal(512) * np.exp2(rng.integers(-12, 12))).astype(np.float32) for _ in range(nrows)]
        rows = [R.encode_window(x) for x in xs]
        extra = dict(record_decode_equals_golden_qdq_fp8=all(
            np.array_equal(G.bits(R.decode_window(r)), G.bits(G4.qdq_fp8(x))) for r, x in zip(rows, xs)))
    else:
        rows = [rng.integers(0, 256, rb, dtype=np.uint8).tobytes() for _ in range(nrows)]
    base, stride = 64, 8192
    nsec = base + ns * stride if not ring else base + ring * pitch + 64
    exp = R.rows_image(nsec, rows, first, rb, pitch, base, stride, ndie if not ring else 1, die if not ring else 0,
                       ns, ring)
    lnd, lns = int(np.log2(ndie)), int(np.log2(ns))
    beats = R.beats_of(b"".join(rows))
    d = R.desc(R.M_ROWS, fence=1, tag=7, a0=base, a1=stride, a2=pitch, a3=ring, n0=first, n1=rb, n2=nrows,
               n4=lnd if not ring else 0, n5=die if not ring else 0, n6=lns if not ring else 0, nb=len(beats))
    return dict(descs=[d], beats=beats, init=np.zeros_like(exp), exp=exp, hd=16, kvh=2,
                meta=dict(kind=kind, rows=nrows, row_bytes=rb, pitch_sectors=pitch, ring=ring, ndie=ndie, die=die,
                          stacks=ns, **extra))


def case_ikey(rng, nkeys, first=0, ndie=4, die=2, ns=4):
    # The ingest descriptor emits scale sectors only after each complete
    # 16-key group; the sender pads a short final group before encoding.
    assert first % 16 == 0 and nkeys % 16 == 0
    import hdc_golden as G
    import hdc_golden_v41 as G4
    xs = [(rng.standard_normal(128) * np.exp2(rng.integers(-12, 12))).astype(np.float32) for _ in range(nkeys)]
    recs = [R.encode_ikey(x) for x in xs]
    lossless = all(np.array_equal(G.bits(R.decode_ikey(r)), G.bits(G4.qdq_fp4_e8m0(x))) for r, x in zip(recs, xs))
    base, stride = 0, 4 * 17 * 128
    exp = R.ikey_image(ns * stride, recs, first, base, stride, ndie, die, ns)
    beats = R.beats_of(b"".join(recs))
    d = R.desc(R.M_IKEY, fence=1, tag=9, a0=base, a1=stride, n0=first, n2=nkeys, n4=int(np.log2(ndie)), n5=die,
               n6=int(np.log2(ns)), nb=len(beats))
    return dict(descs=[d], beats=beats, init=np.zeros_like(exp), exp=exp, hd=16, kvh=2,
                meta=dict(keys=nkeys, first_key=first, record_bytes=68, ndie=ndie, die=die, stacks=ns,
                          record_decode_equals_golden_qdq_fp4_e8m0=bool(lossless)))


def case_raw(rng, n=300):
    data = rng.integers(0, 256, n * 32, dtype=np.uint8)
    exp = np.zeros((n + 100) * 32, dtype=np.uint8)
    exp[50 * 32:(50 + n) * 32] = data
    beats = R.beats_of(data.tobytes())
    d = R.desc(R.M_RAW, fence=1, tag=3, a0=50, n0=n, nb=len(beats))
    return dict(descs=[d], beats=beats, init=np.zeros_like(exp), exp=exp, hd=16, kvh=2, meta=dict(sectors=n))


# -- running ----------------------------------------------------------------------------
def build(obj: Path, memw, nd, np_, hd, kvh):
    subprocess.run(["verilator", *VL, "--top-module", "tb_hdc_kv_ingest", "-Mdir", str(obj),
                    f"-GMEMW={memw}", f"-GND={nd}", f"-GNP={np_}", f"-GHDMAX={hd}", f"-GKVHMAX={kvh}",
                    "-CFLAGS", "-DVTOP=Vtb_hdc_kv_ingest", "-CFLAGS", "-O1", "-j", "8",
                    *map(str, RTL), str(TB), str(HARNESS)], check=True, capture_output=True, text=True)
    return obj / "Vtb_hdc_kv_ingest"


def pow2(n):
    return 1 << max(4, (n - 1).bit_length())


def write_case(d: Path, case, memw):
    d.mkdir(parents=True, exist_ok=True)
    (d / "desc.mem").write_text("".join(f"{x:064x}\n" for x in case["descs"]))
    (d / "pay.mem").write_text("".join(f"{x:0128x}\n" for x in case["beats"]))
    for name, img in (("init", case["init"]), ("exp", case["exp"])):
        full = np.zeros(memw * 32, dtype=np.uint8)
        full[:img.size] = img
        (d / f"{name}.mem").write_text("".join(f"{s:064x}\n" for s in R.sectors(full)))


def run(exe, d, nd, np_, seed=1, **pa):
    args = dict(ND=nd, NP=np_, SEED=seed, **pa)
    t = time.time()
    p = subprocess.run([str(exe), f"+verilator+seed+{seed}", "+verilator+rand+reset+0",
                        *(f"+{k}={v}" for k, v in args.items())], cwd=d, capture_output=True, text=True,
                       timeout=7200)
    m = RE_ING.search(p.stdout)
    if not m:
        return dict(pass_=False, stdout=p.stdout[-1500:], stderr=p.stderr[-800:])
    (descs, beats, npay, secs, err, oob, dones, cyc, first, last, dreq, dgr, igr, dwait, tmo) = map(int, m.groups())
    span = max(1, last - max(first, 0) + 1)
    return {"pass": err == 0 and oob == 0 and tmo == 0 and beats == npay and dones == descs,
            "errors": err, "oob": oob, "timeout": bool(tmo), "descriptors": descs, "fenced_done": dones,
            "beats": beats, "sectors_written": secs, "cycles": cyc, "active_cycles": span,
            "beats_per_cycle": round(beats / span, 4), "sectors_per_cycle": round(secs / span, 4),
            "decode_requests": dreq, "decode_granted": dgr, "ingest_granted": igr, "decode_wait_cycles": dwait,
            "plusargs": pa, "seed": seed, "wall_s": round(time.time() - t, 1),
            "first_mismatch": [ln for ln in p.stdout.splitlines() if ln.startswith("MISMATCH")][:2]}


def final_image(d, nbytes):
    words = [int(x, 16) for x in (d / "final.mem").read_text().split() if not x.startswith("@") and x.strip()]
    b = b"".join(w.to_bytes(32, "little") for w in words)
    return np.frombuffer(b[:nbytes], dtype=np.uint8)


def isa_decode_from_image(case, img):
    """Decode the next token on the ISA machine from the ingested image, vs the golden decode."""
    import hdc_golden as G
    import hdc_program as P
    ref, (model, prompt, cache, ks, vs) = case["qwen"]["ref"], case["qwen"]["cap"]
    lay = P.Layout(model)
    assert lay.kv_elems == ref.nbytes
    kv = R.fp8_value(img[:ref.nbytes]).astype(np.float32)
    token, pos = prompt[-1], len(prompt) - 1
    mach = P.Machine(lay, kv)
    got = mach.run(P.build_program(lay), token, pos)
    gold = model.decode_token(token, pos, [list(c) for c in cache])
    # the image's own cache (what the ingested values imply), for the bit-exact-given-ingested-KV check
    ing_cache = [[(kv[[lay.k_elem(L, g, t, d) for g in range(lay.KV) for d in range(lay.HD)]].reshape(lay.KV, lay.HD),
                   kv[[lay.v_elem(L, g, t, d) for g in range(lay.KV) for d in range(lay.HD)]].reshape(lay.KV, lay.HD))
                  for t in range(pos)] for L in range(lay.L)]
    given = model.decode_token(token, pos, ing_cache)
    return dict(isa_token=int(got), golden_token_own_cache=int(np.argmax(gold)),
                isa_logits_bitexact_vs_golden_given_ingested_kv=bool(np.array_equal(G.bits(mach.logits), G.bits(given))),
                isa_logits_bitexact_vs_golden_own_cache=bool(np.array_equal(G.bits(mach.logits), G.bits(gold))),
                max_abs_logit_diff_vs_own_cache=float(np.max(np.abs(mach.logits - gold))))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--output", type=Path, default=OUT)
    ap.add_argument("--quick", action="store_true", help="skip the traffic sweep")
    ap.add_argument("--cross-superblock-only", action="store_true",
                    help="run a V4.1 key ingest window across the 1,024-key physical super-block boundary")
    ap.add_argument("--work", type=Path)
    args = ap.parse_args()
    rng = np.random.default_rng(20260927)
    if args.cross_superblock_only:
        # This 1,008-key global window contains local keys 1,023 and 1,024 on
        # die 2, stack 0. It crosses the 17-block boundary with a modest HBM
        # image, unlike the ordinary case which starts at local key zero.
        cases = {"v41_ikey_cross_superblock": case_ikey(rng, 1008, first=16_000)}
    else:
        cap = qwen_capture()
        cases = {
            "qwen_reduced_fp32": case_qwen_reduced(R.FMT_FP32, cap),
            "qwen_reduced_bf16": case_qwen_reduced(R.FMT_BF16, cap),
            "qwen_reduced_fp8": case_qwen_reduced(R.FMT_FP8, cap),
            "qwen_append_rmw": case_qwen_append(cap),
            "qwen_shipped_geom": case_shipped(rng),
            "v41_ckv": case_rows(rng, "ckv", 1000, first=48),
            "v41_win": case_rows(rng, "win", 200, first=0),
            "v41_ikey": case_ikey(rng, 4096),
            "raw": case_raw(rng),
        }
    work = Path(args.work or tempfile.mkdtemp(prefix="ing_", dir=os.environ.get("TMPDIR", "/tmp")))
    exes = {}
    rec = {"schema": "opentallas.rtl-kv-ingest.v1", "tool": "tools/rtl_hdc_kv_ingest_campaign.py",
           "spec": "docs/ARCH_SPEC_PREFILL.md section 6", "cases": {}, "traffic": {}, "mutations": {}}
    rtl_ok = True
    for name, case in cases.items():
        memw = pow2(max(case["exp"].size // 32 + 1, 1024 + 64))
        key = (memw, pow2(len(case["descs"])), pow2(len(case["beats"])), case["hd"], case["kvh"])
        if key not in exes:
            exes[key] = build(work / f"obj_{len(exes)}", *key)
        d = work / name
        write_case(d, case, memw)
        r = run(exes[key], d, len(case["descs"]), len(case["beats"]), DECBASE=memw - 1024, DECLEN=1024)
        r.update(case["meta"])
        if r["pass"] and "qwen" in case:
            r["decode_from_ingested_image"] = isa_decode_from_image(case, final_image(d, case["exp"].size))
        # traffic: decode bursts, memory stalls, source gaps (the arbiter's contract)
        if not args.quick and name in ("qwen_shipped_geom", "v41_ikey", "v41_ikey_cross_superblock", "qwen_append_rmw"):
            rows = []
            for duty, share, mst, gap in ((0, 64, 0, 0), (50, 64, 0, 0), (90, 64, 0, 0), (90, 64, 20, 10),
                                          (100, 64, 0, 0), (100, 32, 0, 0)):
                rr = run(exes[key], d, len(case["descs"]), len(case["beats"]), seed=duty + share + mst,
                         DUTY=duty, DON=256, MSTALL=mst, SHARE=share, PGAP=gap, DGAP=gap, DECBASE=memw - 1024, DECLEN=1024)
                rr.update(duty_pct=duty, share_x256=share)
                rows.append(rr)
                rtl_ok &= rr["pass"]
            rec["traffic"][name] = rows
        rec["cases"][name] = r
        rtl_ok &= r["pass"]
        print(name, {k: r.get(k) for k in ("pass", "errors", "cycles", "beats_per_cycle", "sectors_per_cycle")},
              flush=True)
    # mutations: each must FAIL
    muts = {}
    if not args.cross_superblock_only:
        c = cases["v41_ikey"]
        bad = dict(c, descs=[c["descs"][0] ^ (1 << 224)])          # DIE 2 -> 3
        muts["ikey_wrong_die"] = bad
        c = cases["qwen_reduced_fp32"]
        muts["qkv_swapped_kv_bases"] = dict(c, descs=[(x & ~(((1 << 64) - 1) << 16)) | (((x >> 48) & 0xFFFFFFFF) << 16)
                                                      | (((x >> 16) & 0xFFFFFFFF) << 48) for x in c["descs"]])
        c = cases["qwen_append_rmw"]
        muts["rmw_tlo_off_by_one"] = dict(c, descs=[x + (1 << 224) if (x >> 6) & 1 else x for x in c["descs"]])
    for name, case in muts.items():
        memw = pow2(max(case["exp"].size // 32 + 1, 1024 + 64))
        key = (memw, pow2(len(case["descs"])), pow2(len(case["beats"])), case["hd"], case["kvh"])
        if key not in exes:
            exes[key] = build(work / f"obj_{len(exes)}", *key)
        d = work / ("mut_" + name)
        write_case(d, case, memw)
        r = run(exes[key], d, len(case["descs"]), len(case["beats"]), DECBASE=memw - 1024, DECLEN=1024,
                MAXCYC=2000000)
        muts_ok = not r.get("pass", False)
        rec["mutations"][name] = dict(detected=muts_ok, errors=r.get("errors"), timeout=r.get("timeout"))
        rtl_ok &= muts_ok
    rec["pass"] = bool(rtl_ok)
    rec["input_sha256"] = {str(p.relative_to(ROOT)): sha(p) for p in RTL + [TB, HARNESS] + TOOLS}
    try:
        rec["git_head"] = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                                         text=True).stdout.strip()
    except Exception:
        pass
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    print("pass:", rec["pass"], "->", args.output)
    return 0 if rec["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
