#!/usr/bin/env python3
"""Gate active Qwen INT8 scale ports and count shipped layer-0 accesses."""
import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RTL = [ROOT / p for p in (
    "rtl/hdc/ot_hdc_matvec.sv", "rtl/hdc/ot_hdc_fpu.sv",
    "rtl/hdc/ot_hdc_fp32_mul_pipe.sv", "rtl/hdc/ot_hdc_fastfp.sv",
    "rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_sfu.sv",
    "rtl/proto/ot_fp32_add_rne_pipe.sv",
)]
TB = [ROOT / p for p in (
    "rtl/test/tb_hdc_qwen_int8_matvec.sv",
    "rtl/test/tb_hdc_qwen_scale_mask_nonpower.sv",
)]
OUT = ROOT / "results/rtl/hdc_qwen_scale_mask.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def layer0_counts(manifest):
    image = json.loads(manifest.read_text())
    if image["status"] != "image_and_isa_emitted" or image["matrix_word_bits"] != 6144 * 16 * 8:
        raise ValueError("unexpected shipped layer-0 matrix image")
    groups, lanes, interleave = 6144, 16, 8
    rows = []
    for m in image["matrix_layout"]:
        per_round = groups // m["split"]
        base = m["rounds"] * interleave * groups
        active = sum(
            r * per_round * lanes * interleave + j * lanes + g * lanes * interleave < m["rows"]
            for r in range(m["rounds"])
            for j in range(interleave)
            for g in range(per_round)
        )
        rows.append({"matrix": m["name"], "all_group_reads": base,
                     "active_group_reads": active, "suppressed_group_reads": base - active})
    total = {name: sum(row[name] for row in rows) for name in
             ("all_group_reads", "active_group_reads", "suppressed_group_reads")}
    return {"checkpoint_revision": image["checkpoint_revision"],
            "emitted_manifest_sha256": sha(manifest), "matrices": rows, "total": total}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layer0-manifest", type=Path)
    args = ap.parse_args()
    outputs = {}
    with tempfile.TemporaryDirectory(prefix="qwen-scale-mask-") as tmp:
        for split in (0, 1):
            binary = Path(tmp) / f"split{split}.vvp"
            subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_qwen_int8_matvec",
                            f"-Ptb_hdc_qwen_int8_matvec.SPLIT={split}", "-o", str(binary),
                            str(TB[0]), *map(str, RTL)], cwd=ROOT, check=True)
            cp = subprocess.run(["vvp", str(binary)], cwd=ROOT,
                                capture_output=True, text=True, check=True)
            if f"PASS Qwen INT8 matvec split={split}" not in cp.stdout:
                raise RuntimeError(cp.stdout)
            outputs[f"split{split}"] = cp.stdout.strip()
        binary = Path(tmp) / "nonpower.vvp"
        subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_qwen_scale_mask_nonpower",
                        "-o", str(binary), str(TB[1]), *map(str, RTL)], cwd=ROOT, check=True)
        cp = subprocess.run(["vvp", str(binary)], cwd=ROOT,
                            capture_output=True, text=True, check=True)
        if "PASS Qwen scale mask: G6/S4" not in cp.stdout:
            raise RuntimeError(cp.stdout)
        outputs["nonpower_split"] = cp.stdout.strip()
        subprocess.run(["verilator", "--lint-only", "-Wno-fatal", "-Wno-WIDTH",
                        "-Wno-TIMESCALEMOD", "--top-module", "ot_hdc_matvec",
                        "-GG=6", "-GW=2", "-GINT8_WEIGHT=1", *map(str, RTL)],
                       cwd=ROOT, capture_output=True, text=True, check=True)
    record = {"schema": "opentallas.qwen-scale-mask.v1", "status": "pass",
              "gates": outputs,
              "source_sha256": {str(p.relative_to(ROOT)): sha(p)
                                for p in [*RTL, *TB, Path(__file__)]},
              "claim_boundary": "Reduced G2/G6 INT8 RTL scale-read and fault masks; active real-layer "
                                "accesses are derived from the emitter's matrix geometry. No ROM macro "
                                "power, full G6144 RTL elaboration, route, or full-shape token is measured."}
    if args.layer0_manifest:
        record["layer0_access_sensitivity"] = layer0_counts(args.layer0_manifest)
    OUT.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    for value in outputs.values():
        print(value)
    if args.layer0_manifest:
        print("active group reads", record["layer0_access_sensitivity"]["total"])


if __name__ == "__main__":
    main()
