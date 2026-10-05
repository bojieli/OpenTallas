#!/usr/bin/env python3
"""Progressive QK arithmetic ONLY from completed accepted OLD capture files.

No VM publication/retirement or full-flow claim; does not run or modify capture.
Reuses the independently checked integer routines from the accepted PV comparison.
"""
import argparse
import json
from pathlib import Path
import time
import numpy as np
from dsrom_i63_accepted_endpoint_compare import decode, iproduct, iadd, sha


def comparison(a, b):
    m = np.flatnonzero(a.ravel() != b.ravel())
    first = None
    if m.size:
        i = int(m[0])
        first = {"index": i, "head": i // 640, "row": i % 640,
                 "a": f"{int(a.ravel()[i]):08x}", "b": f"{int(b.ravel()[i]):08x}"}
    return {"compared": int(a.size), "mismatches": int(m.size), "first": first}


def run(root, out):
    start = time.monotonic()
    out.mkdir(exist_ok=False)
    paths = {n: root / "captured" / n for n in
             ("QK_accepted_q.u32", "QK_accepted_kv.u32", "QK_old_score.u32")}
    sizes = dict(zip(paths, (16384, 339200, 40960)))
    for n, p in paths.items():
        if p.stat().st_size != sizes[n]:
            raise ValueError(f"incomplete exact capture extent {n}")
    before = {n: sha(p) for n, p in paths.items()}
    q = np.fromfile(paths["QK_accepted_q.u32"], dtype="<u2").reshape(16, 512)
    kv = np.fromfile(paths["QK_accepted_kv.u32"], dtype="<u4")
    old = np.fromfile(paths["QK_old_score.u32"], dtype="<u4").reshape(640, 16).T.copy()
    ki, kg, faults, formats = decode(kv)
    if np.any(faults) or np.any(((q >> 7) & 255) == 255):
        raise ValueError("exceptional captured operands require explicit fault golden")
    integer, golden = np.zeros((16, 640), dtype=np.uint32), np.zeros((16, 640), dtype=np.uint32)
    stages = {"product_mismatches": 0, "chunk8_mismatches": 0,
              "tree_mismatches": 0, "integer_faults": 0}
    for h in range(16):
        products, bad = iproduct(q[h][None, :], ki)
        gf = (kg * (q[h].astype(np.uint32) << 16).view(np.float32)[None, :]).astype(np.float32)
        gf[gf == 0] = np.float32(0)
        stages["product_mismatches"] += int(np.count_nonzero(products != gf.view(np.uint32)))
        stages["integer_faults"] += int(np.count_nonzero(bad))
        products, gf = products.reshape(640, 64, 8), gf.reshape(640, 64, 8)
        chunks, gc = np.zeros((640, 64), dtype=np.uint32), np.zeros((640, 64), dtype=np.float32)
        for j in range(8):
            chunks, bad = iadd(chunks, products[:, :, j])
            stages["integer_faults"] += int(np.count_nonzero(bad))
            gc = (gc + gf[:, :, j]).astype(np.float32)
            gc[gc == 0] = np.float32(0)
        stages["chunk8_mismatches"] += int(np.count_nonzero(chunks != gc.view(np.uint32)))
        while chunks.shape[1] > 1:
            chunks, bad = iadd(chunks[:, 0::2], chunks[:, 1::2])
            stages["integer_faults"] += int(np.count_nonzero(bad))
            gc = (gc[:, 0::2] + gc[:, 1::2]).astype(np.float32)
            gc[gc == 0] = np.float32(0)
            stages["tree_mismatches"] += int(np.count_nonzero(chunks != gc.view(np.uint32)))
        integer[h], golden[h] = chunks[:, 0], gc[:, 0].view(np.uint32)
    after = {n: sha(p) for n, p in paths.items()}
    if before != after:
        raise ValueError("capture changed during arithmetic comparison")
    checks = {"integer_vs_golden": comparison(integer, golden),
              "integer_vs_old_score": comparison(integer, old),
              "golden_vs_old_score": comparison(golden, old),
              "dequant_mismatches": int(np.count_nonzero((ki.astype(np.uint32) << 16) != kg.view(np.uint32)))}
    integer.astype("<u4").tofile(out / "integer_QK.u32")
    golden.astype("<u4").tofile(out / "golden_QK.u32")
    record = {"scope": "Progressive SAME-input rank0 QK arithmetic only; OLD score complete; actual VM publication, SU/PV flow and original-run qualification unproven",
              "capture_root": str(root), "capture_sha256": before,
              "capture_source_sha256": sha(root / "source/capture.cpp"),
              "frozen_inputs_sha256": sha(root / "frozen_inputs.json"),
              "tool_sha256": sha(Path(__file__)),
              "integer_helper_sha256": sha(Path(__file__).with_name("dsrom_i63_accepted_endpoint_compare.py")),
              "heads": 16, "rows": 640, "dimensions": 512, "products": 5242880,
              "chunk_size": 8, "chunks": 64, "fp4_rows_by_group": formats,
              "checks": checks, "stage_checks": stages,
              "actual_vm_publication_qualified": False, "full_stage_flow_qualified": False,
              "original_full_run_qualified": False, "elapsed_seconds": time.monotonic() - start,
              "verdict": "PASS" if checks["dequant_mismatches"] == 0 and not any(stages.values()) and all(checks[n]["mismatches"] == 0 for n in ("integer_vs_golden", "integer_vs_old_score", "golden_vs_old_score")) else "FAIL"}
    (out / "record.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))
    return 0 if record["verdict"] == "PASS" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.capture_root, args.out))
