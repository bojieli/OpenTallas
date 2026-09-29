#!/usr/bin/env python3
"""Actual QE + actual QE weight streamer on the shared one-stack HBM service, real L0 wq_a rows.

The production L0 program's wq_a LINQ (PC7: nb 160, tiles 3, nout 320, 3,840 weight words) runs on
ot_hdc_v41_qe (full shape, CHUNK8) fed by ot_hdc_qstream through ot_chip_v41x_shared_hbm_model while 32
K/KV requesters read the same stack (rtl/test/tb_v41_qe_shared_stall.sv).  Weights are the RELEASED
checkpoint's layer-0 attn.wq_a rows 0..319 (tensor-parallel rank 0 of 4) with their 32x32 UE8M0 block
exponents; round 2's rows 320..383 are zero padding (written with an all-zero mask).  The activation is a
seeded random BF16 vector (synthetic).  Expected outputs come from hdc_golden_v41.linear_q (chunk8), not
from the RTL.  Every written word is compared bit for bit.

Cases: WEIGHT_STALL=1 (ALLOW_QE_STALL) with no K traffic and with one-sector K reads offered on all 32
pseudo-channels every KPER cycles (KCRED outstanding each); and the no-stall admission (WEIGHT_STALL=0)
at a 1,024-word window (fixed rate, expected to fail closed) and a 4,096-word window (whole-matrix lead).

    python3 tools/v41_qe_shared_stall_gate.py [--output results/rtl/v41_qe_shared_stall.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as G  # noqa: E402

TB = ROOT / "rtl/test/tb_v41_qe_shared_stall.sv"
RTL = [ROOT / p for p in (
    "rtl/hdc/v41/ot_hdc_v41_qe.sv", "rtl/hdc/v41/ot_hdc_actquant.sv", "rtl/hdc/v41/ot_hdc_fp4qdq.sv",
    "rtl/hdc/v41/ot_hdc_blockdot.sv", "rtl/hdc/v41/ot_hdc_chunk8_stack.sv", "rtl/hdc/ot_hdc_delay.sv",
    "rtl/hdc/ot_hdc_fpu.sv", "rtl/hdc/ot_hdc_fp32_mul_pipe.sv", "rtl/proto/ot_fp32_add_rne_pipe.sv",
    "rtl/hdc/hbm/ot_hdc_qstream.sv", "rtl/chip/ot_chip_v41x_shared_hbm_model.sv",
    "rtl/chip/ot_chip_v41x_weight_pc_adapter.sv", "rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv")]
OUT = ROOT / "results/rtl/v41_qe_shared_stall.json"
HF = Path(os.environ.get("OT_V41_FLASH_SNAPSHOT", Path.home() / ".cache/huggingface/hub/models--deepseek-ai--"
                         "DeepSeek-V4.1-Flash/snapshots/dba1be0a40aa45a94ad051997016db3960a90277"))
PROGRAM_BIND = ROOT / "results/rtl/hdc_v41x_fullshape_program_bind_rope_hbm.json"
NB, TILES, NOUT, IL, BL = 160, 3, 320, 8, 16
VERILATOR = os.environ.get("OT_VERILATOR", str(Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"))
LINE = re.compile(r"V41QESHARED status=\s*(\w+)(.*)")
# (name, STALL, LWIN, KPER, KCRED, LEAD, RATE)
CASES = [
    ("stall_noK", 1, 10, 0, 8, 1, 0),
    ("stall_K32", 1, 10, 32, 8, 1, 0),
    ("stall_K8", 1, 10, 8, 8, 1, 0),
    ("stall_K4", 1, 10, 4, 8, 1, 0),
    ("stall_K2", 1, 10, 2, 8, 1, 0),
    ("stall_Ksat", 1, 10, 1, 8, 1, 0),
    ("nostall_win1024_rate188_noK", 0, 10, 0, 8, 0, 188),
    ("nostall_win1024_rate188_Ksat", 0, 10, 1, 8, 0, 188),
    ("nostall_win4096_full_lead_noK", 0, 12, 0, 8, 3840, 0),
    ("nostall_win4096_full_lead_Ksat", 0, 12, 1, 8, 3840, 0),
]


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def checkpoint_rows():
    """Layer-0 attn.wq_a rows 0..319 (rank 0 of the output split) as raw E4M3 codes and per-row block exponents."""
    import struct
    idx = json.loads((HF / "model.safetensors.index.json").read_text())["weight_map"]
    out = {}
    for name in ("layers.0.attn.wq_a.weight", "layers.0.attn.wq_a.scale"):
        f = HF / idx[name]
        with open(f, "rb") as fh:
            n = struct.unpack("<Q", fh.read(8))[0]
            hdr = json.loads(fh.read(n))
            meta = hdr[name]
            s, e = meta["data_offsets"]
            fh.seek(8 + n + s)
            out[name] = (np.frombuffer(fh.read(e - s), dtype=np.uint8).reshape(meta["shape"]), meta, idx[name])
    codes, cmeta, cfile = out["layers.0.attn.wq_a.weight"]
    scale, smeta, sfile = out["layers.0.attn.wq_a.scale"]
    assert cmeta["dtype"] == "F8_E4M3" and cmeta["shape"] == [1280, 5120], cmeta
    assert smeta["dtype"] == "F8_E8M0" and smeta["shape"] == [40, 160], smeta
    codes = codes[:NOUT].astype(np.int64)
    exps = np.repeat(scale.astype(np.int64) - 127, 32, axis=0)[:NOUT]
    assert not np.any((codes & 0x7F) == 0x7F), "NaN code in wq_a"
    src = dict(files={cfile: None, sfile: None}, tensor="layers.0.attn.wq_a", rows=[0, NOUT], rank=0, tp=4,
               codes_sha256=hashlib.sha256(codes.astype(np.uint8).tobytes()).hexdigest(),
               exps_sha256=hashlib.sha256(exps.astype(np.int16).tobytes()).hexdigest())
    return codes, exps, src


def vectors(d: Path):
    G.set_arith("chunk8")
    codes, exps, src = checkpoint_rows()
    rng = np.random.default_rng(20260929)
    x = G.to_bf16(rng.normal(size=32 * NB).astype(np.float32))
    w = G.Q8(G.E4M3[codes].astype(np.float64), exps)
    y = G.linear_q(w, x)
    rows = TILES * IL * BL
    allc = np.zeros((rows, 32 * NB), dtype=np.int64); allc[:NOUT] = codes
    alle = np.zeros((rows, NB), dtype=np.int64); alle[:NOUT] = exps
    with (d / "w.mem").open("w") as f:
        for r in range(TILES):
            for kb in range(NB):
                for j in range(IL):
                    word = 0
                    for lane in range(BL):
                        row = (r * IL + j) * BL + lane
                        lw = 0
                        for c in range(32):
                            lw |= int(allc[row, kb * 32 + c]) << (8 * c)
                        lw |= (int(alle[row, kb]) & 0xFFFF) << 256
                        word |= lw << (272 * lane)
                    for s in range(17):
                        f.write(f"{(word >> (256 * s)) & ((1 << 256) - 1):064x}\n")
    with (d / "x.mem").open("w") as f:
        for b in range(NB):
            v = 0
            for k, bits in enumerate(G.bits(x[b * 32:(b + 1) * 32])):
                v |= int(bits) << (32 * k)
            f.write(f"{v:0256x}\n")
    (d / "y.mem").write_text("".join(f"{int(v):08x}\n" for v in G.bits(y)))
    src.update(activation="seeded random BF16 normal, seed 20260929 (synthetic)",
               images={p.name: sha(p) for p in sorted(d.glob("*.mem"))},
               expected_nonzero=int(np.count_nonzero(G.bits(y))))
    return src


def build(d: Path, stall: int, lwin: int) -> Path:
    obj = d / f"obj_s{stall}_w{lwin}"
    cmd = [VERILATOR, "--binary", "-O2", "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-TIMESCALEMOD",
           "-Wno-UNOPTFLAT", "--top-module", "tb_v41_qe_shared_stall", f"-GSTALL={stall}", f"-GLWIN={lwin}",
           "-Mdir", str(obj), *map(str, RTL + [TB]), "-j", "8"]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=3600)
    if r.returncode:
        raise RuntimeError("build failed: " + r.stderr[-3000:])
    return obj / "Vtb_v41_qe_shared_stall"


def run(output: Path, workdir: Path | None):
    tmp = tempfile.TemporaryDirectory(prefix="v41_qe_shared_") if workdir is None else None
    d = Path(tmp.name) if tmp else workdir
    d.mkdir(parents=True, exist_ok=True)
    src = vectors(d)
    exes = {}
    results = []
    for name, stall, lwin, kper, kcred, lead, rate in CASES:
        if (stall, lwin) not in exes:
            exes[(stall, lwin)] = build(d, stall, lwin)
        p = subprocess.run([str(exes[(stall, lwin)]), f"+KPER={kper}", f"+KCRED={kcred}", f"+LEAD={lead}",
                            f"+RATE={rate}"], cwd=d, capture_output=True, text=True, timeout=3600)
        m = LINE.search(p.stdout)
        rec = dict(case=name, stall=stall, window_words=1 << lwin, k_period=kper, k_credits=kcred, lead=lead,
                   rate=rate, returncode=p.returncode, status=m.group(1) if m else "no_report")
        if m:
            rec.update({k: int(v) for k, v in re.findall(r"(\w+)=(-?\d+)", m.group(2))})
        hb = re.search(r"V41QEHBM (.*)", p.stdout)
        if hb:
            rec["hbm"] = {k: int(v) for k, v in re.findall(r"(\w+)=(-?\d+)", hb.group(1))}
        fl = re.search(r"FAULT (.*)", p.stdout)
        if fl:
            rec["fault"] = fl.group(1)
        rec["log_tail"] = p.stdout.strip().splitlines()[-3:]
        if rec["status"] == "pass":
            qe_cycles = rec["end"] - rec["go"]
            words = TILES * NB * IL
            rec["derived"] = dict(
                token_to_done_cycles=rec["end"],
                qe_cycles=qe_cycles,
                row_phase_cycles=rec["rows_cycles"],
                ideal_row_phase_cycles=words,
                weight_stall_cycles=rec["starve"],
                weight_bytes_per_cycle_row_phase=round(words * 544 / rec["rows_cycles"], 2),
                weight_bytes_per_cycle_token=round(words * 544 / rec["end"], 2),
                k_sectors_per_cycle=round(rec["k_rsp"] / rec["end"], 3),
                k_offer_accept_ratio=round(rec["k_acc"] / rec["k_offer"], 4) if rec["k_offer"] else None)
        results.append(rec)
        print(json.dumps({k: rec.get(k) for k in ("case", "status", "errors", "end", "starve", "k_stall", "k_rsp")}))
    stall_ok = all(r["status"] == "pass" and r["errors"] == 0 for r in results if r["stall"])
    record = {
        "schema": "opentallas.rtl.v41_qe_shared_stall.v1",
        "status": "pass" if stall_ok else "fail",
        "scope": ("Actual QE (full shape, CHUNK8, WEIGHT_STALL) + actual qstream (ALLOW_QE_STALL, NPC32) + shared "
                  "one-stack HBM timing owner, real released-checkpoint L0 wq_a rank-0 rows (320 x 5120 FP8, "
                  "UE8M0 32x32 exponents), synthetic BF16 activation, synthetic one-sector K read traffic on all "
                  "32 pseudo-channels. One descriptor, one stack; no core sequencer, no production WINDOW/index "
                  "trace, no physical timing."),
        "descriptor": dict(program="L0 PC7 wq_a", nb=NB, tiles=TILES, nout=NOUT, words=TILES * NB * IL,
                           sectors=TILES * NB * IL * 17),
        "vectors": src,
        "cases": results,
        "verilator": subprocess.run([VERILATOR, "--version"], capture_output=True, text=True).stdout.strip(),
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in RTL + [TB, Path(__file__).resolve(),
                          ROOT / "tools/hdc_golden_v41.py", ROOT / "tools/hdc_golden.py", PROGRAM_BIND]},
    }
    if output.exists():
        old = json.loads(output.read_text())
        if old.get("status") == "fail" and record["status"] == "pass":
            output = output.with_name(output.stem + "_rerun.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2) + "\n")
    if tmp:
        tmp.cleanup()
    return record


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output", type=Path, default=OUT)
    ap.add_argument("--workdir", type=Path)
    a = ap.parse_args()
    rec = run(a.output, a.workdir)
    print(rec["status"])
    sys.exit(0 if rec["status"] == "pass" else 1)
