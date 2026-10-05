#!/usr/bin/env python3
"""Exact packed4 V4.1 w2 row-split boundary and adopted-width gather gate.

Real 200K/L0 code, UE8M0 and BF16 bits are source-pinned by the companion
numerics gate. Timing remains a producer-stub stage bench, not token throughput.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_v41_stage_collective_campaign as B  # noqa: E402
B.LANES = 16
B.WORD_B = 64
import rtl_v41_collective_levers_campaign as L  # noqa: E402
from rtl_v41_tp_rowsplit_collectives import patterns_from_design_point  # noqa: E402

FIXTURE = ROOT / "results/rtl/fixtures/v41_w2_stream_l0_200k.npz"
OUT = ROOT / "results/rtl/v41_w2_packed_collective.json"


def _hex_u32(byte_row: np.ndarray) -> str:
    return "".join(f"{int(v):08x}" for v in byte_row.view("<u4")[::-1])


def vectors(work: Path) -> dict:
    p = np.load(FIXTURE)
    codes, scales, y = p["codes"], p["scales"], p["y_bf16"]
    assert codes.shape == (7, 4, 576) and scales.shape == (7, 4, 18) and y.shape == (4, 1280)
    assert codes.dtype == scales.dtype == np.dtype("uint8") and y.dtype == np.dtype("uint16")
    act = np.zeros((4, 77, 64), np.uint8)
    unpacked = np.zeros((4, 7, 38, 64), np.uint8)
    for r in range(4):
        for e in range(7):
            local = np.zeros((11, 64), np.uint8)
            local[:9] = codes[e, r].reshape(9, 64)
            for j in range(18):
                local[9 + j // 16, 4 * (j % 16)] = scales[e, r, j]
            act[r, 11 * e:11 * (e + 1)] = local
            for k in range(576):
                unpacked[r, e, k // 16, 4 * (k % 16)] = codes[e, r, k]
            for k in range(18):
                unpacked[r, e, 36 + k // 16, 4 * (k % 16)] = scales[e, r, k]
    ybytes = np.ascontiguousarray(y.astype("<u2")).view(np.uint8).reshape(4, 40, 64)
    y_unpacked = np.zeros((4, 80, 64), np.uint8)
    for r in range(4):
        for c in range(1280):
            y_unpacked[r, c//16, (c%16)*4:(c%16)*4+2] = np.frombuffer(
                np.uint16(y[r, c]).tobytes(), dtype=np.uint8)
    assert np.array_equal(act[:, :, :].reshape(4, 7, 11, 64)[:, :, :9].reshape(4, 7, 576),
                          codes.transpose(1, 0, 2))
    work.mkdir(parents=True, exist_ok=True)
    (work / "act_flit.hex").write_text("\n".join(_hex_u32(row) for row in act.reshape(-1, 64)) + "\n")
    (work / "unpacked.hex").write_text("\n".join(_hex_u32(row) for row in unpacked.reshape(-1, 64)) + "\n")
    (work / "y_flit.hex").write_text("\n".join(_hex_u32(row) for row in ybytes.reshape(-1, 64)) + "\n")
    (work / "y_unpacked.hex").write_text("\n".join(_hex_u32(row) for row in y_unpacked.reshape(-1, 64)) + "\n")
    (work / "code.hex").write_text("\n".join(f"{int(x):02x}" for x in codes.transpose(1, 0, 2).reshape(-1)) + "\n")
    (work / "scale.hex").write_text("\n".join(f"{int(x):02x}" for x in
                                          np.broadcast_to(scales[:, :, :, None], (7, 4, 18, 32))
                                          .reshape(7, 4, 576).transpose(1, 0, 2).reshape(-1)) + "\n")
    (work / "y.hex").write_text("\n".join(f"{int(x):04x}" for x in y.reshape(-1)) + "\n")
    return dict(expert_ids=p["expert_ids"].astype(int).tolist(),
                fp8_codes=int(codes.size), ue8m0_scales=int(scales.size), bf16_y=int(y.size),
                act_input_vm_words=4*7*38, act_flits_per_rank=77, y_flits_per_rank=40,
                act_payload_bytes_per_rank=7*(576+18), act_link_bytes_per_rank=77*64,
                y_link_bytes_per_rank=40*64)


def run_stage(work: Path) -> dict:
    p = np.load(FIXTURE)
    codes, scales, y = p["codes"], p["scales"], p["y_bf16"]
    base_act = np.zeros((4, 266, 64), np.uint8)
    pack_act = np.zeros((4, 77, 64), np.uint8)
    base_y = np.zeros((4, 80, 64), np.uint8)
    pack_y = np.ascontiguousarray(y.astype("<u2")).view(np.uint8).reshape(4, 40, 64)
    for r in range(4):
        for e in range(7):
            for col in range(576):
                base_act[r, e*38 + col//16, (col%16)*4] = codes[e, r, col]
                pack_act[r, e*11 + col//64, col%64] = codes[e, r, col]
            for block in range(18):
                base_act[r, e*38 + 36 + block//16, (block%16)*4] = scales[e, r, block]
                pack_act[r, e*11 + 9 + block//16, (block%16)*4] = scales[e, r, block]
        for col in range(1280):
            base_y[r, col//16, (col%16)*4:(col%16)*4+2] = np.frombuffer(
                np.uint16(y[r, col]).tobytes(), dtype=np.uint8)
    payload = {266: base_act, 77: pack_act, 80: base_y, 40: pack_y}
    pats = patterns_from_design_point()
    base = {"act": pats["act"], "y": pats["y"]}
    for name in ("act", "y"):
        for kind in ("base", "pack"):
            q = dict(base[name], words={"act": (266, 77), "y": (80, 40)}[name][kind == "pack"],
                     order="blocked", name=name, kind=kind)
            B.PATTERNS[f"{name}_{kind}"] = q
    original_schedule, original_vectors, original_top, original_tb = (
        B.schedule, L.coll_vectors, L.top_params, L.TB)
    L.TB = ROOT / "rtl/test/tb_v41_tp_rowsplit_px.sv"

    def schedule(q, order=None):
        if q.get("kind") == "base":
            return [q["depth"] + q["issue"]] * q["words"]
        if q.get("name") == "act":
            return [q["depth"] + q["issue"] + (k//11)*38 +
                    (4*((k%11)+1) if k%11 < 9 else 37 + (k%11-9))
                    for k in range(77)]
        return [q["depth"] + q["issue"] + 2*(k+1) for k in range(40)]

    def coll_vectors(path, words, sch, mode, seed, lanes):
        assert mode == 1 and lanes == 16 and words in payload
        path.mkdir(parents=True, exist_ok=True)
        part, ready = [], []
        for r in range(4):
            part.append(f"@{r*B.MAXW:x}")
            ready.append(f"@{r*B.MAXW:x}")
            part += [_hex_u32(row) for row in payload[words][r]]
            ready += [f"{s:08x}" for s in sch]
        (path / "part.hex").write_text("\n".join(part) + "\n")
        (path / "ready.hex").write_text("\n".join(ready) + "\n")
        (path / "exp.hex").write_text("\n".join(["0"*128] * words) + "\n")

    def top_params(q, link):
        top, params = original_top(q, link)
        params.update(PUSHW=1, PAIRWISE=1)
        return top, params

    B.schedule, L.coll_vectors, L.top_params = schedule, coll_vectors, top_params
    B.PATTERNS.update({f"{n}_{k}": B.PATTERNS[f"{n}_{k}"] for n in base for k in ("base", "pack")})
    try:
        lp = B.link_params()
        cases = [L.run_case(work, dict(name=f"{n}_{k}_d128_q2", pattern=f"{n}_{k}",
                                       lever="relay_add3", depth=128, qtx=2, lanes=16,
                                       order="blocked"), lp)
                 for n in ("act", "y") for k in ("base", "pack")]
    finally:
        B.schedule, L.coll_vectors, L.top_params, L.TB = (
            original_schedule, original_vectors, original_top, original_tb)
    assert all(c["passed"] and c["mismatches"] == c["out_err"] == c["timeout"] == 0 for c in cases)
    rows = {c["case"].split("_d128")[0]: c for c in cases}
    summary = {}
    for n in ("act", "y"):
        b, pck = rows[f"{n}_base"], rows[f"{n}_pack"]
        pack_ref_shift = 266 if n == "act" else 80
        comparable = pck["exposed_tail_cycles"] + pack_ref_shift
        summary[n] = dict(baseline_tail_cycles=b["exposed_tail_cycles"],
                          packed_engine_tail_cycles=pck["exposed_tail_cycles"],
                          packed_comparable_tail_cycles=comparable,
                          exposed_tail_delta_cycles=comparable-b["exposed_tail_cycles"],
                          baseline_output_writes=4*b["words_per_die"],
                          packed_output_writes=4*pck["words_per_die"],
                          source_pack_input_words=pack_ref_shift)
    return dict(contract="one 64-byte producer word/cycle feeds lossless pack4; one packed scratchpad write/cycle; blocking COLL v1; real L0/200K payload; not full-shape token or P&R",
                link=lp, cases=cases, summary=summary)


def run_rtl(work: Path, top: str, sources: list[str]) -> str:
    obj = work / f"{top}.vvp"
    cmd = ["iverilog", "-g2012", "-s", top, "-o", str(obj),
           *[str(ROOT / s) for s in sources]]
    r = subprocess.run(cmd, text=True, capture_output=True)
    if r.returncode:
        raise RuntimeError(r.stderr[-4000:] + r.stdout[-2000:])
    run = subprocess.run(["vvp", str(obj), f"+VEC={work / 'vec'}"], text=True,
                         capture_output=True, timeout=240)
    if run.returncode or "PASS" not in run.stdout:
        raise RuntimeError(run.stdout[-4000:] + run.stderr[-1000:])
    return next(line for line in run.stdout.splitlines() if "PASS" in line)


def run_standalone(work: Path) -> dict:
    return {
        "pack4": run_rtl(work, "tb_v41_w2_pack4", [
            "rtl/chip/ot_chip_v41x_w2_pack4.sv", "rtl/test/tb_v41_w2_pack4.sv"]),
        "y_pack2": run_rtl(work, "tb_v41_w2_y_pack2", [
            "rtl/chip/ot_chip_v41x_w2_y_pack2.sv", "rtl/test/tb_v41_w2_y_pack2.sv"]),
        "direct_scratchpad": run_rtl(work, "tb_v41_w2_packed_spad", [
            "rtl/chip/ot_chip_v41x_w2_packed_spad.sv", "rtl/chip/ot_chip_v41x_w2_y_spad.sv",
            "rtl/test/tb_v41_w2_packed_spad.sv"]),
    }


def run_generic_synth() -> dict:
    out = {}
    for mod, path in (
        ("ot_chip_v41x_w2_pack4", "rtl/chip/ot_chip_v41x_w2_pack4.sv"),
        ("ot_chip_v41x_w2_y_pack2", "rtl/chip/ot_chip_v41x_w2_y_pack2.sv"),
    ):
        cmd = ["yosys", "-Q", "-T", "-p", f"read_verilog -sv {ROOT / path}; synth -top {mod}; stat"]
        run = subprocess.run(cmd, text=True, capture_output=True, timeout=300)
        if run.returncode:
            raise RuntimeError(run.stderr[-2000:] + run.stdout[-1000:])
        stat = run.stdout.rsplit(f"=== {mod} ===", 1)[-1]
        def number(label):
            pattern = rf"^\s*{re.escape(label)}\s+(\d+)\s*$"
            m = re.search(pattern, stat, re.M)
            assert m, (mod, label)
            return int(m.group(1))
        out[mod] = dict(generic_cells=number("Number of cells:"),
                        dff_cells=number("$_DFF_PN0_"), mux_cells=number("$_MUX_"),
                        scope="generic synthesis only; no timing, placement or route")
    return out


def build(work: Path) -> dict:
    contract = vectors(work / "vec")
    standalone = run_standalone(work)
    stage = run_stage(work / "stage")
    synth = run_generic_synth()
    paths = ["tools/rtl_v41_w2_packed_collective.py", "tools/v41_w2_stream_exact.py",
             "results/rtl/fixtures/v41_w2_stream_l0_200k.npz",
             "rtl/chip/ot_chip_v41x_w2_pack4.sv", "rtl/chip/ot_chip_v41x_w2_packed_spad.sv",
             "rtl/chip/ot_chip_v41x_w2_y_spad.sv", "rtl/test/tb_v41_w2_pack4.sv",
             "rtl/chip/ot_chip_v41x_w2_y_pack2.sv", "rtl/test/tb_v41_w2_y_pack2.sv",
             "rtl/test/tb_v41_w2_packed_spad.sv", "rtl/test/tb_v41_tp_rowsplit_px.sv",
             "rtl/rom/ot_rom_oneshot_px.sv", "rtl/hdc/ot_hdc_fastfp.sv",
             "tools/rtl_v41_collective_levers_campaign.py", "tools/rtl_v41_stage_collective_campaign.py",
             "tools/rtl_v41_tp_rowsplit_collectives.py", "tools/arch_lanes_v41.py",
             "tools/decode_critical_path.py", "rtl/proto/ot_fp32_add_rne_pipe.sv"]
    pins = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}
    return dict(schema="v41_w2_packed_collective_v1", source_sha256=pins, contract=contract,
                standalone=standalone, stage=stage, packer_generic_synth=synth,
                scope="real L0/200K bit-exact pack, direct packed scratchpad, and producer-stub stage timing; no integrated die or token rate",
                physical_estimate=dict(act_scratchpad_bytes=4*77*64, y_scratchpad_bytes=4*40*64,
                                       total_scratchpad_bytes=(4*77+4*40)*64,
                                       scratchpad_bitcell_area_mm2=(4*77+4*40)*64*8*0.021*2.5*1e-6,
                                       area_basis="assumed N5 0.021 um2/bit HD bitcell x2.5 for 1R1W RF; excludes packer, ports, timing margin and wires",
                                       act_output_write_floor_cycles=4*77,
                                       y_output_write_floor_cycles=4*40,
                                       note="One 64-byte scratchpad write per cycle; 1R1W code and scale banks plus one BF16 y bank are required. Not routed."))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    rec = build(a.work)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    print(json.dumps(rec["standalone"], indent=2))


if __name__ == "__main__":
    main()
