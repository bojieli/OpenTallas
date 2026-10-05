#!/usr/bin/env python3
"""Exact full-shape V4.1 weight-image read gate through segmented HBM windows.

The program reads ROM words 1, 0, 1 in both arms. The HBM arm fetches two
checkpoint-derived words first, with bounded requests and reordered sector
responses. This checks weight bytes and service cycles, not QE/ME/HE arithmetic,
full-token execution, shared-HBM arbitration or chip throughput.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "results/rtl/hdc_v41x_fullshape_token_selected_rom_layout.json"
RTL = ROOT / "rtl/hdc/hbm/ot_hdc_v41x_weight_window.sv"
TB = ROOT / "rtl/test/tb_hdc_v41x_weight_window_fullshape.sv"
FAULT_TB = ROOT / "rtl/test/tb_hdc_v41x_weight_window_segment_fault.sv"
LEGACY_TB = ROOT / "rtl/test/tb_hdc_v41x_weight_window.sv"
QE_UNPACK = ROOT / "rtl/hdc/hbm/ot_hdc_v41x_qe_weight_unpack.sv"
QE_TB = ROOT / "rtl/test/tb_hdc_v41x_qe_weight_unpack.sv"
CASES = (
    ("wq_a", "wq_a.qe.bin", 66, 0x100000),
    ("exp110.w1", "exp110.w1.qe.bin", 34, 0x200000),
    ("hc_attn_fn", "hc_attn_fn.he.bin", 8, 0x300000),
    ("gate", "gate.me.bin", 8, 0x400000),
)
PASS = re.compile(r"FULLSHAPE_WEIGHT_PASS sectors_per_word=(\d+) npc=(\d+) requests=(\d+) "
                  r"sectors=(\d+) reads=(\d+) wait_cycles=(\d+)")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(cmd: list[str], cwd: Path) -> str:
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=600)
    if p.returncode:
        raise RuntimeError(f"{cmd[0]} failed:\n{p.stdout[-3000:]}\n{p.stderr[-3000:]}")
    return p.stdout


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", type=Path, default=Path("/tmp/v41_fullshape_rank0_rom_images"))
    ap.add_argument("--scratch", type=Path, default=Path("/tmp/v41-fullshape-weight-window"))
    ap.add_argument("--output", type=Path,
                    default=ROOT / "results/rtl/hdc_v41x_fullshape_weight_hbm_window.json")
    args = ap.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["schema"] == "opentallas.v41x.fullshape.weight_layout.v1"
    assert manifest["layer"] == 0 and manifest["rank"] == 0
    rows = {}
    region_end = 0
    for name, image, sw, base in CASES:
        mat = manifest["matrices"][name]
        blob_path = args.images / image
        blob = blob_path.read_bytes()
        word_bytes = sw * 32
        if mat["output_image_sha256"] != hashlib.sha256(blob).hexdigest():
            raise RuntimeError(f"{image} differs from the source-pinned selected ROM image")
        if mat["output_image_bytes"] != len(blob) or len(blob) != mat["word_count"] * word_bytes:
            raise RuntimeError(f"{image} word geometry differs from the manifest")
        if base < region_end:
            raise RuntimeError(f"HBM weight regions overlap at {name}")
        region_end = base + mat["word_count"] * sw
        if region_end >= 1 << 28:
            raise RuntimeError(f"{name} HBM region exceeds this gate's address width")
        fixture = blob[:2 * word_bytes]
        d = args.scratch / name.replace(".", "_")
        d.mkdir(parents=True, exist_ok=True)
        sector_hex = d / "sectors.hex"
        sector_hex.write_text("\n".join(
            f"{int.from_bytes(fixture[i:i+32], 'little'):064x}"
            for i in range(0, len(fixture), 32)) + "\n")
        qe_unpack = None
        if mat["engine"] == "qe":
            # Reference follows the existing QE port: 32 byte code slots,
            # an unsigned 10-bit scale field (UE8M0 zero extended), and zeros.
            fp4 = mat["format"].startswith("F4_")
            expected = []
            lane_bytes = 17 if fp4 else 33
            for wi in range(2):
                lanes = bytearray()
                for lane in range(64):
                    off = wi * word_bytes + lane * lane_bytes
                    raw = fixture[off:off+lane_bytes]
                    if fp4:
                        codes = bytes(v for byte in raw[:16] for v in (byte & 15, byte >> 4))
                    else:
                        codes = raw[:32]
                    lanes.extend(codes + raw[-1:] + b"\x00")
                expected.append(f"{int.from_bytes(lanes, 'little'):0{len(lanes)*2}x}")
            exp = d / "qe_expected.hex"
            exp.write_text("\n".join(expected) + "\n")
            exe = d / "qe_unpack.vvp"
            run(["iverilog", "-g2012", "-s", "tb_hdc_v41x_qe_weight_unpack",
                 f"-Ptb_hdc_v41x_qe_weight_unpack.FP4={int(fp4)}", "-o", str(exe),
                 str(QE_UNPACK), str(QE_TB)], ROOT)
            log = run(["vvp", str(exe)], d)
            if f"QE_WEIGHT_UNPACK_PASS fp4={int(fp4)} words=2 lanes=64" not in log:
                raise RuntimeError(f"QE port conversion failed for {name}: {log[-3000:]}")
            qe_unpack = {"words_exact": 2, "lanes_per_word": 64,
                         "qe_port_bytes_per_word": 64 * 34,
                         "expected_qe_words_sha256": sha(exp),
                         "log_sha256": hashlib.sha256(log.encode()).hexdigest()}
        arms = {}
        for npc in (1, 4):
            exe = d / f"tb{npc}.vvp"
            run(["iverilog", "-g2012", "-s", "tb_hdc_v41x_weight_window_fullshape",
                 f"-Ptb_hdc_v41x_weight_window_fullshape.SW={sw}",
                 f"-Ptb_hdc_v41x_weight_window_fullshape.NPC={npc}",
                 f"-Ptb_hdc_v41x_weight_window_fullshape.HBM_BASE={base}",
                 "-o", str(exe), str(RTL), str(TB)], ROOT)
            out = run(["vvp", str(exe)], d)
            m = PASS.search(out)
            if not m:
                raise RuntimeError(f"no exact PASS for {name} npc={npc}: {out[-3000:]}")
            got_sw, got_npc, requests, sectors, reads, wait = map(int, m.groups())
            expected_requests = 2 * ((sw + 31) // 32)
            if (got_sw, got_npc, requests, sectors, reads) != (sw, npc, expected_requests, 2*sw, 3):
                raise RuntimeError(f"wrong HBM service coverage for {name} npc={npc}: {m.group(0)}")
            arms[str(npc)] = {"same_program_reads_exact": reads, "hbm_requests": requests,
                              "hbm_sectors": sectors, "window_wait_cycles": wait,
                              "sectors_per_wait_cycle": round(sectors / wait, 6),
                              "log_sha256": hashlib.sha256(out.encode()).hexdigest()}
        rows[name] = {"engine": mat["engine"], "format": mat["format"],
                      "image_sha256": sha(blob_path), "image_bytes": len(blob),
                      "word_bytes": word_bytes, "sectors_per_word": sw,
                      "full_region_hbm_start_sector": base,
                      "full_region_hbm_end_sector_exclusive": region_end,
                      "fixture_first_two_words_sha256": hashlib.sha256(fixture).hexdigest(),
                      "fixture_sector_hex_sha256": sha(sector_hex), "arms": arms,
                      "qe_port_unpack": qe_unpack}
    focused = {}
    for label, top, tb, expected in (
        ("segmented_bad_response", "tb_hdc_v41x_weight_window_segment_fault", FAULT_TB,
         "FULLSHAPE_WEIGHT_SEGMENT_FAULT_PASS"),
        ("legacy_small_window", "tb_hdc_v41x_weight_window", LEGACY_TB,
         "PASS v41x bounded HBM weight window"),
    ):
        exe = args.scratch / f"{label}.vvp"
        run(["iverilog", "-g2012", "-s", top, "-o", str(exe), str(RTL), str(tb)], ROOT)
        out = run(["vvp", str(exe)], ROOT)
        if expected not in out:
            raise RuntimeError(f"{label} missing PASS: {out[-3000:]}")
        focused[label] = {"pass": True, "log_sha256": hashlib.sha256(out.encode()).hexdigest()}
    record = {
        "schema": "opentallas.rtl.hdc_v41x_fullshape_weight_hbm_window.v1",
        "status": "pass",
        "claim_boundary": "Token-selected full-shape layer-0 rank-0 ROM weight bytes for one FP8 QE, one FP4 QE, one HE and one ME image. Two words per family; identical three-address ROM program in both modes. Behavioural 1/4-PC HBM sector service with reversed request and beat order. No full-shape engine execution, token/logit verdict, shared-controller contention, P&R or chip throughput claim.",
        "source_layout_commit": manifest["source_commit"],
        "source_layout_manifest_sha256": sha(MANIFEST),
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in
                          (RTL, TB, FAULT_TB, LEGACY_TB, QE_UNPACK, QE_TB,
                           Path(__file__).resolve())},
        "sector_bytes": 32, "max_request_sectors": 32,
        "rom_read_program_word_indices": [1, 0, 1], "weight_families": rows,
        "focused_checks": focused,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({n: {pc: a["window_wait_cycles"] for pc, a in r["arms"].items()}
                      for n, r in rows.items()}))


if __name__ == "__main__":
    main()
