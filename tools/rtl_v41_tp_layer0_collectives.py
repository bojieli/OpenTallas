#!/usr/bin/env python3
"""Prepare and collect the exact 12-COLL TP layer-0 four-rank stage gate.

The descriptor sequence is emitted by ShapeBuilder. Operand values are a
deterministic arithmetic stress fixture; this is not a full layer simulation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np

import hdc_golden as G
import hdc_isa_v41 as I
import hdc_replay_v41 as R

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/rtl/v41_tp_layer0_collective_sequence.json"
MAXW = 320
OPS = 12
RANKS = 4
LANES = 16
WORDS = OPS * RANKS * MAXW
SOURCES = [
    "tools/rtl_v41_tp_layer0_collectives.py",
    "rtl/test/tb_v41_tp_layer0_collectives.sv",
    "rtl/test/tb_v41_tp_rowsplit_gw4_banked.sv",  # adopted-link ot_v41px_link
    "rtl/chip/ot_chip_v41x_coll_dma.sv",
    "rtl/chip/ot_chip_v41x_coll_transpose.sv",
    "rtl/rom/ot_rom_oneshot_px.sv",
    "rtl/hdc/ot_hdc_fastfp.sv",
    "rtl/proto/ot_fp32_add_rne_pipe.sv",
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def descriptors(program_bind: Path | None = None) -> list[dict]:
    if program_bind is None:
        prog = R.build_tp_layer0()
        rows = [(pc, op["_tag"], op) for pc, op in enumerate(prog)
                if op.get("unit") == I.UNIT_COLL]
    else:
        bound = json.loads(program_bind.read_text())
        assert bound["schema"] == "opentallas.v41x.fullshape.program_bind.v1"
        rows = [(row["pc"], row["tag"], row["fields"])
                for row in bound["instruction_trace"] if row["unit"] == I.UNIT_COLL]
    out = []
    for pc, tag, op in rows:
        n = op["coll_n"] // LANES
        assert op["coll_n"] == n * LANES and 0 < n <= MAXW
        assert op["coll_op"] in (I.COLL_ALL_REDUCE_SUM, I.COLL_ALL_GATHER)
        out.append({"pc": pc, "tag": tag, "seq": op["coll_seq"],
                    "mode": op["coll_op"], "rnd": op["coll_rnd"],
                    "source_elements": op["coll_n"], "source_words": n,
                    "src_element": op["coll_src"], "dst_element": op["coll_dst"]})
    assert len(out) == OPS
    assert [d["source_words"] for d in out] == [20, 8, 320, 36, 6, 36, 36, 36, 36, 36, 36, 80]
    assert sum(d["source_words"] for d in out) == 686
    assert [d["seq"] for d in out] == list(range(OPS))
    return out


def operand(op: int, rank: int, word: int, lane: int, reduce: bool) -> np.float32:
    if reduce:
        # Pairwise and rank-linear folding differ on this cancellation case.
        vals = (np.float32(1e10), np.float32(1), np.float32(-1e10), np.float32(1))
        return vals[rank]
    # BF16 source containers for gathers, FP32 score containers for router.
    value = np.float32((op + 1) * 0.125 + rank * 0.03125 + ((word * LANES + lane) % 97) / 4096)
    return value if op == 4 else G.to_bf16(value).item()


def prepare(outdir: Path, program_bind: Path | None) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    ds = descriptors(program_bind)
    part = np.zeros((OPS, RANKS, MAXW, LANES), dtype=np.uint32)
    exp = np.zeros((OPS, RANKS * MAXW, LANES), dtype=np.uint32)
    desc_words = []
    for oi, d in enumerate(ds):
        n, red = d["source_words"], d["mode"] == I.COLL_ALL_REDUCE_SUM
        desc_words.append((d["mode"] << 31) | (d["rnd"] << 30) | (d["seq"] << 15) | n)
        for rank in range(RANKS):
            for k in range(n):
                for lane in range(LANES):
                    part[oi, rank, k, lane] = G.bits(operand(oi, rank, k, lane, red)).item()
        for k in range(n):
            for lane in range(LANES):
                if red:
                    vals = [G.from_bits(part[oi, rank, k, lane]).item() for rank in range(RANKS)]
                    x = G.add(G.add(vals[0], vals[1]), G.add(vals[2], vals[3]))
                    if d["rnd"]:
                        x = G.to_bf16(x)
                    exp[oi, k, lane] = G.bits(x).item()
                else:
                    for rank in range(RANKS):
                        exp[oi, rank * n + k, lane] = part[oi, rank, k, lane]
    def write_words(path: Path, array: np.ndarray) -> None:
        with path.open("w") as f:
            for lanes in array.reshape(-1, LANES):
                f.write("".join(f"{int(x):08x}" for x in lanes[::-1]) + "\n")
    write_words(outdir / "part.hex", part)
    write_words(outdir / "expected.hex", exp)
    (outdir / "desc.hex").write_text("".join(f"{x:08x}\n" for x in desc_words))
    meta = {"schema": "v41_tp_layer0_collective_fixture_v1", "descriptors": ds,
            "images_sha256": {p.name: sha(p) for p in (outdir / "part.hex", outdir / "expected.hex", outdir / "desc.hex")},
            "fixture_reference_sha256": {"tools/hdc_golden.py": sha(ROOT / "tools/hdc_golden.py")},
            "source_sha256": {p: sha(ROOT / p) for p in SOURCES}}
    if program_bind is not None:
        bound = json.loads(program_bind.read_text())
        meta["program_bind_record"] = "results/rtl/hdc_v41x_fullshape_program_bind.json"
        meta["program_bind_sha256"] = sha(program_bind)
        meta["program_bind_sources"] = bound["source_sha256"]
    (outdir / "manifest.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")
    return meta


LINE = re.compile(
    r"OP op=(?P<op>\d+) die=(?P<die>\d+) mode=(?P<mode>\d+) words=(?P<words>\d+) tag=(?P<tag>\d+) "
    r"start=(?P<start>\d+) first_tx=(?P<first_tx>-?\d+) last_tx=(?P<last_tx>-?\d+) "
    r"first_vm=(?P<first_vm>-?\d+) last_vm=(?P<last_vm>-?\d+) finish=(?P<finish>\d+) "
    r"txstall=(?P<txstall>\d+) outstall=(?P<outstall>\d+) peak_fifo=(?P<peak_fifo>\d+) writes=(?P<writes>\d+)"
)


def collect(outdir: Path, log: Path, verilator_version: str, binary_sha256: str) -> dict:
    meta = json.loads((outdir / "manifest.json").read_text())
    for p, digest in meta["source_sha256"].items():
        assert sha(ROOT / p) == digest, p
    for p, digest in meta["fixture_reference_sha256"].items():
        assert sha(ROOT / p) == digest, p
    for p, digest in meta["images_sha256"].items():
        assert sha(outdir / p) == digest, p
    lines = log.read_text()
    rows = [{k: int(v) for k, v in m.groupdict().items()} for m in LINE.finditer(lines)]
    ds = meta["descriptors"]
    assert len(rows) == OPS * RANKS, len(rows)
    assert f"L0_COLLECTIVES_PASS ops={OPS}" in lines
    cases = []
    for oi, d in enumerate(ds):
        four = [r for r in rows if r["op"] == oi]
        assert [r["die"] for r in four] == list(range(RANKS))
        for r in four:
            assert (r["mode"], r["words"], r["tag"]) == (d["mode"], d["source_words"], d["seq"])
            assert r["writes"] == d["source_words"] * (1 if d["mode"] == 0 else RANKS)
            assert r["start"] <= r["first_tx"] <= r["last_tx"] <= r["last_vm"] < r["finish"]
        start = min(r["start"] for r in four)
        first_tx = min(r["first_tx"] for r in four)
        last_tx = max(r["last_tx"] for r in four)
        first_vm = min(r["first_vm"] for r in four)
        last_vm = max(r["last_vm"] for r in four)
        finish = max(r["finish"] for r in four)
        cases.append({"descriptor": d, "per_die": four,
                      "startup_cycles": first_tx - start,
                      "input_stream_cycles": last_tx - first_tx + 1,
                      "network_to_first_vm_cycles": first_vm - first_tx,
                      "transfer_through_last_vm_cycles": last_vm - first_tx + 1,
                      "commit_cycles_after_last_vm": finish - last_vm - 1,
                      "cycles_from_issue_to_commit": last_vm - start + 1,
                      "cycles_blocked_to_all_done": finish - start})
    return {"schema": "v41_tp_layer0_collective_sequence_v1", "scope": "exact emitted 12 blocking COLL descriptors with deterministic synthetic BF16/FP32 operands through persistent four-rank adopted links, engines, DMA and behavioral VM; producers, full layer, HBM and route omitted",
            "contract": {"ranks": 4, "packages": 2, "dies_per_package": 2, "CL_LANES": 16,
                         "CL_DEPTH": 256, "RELAY": 1, "ADD_LAT": 3, "PAIRWISE": 1,
                         "GW": 4, "bank_vm_writes_per_cycle": 4, "blocked_COLL_v1": True},
            "verilator": verilator_version, "binary_sha256": binary_sha256,
            "build": {"top": "tb_v41_tp_layer0_collectives", "flags": ["--binary", "--timing", "-j", "4", "-Wno-fatal", "-Wno-WIDTH", "-Wno-TIMESCALEMOD"],
                      "rtl_sources": [p for p in SOURCES if p.endswith(".sv")]},
            "source_sha256": meta["source_sha256"],
            "fixture_reference_sha256": meta["fixture_reference_sha256"],
            "program_bind_sha256": meta.get("program_bind_sha256"),
            "program_bind_record": meta.get("program_bind_record"),
            "program_bind_sources": meta.get("program_bind_sources"),
            "images_sha256": meta["images_sha256"], "cases": cases,
            "total_source_words_per_die": sum(d["source_words"] for d in ds),
            "sum_blocked_service_cycles": sum(c["cycles_blocked_to_all_done"] for c in cases),
            "wall_cycles_including_fixture_readback": cases[-1]["per_die"][0]["finish"] - cases[0]["per_die"][0]["start"],
            "passed": True}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prepare", type=Path)
    ap.add_argument("--program-bind", type=Path)
    ap.add_argument("--collect", type=Path)
    ap.add_argument("--log", type=Path)
    ap.add_argument("--verilator-version", type=str, default="Verilator 5.050 2026-07-01 rev v5.050")
    ap.add_argument("--binary-sha256", type=str, default="")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    if args.prepare:
        print(json.dumps(prepare(args.prepare, args.program_bind)["descriptors"], indent=2))
    elif args.collect and args.log:
        record = collect(args.collect, args.log, args.verilator_version, args.binary_sha256)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
        print(json.dumps({"ops": len(record["cases"]), "words": record["total_source_words_per_die"],
                          "service_cycles": record["sum_blocked_service_cycles"]}))
    else:
        ap.error("provide --prepare DIR or --collect DIR --log PATH")


if __name__ == "__main__":
    main()
